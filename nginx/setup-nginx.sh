#!/bin/bash
# Setup script for mytradeflow.app Nginx configuration
# Run with: sudo bash setup-nginx.sh

set -e

echo "=== Installing Nginx ==="
apt update
apt install -y nginx

echo "=== Copying configuration ==="
cp mytradeflow.app.conf /etc/nginx/sites-available/mytradeflow.app

echo "=== Enabling site ==="
ln -sf /etc/nginx/sites-available/mytradeflow.app /etc/nginx/sites-enabled/

echo "=== Removing default site ==="
rm -f /etc/nginx/sites-enabled/default

echo "=== Testing configuration ==="
nginx -t

echo "=== Restarting Nginx ==="
systemctl restart nginx
systemctl enable nginx

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Your sites are now live:"
echo "  Frontend: http://mytradeflow.app → localhost:3456"
echo "  Backend:  http://api.mytradeflow.app → localhost:8765"
echo ""
echo "Make sure in Cloudflare:"
echo "  1. SSL/TLS mode is set to 'Flexible' or 'Full'"
echo "  2. Both A records point to 69.206.22.77"
echo "  3. Proxy status (orange cloud) is ON for both"
echo ""
