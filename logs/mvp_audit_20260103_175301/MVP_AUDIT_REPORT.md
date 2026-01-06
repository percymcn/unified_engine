# MVP Audit Report - Unified Trading Engine

Timestamp: 2026-01-03 17:53:01 EST
Host: pharma5
Repo: /home/pharma5/unified_engine

## Expected Architecture (from repo)
- Backend: FastAPI app in `app/main.py` with health at `/health`, running on 8000.
- UI: React/Vite app in `ui/`, build output `ui/build`, Nginx container serving on port 80.
- Swarm stack file: `docker-stack.yml` publishes API on 3012, UI on 3411, Nginx on 3013, Flower on 5558.
- Compose files also reference API on 8000, UI on 3000, Redis 6379, Postgres 5432.

## LAN IP(s)
- 192.168.1.254 (Docker Swarm manager address from `docker info`)

## What Is Actually Running
### Swarm stacks (relevant)
- `unified_engine_stack` is present with API/DB/Redis running; UI/NGINX/Flower are not running.
- `trading` stack is present; API/DB/Redis running; UI/NGINX/Flower are not running.

### Unified Engine services (Swarm)
- `unified_engine_stack_api` is running 1/2 replicas. Published: 3012 -> 8000.
- `unified_engine_stack_postgres` running 1/1.
- `unified_engine_stack_redis` running 1/1.
- `unified_engine_stack_ui` 0/1 (image missing on nodes).
- `unified_engine_stack_nginx` 0/1 (fails due to missing UI upstream).
- `unified_engine_stack_flower` 0/1.

### Containers related to unified_engine
- `unified_engine_stack_api.*` (swarm task) running.
- `unified_engine_stack_postgres.*` and `unified_engine_stack_redis.*` running.
- `unified_trading_api` container exists but has no published port.

## UI Status
- UI build output exists locally: `ui/build/index.html`.
- UI image `unified-engine/ui:latest` is NOT present locally.
- Swarm UI service fails on both `unified_engine_stack_ui` and `trading_ui` with error:
  - `No such image: unified-engine/ui:latest`.
- Published UI port 3411 is not reachable.

UI URLs:
- Expected (Swarm): http://192.168.1.254:3411 (DOWN)

## Backend Status
### Unified Engine API (Swarm)
- URL: http://192.168.1.254:3012
- `/` returns 200 (API alive)
- `/health` returns 200 (Redis connected; brokers mostly connected)
- `/openapi.json` returns 200

Backend URLs:
- API: http://192.168.1.254:3012
- OpenAPI: http://192.168.1.254:3012/openapi.json
- Health: http://192.168.1.254:3012/health

### Other backends (not part of unified_engine MVP)
- A separate service responds on 8000 (`FluxEmpire Master Control API`), not part of this repo.

## End-to-End MVP Smoke Test
- UI -> API -> DB: **FAIL** (UI not running; NGINX not running; UI image missing)
- API health: **PASS** (HTTP 200 on `/health`)
- DB/Redis: **RUNNING** (Swarm services 1/1)

## What Is Missing / Broken
1) UI image missing on Swarm nodes.
   - Evidence: `No such image: unified-engine/ui:latest` in `docker service ps unified_engine_stack_ui`.
2) NGINX service fails because UI service is not resolvable.
   - Evidence: `host not found in upstream "unified_engine_stack_ui:80"` in service logs.
3) Swarm replicas fail on pharma4 due to missing bind mount paths.
   - Evidence: `invalid mount config ... /home/pharma5/unified_engine/data` and `/home/pharma5/unified_engine/logs`.

## Evidence Files
- Phase 0 snapshot: `logs/mvp_audit_20260103_175301/phase0_*`
- Docker/Swarm status: `logs/mvp_audit_20260103_175301/phase0_swarm.txt`
- Service failures: `logs/mvp_audit_20260103_175301/phase2_service_ps.txt`
- NGINX/API logs: `logs/mvp_audit_20260103_175301/phase2_service_logs.txt`
- API health: `logs/mvp_audit_20260103_175301/phase4_api_health_3012.txt`

