#!/bin/bash
# Production Deployment Script for Unified Trading Engine
# This script handles the complete deployment process

set -e  # Exit on any error

# =============================================================================
# CONFIGURATION
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
LOG_FILE="$PROJECT_ROOT/deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}" | tee -a "$LOG_FILE"
}

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================
validate_requirements() {
    log "Validating deployment requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed or not in PATH"
        exit 1
    fi
    
    # Check required files
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "docker-compose.yml not found at $COMPOSE_FILE"
        exit 1
    fi
    
    if [[ ! -f "$ENV_FILE" ]]; then
        log_warning ".env file not found. Creating from template..."
        cp "$PROJECT_ROOT/.env.example" "$ENV_FILE"
        log_warning "Please update $ENV_FILE with your configuration before proceeding"
        exit 1
    fi
    
    log_success "All requirements validated"
}

validate_environment() {
    log "Validating environment configuration..."
    
    # Check critical environment variables
    local required_vars=(
        "SECRET_KEY"
        "DATABASE_URL"
        "REDIS_URL"
        "JWT_SECRET_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^$var=" "$ENV_FILE"; then
            log_error "Required environment variable $var is not set in $ENV_FILE"
            exit 1
        fi
    done
    
    log_success "Environment configuration validated"
}

# =============================================================================
# DEPLOYMENT FUNCTIONS
# =============================================================================
setup_directories() {
    log "Setting up directories..."
    
    # Create necessary directories
    mkdir -p "$PROJECT_ROOT/logs"
    mkdir -p "$PROJECT_ROOT/data/postgres"
    mkdir -p "$PROJECT_ROOT/data/redis"
    mkdir -p "$PROJECT_ROOT/backups"
    mkdir -p "$PROJECT_ROOT/uploads"
    
    # Set proper permissions
    chmod 755 "$PROJECT_ROOT/logs"
    chmod 755 "$PROJECT_ROOT/data"
    chmod 755 "$PROJECT_ROOT/backups"
    chmod 755 "$PROJECT_ROOT/uploads"
    
    log_success "Directories created and permissions set"
}

build_images() {
    log "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    # Build images with no cache for production
    docker-compose build --no-cache --parallel
    
    log_success "Docker images built successfully"
}

start_services() {
    log "Starting services..."
    
    cd "$PROJECT_ROOT"
    
    # Start services in detached mode
    docker-compose up -d
    
    log_success "Services started successfully"
}

stop_services() {
    log "Stopping services..."
    
    cd "$PROJECT_ROOT"
    
    # Stop services
    docker-compose down
    
    log_success "Services stopped successfully"
}

restart_services() {
    log "Restarting services..."
    
    stop_services
    sleep 5
    start_services
}

# =============================================================================
# HEALTH CHECK FUNCTIONS
# =============================================================================
wait_for_service() {
    local service_name=$1
    local max_attempts=${2:-30}
    local attempt=1
    
    log "Waiting for $service_name to be healthy..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose ps | grep -q "$service_name.*Up"; then
            if [[ "$service_name" == "api" ]]; then
                # Check API health endpoint
                if curl -f http://localhost:8000/health &>/dev/null; then
                    log_success "$service_name is healthy"
                    return 0
                fi
            else
                # For other services, just check if they're up
                log_success "$service_name is up"
                return 0
            fi
        fi
        
        log_info "Attempt $attempt/$max_attempts: $service_name not ready yet..."
        sleep 2
        ((attempt++))
    done
    
    log_error "$service_name failed to start within $max_attempts attempts"
    return 1
}

check_service_health() {
    log "Checking service health..."
    
    local services_healthy=true
    
    # Check API service
    if ! wait_for_service "api" 60; then
        services_healthy=false
    fi
    
    # Check database service
    if ! wait_for_service "db" 30; then
        services_healthy=false
    fi
    
    # Check Redis service
    if ! wait_for_service "redis" 30; then
        services_healthy=false
    fi
    
    if [[ "$services_healthy" == "true" ]]; then
        log_success "All services are healthy"
        return 0
    else
        log_error "Some services are not healthy"
        return 1
    fi
}

# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================
run_migrations() {
    log "Running database migrations..."
    
    cd "$PROJECT_ROOT"
    
    # Run migrations
    docker-compose exec api python scripts/migrate.py --create-tables
    
    log_success "Database migrations completed"
}

seed_database() {
    log "Seeding database..."
    
    cd "$PROJECT_ROOT"
    
    # Seed database with sample data
    docker-compose exec api python scripts/migrate.py --seed
    
    log_success "Database seeding completed"
}

create_admin_user() {
    log "Creating admin user..."
    
    cd "$PROJECT_ROOT"
    
    # Create admin user
    docker-compose exec api python scripts/migrate.py --admin-only
    
    log_success "Admin user created"
}

# =============================================================================
# MONITORING FUNCTIONS
# =============================================================================
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Create monitoring directories
    mkdir -p "$PROJECT_ROOT/monitoring"
    
    # Create log rotation configuration
    cat > "$PROJECT_ROOT/monitoring/logrotate.conf" << EOF
$PROJECT_ROOT/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644
    postrotate
        docker-compose exec api kill -USR1 $(cat $PROJECT_ROOT/api.pid)
    endscript
}
EOF
    
    log_success "Monitoring setup completed"
}

show_service_status() {
    log "Current service status:"
    echo
    docker-compose ps
    echo
}

show_logs() {
    local service=${1:-api}
    local lines=${2:-50}
    
    log "Showing last $lines lines of $service logs:"
    docker-compose logs --tail="$lines" "$service"
}

# =============================================================================
# BACKUP FUNCTIONS
# =============================================================================
backup_database() {
    log "Creating database backup..."
    
    local backup_file="$PROJECT_ROOT/backups/db_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    cd "$PROJECT_ROOT"
    
    # Create database backup
    docker-compose exec db pg_dump -U postgres -d trading_engine > "$backup_file"
    
    if [[ -f "$backup_file" ]]; then
        log_success "Database backup created: $backup_file"
        
        # Compress backup
        gzip "$backup_file"
        log_success "Database backup compressed: $backup_file.gz"
    else
        log_error "Database backup failed"
    fi
}

# =============================================================================
# CLEANUP FUNCTIONS
# =============================================================================
cleanup() {
    log "Performing cleanup..."
    
    # Remove unused Docker images
    docker image prune -f
    
    # Remove unused Docker volumes (with confirmation)
    log_warning "Skipping volume cleanup (requires manual confirmation)"
    
    # Clean old logs (keep last 7 days)
    find "$PROJECT_ROOT/logs" -name "*.log" -mtime +7 -delete 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# =============================================================================
# MAIN MENU
# =============================================================================
show_menu() {
    echo
    echo "=========================================="
    echo "  Unified Trading Engine Deployment"
    echo "=========================================="
    echo
    echo "1)  Deploy (Full)"
    echo "2)  Quick Deploy (Skip Build)"
    echo "3)  Start Services"
    echo "4)  Stop Services"
    echo "5)  Restart Services"
    echo "6)  Check Health"
    echo "7)  Run Migrations"
    echo "8)  Seed Database"
    echo "9)  Create Admin User"
    echo "10) Show Service Status"
    echo "11) Show Logs"
    echo "12)  Backup Database"
    echo "13)  Cleanup"
    echo "14)  Full Reset"
    echo "15)  Exit"
    echo
    echo -n "Select an option [1-15]: "
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================
main() {
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Parse command line arguments
    case "${1:-}" in
        "deploy"|"")
            log "Starting full deployment..."
            validate_requirements
            validate_environment
            setup_directories
            build_images
            start_services
            check_service_health
            run_migrations
            seed_database
            create_admin_user
            setup_monitoring
            log_success "Deployment completed successfully!"
            ;;
        "quick-deploy")
            log "Starting quick deployment..."
            validate_requirements
            validate_environment
            setup_directories
            start_services
            check_service_health
            log_success "Quick deployment completed successfully!"
            ;;
        "start")
            start_services
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            restart_services
            ;;
        "health")
            check_service_health
            ;;
        "migrate")
            run_migrations
            ;;
        "seed")
            seed_database
            ;;
        "admin")
            create_admin_user
            ;;
        "status")
            show_service_status
            ;;
        "logs")
            show_logs "${2:-api}" "${3:-50}"
            ;;
        "backup")
            backup_database
            ;;
        "cleanup")
            cleanup
            ;;
        "reset")
            log "Performing full reset..."
            stop_services
            docker-compose down -v
            docker system prune -f
            setup_directories
            build_images
            start_services
            check_service_health
            run_migrations
            seed_database
            create_admin_user
            log_success "Full reset completed successfully!"
            ;;
        "menu")
            while true; do
                show_menu
                read -r choice
                case $choice in
                    1)
                        main deploy
                        ;;
                    2)
                        main quick-deploy
                        ;;
                    3)
                        main start
                        ;;
                    4)
                        main stop
                        ;;
                    5)
                        main restart
                        ;;
                    6)
                        main health
                        ;;
                    7)
                        main migrate
                        ;;
                    8)
                        main seed
                        ;;
                    9)
                        main admin
                        ;;
                    10)
                        main status
                        ;;
                    11)
                        main logs
                        ;;
                    12)
                        main backup
                        ;;
                    13)
                        main cleanup
                        ;;
                    14)
                        main reset
                        ;;
                    15)
                        log "Exiting..."
                        exit 0
                        ;;
                    *)
                        log_error "Invalid option. Please select 1-15."
                        ;;
                esac
            done
            ;;
        *)
            echo "Usage: $0 [command]"
            echo
            echo "Commands:"
            echo "  deploy       Full deployment (build + start + migrate + seed)"
            echo "  quick-deploy  Quick deployment (start only)"
            echo "  start        Start services"
            echo "  stop         Stop services"
            echo "  restart      Restart services"
            echo "  health        Check service health"
            echo "  migrate       Run database migrations"
            echo "  seed          Seed database"
            echo "  admin         Create admin user"
            echo "  status        Show service status"
            echo "  logs [service] Show service logs"
            echo "  backup        Backup database"
            echo "  cleanup       Cleanup unused resources"
            echo "  reset         Full reset (stop + clean + deploy)"
            echo "  menu          Show interactive menu"
            exit 1
            ;;
    esac
}

# Trap signals for cleanup
trap 'log_error "Deployment interrupted"; exit 1' INT TERM

# Execute main function
main "$@"