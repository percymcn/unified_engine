---
phase: 10-deployment
plan: 01
subsystem: infra
tags: [docker, nextjs, deployment, standalone, health-check]

# Dependency graph
requires:
  - phase: 09-ui-configuration
    provides: Fully functional Next.js 14 UI with all configuration pages
  - phase: 07-ui-foundation
    provides: Next.js 14 foundation with authentication and layout
provides:
  - Production-ready Docker image for Next.js UI with multi-stage build
  - Standalone output mode for minimal deployment footprint
  - Health check endpoint for container orchestration
  - Non-root user security configuration
affects: [10-deployment (plans 02-04 will integrate this image into docker-stack.yml)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Multi-stage Docker builds for Next.js (deps → builder → runner)"
    - "Standalone output mode for minimal production bundles"
    - "Non-root container users for security (nextjs:nodejs 1001:1001)"
    - "Health check endpoints for orchestration monitoring"

key-files:
  created:
    - ui-next/Dockerfile
    - ui-next/.dockerignore
    - ui-next/src/app/api/health/route.ts
  modified:
    - ui-next/next.config.mjs

key-decisions:
  - "Node.js 20 Alpine base image for minimal size (~225MB final image)"
  - "Three-stage build (deps/builder/runner) for optimal Docker layer caching"
  - "Standalone output mode eliminates full node_modules in production image"
  - "Health check at 30s intervals with 10s timeout for Swarm readiness"
  - "HEALTHCHECK uses wget spider mode for lightweight health probes"

patterns-established:
  - "Next.js Dockerfile pattern: Multi-stage with standalone output"
  - ".dockerignore excludes node_modules, .next, .env* for minimal build context"
  - "Health endpoints return JSON with service name and timestamp"

# Metrics
duration: 11min
completed: 2026-01-20
---

# Phase 10 Plan 01: Next.js Production Dockerfile Summary

**Production-ready Next.js 14 Docker image with multi-stage build, standalone output, and health monitoring**

## Performance

- **Duration:** 11 min
- **Started:** 2026-01-20T22:53:16Z
- **Completed:** 2026-01-20T23:04:31Z
- **Tasks:** 5 (4 code + 1 verification)
- **Files modified:** 4

## Accomplishments
- Multi-stage Dockerfile optimized for Next.js standalone mode with minimal image size (225MB)
- Health check endpoint for Docker Swarm orchestration monitoring
- Non-root user configuration for production security
- Verified Docker build and runtime with health endpoint testing

## Task Commits

Each task was committed atomically:

1. **Task 1: Configure Next.js for Standalone Output** - `c194629` (feat)
   - Enabled output: 'standalone' in next.config.mjs
   - Disables telemetry for production builds

2. **Task 2: Create Production Dockerfile** - `5df38af` (feat)
   - Three-stage build: deps → builder → runner
   - Node.js 20 Alpine base for minimal size
   - Non-root nextjs:nodejs user (1001:1001)
   - HEALTHCHECK directive with wget spider

3. **Task 3: Create .dockerignore** - `fb02c15` (chore)
   - Excludes node_modules, .next, .env*, test files
   - Minimal Docker build context

4. **Task 4: Add Health Check Endpoint** - `9ea872a` (feat)
   - GET /api/health returns JSON with status/service/timestamp
   - No authentication required for orchestration access

5. **Task 5: Test Local Docker Build** - (verification only, no commit)
   - Build completed successfully (~225MB image size)
   - Container starts and serves on port 3000
   - Health endpoint returns 200 OK with expected JSON
   - Main app returns 307 redirect (expected auth middleware behavior)

## Files Created/Modified

- `ui-next/next.config.mjs` - Added standalone output configuration
- `ui-next/Dockerfile` - Multi-stage production build for Next.js
- `ui-next/.dockerignore` - Excluded files from Docker build context
- `ui-next/src/app/api/health/route.ts` - Health check endpoint for orchestration

## Decisions Made

1. **Node.js 20 Alpine**: Chose Alpine variant for minimal base image size while maintaining compatibility
2. **Standalone output mode**: Eliminates full node_modules in production, reducing image size significantly
3. **Three-stage build**: Separates dependency installation, build, and runtime for optimal Docker layer caching
4. **Non-root user (1001:1001)**: Security best practice for production containers
5. **wget-based HEALTHCHECK**: Lightweight health probe using wget spider mode instead of curl
6. **30s health check interval**: Balances responsiveness with resource overhead for Swarm monitoring

## Deviations from Plan

### Minor Implementation Details

**1. Public directory handling**
- **Context:** Plan Task 2 included copying public directory from builder stage
- **Finding:** ui-next project has no public directory (Next.js App Router with no static assets)
- **Action:** Omitted public directory copy from Dockerfile (not needed)
- **Impact:** None - standalone build handles assets appropriately

**2. HEALTHCHECK directive added to Dockerfile**
- **Context:** Plan specified health check endpoint but didn't mention Docker HEALTHCHECK directive
- **Action:** Added HEALTHCHECK directive to Dockerfile using wget spider mode
- **Rationale:** Essential for Docker Swarm to detect container health status
- **Configuration:** 30s interval, 10s timeout, 5s start period, 3 retries
- **Impact:** Positive - enables automatic container restart on health check failure

---

**Total deviations:** 2 minor implementation details (1 omission, 1 addition)
**Impact on plan:** Both changes align with plan intent (production-ready containerization). No scope creep.

## Issues Encountered

None - Docker build and runtime verification completed successfully on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for next plans:**
- ui-next Docker image can be integrated into docker-stack.yml (Plan 10-04)
- Image includes health check endpoint for Swarm health monitoring
- Standalone mode minimizes deployment footprint
- Non-root user meets production security requirements

**Integration notes:**
- Image expects environment variables at runtime (BACKEND_URL, etc.)
- Health check available at GET /api/health
- Runs on port 3000 by default (configurable via PORT env var)
- Requires network connectivity to FastAPI backend for BFF proxy pattern

---
*Phase: 10-deployment*
*Completed: 2026-01-20*
