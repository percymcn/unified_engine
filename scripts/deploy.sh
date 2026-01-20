#!/bin/bash
# Usage: ./scripts/deploy.sh [development|staging|production]
# Deploys stack to Docker Swarm with environment-specific config

set -e
ENV=${1:-production}

echo "Deploying unified-engine to $ENV environment..."

# Load environment
source scripts/load-env.sh $ENV

# For production/staging, ensure secrets exist
if [ "$ENV" != "development" ]; then
    echo "Checking Docker secrets..."
    for secret in db_password secret_key jwt_secret credential_encryption_key; do
        if ! docker secret inspect $secret >/dev/null 2>&1; then
            echo "Error: Secret '$secret' not found. Run scripts/create-secrets.sh first."
            exit 1
        fi
    done
fi

# Deploy stack
docker stack deploy -c docker-stack.yml unified-$ENV

echo "Deployment complete. Check status with: docker stack services unified-$ENV"
