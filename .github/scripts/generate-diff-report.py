#!/usr/bin/env python3
"""
Manifest Diff Report Generator
Generates a markdown report showing differences between before/after manifests.
"""

import difflib
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class DiffReportGenerator:
    def __init__(self, before_dir: str, after_dir: str):
        self.before_dir = Path(before_dir)
        self.after_dir = Path(after_dir)
    
    def get_manifest_pairs(self) -> List[Tuple[str, Path, Path]]:
        """Get pairs of before/after manifest files."""
        pairs = []
        
        # Get all YAML files from after directory
        after_files = {f.name: f for f in self.after_dir.glob("*.yaml")}
        before_files = {f.name: f for f in self.before_dir.glob("*.yaml")}
        
        # All files that exist in after (including new ones)
        all_files = set(after_files.keys()) | set(before_files.keys())
        
        for filename in sorted(all_files):
            before_path = before_files.get(filename)
            after_path = after_files.get(filename)
            
            # Create empty Path for missing files
            if before_path is None:
                before_path = Path("/dev/null")
            if after_path is None:
                after_path = Path("/dev/null")
            
            pairs.append((filename, before_path, after_path))
        
        return pairs
    
    def read_file(self, path: Path) -> List[str]:
        """Read file and return lines, or empty list if file doesn't exist."""
        if not path.exists() or str(path) == "/dev/null":
            return []
        
        with open(path) as f:
            return f.readlines()
    
    def generate_diff(self, before_lines: List[str], after_lines: List[str], 
                     filename: str) -> Tuple[str, int, int]:
        """Generate unified diff and count changes."""
        diff = list(difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"before/{filename}",
            tofile=f"after/{filename}",
            lineterm=''
        ))
        
        additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
        
        return '\n'.join(diff), additions, deletions
    
    def classify_change(self, before_exists: bool, after_exists: bool, 
                       additions: int, deletions: int) -> str:
        """Classify the type of change."""
        if not before_exists and after_exists:
            return "🆕 New"
        elif before_exists and not after_exists:
            return "🗑️ Deleted"
        elif additions == 0 and deletions == 0:
            return "✅ No Change"
        else:
            return "✏️ Modified"
    
    def generate_summary_table(self, changes: List[Dict]) -> List[str]:
        """Generate summary table of changes."""
        lines = []
        lines.append("| Service | Environment | Status | Changes |")
        lines.append("|---------|-------------|--------|---------|")
        
        for change in changes:
            filename = change['filename']
            # Parse filename: service-environment.yaml
            parts = filename.replace('.yaml', '').rsplit('-', 1)
            if len(parts) == 2:
                service, env = parts
            else:
                service = parts[0]
                env = "unknown"
            
            status = change['status']
            additions = change['additions']
            deletions = change['deletions']
            
            changes_str = ""
            if additions > 0 or deletions > 0:
                changes_str = f"+{additions} -{deletions}"
            
            lines.append(f"| `{service}` | `{env}` | {status} | {changes_str} |")
        
        return lines
    
    def generate(self) -> str:
        """Generate the full diff report."""
        lines = []
        
        # Header
        lines.append("## 📊 Manifest Changes")
        lines.append("")
        lines.append("This report shows the differences between the current state (base branch) and the proposed changes (PR branch).")
        lines.append("")
        
        # Get all manifest pairs
        pairs = self.get_manifest_pairs()
        
        if not pairs:
            lines.append("⚠️ No manifest files found.")
            return '\n'.join(lines)
        
        # Process each pair
        changes = []
        detailed_diffs = []
        
        for filename, before_path, after_path in pairs:
            before_exists = before_path.exists() and str(before_path) != "/dev/null"
            after_exists = after_path.exists() and str(after_path) != "/dev/null"
            
            before_lines = self.read_file(before_path)
            after_lines = self.read_file(after_path)
            
            diff_text, additions, deletions = self.generate_diff(
                before_lines, after_lines, filename
            )
            
            status = self.classify_change(before_exists, after_exists, additions, deletions)
            
            changes.append({
                'filename': filename,
                'status': status,
                'additions': additions,
                'deletions': deletions,
                'diff': diff_text,
                'has_changes': additions > 0 or deletions > 0 or not before_exists or not after_exists
            })
        
        # Summary section
        lines.append("### Summary")
        lines.append("")
        total_files = len(changes)
        changed_files = sum(1 for c in changes if c['has_changes'])
        new_files = sum(1 for c in changes if c['status'] == "🆕 New")
        deleted_files = sum(1 for c in changes if c['status'] == "🗑️ Deleted")
        modified_files = sum(1 for c in changes if c['status'] == "✏️ Modified")
        
        lines.append(f"- **Total manifests:** {total_files}")
        lines.append(f"- **Changed:** {changed_files}")
        lines.append(f"  - New: {new_files}")
        lines.append(f"  - Modified: {modified_files}")
        lines.append(f"  - Deleted: {deleted_files}")
        lines.append("")
        
        # Summary table
        lines.extend(self.generate_summary_table(changes))
        lines.append("")
        
        # Detailed diffs
        has_diffs = any(c['has_changes'] for c in changes)
        
        if has_diffs:
            lines.append("<details>")
            lines.append("<summary>📝 Detailed Diffs - Click to expand</summary>")
            lines.append("")
            
            for change in changes:
                if not change['has_changes']:
                    continue
                
                lines.append(f"### {change['filename']}")
                lines.append("")
                lines.append(f"**Status:** {change['status']}")
                
                if change['additions'] > 0 or change['deletions'] > 0:
                    lines.append(f"**Changes:** +{change['additions']} -{change['deletions']}")
                
                lines.append("")
                
                if change['diff']:
                    lines.append("```diff")
                    lines.append(change['diff'])
                    lines.append("```")
                elif change['status'] == "🆕 New":
                    lines.append("_New file created_")
                elif change['status'] == "🗑️ Deleted":
                    lines.append("_File deleted_")
                
                lines.append("")
            
            lines.append("</details>")
        
        # Footer
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("<sub>🤖 This diff is automatically generated. Review carefully before merging.</sub>")
        
        return '\n'.join(lines)


def main():
    if len(sys.argv) != 3:
        print("Usage: generate-diff-report.py <before_dir> <after_dir>")
        sys.exit(1)
    
    before_dir, after_dir = sys.argv[1:3]
    
    generator = DiffReportGenerator(before_dir, after_dir)
    report = generator.generate()
    print(report)


if __name__ == "__main__":
    main()

