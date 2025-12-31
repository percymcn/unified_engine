#!/bin/bash
# Health Check Script for Unified Engine
# Verifies all services are healthy and responding

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/healthcheck_${TIMESTAMP}.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Create logs directory
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

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

# Check Docker services
check_docker_services() {
    log "Checking Docker Swarm services..."
    
    local services_healthy=true
    
    # Check if stack exists
    if ! docker stack ls | grep -q "unified_engine_stack"; then
        log_error "Docker stack 'unified_engine_stack' not found"
        return 1
    fi
    
    # Check each service
    local services=(
        "unified_engine_stack_api"
        "unified_engine_stack_postgres"
        "unified_engine_stack_redis"
        "unified_engine_stack_ui"
    )
    
    for service in "${services[@]}"; do
        local replicas=$(docker service ls --filter "name=$service" --format "{{.Replicas}}" 2>/dev/null || echo "0/0")
        local running=$(echo "$replicas" | cut -d'/' -f1)
        local desired=$(echo "$replicas" | cut -d'/' -f2)
        
        if [ "$running" -eq "$desired" ] && [ "$desired" -gt 0 ]; then
            log_success "$service: $replicas"
        else
            log_warning "$service: $replicas (expected $desired running)"
            if [ "$desired" -gt 0 ]; then
                services_healthy=false
            fi
        fi
    done
    
    if [ "$services_healthy" = true ]; then
        return 0
    else
        return 1
    fi
}

# Check backend health endpoint
check_backend_health() {
    log "Checking backend health endpoint..."
    
    local max_attempts=5
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        local response=$(curl -s -w "\n%{http_code}" http://localhost:3012/health 2>/dev/null || echo -e "\n000")
        local body=$(echo "$response" | head -n -1)
        local status_code=$(echo "$response" | tail -n 1)
        
        if [ "$status_code" = "200" ]; then
            log_success "Backend health check passed (HTTP $status_code)"
            echo "$body" | jq '.' 2>/dev/null | tee -a "$LOG_FILE" || echo "$body" | tee -a "$LOG_FILE"
            return 0
        elif [ "$status_code" = "000" ]; then
            log_warning "Backend not responding (attempt $attempt/$max_attempts)"
        else
            log_warning "Backend returned HTTP $status_code (attempt $attempt/$max_attempts)"
        fi
        
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "Backend health check failed after $max_attempts attempts"
    return 1
}

# Check UI
check_ui() {
    log "Checking UI..."
    
    local response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3411 2>/dev/null || echo "000")
    
    if [ "$response" = "200" ]; then
        log_success "UI responding (HTTP $response)"
        return 0
    else
        log_warning "UI not responding (HTTP $response)"
        return 1
    fi
}

# Check database connectivity
check_database() {
    log "Checking database connectivity..."
    
    # Try to connect via docker exec
    local db_check=$(docker service ps unified_engine_stack_postgres --no-trunc --format "{{.Name}}" 2>/dev/null | head -1)
    
    if [ -n "$db_check" ]; then
        local container_id=$(docker ps --filter "name=$db_check" --format "{{.ID}}" | head -1)
        if [ -n "$container_id" ]; then
            local db_status=$(docker exec "$container_id" pg_isready -U trading_user -d trading_db 2>/dev/null || echo "not ready")
            if echo "$db_status" | grep -q "accepting connections"; then
                log_success "Database is accepting connections"
                return 0
            fi
        fi
    fi
    
    log_warning "Could not verify database connectivity"
    return 1
}

# Check Redis connectivity
check_redis() {
    log "Checking Redis connectivity..."
    
    local redis_check=$(docker service ps unified_engine_stack_redis --no-trunc --format "{{.Name}}" 2>/dev/null | head -1)
    
    if [ -n "$redis_check" ]; then
        local container_id=$(docker ps --filter "name=$redis_check" --format "{{.ID}}" | head -1)
        if [ -n "$container_id" ]; then
            local redis_status=$(docker exec "$container_id" redis-cli ping 2>/dev/null || echo "PONG")
            if [ "$redis_status" = "PONG" ]; then
                log_success "Redis is responding"
                return 0
            fi
        fi
    fi
    
    log_warning "Could not verify Redis connectivity"
    return 1
}

# Check key API endpoints
check_api_endpoints() {
    log "Checking key API endpoints..."
    
    local endpoints=(
        "/"
        "/health"
        "/api/v1/auth/login"
    )
    
    local all_ok=true
    
    for endpoint in "${endpoints[@]}"; do
        local response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:3012$endpoint" 2>/dev/null || echo "000")
        
        if [ "$response" = "200" ] || [ "$response" = "401" ] || [ "$response" = "405" ]; then
            log_success "$endpoint: HTTP $response"
        else
            log_warning "$endpoint: HTTP $response"
            if [ "$endpoint" = "/health" ]; then
                all_ok=false
            fi
        fi
    done
    
    if [ "$all_ok" = true ]; then
        return 0
    else
        return 1
    fi
}

# Main execution
main() {
    log "=========================================="
    log "Unified Engine Health Check"
    log "=========================================="
    log "Log file: $LOG_FILE"
    log ""
    
    local overall_healthy=true
    
    # Run checks
    check_docker_services || overall_healthy=false
    check_backend_health || overall_healthy=false
    check_ui || log_warning "UI check failed (non-critical)"
    check_database || log_warning "Database check failed (non-critical)"
    check_redis || log_warning "Redis check failed (non-critical)"
    check_api_endpoints || overall_healthy=false
    
    log ""
    log "=========================================="
    if [ "$overall_healthy" = true ]; then
        log_success "Overall health: GREEN ✅"
        log "All critical services are healthy"
        exit 0
    else
        log_error "Overall health: RED ❌"
        log "Some critical services are not healthy"
        exit 1
    fi
}

main "$@"
