# PHASE 0 & 1: Safety Snapshot + Discovery

## ABSOLUTE RULES (NON-NEGOTIABLE):
- Do NOT fix anything yet - only DISCOVER and DOCUMENT
- Do NOT break any currently working API endpoints
- Make small, atomic, testable changes only
- Everything must be runnable via terminal commands
- Log every meaningful action and append changes to INTEGRATION_REPORT.md

────────────────────────────
PHASE 0 — SAFETY SNAPSHOT
────────────────────────────
Before modifying anything:
- Capture date, hostname, pwd
- Capture git status
- Capture docker version and docker info
- Create logs/integration_run_<timestamp>/
- Tee important terminal output into logs

────────────────────────────
PHASE 1 — DISCOVERY (NO FIXES YET)
────────────────────────────
Discover and document the actual system state.

1) Project discovery:
- Map directory structure
- Locate frontend root (ui/)
- Locate backend root (app/)
- Locate Docker stack / compose files (docker-compose.yml, docker-stack.yml)
- Locate nginx configuration (nginx.conf, nginx-reverse-proxy.conf)
- Locate env files (.env, .env.example)
- Locate broker SDK modules (broker_sdks/)

2) Runtime discovery:
- List docker stacks: `docker stack ls`
- List services: `docker service ls`
- List tasks: `docker service ps <service-name>`
- Capture failing services and exact error messages
- Identify missing images: `docker images`
- Identify rejected tasks and why
- Identify networks: `docker network ls`
- Identify DNS service names and published ports

3) Backend verification:
- Confirm backend health endpoint (try: curl http://localhost:<port>/api/health)
- Confirm OpenAPI docs (try: curl http://localhost:<port>/docs or /openapi.json)
- Inventory available broker endpoints from app/routers/

Output: Create/update INTEGRATION_REPORT.md with a factual DISCOVERY section.
Do NOT fix anything until discovery is complete.

## Success Criteria
- INTEGRATION_REPORT.md created/updated with discovery findings
- All Docker services documented with status
- All endpoints documented
- All configuration files located
- No fixes attempted yet
