# GitOps Policy CI Flow

Automated policy enforcement for Kubernetes manifests in a GitOps workflow using OPA (Open Policy Agent).

## Features

- **Three-Level Enforcement**: RECOMMEND → WARNING → BLOCKING policies with date-based progression
- **Parallel Builds**: Matrix strategy builds all service × environment combinations simultaneously
- **Smart CI Checks**: Separate required (blocking) and advisory (warnings/recommendations) checks
- **Automatic PR Reports**: Concise reports with expandable sections for details
- **Override Support**: Policy-specific override comments for exceptions
- **Local Testing**: Test policies locally before pushing

## Quick Start

### Testing Locally

```bash
# Install Python dependencies first
pip install -r requirements.txt

# Test a specific service/environment against a policy
python scripts/test-policy-local.py my-app stg policies/ha.opa

# Or test all policies
for policy in policies/*.opa; do
  echo "Testing $policy"
  python scripts/test-policy-local.py my-app stg "$policy"
done
```

### Adding a New Service

```bash
# Create service structure
mkdir -p manifests/services/my-new-service/{base,environments/{stg,prod,sandbox}}

# Add base manifests
cp -r manifests/services/my-app/base/* manifests/services/my-new-service/base/

# Add environment overlays
# ... customize for each environment
```

### Adding a New Policy

1. Create `.opa` file in `policies/` directory:

```rego
package kustomization.mypolicy

import rego.v1

deny contains msg if {
    input.request.kind.kind == "Deployment"
    # Your conditions here
    msg := "Violation message"
}
```

2. Register in `policies/compliance-config.yaml`:

```yaml
policies:
  my-policy:
    name: My Policy Name
    description: What this policy checks
    type: opa
    filePath: mypolicy.opa
    enforcement:
      inEffectAfter: 2025-11-01T00:00:00Z
      isWarningAfter: 2026-01-01T00:00:00Z
      isBlockingAfter: 2026-03-01T00:00:00Z
      override:
        comment: "/sp-override-mypolicy"
```

## How It Works

See [.github/CI-SETUP.md](.github/CI-SETUP.md) for detailed CI architecture.

**Short version:**
1. PR opened → detect changed services
2. Build all overlays (stg/prod/sandbox) in parallel with kustomize
3. Evaluate against OPA policies with time-based enforcement levels
4. Two CI checks: one required (BLOCKING only), one advisory (all levels)
5. Generate markdown report and post to PR

## Project Structure

```
.
├── .github/
│   ├── workflows/
│   │   └── policy-check.yml          # Main CI workflow
│   └── scripts/
│       ├── evaluate-policies.sh      # OPA evaluation logic
│       └── generate-report.sh        # Report generation
├── manifests/
│   └── services/
│       └── <service>/
│           ├── base/                 # Base Kustomize resources
│           └── environments/
│               ├── stg/              # Staging overlay
│               ├── prod/             # Production overlay
│               └── sandbox/          # Sandbox overlay
├── policies/
│   ├── compliance-config.yaml        # Policy definitions & enforcement
│   ├── ha.opa                        # High availability policy
│   └── ingress-tls.opa              # Ingress TLS policy
└── scripts/
    └── test-policy-local.sh          # Local policy testing
```

## Enforcement Levels

| Level | CI Fails? | PR Blocks? | Override? |
|-------|-----------|------------|-----------|
| **RECOMMEND** | ❌ No | ❌ No | N/A |
| **WARNING** | ✅ Yes | ❌ No | ✅ Yes |
| **BLOCKING** | ✅ Yes | ✅ Yes | ✅ Yes |

Enforcement progresses based on dates in `compliance-config.yaml`:
- Before `inEffectAfter`: Policy is inactive
- After `inEffectAfter`: RECOMMEND level
- After `isWarningAfter`: WARNING level
- After `isBlockingAfter`: BLOCKING level

## Examples

### Policy Override

To override a policy violation, add the override comment from the policy config:

```
/sp-override-ha
```

This will skip the `service-high-availability` policy for that PR.

### Policy Result Example

When violations are found:

```
## 🔍 Policy Compliance Report

**Status:** 🚫 **BLOCKED**

---

### 🚫 Blocking Issues (1)

#### ❌ Service High Availability
- **Resource:** `Deployment/my-app`
- **Manifest:** `my-app-prod`
- **Violations:**
  - Deployment 'my-app' must have at least 2 replicas for high availability, found: 1
```

## Tips

- Use `sandbox` environment for relaxed policies (lower resource limits, single replicas)
- Set progressive dates in policy config to give teams time to adapt
- Keep policies focused on one concern per file
- Write helper functions in Rego to keep deny rules readable
- Test policies locally before pushing to avoid CI churn

## License

MIT
