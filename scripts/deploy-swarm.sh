#!/bin/bash
# =============================================================================
# TRADEFLOW DOCKER SWARM DEPLOYMENT SCRIPT
# =============================================================================
# This script deploys Tradeflow to a Docker Swarm cluster
#
# Prerequisites:
# - Docker Swarm initialized (docker swarm init)
# - .env.production file with required secrets
# - Access to Docker registry (if pushing images)
#
# Usage:
#   ./scripts/deploy-swarm.sh [options]
#
# Options:
#   --build     Build images before deploying
#   --push      Push images to registry before deploying
#   --stop      Stop and remove the stack
#   --logs      Show logs from all services
#   --help      Show this help message
# =============================================================================

set -e

# Configuration
STACK_NAME="${STACK_NAME:-tradeflow}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.production.yml}"
ENV_FILE="${ENV_FILE:-.env.production}"
REGISTRY="${REGISTRY:-192.168.1.254:5000}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show help
show_help() {
    head -30 "$0" | grep -E "^#" | sed 's/^# //' | sed 's/^#//'
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check if Docker Swarm is initialized
    if ! docker info 2>/dev/null | grep -q "Swarm: active"; then
        log_error "Docker Swarm is not initialized. Run: docker swarm init"
        exit 1
    fi

    # Check if compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Compose file not found: $COMPOSE_FILE"
        exit 1
    fi

    # Check if env file exists
    if [ ! -f "$ENV_FILE" ]; then
        log_warning "Environment file not found: $ENV_FILE"
        log_info "Creating template .env.production file..."
        create_env_template
    fi

    log_success "Prerequisites check passed"
}

# Create environment template
create_env_template() {
    cat > "$ENV_FILE" << 'EOF'
# =============================================================================
# TRADEFLOW PRODUCTION ENVIRONMENT VARIABLES
# =============================================================================
# Copy this file to .env.production and fill in the values

# Database
POSTGRES_PASSWORD=your_secure_database_password

# Redis
REDIS_PASSWORD=your_secure_redis_password

# Security Keys (generate with: openssl rand -hex 32)
SECRET_KEY=your_secret_key_here
JWT_SECRET=your_jwt_secret_here
ENCRYPTION_KEY=your_encryption_key_here

# Google OAuth (optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Stripe (optional)
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=fluxio484@gmail.com
SMTP_PASSWORD=your_app_password_here
SMTP_FROM_EMAIL=fluxio484@gmail.com

# MetaAPI (for MT4/MT5)
METAAPI_TOKEN=
METAAPI_ACCOUNT_ID=
EOF
    log_info "Template created. Please edit $ENV_FILE with your values."
}

# Load environment variables
load_env() {
    if [ -f "$ENV_FILE" ]; then
        log_info "Loading environment from $ENV_FILE"
        set -a
        source "$ENV_FILE"
        set +a
    fi
}

# Build images
build_images() {
    log_info "Building Docker images..."

    # Build backend
    log_info "Building backend image..."
    docker build -t ${REGISTRY}/tradeflow/backend:latest -f Dockerfile .

    # Build frontend
    log_info "Building frontend image..."
    docker build -t ${REGISTRY}/tradeflow/frontend:latest -f ui-next/Dockerfile ui-next/

    log_success "Images built successfully"
}

# Push images to registry
push_images() {
    log_info "Pushing images to registry: $REGISTRY"

    docker push ${REGISTRY}/tradeflow/backend:latest
    docker push ${REGISTRY}/tradeflow/frontend:latest

    log_success "Images pushed successfully"
}

# Deploy stack
deploy_stack() {
    log_info "Deploying stack: $STACK_NAME"

    # Load environment
    load_env

    # Create secrets if they don't exist
    create_secrets

    # Deploy the stack
    docker stack deploy -c "$COMPOSE_FILE" "$STACK_NAME"

    log_success "Stack deployed: $STACK_NAME"
    log_info "Run 'docker stack services $STACK_NAME' to check status"
}

# Create Docker secrets
create_secrets() {
    log_info "Creating Docker secrets..."

    # Only create if they don't exist
    if ! docker secret ls | grep -q "${STACK_NAME}_db_password"; then
        echo "$POSTGRES_PASSWORD" | docker secret create ${STACK_NAME}_db_password - 2>/dev/null || true
    fi

    if ! docker secret ls | grep -q "${STACK_NAME}_redis_password"; then
        echo "$REDIS_PASSWORD" | docker secret create ${STACK_NAME}_redis_password - 2>/dev/null || true
    fi

    if ! docker secret ls | grep -q "${STACK_NAME}_secret_key"; then
        echo "$SECRET_KEY" | docker secret create ${STACK_NAME}_secret_key - 2>/dev/null || true
    fi
}

# Stop and remove stack
stop_stack() {
    log_info "Stopping stack: $STACK_NAME"
    docker stack rm "$STACK_NAME"
    log_success "Stack removed: $STACK_NAME"
}

# Show logs
show_logs() {
    log_info "Showing logs for stack: $STACK_NAME"
    docker service logs -f "${STACK_NAME}_backend" &
    docker service logs -f "${STACK_NAME}_frontend" &
    wait
}

# Status check
check_status() {
    log_info "Stack status: $STACK_NAME"
    echo ""
    docker stack services "$STACK_NAME"
    echo ""
    log_info "To see detailed status: docker stack ps $STACK_NAME"
}

# Main script
main() {
    cd "$(dirname "$0")/.."

    case "${1:-}" in
        --help|-h)
            show_help
            ;;
        --build)
            check_prerequisites
            build_images
            ;;
        --push)
            check_prerequisites
            push_images
            ;;
        --stop)
            stop_stack
            ;;
        --logs)
            show_logs
            ;;
        --status)
            check_status
            ;;
        *)
            check_prerequisites

            if [ "${1:-}" == "--build" ] || [ "${2:-}" == "--build" ]; then
                build_images
            fi

            if [ "${1:-}" == "--push" ] || [ "${2:-}" == "--push" ]; then
                push_images
            fi

            deploy_stack

            log_info ""
            log_info "Deployment complete! Next steps:"
            log_info "  1. Check services: docker stack services $STACK_NAME"
            log_info "  2. View logs: docker service logs ${STACK_NAME}_backend"
            log_info "  3. Access frontend: https://tradeflow.fluxeo.net"
            log_info "  4. Access API: https://tradeflow.fluxeo.net/api"
            ;;
    esac
}

main "$@"
