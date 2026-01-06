# MISSION: Unified Trading Engine — End-to-End Recovery and Integration in Docker Swarm

You are operating inside an existing production-bound codebase. Your job is NOT to redesign or refactor the system, but to DISCOVER the real state, UNBLOCK broken infrastructure, ITERATE to GREEN, and then COMPLETE frontend ↔ backend integration using LIVE data.

## ABSOLUTE RULES (NON-NEGOTIABLE):
- Do NOT rewrite the application or introduce new architectures.
- Do NOT break any currently working API endpoints.
- Make small, atomic, testable changes only.
- Everything must be runnable via terminal commands.
- Prefer wiring and deployment fixes over refactors.
- If something is already running, wire to it — do not replace it.
- Do NOT assume ports, IPs, service names, or paths — only use what you discover from files or live Docker output.
- Log every meaningful action and append changes to INTEGRATION_REPORT.md.

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
- Locate frontend root
- Locate backend root
- Locate Docker stack / compose files
- Locate nginx configuration
- Locate env files
- Locate broker SDK modules

2) Runtime discovery:
- List docker stacks, services, tasks
- Capture failing services and exact error messages
- Identify missing images
- Identify rejected tasks and why
- Identify networks, DNS service names, published ports

3) Backend verification:
- Confirm backend health endpoint
- Confirm OpenAPI or route definitions
- Inventory available broker endpoints

Output: a factual DISCOVERY section in INTEGRATION_REPORT.md.
Do NOT fix anything until discovery is complete.

────────────────────────────
PHASE 2 — UNBLOCK INFRASTRUCTURE (MUST TURN GREEN)
────────────────────────────
Fix only what is required to make the platform runnable.

Hard requirements:
- Resolve missing UI Docker image (find correct Dockerfile, build/tag/push if needed).
- Resolve Swarm task rejects caused by missing bind mount paths OR apply minimal placement constraints.
- Resolve NGINX upstream DNS failures by aligning service names and networks.
- Redeploy stack after each fix and re-check status.

Stop condition:
- Docker stack converges
- UI service runs
- NGINX can resolve UI upstream
- No rejected tasks remain

Document each fix immediately in INTEGRATION_REPORT.md.

────────────────────────────
PHASE 3 — INTEGRATION PLANNING
────────────────────────────
Once infrastructure is GREEN:

- Identify frontend framework and API client pattern
- Locate all mock/demo data usage
- Read backend OpenAPI or router definitions
- Produce a mapping table:
  FRONTEND COMPONENT → BACKEND ENDPOINT → DATA SHAPE → TRANSFORM

────────────────────────────
PHASE 4 — IMPLEMENTATION (MOCK → LIVE)
────────────────────────────
- Introduce a single API base URL env variable (framework-appropriate).
- Wire frontend API calls to live backend endpoints.
- Remove mock data incrementally, screen by screen.
- Add loading and error handling.
- Do NOT hardcode credentials or secrets.
- Add backend endpoints ONLY if missing; do not break existing ones.
- Ensure CORS is correct for the UI origin.

────────────────────────────
PHASE 5 — VALIDATION
────────────────────────────
- Verify inter-service DNS inside Swarm.
- Verify env vars are injected into containers.
- Verify production UI build runs.
- Smoke test:
  - backend health
  - UI loads live data
  - basic trading flows execute or fail gracefully if creds missing

────────────────────────────
PHASE 6 — DELIVERABLES
────────────────────────────
You MUST produce:

1) INTEGRATION_REPORT.md including:
- Architecture overview
- What was broken and how it was fixed
- Endpoint inventory
- UI → API mapping table
- Required env vars
- Exact deployment commands
- GREEN CHECK verification commands

2) .env.example with all required variables (no secrets)

Execution mode:
- After every 3–5 commands, summarize findings and next steps.
- Do not advance phases unless the current phase is GREEN.
- If blocked, document the blocker with exact evidence.

END STATE:
The Unified Trading Engine UI runs in Docker Swarm, displays LIVE backend data, routes orders end-to-end, and the stack is stable and documented.
