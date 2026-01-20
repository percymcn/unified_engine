# Docker Stack Verification Guide

This document outlines the verification steps for the complete production stack deployment.

## Prerequisites

1. Docker Swarm initialized: `docker swarm init`
2. Private registry available at 192.168.1.254:5000
3. Host directories exist: `/data/unified-engine/postgres` and `/data/unified-engine/redis`

## Deployment Steps

### 1. Create Secrets (if not already created)

```bash
cd /home/pharma5/unified_engine
./scripts/create-secrets.sh
```

Verify secrets:
```bash
docker secret ls
```

Expected secrets:
- db_password
- secret_key
- jwt_secret
- credential_encryption_key
- flower_auth

### 2. Create Configs

```bash
./scripts/create-configs.sh
```

Verify configs:
```bash
docker config ls
```

Expected: `unified_nginx_conf_v2`

### 3. Create Host Directories

```bash
sudo mkdir -p /data/unified-engine/postgres
sudo mkdir -p /data/unified-engine/redis
sudo chown -R 999:999 /data/unified-engine/postgres  # postgres user
sudo chown -R 1000:1000 /data/unified-engine/redis    # redis user
```

### 4. Deploy Stack

```bash
./scripts/deploy.sh production
```

This will:
- Load production environment variables
- Deploy the stack to Docker Swarm
- Name: unified-production

### 5. Verify Services

Check all services are running:
```bash
docker stack services unified-production
```

Expected services (all with 1/1 replicas):
- unified-production_api
- unified-production_postgres
- unified-production_redis
- unified-production_nats
- unified-production_celery-worker
- unified-production_celery-beat
- unified-production_flower
- unified-production_ui
- unified-production_nginx
- unified-production_funnel-automation

### 6. Check Health Checks

All services should show "healthy" status:
```bash
docker service ps unified-production_api
docker service ps unified-production_postgres
docker service ps unified-production_redis
docker service ps unified-production_nats
docker service ps unified-production_celery-worker
docker service ps unified-production_ui
```

### 7. Test Endpoints

Test each service endpoint:

```bash
# Nginx (reverse proxy)
curl http://localhost:3013/health
# Expected: ok

# API (direct)
curl http://localhost:3012/health
# Expected: {"status":"healthy"}

# UI (Next.js)
curl http://localhost:3411/api/health
# Expected: {"status":"ok","service":"unified-ui-next"}

# NATS monitoring
curl http://localhost:8223/healthz
# Expected: NATS health info

# Flower (Celery monitoring)
# Open browser: http://localhost:5558
# Login with credentials from flower_auth secret
```

### 8. Check Service Logs

Inspect logs for any errors:
```bash
docker service logs unified-production_api --tail 50
docker service logs unified-production_celery-worker --tail 50
docker service logs unified-production_ui --tail 50
docker service logs unified-production_nginx --tail 50
```

### 9. Test Data Persistence

Test that data survives stack restart:

```bash
# Remove stack
docker stack rm unified-production

# Wait for services to stop
watch docker stack ps unified-production

# Redeploy
./scripts/deploy.sh production

# Verify data intact (check logs for database migrations, etc.)
docker service logs unified-production_postgres --tail 50
```

## Troubleshooting

### Service not starting

```bash
# Check service details
docker service ps unified-production_<service-name> --no-trunc

# Check logs
docker service logs unified-production_<service-name>
```

### Health check failing

```bash
# Get container ID
docker ps | grep <service-name>

# Execute health check manually
docker exec <container-id> <health-check-command>
```

### Secret not mounted

```bash
# Check secret exists
docker secret ls

# Check service has secret
docker service inspect unified-production_<service-name> | grep -A 5 Secrets

# Check inside container
docker exec <container-id> ls -la /run/secrets/
```

### Volume not mounting

```bash
# Check host directory exists
ls -la /data/unified-engine/

# Check permissions
stat /data/unified-engine/postgres
stat /data/unified-engine/redis

# Check volume mount in service
docker service inspect unified-production_<service-name> | grep -A 10 Mounts
```

## Success Criteria

Stack is healthy when:

- [ ] All services show 1/1 replicas
- [ ] All health checks pass
- [ ] All endpoints return expected responses
- [ ] No error logs in service outputs
- [ ] Stack survives restart with data intact
- [ ] Nginx correctly routes traffic to backend and UI
- [ ] WebSocket connections work through nginx
- [ ] Secrets are mounted at /run/secrets/
- [ ] No hardcoded passwords visible in stack configuration
- [ ] Postgres uses POSTGRES_PASSWORD_FILE pattern

## Monitoring

Continuous monitoring commands:

```bash
# Watch service status
watch docker stack services unified-production

# Follow API logs
docker service logs -f unified-production_api

# Follow UI logs
docker service logs -f unified-production_ui

# Check resource usage
docker stats
```
