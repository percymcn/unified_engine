#!/bin/bash
set -euo pipefail

# MVP Fix Plan for Unified Trading Engine
# NOTE: This script is NOT executed automatically. Review before running.

# 1) Ensure bind-mount paths exist on ALL swarm nodes (pharma5 + pharma4).
#    This prevents service placement failures on pharma4.
#    Run these on each node (example uses ssh to pharma4):
# ssh pharma4@192.168.1.241 "mkdir -p /home/pharma5/unified_engine/data /home/pharma5/unified_engine/logs"
# ssh pharma4@192.168.1.241 "chown -R 1000:1000 /home/pharma5/unified_engine"

# 2) Build UI image locally and push to the local registry for swarm pull.
#    Use the local registry address from docker info (192.168.1.254:5000).
cd /home/pharma5/unified_engine

docker build -t 192.168.1.254:5000/unified-engine/ui:latest ./ui

docker push 192.168.1.254:5000/unified-engine/ui:latest

# 3) Update swarm services to use the registry-backed UI image.
#    This ensures pharma4 can pull the image.
docker service update --image 192.168.1.254:5000/unified-engine/ui:latest unified_engine_stack_ui

docker service update --image 192.168.1.254:5000/unified-engine/ui:latest trading_ui

# 4) Restart nginx once UI is up (nginx fails when UI DNS is missing).
docker service update --force unified_engine_stack_nginx

# 5) Verify services and endpoints
#    - API health
curl -sS http://192.168.1.254:3012/health | head -n 20
#    - UI root
curl -sS -D- http://192.168.1.254:3411/ | head -n 20

