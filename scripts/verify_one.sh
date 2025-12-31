#!/bin/bash
# One-Command Verification Script
# Runs all verification checks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/verify_${TIMESTAMP}.log"

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
    log "Unified Engine - One-Command Verify"
    log "=========================================="
    log ""
    
    local all_passed=true
    
    # Run health check
    log "Running health check..."
    if bash "$SCRIPT_DIR/verify_green.sh" >> "$LOG_FILE" 2>&1; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        all_passed=false
    fi
    
    log ""
    
    # Run smoke test (non-blocking)
    log "Running user flow smoke test..."
    if bash "$SCRIPT_DIR/smoke_user_flow.sh" >> "$LOG_FILE" 2>&1; then
        log_success "Smoke test passed"
    else
        log_warning "Smoke test failed (check logs)"
    fi
    
    log ""
    log "=========================================="
    if [ "$all_passed" = true ]; then
        log_success "Verification: PASSED ✅"
        log "System is operational"
        exit 0
    else
        log_error "Verification: FAILED ❌"
        log "Some checks failed - see logs for details"
        exit 1
    fi
}

main "$@"
