#!/bin/bash
# =============================================================================
# Unified Trading Engine - Swarm Stack Deployment Script
# Stops local services, builds images, and deploys to Docker Swarm
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Unified Trading Engine - Swarm Deploy${NC}"
echo -e "${BLUE}========================================${NC}"

# Configuration
STACK_NAME="unified_engine"
STACK_FILE="docker-stack.yml"
PROJECT_DIR="/home/pharma5/unified_engine"
REGISTRY="192.168.1.254:5000"
API_PORT=8765
UI_PORT=3456
LAN_IP="192.168.1.254"

cd "$PROJECT_DIR"

# Check if running from correct directory
if [ ! -f "$STACK_FILE" ]; then
    echo -e "${RED}Error: $STACK_FILE not found. Run from project root.${NC}"
    exit 1
fi

echo -e "\n${YELLOW}[1/7] Stopping local services...${NC}"

# Kill local uvicorn/backend processes
echo -e "  Stopping uvicorn processes..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true
sleep 1

# Kill any process on API port
echo -e "  Freeing port $API_PORT..."
fuser -k ${API_PORT}/tcp 2>/dev/null || true

# Kill local Next.js processes
echo -e "  Stopping Next.js processes..."
pkill -f "next-server" 2>/dev/null || true
pkill -f "node.*server.js" 2>/dev/null || true
sleep 1

# Kill any process on UI port
echo -e "  Freeing port $UI_PORT..."
fuser -k ${UI_PORT}/tcp 2>/dev/null || true

echo -e "${GREEN}  Local services stopped.${NC}"

echo -e "\n${YELLOW}[2/7] Checking Docker Swarm...${NC}"

if docker info 2>/dev/null | grep -q "Swarm: active"; then
    echo -e "${GREEN}  Docker Swarm is active.${NC}"
else
    echo -e "${RED}  Docker Swarm is not active!${NC}"
    echo -e "  Initialize with: docker swarm init"
    exit 1
fi

echo -e "\n${YELLOW}[3/7] Building API image...${NC}"

docker build -t ${REGISTRY}/unified-engine/api:latest -f Dockerfile.stack .
echo -e "${GREEN}  API image built.${NC}"

echo -e "\n${YELLOW}[4/7] Building UI image...${NC}"

docker build -t ${REGISTRY}/unified-engine/ui:latest ./ui-next
echo -e "${GREEN}  UI image built.${NC}"

echo -e "\n${YELLOW}[5/7] Pushing images to registry...${NC}"

docker push ${REGISTRY}/unified-engine/api:latest
docker push ${REGISTRY}/unified-engine/ui:latest
echo -e "${GREEN}  Images pushed to registry.${NC}"

echo -e "\n${YELLOW}[6/7] Deploying stack...${NC}"

# Check if stack exists and update, otherwise deploy new
if docker stack ls | grep -q "$STACK_NAME"; then
    echo -e "  Updating existing stack..."
else
    echo -e "  Deploying new stack..."
fi

docker stack deploy -c $STACK_FILE $STACK_NAME --with-registry-auth

echo -e "${GREEN}  Stack deployed.${NC}"

echo -e "\n${YELLOW}[7/7] Waiting for services to be healthy...${NC}"

# Wait for services to start
sleep 10

# Check API health
echo -e "  Waiting for API (port $API_PORT)..."
API_HEALTHY=false
for i in {1..60}; do
    if curl -sf http://localhost:$API_PORT/health > /dev/null 2>&1; then
        echo -e "\n${GREEN}  API is healthy!${NC}"
        API_HEALTHY=true
        break
    fi
    sleep 3
    echo -n "."
done

if [ "$API_HEALTHY" = false ]; then
    echo -e "\n${YELLOW}  API not ready yet. Check logs:${NC}"
    echo -e "  docker service logs ${STACK_NAME}_api"
fi

# Check UI health
echo -e "  Waiting for UI (port $UI_PORT)..."
UI_HEALTHY=false
for i in {1..30}; do
    if curl -sf http://localhost:$UI_PORT > /dev/null 2>&1; then
        echo -e "\n${GREEN}  UI is ready!${NC}"
        UI_HEALTHY=true
        break
    fi
    sleep 3
    echo -n "."
done

if [ "$UI_HEALTHY" = false ]; then
    echo -e "\n${YELLOW}  UI not ready yet. Check logs:${NC}"
    echo -e "  docker service logs ${STACK_NAME}_ui"
fi

# Show service status
echo -e "\n${YELLOW}Service Status:${NC}"
docker service ls | grep $STACK_NAME

echo -e "\n${BLUE}========================================${NC}"
if [ "$API_HEALTHY" = true ] && [ "$UI_HEALTHY" = true ]; then
    echo -e "${GREEN}  Deployment Complete!${NC}"
else
    echo -e "${YELLOW}  Deployment finished (services starting)${NC}"
fi
echo -e "${BLUE}========================================${NC}"
echo -e ""
echo -e "${YELLOW}Public URLs (via Cloudflare):${NC}"
echo -e "  UI:     https://mytradeflow.app"
echo -e "  API:    https://api.mytradeflow.app"
echo -e "  Docs:   https://api.mytradeflow.app/docs"
echo -e ""
echo -e "${YELLOW}Local URLs (internal):${NC}"
echo -e "  API:    http://localhost:$API_PORT"
echo -e "  UI:     http://localhost:$UI_PORT"
echo -e "  Flower: http://${LAN_IP}:5558"
echo -e ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo -e "  Service status:  docker service ls | grep $STACK_NAME"
echo -e "  API logs:        docker service logs -f ${STACK_NAME}_api"
echo -e "  UI logs:         docker service logs -f ${STACK_NAME}_ui"
echo -e "  Scale workers:   docker service scale ${STACK_NAME}_celery-worker=2"
echo -e "  Remove stack:    docker stack rm $STACK_NAME"
echo -e ""
