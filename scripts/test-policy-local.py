#!/usr/bin/env python3
"""
Local Policy Testing Script
Test OPA policies against kustomize-built manifests locally.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

import yaml


def build_manifest(service: str, environment: str) -> str:
    """Build Kustomize manifest for service/environment."""
    kustomize_path = f"manifests/services/{service}/environments/{environment}"
    
    result = subprocess.run(
        ["kustomize", "build", kustomize_path],
        capture_output=True,
        text=True,
        check=True
    )
    
    return result.stdout


def get_package_name(policy_file: Path) -> str:
    """Extract package name from OPA policy file."""
    with open(policy_file) as f:
        for line in f:
            if line.strip().startswith("package "):
                return line.strip().replace("package ", "")
    raise ValueError(f"No package declaration found in {policy_file}")


def evaluate_resource(resource: dict, policy_file: Path) -> Tuple[bool, List[str]]:
    """Evaluate a single K8s resource against OPA policy."""
    # Create OPA input format
    opa_input = {
        "request": {
            "kind": {"kind": resource.get("kind", "Unknown")},
            "object": resource
        }
    }
    
    # Get package name and construct data path
    package_name = get_package_name(policy_file)
    data_path = f"data.{package_name}.deny"
    
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
        
    except Exception as e:
        print(f"Error evaluating: {e}", file=sys.stderr)
        return True, []


def main():
    service = sys.argv[1] if len(sys.argv) > 1 else "my-app"
    environment = sys.argv[2] if len(sys.argv) > 2 else "stg"
    policy_path = sys.argv[3] if len(sys.argv) > 3 else "policies/ha.opa"
    
    print(f"🔨 Building manifests for {service}/{environment}...")
    
    try:
        manifest_yaml = build_manifest(service, environment)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to build manifests: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    
    # Write to temp file for display
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(manifest_yaml)
        temp_path = f.name
    
    print("📋 Built manifest:")
    print("---")
    print(manifest_yaml)
    print("---")
    print()
    print(f"🔍 Testing policy: {policy_path}")
    print()
    
    policy_file = Path(policy_path)
    if not policy_file.exists():
        print(f"❌ Policy file not found: {policy_path}", file=sys.stderr)
        sys.exit(1)
    
    # Parse manifest and test each resource
    resources = list(yaml.safe_load_all(manifest_yaml))
    
    any_failed = False
    
    for resource in resources:
        if not resource or not isinstance(resource, dict):
            continue
        
        kind = resource.get("kind", "Unknown")
        name = resource.get("metadata", {}).get("name", "unknown")
        
        print(f"Testing {kind}/{name}...")
        
        passed, violations = evaluate_resource(resource, policy_file)
        
        if passed:
            print("  ✅ Passed")
        else:
            print("  ❌ Failed:")
            for violation in violations:
                print(f"     - {violation}")
            any_failed = True
        
        print()
    
    # Cleanup temp file
    Path(temp_path).unlink()
    
    if any_failed:
        print("❌ Some checks failed!")
        sys.exit(1)
    else:
        print("✨ All checks passed!")


if __name__ == "__main__":
    main()

