#!/bin/bash
# TradeFlow MVP - Automated Deployment Script
# Generated: 2026-01-01
# This script automates the deployment of TradeFlow unified trading engine

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="unified_engine_stack"
DOCKER_STACK_FILE="docker-stack.yml"
PROJECT_ROOT="/home/pharma5/unified_engine"
LAN_IP="192.168.1.254"

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}TradeFlow MVP - Automated Deployment${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if running from correct directory
if [ ! -f "$DOCKER_STACK_FILE" ]; then
    print_error "docker-stack.yml not found. Please run this script from the project root."
    exit 1
fi

# Step 1: Check Docker Swarm
echo -e "\n${YELLOW}Step 1: Checking Docker Swarm status...${NC}"
if docker info | grep -q "Swarm: active"; then
    print_status "Docker Swarm is active"
else
    print_error "Docker Swarm is not active. Please initialize Swarm first."
    exit 1
fi

# Step 2: Check required images
echo -e "\n${YELLOW}Step 2: Checking Docker images...${NC}"
if docker images | grep -q "unified-engine/api"; then
    print_status "API image found"
else
    print_warning "API image not found. Building..."
    docker build -t unified-engine/api:latest -f Dockerfile.stack .
fi

if docker images | grep -q "unified-engine/ui"; then
    print_status "UI image found"
else
    print_error "UI image not found. Please build it first:"
    echo "  cd ui && npm install --legacy-peer-deps && cd .."
    echo "  docker build -t unified-engine/ui:latest ./ui"
    exit 1
fi

# Step 3: Check nginx config
echo -e "\n${YELLOW}Step 3: Checking nginx configuration...${NC}"
if docker config ls | grep -q "unified_nginx_conf"; then
    print_status "Nginx config already exists"
else
    print_warning "Creating nginx config..."
    if [ -f "nginx-reverse-proxy.conf" ]; then
        docker config create unified_nginx_conf nginx-reverse-proxy.conf
        print_status "Nginx config created"
    else
        print_error "nginx-reverse-proxy.conf not found"
        exit 1
    fi
fi

# Step 4: Check directories
echo -e "\n${YELLOW}Step 4: Checking required directories...${NC}"
mkdir -p data logs
print_status "Directories verified"

# Step 5: Check environment file
echo -e "\n${YELLOW}Step 5: Checking environment configuration...${NC}"
if [ -f ".env" ]; then
    print_status ".env file found"
else
    print_warning ".env file not found, using docker-stack.yml defaults"
fi

if [ -f "ui/.env" ]; then
    print_status "UI .env file found"
else
    print_warning "Creating UI .env file..."
    echo "VITE_API_BASE_URL=http://${LAN_IP}:3012" > ui/.env
    print_status "UI .env created"
fi

# Step 6: Apply database migrations
echo -e "\n${YELLOW}Step 6: Checking database migrations...${NC}"
print_status "Migrations will be applied automatically when API starts"

# Step 7: Deploy/Update stack
echo -e "\n${YELLOW}Step 7: Deploying stack...${NC}"
if docker stack ls | grep -q "$STACK_NAME"; then
    print_warning "Stack already exists. Updating..."
    docker stack deploy -c $DOCKER_STACK_FILE $STACK_NAME
else
    print_warning "Deploying new stack..."
    docker stack deploy -c $DOCKER_STACK_FILE $STACK_NAME
fi
print_status "Stack deployed"

# Step 8: Wait for services to start
echo -e "\n${YELLOW}Step 8: Waiting for services to start...${NC}"
echo "This may take a minute..."
sleep 10

# Step 9: Check service status
echo -e "\n${YELLOW}Step 9: Checking service status...${NC}"
docker service ls | grep $STACK_NAME

# Step 10: Health checks
echo -e "\n${YELLOW}Step 10: Running health checks...${NC}"
echo "Waiting for API to be ready..."
sleep 5

MAX_RETRIES=12
RETRY_COUNT=0
API_HEALTHY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://${LAN_IP}:3012/health > /dev/null 2>&1; then
        API_HEALTHY=true
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting for API... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 5
done

if [ "$API_HEALTHY" = true ]; then
    print_status "API is healthy"
    echo ""
    curl -s http://${LAN_IP}:3012/health | python3 -m json.tool
else
    print_error "API failed to become healthy after $MAX_RETRIES retries"
    print_warning "Check logs with: docker service logs ${STACK_NAME}_api"
fi

# Step 11: Display summary
echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}Deployment Summary${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Stack Name: $STACK_NAME"
echo "Project Root: $PROJECT_ROOT"
echo "LAN IP: $LAN_IP"
echo ""
echo -e "${YELLOW}Service Endpoints:${NC}"
echo "  API:    http://${LAN_IP}:3012"
echo "  Docs:   http://${LAN_IP}:3012/docs"
echo "  Health: http://${LAN_IP}:3012/health"
echo "  UI:     http://${LAN_IP}:3411"
echo "  Nginx:  http://${LAN_IP}:3013"
echo "  Flower: http://${LAN_IP}:5558"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  View services:    docker service ls | grep $STACK_NAME"
echo "  View logs:        docker service logs -f ${STACK_NAME}_api"
echo "  Scale service:    docker service scale ${STACK_NAME}_celery-worker=4"
echo "  Update stack:     docker stack deploy -c $DOCKER_STACK_FILE $STACK_NAME"
echo "  Remove stack:     docker stack rm $STACK_NAME"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Verify all services are running: docker service ls | grep $STACK_NAME"
echo "  2. Check API health: curl http://${LAN_IP}:3012/health"
echo "  3. Access UI: http://${LAN_IP}:3411"
echo "  4. Review MANUAL_STEPS_REQUIRED.md for any remaining setup"
echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo ""
