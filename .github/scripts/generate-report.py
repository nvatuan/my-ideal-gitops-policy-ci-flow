#!/usr/bin/env python3
"""
Policy Report Generator
Generates a markdown report from policy evaluation results.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


class ReportGenerator:
    def __init__(self, results_file: str):
        self.results_file = Path(results_file)
        
        if not self.results_file.exists():
            self.results = {"results": []}
        else:
            with open(self.results_file) as f:
                self.results = json.load(f)
    
    def count_by_level_and_status(self) -> Dict[str, int]:
        """Count results by level and pass/fail status."""
        counts = defaultdict(int)
        
        for result in self.results.get("results", []):
            level = result.get("level", "UNKNOWN")
            passed = result.get("passed", True)
            
            if not passed:
                counts[f"{level}_failed"] += 1
            else:
                counts["passed"] += 1
            
            counts["total"] += 1
        
        return counts
    
    def get_status_badge(self, counts: Dict[str, int]) -> tuple[str, str]:
        """Determine overall status and badge."""
        if counts.get("BLOCKING_failed", 0) > 0:
            return "🚫 **BLOCKED**", "red"
        elif counts.get("WARNING_failed", 0) > 0:
            return "⚠️ **WARNING**", "orange"
        elif counts.get("RECOMMEND_failed", 0) > 0:
            return "💡 **RECOMMENDATIONS**", "yellow"
        else:
            return "✅ **PASSED**", "green"
    
    def format_violations_section(self, level: str, emoji: str, title: str, description: str) -> List[str]:
        """Format a section for violations of a specific level."""
        lines = []
        violations = [r for r in self.results.get("results", []) 
                     if r.get("level") == level and not r.get("passed", True)]
        
        if not violations:
            return lines
        
        lines.append(f"### {emoji} {title} ({len(violations)})")
        lines.append("")
        lines.append(description)
        lines.append("")
        
        for result in violations:
            policy_name = result.get("policyName", "Unknown Policy")
            resource = result.get("resource", {})
            manifest = result.get("manifest", "unknown")
            violation_msgs = result.get("violations", [])
            
            lines.append(f"#### {emoji} {policy_name}")
            lines.append(f"- **Resource:** `{resource.get('kind', 'Unknown')}/{resource.get('name', 'unknown')}`")
            lines.append(f"- **Manifest:** `{manifest}`")
            
            if violation_msgs:
                lines.append("- **Violations:**")
                for msg in violation_msgs:
                    lines.append(f"  - {msg}")
            
            lines.append("")
        
        return lines
    
    def format_passed_checks(self, max_display: int = 20) -> List[str]:
        """Format the passed checks section."""
        lines = []
        passed = [r for r in self.results.get("results", []) 
                 if r.get("passed", True)]
        
        if not passed:
            return lines
        
        lines.append("<details>")
        lines.append(f"<summary>✅ Passed Checks ({len(passed)}) - Click to expand</summary>")
        lines.append("")
        
        for i, result in enumerate(passed):
            if i >= max_display:
                remaining = len(passed) - max_display
                lines.append("")
                lines.append(f"_... and {remaining} more_")
                break
            
            policy_name = result.get("policyName", "Unknown Policy")
            resource = result.get("resource", {})
            manifest = result.get("manifest", "unknown")
            
            lines.append(f"- **{policy_name}** ✓ `{resource.get('kind', 'Unknown')}/{resource.get('name', 'unknown')}` in `{manifest}`")
        
        lines.append("")
        lines.append("</details>")
        
        return lines
    
    def generate(self) -> str:
        """Generate the full markdown report."""
        lines = []
        counts = self.count_by_level_and_status()
        status, _ = self.get_status_badge(counts)
        
        # Header
        lines.append("## 🔍 Policy Compliance Report")
        lines.append("")
        lines.append(f"**Status:** {status}")
        lines.append("")
        lines.append(f"**Summary:** {counts.get('passed', 0)}/{counts.get('total', 0)} checks passed")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Blocking issues
        blocking_lines = self.format_violations_section(
            "BLOCKING",
            "🚫",
            "Blocking Issues",
            "These violations must be fixed before merging."
        )
        lines.extend(blocking_lines)
        
        # Warnings
        warning_lines = self.format_violations_section(
            "WARNING",
            "⚠️",
            "Warnings",
            "These violations cause CI to fail but can be overridden."
        )
        lines.extend(warning_lines)
        
        # Recommendations (in collapsible section)
        recommend_violations = [r for r in self.results.get("results", []) 
                               if r.get("level") == "RECOMMEND" and not r.get("passed", True)]
        
        if recommend_violations:
            lines.append("<details>")
            lines.append(f"<summary>💡 Recommendations ({len(recommend_violations)}) - Click to expand</summary>")
            lines.append("")
            lines.append("These are suggestions for improvement and don't block merging.")
            lines.append("")
            
            for result in recommend_violations:
                policy_name = result.get("policyName", "Unknown Policy")
                resource = result.get("resource", {})
                manifest = result.get("manifest", "unknown")
                violation_msgs = result.get("violations", [])
                
                lines.append(f"#### 💡 {policy_name}")
                lines.append(f"- **Resource:** `{resource.get('kind', 'Unknown')}/{resource.get('name', 'unknown')}`")
                lines.append(f"- **Manifest:** `{manifest}`")
                
                if violation_msgs:
                    lines.append("- **Violations:**")
                    for msg in violation_msgs:
                        lines.append(f"  - {msg}")
                
                lines.append("")
            
            lines.append("</details>")
            lines.append("")
        
        # Passed checks
        passed_lines = self.format_passed_checks()
        lines.extend(passed_lines)
        
        # Footer
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("<sub>🤖 This report is automatically generated. To override a policy, use the override comment specified in the policy configuration.</sub>")
        
        return "\n".join(lines)


def main():
    if len(sys.argv) != 2:
        print("Usage: generate-report.py <results_file>")
        sys.exit(1)
    
    results_file = sys.argv[1]
    
    generator = ReportGenerator(results_file)
    report = generator.generate()
    print(report)


if __name__ == "__main__":
    main()

