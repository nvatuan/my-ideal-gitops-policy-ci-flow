Environments is common manifests to two clusters. So we should build the final manifest in the clusters.env location

```
kustomize build services/my-app/clusters/blue/stg > blue-stg-my-app.yaml
```