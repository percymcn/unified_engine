#!/bin/bash
# Usage: source scripts/load-env.sh [development|staging|production]
# Loads environment-specific variables

ENV=${1:-development}
ENV_FILE="deploy/envs/.env.${ENV}"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: Environment file not found: $ENV_FILE"
    exit 1
fi

export $(grep -v '^#' "$ENV_FILE" | xargs)
echo "Loaded environment: $ENV"
