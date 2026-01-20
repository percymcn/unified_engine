# Deployment Guide

## Environments

- **development**: Local development with docker-compose
- **staging**: Pre-production testing with Docker Swarm
- **production**: Live deployment with Docker Swarm + secrets

## Quick Start

### Development
```bash
cp deploy/envs/.env.development .env
docker-compose up -d
```

### Staging/Production
```bash
# 1. Initialize secrets (first time only)
./scripts/create-secrets.sh

# 2. Deploy
./scripts/deploy.sh production
```

## Environment Variables
See `.env.example` for all available variables.
