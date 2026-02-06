#!/bin/bash
# Docker entrypoint script that loads secrets from files into environment variables

# Load secrets from files if they exist
load_secret() {
    local secret_name="$1"
    local env_var="$2"
    local secret_file="/run/secrets/$secret_name"

    if [ -f "$secret_file" ]; then
        export "$env_var"="$(cat $secret_file)"
        echo "Loaded secret: $env_var"
    fi
}

# Load all secrets
load_secret "db_password" "DB_PASSWORD"
load_secret "secret_key" "SECRET_KEY"
load_secret "jwt_secret" "JWT_SECRET"
load_secret "credential_encryption_key" "CREDENTIAL_ENCRYPTION_KEY"
load_secret "google_client_secret" "GOOGLE_CLIENT_SECRET"
load_secret "metaapi_token" "METAAPI_TOKEN"
load_secret "stripe_secret_key" "STRIPE_SECRET_KEY"
load_secret "stripe_webhook_secret" "STRIPE_WEBHOOK_SECRET"
load_secret "anthropic_api_key" "ANTHROPIC_API_KEY"

# Update DATABASE_URL with password if it was loaded
if [ -n "$DB_PASSWORD" ]; then
    # Replace @postgres: with :password@postgres: in DATABASE_URL
    if [ -n "$DATABASE_URL" ]; then
        export DATABASE_URL=$(echo "$DATABASE_URL" | sed "s|@postgres:|:${DB_PASSWORD}@postgres:|")
    fi
fi

# Execute the main command
exec "$@"
