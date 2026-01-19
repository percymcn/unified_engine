# Technology Stack

**Analysis Date:** 2026-01-19

## Languages

**Primary:**
- Python 3.13.7 - Backend application and all core services
- TypeScript/JavaScript - Frontend UI application

**Secondary:**
- SQL - Database schema and migrations (PostgreSQL)
- Shell - Deployment and automation scripts

## Runtime

**Environment:**
- Python 3.13.7 (backend)
- Node.js v20.19.4 (frontend)

**Package Manager:**
- pip - Python dependencies
- npm - JavaScript dependencies
- Lockfile: `package-lock.json` present for frontend, `requirements.txt` for backend

## Frameworks

**Core:**
- FastAPI 0.104.1 - Primary backend web framework
- Uvicorn 0.24.0 - ASGI server for FastAPI
- React 18.3.1 - Frontend UI framework
- Vite 6.3.5 - Frontend build tool and dev server

**Testing:**
- pytest 7.4.3 - Backend testing framework
- pytest-asyncio 0.21.1 - Async test support
- No frontend testing framework currently configured

**Build/Dev:**
- Vite 6.3.5 - Frontend bundler with HMR
- @vitejs/plugin-react-swc 3.10.2 - React plugin with SWC compiler
- Alembic 1.13.1 - Database migration tool
- Docker - Containerization (Dockerfile, docker-compose.yml)

## Key Dependencies

**Critical:**
- SQLAlchemy 2.0.23 - ORM and database abstraction layer
- asyncpg 0.29.0 - Async PostgreSQL driver
- psycopg2-binary 2.9.9 - PostgreSQL adapter
- redis 5.0.1 - Redis client for caching and sessions
- aioredis 2.0.1 - Async Redis client
- pydantic 2.5.0 - Data validation and settings management
- pydantic-settings 2.1.0 - Environment configuration

**Infrastructure:**
- Celery 5.3.4 - Distributed task queue
- Flower 2.0.1 - Celery monitoring UI
- prometheus-client 0.19.0 - Metrics collection
- websockets 12.0 - WebSocket support
- python-socketio 5.10.0 - Socket.IO implementation
- nats-py 2.6.0 - NATS messaging (optional, graceful fallback)

**Security:**
- python-jose[cryptography] 3.3.0 - JWT token handling
- passlib[bcrypt] 1.7.4 - Password hashing

**HTTP/Networking:**
- httpx 0.25.2 - Modern async HTTP client
- aiohttp 3.9.1 - Async HTTP client/server

**Frontend UI:**
- @supabase/supabase-js 2.49.8 - Supabase client for auth
- @radix-ui/* 1.x - UI component primitives (30+ packages)
- recharts 2.15.2 - Charting library
- react-hook-form 7.55.0 - Form state management
- lucide-react 0.487.0 - Icon library
- tailwind-merge - Utility for merging Tailwind classes
- class-variance-authority 0.7.1 - CVA for component variants

## Configuration

**Environment:**
- Configuration via `.env` file (pydantic-settings based)
- Template: `.env.example` with comprehensive broker/service configs
- Secrets: `.env.secrets` for sensitive values
- Dynamic port detection: `run_backend.py` script finds free ports automatically
- Frontend: Vite env vars with `VITE_` prefix

**Build:**
- Backend: `requirements.txt` for dependencies
- Frontend: `ui/package.json` with ESM modules (`"type": "module"`)
- Docker: Multi-stage builds with `Dockerfile`, `Dockerfile.backend`, `Dockerfile.demo`, `Dockerfile.stack`
- Docker Compose: `docker-compose.yml` (dev), `docker-compose.prod.yml` (production), `docker-compose.demo.yml` (demo)
- Vite config: `ui/vite.config.ts` with path aliases (`@` -> `./src`)

## Platform Requirements

**Development:**
- Python >= 3.9 (running 3.13.7)
- Node.js >= 18.0.0
- npm >= 9.0.0
- PostgreSQL 15
- Redis 7
- Docker & Docker Compose (optional but recommended)

**Production:**
- Deployment target: Docker containers orchestrated via docker-compose
- Reverse proxy: Nginx (configured in `nginx.conf`)
- Monitoring: Prometheus + Grafana stack (optional)
- Hosting: Designed for containerized deployment (Fluxeo platform integration)

---

*Stack analysis: 2026-01-19*
