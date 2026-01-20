#!/bin/bash
# Create Docker configs for Swarm deployment

set -e

echo "Creating Docker configs for Swarm deployment..."

# Remove old config if exists
docker config rm unified_nginx_conf_v2 2>/dev/null || true

# Create nginx config
echo "Creating nginx configuration..."
docker config create unified_nginx_conf_v2 deploy/nginx/nginx.conf

echo ""
echo "Configs created successfully!"
echo ""
echo "List configs with: docker config ls"
echo "Inspect config with: docker config inspect unified_nginx_conf_v2"
