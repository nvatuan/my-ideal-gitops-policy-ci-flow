# Workflows

GitOps Policy CI system with modular workflow design for parallel execution.

## Workflow Architecture

```
┌─────────────────────────────────┐
│  P01: Kustomize Build           │
│  - Detect changed services      │
│  - Build before/after manifests │
│  - Upload artifacts             │
└────────────┬────────────────────┘
             │
             ├──────────────┬──────────────┐
             ▼              ▼              ▼
    ┌────────────────┐ ┌─────────────┐ ┌──────────────┐
    │ P02: Diff      │ │ P02: Policy │ │  (Future)    │
    │ Commenter      │ │ Evaluation  │ │   MINT       │
    └────────────────┘ └─────────────┘ └──────────────┘
```

## Workflows

### p01-kustomize-build.yml
**Purpose:** Detect changes and build manifests

**Triggers:** On pull_request to main branch when manifests/services/** or policies/** change

**Jobs:**
1. `detect-changes` - Finds which services changed in the PR
2. `build-before-after` - Matrix job that builds manifests for:
   - Each changed service
   - Each environment (stg/prod/sandbox)
   - Before (base branch) and After (PR branch)
3. `build-complete` - Validation that all builds succeeded

**Outputs:**
- Artifacts: `before-{service}-{env}` and `after-{service}-{env}`
- Each artifact contains the built Kustomize manifest YAML

### p02-diff-commenter.yml
**Purpose:** Generate and post manifest diffs to PR

**Triggers:** `workflow_run` after p01-kustomize-build completes

**Jobs:**
1. Downloads before/after artifacts from P01
2. Generates unified diff report showing:
   - Summary table (service, env, status, changes)
   - Detailed diffs in collapsible section
   - Statistics (new/modified/deleted files)
3. Posts comment to PR (removes old comment first)

**Script:** `.github/scripts/generate-diff-report.py`

### p02-policy-eval.yml
**Purpose:** Evaluate OPA policies against manifests

**Triggers:** `workflow_run` after p01-kustomize-build completes

**Jobs:**
1. `policy-check-blocking` - Evaluates BLOCKING level policies (required check)
2. `policy-check-advisory` - Evaluates all policy levels (continues on error)
3. `report` - Generates and posts policy compliance report to PR

**Scripts:**
- `.github/scripts/evaluate-policies.py` - OPA policy evaluator
- `.github/scripts/generate-report.py` - Report generator

## Benefits of Modular Design

1. **Parallel Execution**: P02 jobs run in parallel after P01 completes
2. **Independent Failures**: Diff comment can succeed even if policy check fails
3. **Reusability**: P01 artifacts can be used by future workflows (MINT integration)
4. **Clear Separation**: Each workflow has a single responsibility
5. **Scalability**: Easy to add new P02 workflows without modifying P01

## Legacy Workflows

- `policy-check.yml` - Original monolithic workflow (kept for reference)
  - Combined all steps in one workflow
  - Can be removed once P01/P02 workflows are validated

## Adding New Workflows

To add a new workflow that uses P01 manifests:

1. Create `p02-{name}.yml`
2. Set trigger to `workflow_run` on "P01 - Kustomize Build"
3. Download artifacts using `actions/github-script@v7`
4. Process manifests
5. Post results to PR

Example skeleton:
```yaml
on:
  workflow_run:
    workflows: ["P01 - Kustomize Build"]
    types: [completed]

jobs:
  my-job:
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'success'
    steps:
      - # Download artifacts from P01
      - # Process
      - # Comment on PR
```
