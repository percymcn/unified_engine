# Deployment Guide - Enterprise SaaS Platform

## Overview

This guide covers deployment options for the Unified Trading Engine enterprise SaaS platform.

---

## Docker Deployment (Recommended)

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+

### Quick Start

```bash
# Clone repository
git clone <repository-url>
cd unified_engine

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down
```

### Services

- **API**: Backend FastAPI service (port 8000)
- **UI**: Frontend Nginx service (port 3000)
- **PostgreSQL**: Database (port 5432)
- **Redis**: Cache (port 6379)
- **Celery**: Background worker (optional)

---

## AWS Deployment

### Option 1: ECS (Elastic Container Service)

#### Prerequisites
- AWS CLI configured
- ECR repository created
- ECS cluster created

#### Steps

1. **Build and push images**
```bash
# Build backend
docker build -f Dockerfile.backend -t unified-engine-backend .

# Build frontend
cd ui && docker build -f Dockerfile -t unified-engine-frontend .

# Tag and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag unified-engine-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/unified-engine-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/unified-engine-backend:latest
```

2. **Create ECS Task Definition**
```json
{
  "family": "unified-engine",
  "networkMode": "awsvpc",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/unified-engine-backend:latest",
      "portMappings": [{"containerPort": 8000}],
      "environment": [
        {"name": "DATABASE_URL", "value": "postgresql://..."},
        {"name": "REDIS_URL", "value": "redis://..."}
      ]
    }
  ]
}
```

3. **Deploy to ECS**
```bash
aws ecs create-service \
  --cluster unified-engine-cluster \
  --service-name unified-engine-api \
  --task-definition unified-engine \
  --desired-count 2 \
  --launch-type FARGATE
```

### Option 2: EC2 with Docker Compose

1. **Launch EC2 instance** (Ubuntu 22.04 LTS)
2. **Install Docker**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker ubuntu
```

3. **Install Docker Compose**
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

4. **Deploy application**
```bash
git clone <repository-url>
cd unified_engine
cp .env.example .env
# Edit .env
docker-compose -f docker-compose.prod.yml up -d
```

5. **Setup Nginx reverse proxy** (optional)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
    }

    location /api {
        proxy_pass http://localhost:8000;
    }
}
```

---

## GCP Deployment

### Cloud Run

1. **Build and push to GCR**
```bash
gcloud builds submit --tag gcr.io/<project-id>/unified-engine-backend
```

2. **Deploy to Cloud Run**
```bash
gcloud run deploy unified-engine-api \
  --image gcr.io/<project-id>/unified-engine-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=...,REDIS_URL=...
```

### Cloud SQL Setup
```bash
gcloud sql instances create unified-engine-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1
```

---

## Render.com Deployment

### Backend Service

1. **Create new Web Service**
2. **Connect GitHub repository**
3. **Configure:**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python run_backend.py`
   - **Environment**: Python 3.9

4. **Environment Variables:**
   - `DATABASE_URL`: Render PostgreSQL connection string
   - `REDIS_URL`: Render Redis connection string
   - `SECRET_KEY`: Generate secure key
   - `ENVIRONMENT`: production

### Frontend Service

1. **Create new Static Site**
2. **Build Command**: `cd ui && npm install && npm run build`
3. **Publish Directory**: `ui/dist`

---

## Railway Deployment

1. **Install Railway CLI**
```bash
npm i -g @railway/cli
railway login
```

2. **Initialize project**
```bash
railway init
railway link
```

3. **Add services**
```bash
# Add PostgreSQL
railway add postgresql

# Add Redis
railway add redis

# Deploy backend
railway up
```

4. **Set environment variables**
```bash
railway variables set DATABASE_URL=$DATABASE_URL
railway variables set REDIS_URL=$REDIS_URL
railway variables set SECRET_KEY=$SECRET_KEY
```

---

## Environment Variables

### Required
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: Secret key for JWT (generate with `openssl rand -hex 32`)

### Optional
- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: 0.0.0.0)
- `ENVIRONMENT`: production/development
- `SMTP_HOST`: Email server host
- `SMTP_PORT`: Email server port
- `SMTP_USER`: Email username
- `SMTP_PASSWORD`: Email password

---

## Health Checks

### Backend
```bash
curl https://your-api.com/health
```

### Frontend
```bash
curl https://your-frontend.com/health
```

---

## Monitoring

### Logs
```bash
# Docker
docker-compose logs -f api

# ECS
aws logs tail /ecs/unified-engine --follow

# Cloud Run
gcloud run services logs read unified-engine-api --follow
```

### Metrics
- Backend metrics: `http://your-api.com/metrics`
- Health endpoint: `http://your-api.com/health`

---

## Scaling

### Horizontal Scaling
- Backend: Deploy multiple instances behind load balancer
- Frontend: Use CDN (CloudFront, Cloudflare)
- Database: Use read replicas for read-heavy workloads

### Vertical Scaling
- Increase instance sizes
- Optimize database queries
- Add Redis caching

---

## Security Checklist

- [ ] Use HTTPS (SSL/TLS certificates)
- [ ] Set secure `SECRET_KEY`
- [ ] Enable database encryption
- [ ] Configure firewall rules
- [ ] Use environment variables for secrets
- [ ] Enable CORS only for trusted domains
- [ ] Set up rate limiting
- [ ] Enable audit logging
- [ ] Regular security updates
- [ ] Backup database regularly

---

## Backup & Recovery

### Database Backup
```bash
# PostgreSQL backup
pg_dump $DATABASE_URL > backup.sql

# Restore
psql $DATABASE_URL < backup.sql
```

### Automated Backups
- Use managed database services with automated backups
- Set up cron jobs for manual backups
- Store backups in S3/GCS

---

## Troubleshooting

### Service won't start
- Check logs: `docker-compose logs api`
- Verify environment variables
- Check database connectivity
- Verify Redis connectivity

### High memory usage
- Check for memory leaks
- Optimize queries
- Increase instance size
- Use connection pooling

### Slow performance
- Check database indexes
- Enable Redis caching
- Optimize API endpoints
- Use CDN for static assets

---

*Last Updated: 2025-01-27*
