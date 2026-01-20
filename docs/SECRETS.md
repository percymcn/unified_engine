# Docker Swarm Secrets Management

This document describes how secrets are managed in the unified trading engine deployment.

## Overview

All sensitive credentials are stored as Docker Swarm secrets instead of hardcoded values in `docker-stack.yml`.

## Secrets Used

| Secret Name | Purpose | Used By |
|-------------|---------|---------|
| `db_password` | PostgreSQL password | postgres, api, celery-worker, celery-beat, funnel-automation |
| `secret_key` | Application secret key | api, celery-worker, celery-beat, funnel-automation |
| `jwt_secret` | JWT signing key | api, celery-worker, celery-beat, funnel-automation |
| `credential_encryption_key` | Fernet encryption key for stored credentials | api, celery-worker, celery-beat, funnel-automation |
| `flower_auth` | Flower basic auth (format: user:password) | flower |

## Initial Setup

### 1. Initialize Docker Swarm

```bash
docker swarm init
```

### 2. Create Secrets

Use the provided script to create all required secrets:

```bash
./scripts/create-secrets.sh
```

This will:
- Generate cryptographically secure random values for each secret
- Create the secrets in Docker Swarm
- Display confirmation messages

**Optional:** Load secrets from environment file:

```bash
# Create .env.secrets file with your values
cat > .env.secrets <<EOF
DB_PASSWORD=your_db_password
SECRET_KEY=your_secret_key
JWT_SECRET=your_jwt_secret
CREDENTIAL_ENCRYPTION_KEY=your_fernet_key
FLOWER_AUTH=admin:your_password
EOF

# Create secrets from file
./scripts/create-secrets.sh .env.secrets
```

### 3. Verify Secrets

List all secrets:

```bash
docker secret ls
```

Expected output:
```
ID                          NAME                        CREATED          UPDATED
abc123...                   db_password                 2 seconds ago    2 seconds ago
def456...                   secret_key                  2 seconds ago    2 seconds ago
ghi789...                   jwt_secret                  2 seconds ago    2 seconds ago
jkl012...                   credential_encryption_key   2 seconds ago    2 seconds ago
mno345...                   flower_auth                 2 seconds ago    2 seconds ago
```

### 4. Deploy Stack

```bash
docker stack deploy -c docker-stack.yml unified
```

## How Secrets Are Used

### PostgreSQL

Uses the `_FILE` suffix pattern supported by the official PostgreSQL image:

```yaml
environment:
  POSTGRES_PASSWORD_FILE: /run/secrets/db_password
secrets:
  - db_password
```

### Application Services (API, Celery, Funnel Automation)

Secrets are mounted at `/run/secrets/{secret_name}` and read by the application at startup:

```python
from app.core.secrets import get_secret

# Automatically reads from /run/secrets/ or falls back to env vars
db_password = get_secret("db_password")
secret_key = get_secret("secret_key")
```

The `app/core/config.py` Settings class automatically loads secrets using validators.

### Flower

Reads the auth credentials from secret file in the command:

```yaml
command: sh -c 'celery -A app.tasks.celery_app flower --port=5555 --basic_auth=$$(cat /run/secrets/flower_auth)'
```

## Development vs Production

### Development (without Docker Swarm)

The application gracefully falls back to environment variables if Docker secrets are not available:

```bash
# Set in .env or export
export DB_PASSWORD=dev_password
export SECRET_KEY=dev_secret_key
export JWT_SECRET=dev_jwt_secret
export CREDENTIAL_ENCRYPTION_KEY=dev_fernet_key

# Run normally
uvicorn app.main:app --reload
```

### Production (with Docker Swarm)

Secrets are required:

1. Swarm must be initialized
2. Secrets must be created with `./scripts/create-secrets.sh`
3. Services will fail to start if secrets are missing

## Secret Rotation

To rotate a secret:

1. **Create new secret with different name:**
   ```bash
   echo "new_password_value" | docker secret create db_password_v2 -
   ```

2. **Update docker-stack.yml to reference new secret:**
   ```yaml
   secrets:
     db_password:
       name: db_password_v2
       external: true
   ```

3. **Redeploy stack:**
   ```bash
   docker stack deploy -c docker-stack.yml unified
   ```

4. **Remove old secret (after verification):**
   ```bash
   docker secret rm db_password
   ```

## Troubleshooting

### Secret not found

**Error:** `secret not found: db_password`

**Solution:** Create the secret:
```bash
./scripts/create-secrets.sh
```

### Service fails to start

**Check logs:**
```bash
docker service logs unified_api
```

**Common issues:**
- Secret file doesn't exist: Verify secret was created
- Permission denied: Check secret is mounted in service definition
- Invalid encryption key: Ensure CREDENTIAL_ENCRYPTION_KEY is valid Fernet format

### Can't read secret value

**By design:** Docker secrets cannot be retrieved after creation. If you need the value:
1. Save it when creating the secret
2. Or rotate the secret with a known value

### Development fallback not working

Ensure environment variables are set:

```bash
# Check if variables are set
env | grep -E "DB_PASSWORD|SECRET_KEY|JWT_SECRET|CREDENTIAL_ENCRYPTION_KEY"

# Set them if missing
export DB_PASSWORD=dev_password
```

## Security Best Practices

1. **Never commit secrets to git:** Use `.env.secrets` (add to `.gitignore`)
2. **Generate strong random values:** Use `./scripts/create-secrets.sh` default generation
3. **Rotate secrets regularly:** Especially after team member changes
4. **Use separate secrets per environment:** dev/staging/prod should have different values
5. **Limit secret access:** Only mount secrets in services that need them
6. **Audit secret usage:** Monitor logs for secret-related errors

## Testing

### Local Testing (Development)

```bash
# Set environment variables
export DB_PASSWORD=test_password
export SECRET_KEY=test_secret_key
export JWT_SECRET=test_jwt_secret
export CREDENTIAL_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Run application
uvicorn app.main:app --reload

# Verify secrets are loaded
curl http://localhost:8000/health
```

### Swarm Testing (Production-like)

```bash
# Initialize swarm (if not already)
docker swarm init

# Create test secrets
echo "testpassword" | docker secret create db_password -
echo "testsecretkey" | docker secret create secret_key -
echo "testjwtsecret" | docker secret create jwt_secret -
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" | docker secret create credential_encryption_key -
echo "admin:testflower" | docker secret create flower_auth -

# Deploy stack
docker stack deploy -c docker-stack.yml unified

# Verify services are running
docker service ls

# Check logs for secret loading
docker service logs unified_api | grep -i secret

# Verify no hardcoded passwords in logs
docker service logs unified_api | grep -i "trading_password"  # Should return nothing

# Test database connection
docker exec $(docker ps -q -f name=unified_api) python -c "from app.core.config import settings; print(settings.DATABASE_URL)"
# Should show URL with password from secret, not "trading_password"

# Cleanup
docker stack rm unified
docker secret rm db_password secret_key jwt_secret credential_encryption_key flower_auth
```

## References

- [Docker Secrets Documentation](https://docs.docker.com/engine/swarm/secrets/)
- [PostgreSQL Docker Image - Using Secrets](https://hub.docker.com/_/postgres)
- [Fernet Encryption](https://cryptography.io/en/latest/fernet/)
