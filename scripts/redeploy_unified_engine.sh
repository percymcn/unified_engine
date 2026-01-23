#!/bin/bash
# Redeploy Unified Engine Stack
# Safe, non-destructive redeploy

set -e

echo "=== Unified Engine Redeploy ==="
echo ""

# Check if stack exists
STACK_NAME="unified"
if docker stack ls | grep -q "$STACK_NAME"; then
    echo "Stack '$STACK_NAME' exists, updating..."
    docker stack deploy -c docker-stack.yml "$STACK_NAME" --with-registry-auth
else
    echo "Stack '$STACK_NAME' not found, creating..."
    docker stack deploy -c docker-stack.yml "$STACK_NAME" --with-registry-auth
fi

echo ""
echo "Waiting for services to be healthy..."
sleep 10

echo ""
echo "Service Status:"
docker service ls | grep -E "unified|postgres|redis|api" || echo "No matching services"

echo ""
echo "=== Redeploy Complete ==="
echo ""
echo "Check service health:"
echo "  docker service ps unified_api"
echo "  docker service ps postgres"
echo "  docker service ps redis"
