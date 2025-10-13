# Workflow Execution Flow

## Complete Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                         Pull Request                             │
│  Changes to: manifests/services/** or policies/**               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  P01: KUSTOMIZE BUILD                                           │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Job 1: detect-changes                                  │    │
│  │  - Parse git diff                                       │    │
│  │  - Extract service names                                │    │
│  │  - Generate matrix: services × environments            │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│                             ▼                                    │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Job 2: build-before-after (matrix)                    │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │    │
│  │  │my-app/stg│ │my-app/prd│ │my-app/sbx│ │  ...     │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │    │
│  │  Each builds:                                           │    │
│  │  - Checkout PR branch → kustomize build → AFTER        │    │
│  │  - Checkout base branch → kustomize build → BEFORE     │    │
│  │  - Upload both as artifacts                            │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│                             ▼                                    │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Job 3: build-complete                                  │    │
│  │  - Verify all builds succeeded                         │    │
│  │  - Artifacts ready for P02 workflows                   │    │
│  └────────────────────────────────────────────────────────┘    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ workflow_run trigger
                             │
          ┌──────────────────┴──────────────────┐
          │                                     │
          ▼                                     ▼
┌─────────────────────────┐         ┌─────────────────────────┐
│ P02: DIFF COMMENTER     │         │ P02: POLICY EVAL        │
│ ┌─────────────────────┐ │         │ ┌─────────────────────┐ │
│ │ Download artifacts  │ │         │ │ Download artifacts  │ │
│ │ - before/*.yaml     │ │         │ │ - after/*.yaml only │ │
│ │ - after/*.yaml      │ │         │ │                     │ │
│ └─────────┬───────────┘ │         │ └─────────┬───────────┘ │
│           │             │         │           │             │
│           ▼             │         │           ▼             │
│ ┌─────────────────────┐ │         │ ┌─────────────────────┐ │
│ │ Generate diffs      │ │         │ │ Parse policies      │ │
│ │ - Unified diff      │ │         │ │ - compliance-config │ │
│ │ - Summary table     │ │         │ │ - Determine levels  │ │
│ │ - Statistics        │ │         │ └─────────┬───────────┘ │
│ └─────────┬───────────┘ │         │           │             │
│           │             │         │           ▼             │
│           ▼             │         │ ┌─────────────────────┐ │
│ ┌─────────────────────┐ │         │ │ Job: blocking       │ │
│ │ Post PR comment     │ │         │ │ - BLOCKING only     │ │
│ │ 📊 Manifest Changes │ │         │ │ - Required check    │ │
│ └─────────────────────┘ │         │ │ - Fail if violations│ │
│                         │         │ └─────────────────────┘ │
└─────────────────────────┘         │           │             │
                                    │           ▼             │
                                    │ ┌─────────────────────┐ │
                                    │ │ Job: advisory       │ │
                                    │ │ - All levels        │ │
                                    │ │ - Continue on error │ │
                                    │ └─────────┬───────────┘ │
                                    │           │             │
                                    │           ▼             │
                                    │ ┌─────────────────────┐ │
                                    │ │ Job: report         │ │
                                    │ │ - Generate markdown │ │
                                    │ │ - Post PR comment   │ │
                                    │ │ 🔍 Policy Report    │ │
                                    │ └─────────────────────┘ │
                                    └─────────────────────────┘
                                    
┌─────────────────────────────────────────────────────────────────┐
│                      Pull Request Comments                       │
│                                                                  │
│  📊 Manifest Changes                                             │
│  - my-app/stg: ✏️ Modified (+5 -2)                              │
│  - my-app/prod: 🆕 New (+210 -0)                                │
│  - Details... (click to expand)                                 │
│                                                                  │
│  🔍 Policy Compliance Report                                     │
│  Status: ⚠️ WARNING                                              │
│  Summary: 4/5 checks passed                                      │
│  - ⚠️ Warning: HA policy failed for sandbox                     │
│  - Details... (click to expand)                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Execution Timeline

```
Time    P01             P02-Diff        P02-Policy
─────   ─────────────   ─────────────   ─────────────
0s      Start
        detect-changes
1s      
2s      build-matrix
        [stg][prod]
        [sandbox]
3s      
30s     All builds ✓
        build-complete
        Upload artifacts
        ──────────────▶ Start           Start
35s                     Download        Download
                        artifacts       artifacts
40s                     Generate        Parse config
                        diff            Run OPA eval
50s                     Post comment ✓  blocking: ✓
                                        advisory: ✓
55s                                     Generate report
60s                                     Post comment ✓
```

## Artifact Flow

```
P01 Output Artifacts:
├── before-my-app-stg.yaml      (157 KB)
├── before-my-app-prod.yaml     (165 KB)
├── before-my-app-sandbox.yaml  (145 KB)
├── after-my-app-stg.yaml       (159 KB)
├── after-my-app-prod.yaml      (168 KB)
└── after-my-app-sandbox.yaml   (146 KB)

       │                    │
       │                    │
       ▼                    ▼
P02-Diff uses           P02-Policy uses
ALL artifacts           AFTER artifacts only
(before + after)        (current state)

       │                    │
       ▼                    ▼
Diff report             Policy results
(markdown)              (JSON → markdown)
```

## Data Processing Flow

```
Kustomize Build (P01):
base/deployment.yaml
  + environments/stg/deployment-patch.yaml
  = stg-deployment.yaml (artifact)

Diff Generation (P02-Diff):
before/my-app-stg.yaml
  vs
after/my-app-stg.yaml
  → unified diff
  → markdown report

Policy Evaluation (P02-Policy):
after/my-app-stg.yaml
  → split into resources
  → for each resource:
    - Deployment/my-app
    - Service/my-app  
    - Ingress/my-app
  → evaluate against policies:
    - ha.opa
    - ingress-tls.opa
  → aggregate results
  → markdown report
```

## Parallelization Benefits

```
Sequential (old):
[Detect][Build][Diff][Policy] = 60s total

Parallel (new):
[Detect][Build]
            └──[Diff  ] = 30s
            └──[Policy] = 30s
Total: 40s (33% faster)

With 3x services:
Sequential: 180s
Parallel: 
  [Detect][Build matrix 3×3]
              └──[Diff  ] = 30s
              └──[Policy] = 30s
Total: 60s (66% faster)
```

## Error Handling

```
Build fails:
  P01: build-complete fails ❌
  P02: Don't trigger (workflow_run checks success)
  Result: No artifacts, no comments

Diff fails:
  P01: Success ✓
  P02-Diff: Fails ❌
  P02-Policy: Still runs ✓ (independent)
  Result: No diff comment, but policy report posted

Policy blocking fails:
  P01: Success ✓
  P02-Diff: Success ✓
  P02-Policy: blocking job fails ❌, advisory continues
  Result: PR blocked, both comments posted

Policy advisory fails:
  P01: Success ✓
  P02-Diff: Success ✓  
  P02-Policy: advisory job fails (continue-on-error), report still posts ✓
  Result: PR not blocked, both comments posted
```
