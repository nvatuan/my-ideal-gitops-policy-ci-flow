#! /bin/bash

# generate the ingress-nginx manifest for the prod environment to yaml

helmfile template > helmed.yaml