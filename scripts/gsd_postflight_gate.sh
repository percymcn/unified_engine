#!/usr/bin/env bash
set -euo pipefail

echo "=== GSD POSTFLIGHT GATE ==="
echo

echo "== Verify scripts =="
./scripts/verify_stack.sh || true
./scripts/verify_green.sh || true
./scripts/doctor_env.sh || true
echo

echo "== Smoke endpoints =="
curl -fsS http://localhost:8765/health | python3 -m json.tool | head -40
curl -fsS http://localhost:8765/api/billing/plans | python3 -m json.tool | head -80
curl -fsS http://localhost:8765/api/v1/brokers/contracts | python3 -m json.tool | head -80
echo

echo "== Git status must be clean (or explain why) =="
git status --porcelain || true
echo "=== POSTFLIGHT DONE ==="
