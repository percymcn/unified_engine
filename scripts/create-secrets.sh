#!/bin/bash
# Creates Docker Swarm secrets for unified trading engine
# Usage: ./scripts/create-secrets.sh [env-file]
#
# Secrets created:
# - db_password: PostgreSQL password
# - secret_key: Application secret key
# - jwt_secret: JWT signing key
# - credential_encryption_key: Credential encryption key (Fernet format)
# - flower_auth: Flower basic auth (user:password)
#
# Environment variables (optional):
# - DB_PASSWORD: Database password (generates random if not set)
# - SECRET_KEY: Application secret key (generates random if not set)
# - JWT_SECRET: JWT signing key (generates random if not set)
# - CREDENTIAL_ENCRYPTION_KEY: Fernet encryption key (generates if not set)
# - FLOWER_AUTH: Flower basic auth user:password (generates if not set)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment file if provided
if [ -n "$1" ] && [ -f "$1" ]; then
    echo -e "${GREEN}Loading environment from: $1${NC}"
    # shellcheck disable=SC1090
    source "$1"
fi

# Generate random 32-character alphanumeric secret
generate_secret() {
    openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32
}

# Generate Fernet encryption key (URL-safe base64, 32 bytes)
generate_fernet_key() {
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
}

# Create or update a Docker secret
create_secret() {
    local secret_name=$1
    local secret_value=$2

    # Check if secret already exists
    if docker secret inspect "$secret_name" >/dev/null 2>&1; then
        echo -e "${YELLOW}Secret '$secret_name' already exists, skipping...${NC}"
        return 0
    fi

    # Create the secret
    echo "$secret_value" | docker secret create "$secret_name" - >/dev/null
    echo -e "${GREEN}Created secret: $secret_name${NC}"
}

# Check if Docker Swarm is initialized
if ! docker info | grep -q "Swarm: active"; then
    echo -e "${RED}Error: Docker Swarm is not initialized${NC}"
    echo "Run: docker swarm init"
    exit 1
fi

echo "Creating Docker Swarm secrets..."
echo ""

# Create db_password
DB_PASSWORD="${DB_PASSWORD:-$(generate_secret)}"
create_secret "db_password" "$DB_PASSWORD"

# Create secret_key
SECRET_KEY="${SECRET_KEY:-$(generate_secret)}"
create_secret "secret_key" "$SECRET_KEY"

# Create jwt_secret
JWT_SECRET="${JWT_SECRET:-$(generate_secret)}"
create_secret "jwt_secret" "$JWT_SECRET"

# Create credential_encryption_key (Fernet format)
if [ -z "$CREDENTIAL_ENCRYPTION_KEY" ]; then
    # Check if Python and cryptography are available
    if command -v python3 >/dev/null 2>&1 && python3 -c "import cryptography" 2>/dev/null; then
        CREDENTIAL_ENCRYPTION_KEY=$(generate_fernet_key)
    else
        echo -e "${YELLOW}Warning: Python cryptography not available, using base64 fallback${NC}"
        CREDENTIAL_ENCRYPTION_KEY=$(openssl rand -base64 32)
    fi
fi
create_secret "credential_encryption_key" "$CREDENTIAL_ENCRYPTION_KEY"

# Create flower_auth (format: user:password)
FLOWER_AUTH="${FLOWER_AUTH:-admin:$(generate_secret)}"
create_secret "flower_auth" "$FLOWER_AUTH"

echo ""
echo -e "${GREEN}Secrets creation complete!${NC}"
echo ""
echo "List secrets with: docker secret ls"
echo "Inspect a secret with: docker secret inspect <secret_name>"
echo ""
echo -e "${YELLOW}Note: Secret values cannot be retrieved after creation.${NC}"
echo "If you need to use these values elsewhere, save them now:"
echo "  DB_PASSWORD: [generated]"
echo "  SECRET_KEY: [generated]"
echo "  JWT_SECRET: [generated]"
echo "  CREDENTIAL_ENCRYPTION_KEY: [generated]"
echo "  FLOWER_AUTH: [generated]"
