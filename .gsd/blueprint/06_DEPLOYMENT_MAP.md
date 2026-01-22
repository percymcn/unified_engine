# Deployment Map: Unified Trading Engine

## Docker Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Main backend image |
| `Dockerfile.backend` | Alternative backend build |
| `Dockerfile.stack` | Swarm-optimized backend |
| `ui-next/Dockerfile` | Frontend image |
| `docker-compose.yml` | Local development |
| `docker-compose.prod.yml` | Production compose |
| `docker-stack.yml` | Docker Swarm deployment |

## Local Development Setup

### 1. Start Infrastructure

```bash
cd /home/pharma5/unified_engine

# Start PostgreSQL and Redis only
docker compose up -d postgres redis

# Verify
docker compose ps
# postgres: 0.0.0.0:5432
# redis: 0.0.0.0:6379
```

### 2. Backend (Outside Docker)

```bash
# Activate Python environment
source venv/bin/activate

# Set environment
export DATABASE_URL="postgresql://trading_user:trading_password@localhost:5432/trading_db"
export REDIS_URL="redis://localhost:6379/0"

# Run migrations
python -m alembic upgrade head

# Start backend
python run_backend.py
# OR
uvicorn app.main:app --host 0.0.0.0 --port 8765 --reload
```

### 3. Frontend (Outside Docker)

```bash
cd ui-next
npm install

# Development
PORT=3456 npm run dev

# Production
npm run build
PORT=3456 npm run start
```

## Production Deployment (Docker Swarm)

### Prerequisites

```bash
# Initialize swarm (if not already)
docker swarm init

# Create secrets
echo "trading_password" | docker secret create db_password -
echo "your-jwt-secret" | docker secret create jwt_secret -
echo "your-secret-key" | docker secret create secret_key -
echo "your-fernet-key" | docker secret create credential_encryption_key -
```

### Deploy Stack

```bash
# Build images
docker build -t 192.168.1.254:5000/unified-engine/api:latest -f Dockerfile.stack .
cd ui-next && docker build -t 192.168.1.254:5000/unified-engine/ui:latest .

# Push to registry
docker push 192.168.1.254:5000/unified-engine/api:latest
docker push 192.168.1.254:5000/unified-engine/ui:latest

# Deploy
docker stack deploy -c docker-stack.yml unified
```

### Stack Services

```yaml
# docker-stack.yml services
services:
  postgres:
    image: postgres:15
    # Internal only (overlay network)

  redis:
    image: redis:7-alpine
    # Internal only

  nats:
    image: nats:2.10-alpine
    ports:
      - "4223:4222"  # Client connections
      - "8223:8223"  # HTTP monitoring

  api:
    image: 192.168.1.254:5000/unified-engine/api:latest
    ports:
      - "8765:8000"  # External:Internal
    deploy:
      replicas: 1

  ui:
    image: 192.168.1.254:5000/unified-engine/ui:latest
    ports:
      - "3456:3000"  # External:Internal
    deploy:
      replicas: 1

  cloudflared:
    image: cloudflare/cloudflared:latest
    # Tunnel to Cloudflare
```

## Port Allocation

### Development Ports

| Service | Port | Notes |
|---------|------|-------|
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache |
| FastAPI Backend | 8765 | API server |
| Next.js UI | 3456 | Frontend (Cloudflare expects this) |
| NATS | 4222 | Message bus (optional) |

### Production Ports (Swarm)

| Service | External | Internal | Notes |
|---------|----------|----------|-------|
| API | 8765 | 8000 | Backend |
| UI | 3456 | 3000 | Frontend |
| NATS | 4223 | 4222 | Message bus |
| NATS HTTP | 8223 | 8223 | Monitoring |

## Environment Variables

### Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_NAME` | No | "Unified Trading Engine" | Application name |
| `APP_VERSION` | No | "1.0.0" | Version string |
| `ENVIRONMENT` | Yes | "development" | dev/staging/production |
| `DEBUG` | No | false | Debug mode |
| `SECRET_KEY` | Yes | - | App secret key |
| `HOST` | No | "0.0.0.0" | Bind host |
| `PORT` | No | 8000 | Bind port |

### Database

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Full PostgreSQL URL |
| `DB_HOST` | No | Database host |
| `DB_PORT` | No | Database port |
| `DB_NAME` | No | Database name |
| `DB_USER` | No | Database user |
| `DB_PASSWORD` | No | Database password |
| `DB_POOL_SIZE` | No | Connection pool size |

### Redis

| Variable | Required | Description |
|----------|----------|-------------|
| `REDIS_URL` | Yes | Full Redis URL |
| `REDIS_HOST` | No | Redis host |
| `REDIS_PORT` | No | Redis port |
| `REDIS_DB` | No | Redis database number |
| `REDIS_PASSWORD` | No | Redis password |

### JWT/Auth

| Variable | Required | Description |
|----------|----------|-------------|
| `JWT_SECRET_KEY` | Yes | JWT signing key |
| `JWT_ALGORITHM` | No | "HS256" |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | 30 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | 7 |

### Credentials

| Variable | Required | Description |
|----------|----------|-------------|
| `CREDENTIAL_ENCRYPTION_KEY` | Yes | Fernet key for credential encryption |

### TradeLocker

| Variable | Description |
|----------|-------------|
| `TRADELOCKER_USERNAME` | SDK mode email |
| `TRADELOCKER_PASSWORD` | SDK mode password |
| `TRADELOCKER_SERVER` | Server name |
| `TRADELOCKER_ENVIRONMENT` | Environment URL |
| `TRADELOCKER_BRAND_API_URL` | Brand API URL |
| `TRADELOCKER_BRAND_ID` | Brand ID |

### ProjectX/TopStep

| Variable | Description |
|----------|-------------|
| `PROJECT_X_USERNAME` | TopStep username |
| `PROJECT_X_API_KEY` | API key |
| `PROJECTX_GATEWAY_API_URL` | Gateway API URL |

### Tradovate

| Variable | Description |
|----------|-------------|
| `TRADOVATE_API_URL` | REST API URL |
| `TRADOVATE_WS_URL` | WebSocket URL |
| `TRADOVATE_CLIENT_ID` | OAuth client ID |
| `TRADOVATE_CLIENT_SECRET` | OAuth client secret |
| `TRADOVATE_OAUTH_REDIRECT_URI` | OAuth callback URL |

### MT4/MT5

| Variable | Description |
|----------|-------------|
| `MT4_MANAGER_API_URL` | Manager API URL |
| `MT4_MANAGER_LOGIN` | Manager login |
| `MT4_MANAGER_PASSWORD` | Manager password |
| `MT5_MANAGER_API_URL` | Manager API URL |
| `MT5_MANAGER_LOGIN` | Manager login |
| `MT5_MANAGER_PASSWORD` | Manager password |

### Stripe

| Variable | Description |
|----------|-------------|
| `STRIPE_SECRET_KEY` | Stripe API key |
| `STRIPE_PUBLISHABLE_KEY` | Public key |
| `STRIPE_WEBHOOK_SECRET` | Webhook signing secret |
| `STRIPE_PRICE_ID_BASIC` | Basic plan price ID |
| `STRIPE_PRICE_ID_PRO` | Pro plan price ID |

### NATS

| Variable | Description |
|----------|-------------|
| `NATS_URL` | NATS connection URL |

## Cloudflare Tunnel

The system uses Cloudflare Tunnel for external access:

```
tradeflow.fluxeo.net → localhost:3456 (UI)
api.tradeflow.fluxeo.net → localhost:8765 (API)
```

Tunnel runs in Docker:
```yaml
cloudflared:
  image: cloudflare/cloudflared:latest
  command: tunnel --no-autoupdate run --token <TOKEN>
```

---
*Generated: 2026-01-22*
