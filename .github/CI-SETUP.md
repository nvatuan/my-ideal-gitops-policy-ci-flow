# GitOps Policy CI Setup

## Overview

This CI system evaluates Kubernetes manifests against OPA policies with three enforcement levels:
- **RECOMMEND**: Adds PR comment, doesn't fail CI
- **WARNING**: Adds PR comment, fails CI check (can override)
- **BLOCKING**: Adds PR comment, fails required CI check, prevents merge

## Architecture

### Jobs

1. **detect-changes**: Finds which services changed in `manifests/services/`
2. **build-manifests**: Runs `kustomize build` for each service × environment (stg/prod/sandbox) in parallel matrix
3. **policy-check-blocking**: Evaluates only BLOCKING policies (required check)
4. **policy-check-advisory**: Evaluates all policy levels (non-required check)
5. **report**: Generates and posts markdown report to PR

### Scripts

- **evaluate-policies.py**: 
  - Parses `compliance-config.yaml` to determine enforcement levels based on dates
  - Runs OPA eval against each resource in built manifests
  - Outputs JSON results
  - Written in Python for better maintainability and error handling

- **generate-report.py**:
  - Reads policy results JSON
  - Generates markdown report with violations grouped by level
  - Uses collapsible sections for recommendations and passed checks
  - Written in Python with structured classes

## Policy Configuration

Policies are defined in `policies/compliance-config.yaml`:

```yaml
policies:
  policy-key:
    name: Human Readable Name
    type: opa
    filePath: policy.opa
    enforcement:
      inEffectAfter: 2025-11-11T00:00:00Z    # When policy starts
      isWarningAfter: 2026-01-14T00:00:00Z   # Escalates to WARNING
      isBlockingAfter: 2025-02-14T00:00:00Z  # Escalates to BLOCKING
      override:
        comment: "/sp-override-policy-key"   # PR comment to skip
```

## OPA Policy Format

Policies should use the `deny` pattern:

```rego
package kustomization.mypolicy

import rego.v1

deny contains msg if {
    input.request.kind.kind == "Deployment"
    # ... conditions ...
    msg := "Violation message"
}
```

## Testing Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Test with the helper script
python scripts/test-policy-local.py my-app stg policies/ha.opa

# Or manually:
# Build manifests
kustomize build manifests/services/my-app/environments/stg > test.yaml

# Test policy with Python
python .github/scripts/evaluate-policies.py all . policies/compliance-config.yaml policies/
```

## Adding New Policies

1. Create `.opa` file in `policies/`
2. Add entry to `policies/compliance-config.yaml`
3. Set enforcement dates
4. PR changes - CI will automatically pick up new policy

