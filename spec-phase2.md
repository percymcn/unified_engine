# PHASE 2: Unblock Infrastructure (MUST TURN GREEN)

## Prerequisites
- Phase 1 (Discovery) must be complete
- INTEGRATION_REPORT.md must exist with discovery findings

## ABSOLUTE RULES:
- Fix only what is required to make the platform runnable
- Make small, atomic, testable changes
- Redeploy stack after each fix and re-check status
- Document each fix immediately in INTEGRATION_REPORT.md

────────────────────────────
PHASE 2 — UNBLOCK INFRASTRUCTURE
────────────────────────────
Fix only what is required to make the platform runnable.

Hard requirements:
1. Resolve missing UI Docker image
   - Find correct Dockerfile (check ui/Dockerfile or root Dockerfile)
   - Build image: `docker build -t <image-name> <path>`
   - Tag appropriately for registry
   - Push if using registry

2. Resolve Swarm task rejects
   - Fix missing bind mount paths OR apply minimal placement constraints
   - Check docker-stack.yml for volume mounts
   - Either create paths on all nodes OR use Docker volumes instead of bind mounts
   - OR add placement constraints to run only on specific node

3. Resolve NGINX upstream DNS failures
   - Align service names in nginx.conf with actual Docker service names
   - Ensure services are on the same network
   - Verify service discovery works: `docker service inspect <service>`

4. Redeploy and verify
   - After each fix: `docker stack deploy -c docker-stack.yml <stack-name>`
   - Check status: `docker service ls`
   - Verify no rejected tasks: `docker service ps <service-name>`

Stop condition (ALL must be GREEN):
- ✅ Docker stack converges (no rejected tasks)
- ✅ UI service runs (docker service ps shows running)
- ✅ NGINX can resolve UI upstream (check nginx logs)
- ✅ No rejected tasks remain

Document each fix immediately in INTEGRATION_REPORT.md with:
- What was broken
- How it was fixed
- Commands used
- Verification steps

## Success Criteria
- All Docker services running (no rejected tasks)
- UI service accessible
- NGINX routing working
- Stack is stable
