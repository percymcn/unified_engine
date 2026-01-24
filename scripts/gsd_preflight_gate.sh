#!/usr/bin/env bash
set -euo pipefail

echo "=== GSD PREFLIGHT GATE ==="
echo "PWD: $(pwd)"
echo "Time: $(date)"
echo

echo "== Canonical ports check =="
ss -ltnp | egrep ':8765|:3456|:5432' || true
echo

echo "== DATABASE_URL (runtime config) =="
python3 - <<'PY'
from app.core.config import settings
print("DATABASE_URL =", settings.DATABASE_URL)
PY
echo

echo "== Git status =="
git status --porcelain || true
echo

echo "== Required docs exist =="
for f in \
  .gsd/00_MANDATORY_READ_FIRST.md \
  .planning/STATE.md \
  .planning/ROADMAP.md \
  .planning/PROJECT.md \
  .planning/codebase/ARCHITECTURE.md \
  .planning/codebase/CONVENTIONS.md
do
  test -f "$f" && echo "OK: $f" || echo "MISSING: $f"
done
echo

echo "== Quick health checks (if running) =="
curl -fsS http://localhost:8765/health | head -c 200 || echo "API not responding on 8765"
echo
curl -fsS http://localhost:8765/api/billing/plans | head -c 200 || echo "billing/plans not responding"
echo
curl -fsS http://localhost:8765/api/v1/brokers/contracts | head -c 200 || echo "brokers/contracts not responding"
echo

echo "=== PREFLIGHT OK ==="
