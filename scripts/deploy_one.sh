#!/bin/bash
# One-Command Deployment Script
# Deploys the entire Unified Engine stack

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/deploy_${TIMESTAMP}.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$LOG_DIR"

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
}

main() {
    log "=========================================="
    log "Unified Engine - One-Command Deploy"
    log "=========================================="
    log ""
    
    cd "$PROJECT_ROOT"
    
    # Ensure required directories exist
    log "Creating required directories..."
    mkdir -p logs data
    log_success "Directories created"
    
    # Check if stack is already deployed
    if docker stack ls | grep -q "unified_engine_stack"; then
        log "Stack already deployed, updating..."
        docker stack deploy -c docker-stack.yml unified_engine_stack
        log_success "Stack updated"
    else
        log "Deploying new stack..."
        
        # Check if nginx config exists
        if ! docker config ls | grep -q "unified_nginx_conf"; then
            log "Creating nginx config..."
            docker config create unified_nginx_conf nginx.conf
            log_success "Nginx config created"
        fi
        
        docker stack deploy -c docker-stack.yml unified_engine_stack
        log_success "Stack deployed"
    fi
    
    log ""
    log "Waiting for services to start..."
    sleep 10
    
    log ""
    log "Deployment complete!"
    log "Run './scripts/verify_one.sh' to verify deployment"
    log ""
}

main "$@"
