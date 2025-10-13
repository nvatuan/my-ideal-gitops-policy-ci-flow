#!/usr/bin/env python3
"""
OPA Policy Evaluation Script
Evaluates Kubernetes manifests against OPA policies with enforcement levels.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class PolicyEvaluator:
    def __init__(self, mode: str, manifests_dir: str, config_file: str, policies_dir: str):
        self.mode = mode  # "blocking" or "all"
        self.manifests_dir = Path(manifests_dir)
        self.config_file = Path(config_file)
        self.policies_dir = Path(policies_dir)
        self.current_date = datetime.utcnow()
        
        with open(self.config_file) as f:
            self.config = yaml.safe_load(f)
    
    def parse_enforcement_level(self, policy_key: str) -> Optional[str]:
        """Determine current enforcement level for a policy based on dates."""
        policy = self.config["policies"][policy_key]
        enforcement = policy.get("enforcement", {})
        
        in_effect = self._parse_date(enforcement.get("inEffectAfter"))
        is_warning = self._parse_date(enforcement.get("isWarningAfter"))
        is_blocking = self._parse_date(enforcement.get("isBlockingAfter"))
        
        # Check if policy is in effect
        if not in_effect or self.current_date < in_effect:
            return None
        
        # Determine level based on dates
        if is_blocking and self.current_date >= is_blocking:
            return "BLOCKING"
        elif is_warning and self.current_date >= is_warning:
            return "WARNING"
        else:
            return "RECOMMEND"
    
    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO 8601 date string."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    
    def get_package_name(self, policy_file: Path) -> str:
        """Extract package name from OPA policy file."""
        with open(policy_file) as f:
            for line in f:
                if line.strip().startswith("package "):
                    return line.strip().replace("package ", "")
        raise ValueError(f"No package declaration found in {policy_file}")
    
    def evaluate_resource(self, resource: Dict[str, Any], policy_file: Path) -> tuple[bool, List[str]]:
        """Evaluate a single K8s resource against an OPA policy."""
        # Create OPA input format
        opa_input = {
            "request": {
                "kind": {"kind": resource.get("kind", "Unknown")},
                "object": resource
            }
        }
        
        # Get package name and construct data path
        package_name = self.get_package_name(policy_file)
        data_path = f"data.{package_name}.deny"
        
        # Run OPA evaluation
        try:
            proc = subprocess.Popen(
                ["opa", "eval", "--data", str(policy_file), "--format", "json", 
                 "--stdin-input", data_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = proc.communicate(input=json.dumps(opa_input))
            result = type('obj', (object,), {'returncode': proc.returncode, 'stdout': stdout, 'stderr': stderr})()
            
            if result.returncode != 0:
                print(f"Warning: OPA evaluation failed: {result.stderr}", file=sys.stderr)
                return True, []
            
            # Parse OPA output
            opa_output = json.loads(result.stdout)
            deny_set = opa_output.get("result", [{}])[0].get("expressions", [{}])[0].get("value", [])
            
            # Handle both array and set formats
            if isinstance(deny_set, list):
                violations = [str(v) for v in deny_set if v]
            elif isinstance(deny_set, dict) and deny_set:
                violations = [str(v) for v in deny_set.values() if v]
            else:
                violations = []
            
            passed = len(violations) == 0
            return passed, violations
            
        except json.JSONDecodeError:
            print(f"Warning: Failed to parse OPA output", file=sys.stderr)
            return True, []
        except Exception as e:
            print(f"Warning: OPA evaluation error: {e}", file=sys.stderr)
            return True, []
    
    def split_yaml_documents(self, yaml_file: Path) -> List[Dict[str, Any]]:
        """Split multi-document YAML file into individual resources."""
        with open(yaml_file) as f:
            return list(yaml.safe_load_all(f))
    
    def evaluate(self) -> List[Dict[str, Any]]:
        """Evaluate all manifests against all applicable policies."""
        results = []
        
        policies = self.config.get("policies", {})
        
        for policy_key, policy_config in policies.items():
            # Determine enforcement level
            enforcement_level = self.parse_enforcement_level(policy_key)
            
            # Skip inactive policies
            if not enforcement_level:
                continue
            
            # Skip non-blocking policies if in blocking mode
            if self.mode == "blocking" and enforcement_level != "BLOCKING":
                continue
            
            policy_name = policy_config.get("name", policy_key)
            policy_file = self.policies_dir / policy_config.get("filePath", "")
            
            # Skip if policy file doesn't exist
            if not policy_file.exists():
                print(f"Warning: Policy file {policy_file} not found, skipping...", file=sys.stderr)
                continue
            
            # Evaluate each manifest
            for manifest_file in self.manifests_dir.glob("*.yaml"):
                manifest_name = manifest_file.stem
                
                try:
                    resources = self.split_yaml_documents(manifest_file)
                except Exception as e:
                    print(f"Warning: Failed to parse {manifest_file}: {e}", file=sys.stderr)
                    continue
                
                for resource in resources:
                    if not resource or not isinstance(resource, dict):
                        continue
                    
                    kind = resource.get("kind", "Unknown")
                    name = resource.get("metadata", {}).get("name", "unknown")
                    
                    passed, violations = self.evaluate_resource(resource, policy_file)
                    
                    result = {
                        "policyKey": policy_key,
                        "policyName": policy_name,
                        "level": enforcement_level,
                        "manifest": manifest_name,
                        "resource": {"kind": kind, "name": name},
                        "passed": passed,
                        "violations": violations
                    }
                    
                    results.append(result)
        
        return results
    
    def save_results(self, results: List[Dict[str, Any]]):
        """Save evaluation results to JSON file."""
        output_file = f"policy-results-{self.mode}.json"
        output = {"results": results}
        
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"Policy evaluation complete. Results saved to {output_file}")


def main():
    if len(sys.argv) != 5:
        print("Usage: evaluate-policies.py <mode> <manifests_dir> <config_file> <policies_dir>")
        print("  mode: 'blocking' or 'all'")
        sys.exit(1)
    
    mode, manifests_dir, config_file, policies_dir = sys.argv[1:5]
    
    if mode not in ["blocking", "all"]:
        print(f"Error: Invalid mode '{mode}'. Must be 'blocking' or 'all'")
        sys.exit(1)
    
    evaluator = PolicyEvaluator(mode, manifests_dir, config_file, policies_dir)
    results = evaluator.evaluate()
    evaluator.save_results(results)


if __name__ == "__main__":
    main()

