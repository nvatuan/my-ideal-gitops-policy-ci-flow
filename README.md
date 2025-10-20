# My Ideal GitOps Policy CI Flow

This repository shows my ideal image of the GitOps CICD flow for running checks on PR that changes manifests.
It is used mainly to check https://github.com/nvatuan/gitops-kustomz

## Structure

The `manifests/` folder uses a Kustomize base + overlay pattern:

```
manifests/
└── services/
    └── my-app/
        ├── base/                           # Base manifests (shared across envs)
        │   ├── deployment.yaml
        │   ├── service.yaml
        │   ├── ingress.yaml
        │   ├── hpa.yaml
        │   ├── keda-scaledobject.yaml
        │   └── kustomization.yaml
        └── environments/                   # Environment-specific overlays
            ├── prod/
            │   ├── kustomization.yaml      # References ../../base
            │   └── *-patch.yaml            # Strategic merge patches
            ├── stg/
            │   ├── kustomization.yaml
            │   └── *-patch.yaml
            └── sandbox/
                ├── kustomization.yaml
                └── deployment-patch.yaml
```

**Base Layer**: Defines the core Kubernetes resources with sensible defaults. Common labels and resource specs are defined here.

**Environment Overlays**: Each environment (`prod`, `stg`, `sandbox`) applies environment-specific patches via `patchesStrategicMerge` or `patches`. They also set:
- `namespace`: Target namespace for the environment
- `namePrefix`: Prefixes resource names (e.g., `prod-my-app`)
- `commonLabels`: Environment-specific labels (e.g., `environment: prod`)

To build manifests for an environment:
```bash
kustomize build manifests/services/my-app/environments/prod
```

## Updating

To update the manifest, you must open a PR and waits for the CI to finish running.