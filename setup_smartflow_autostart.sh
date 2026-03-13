#!/bin/bash
# Setup SmartFlow components to auto-start on reboot

echo "=== Setting up SmartFlow Auto-Start ==="

# 1. Install FlowAlgo Proxy systemd service
echo "1. Installing FlowAlgo Proxy service..."
sudo cp /home/pharma5/unified_engine/flow_confluence_proxy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable flow_confluence_proxy
sudo systemctl start flow_confluence_proxy
echo "   FlowAlgo Proxy service: $(systemctl is-enabled flow_confluence_proxy)"

# 2. Ensure Docker starts on boot
echo "2. Ensuring Docker auto-starts..."
sudo systemctl enable docker
echo "   Docker service: $(systemctl is-enabled docker)"

# 3. Docker Swarm services auto-restart by default, but verify
echo "3. Checking Docker Swarm services..."
docker service ls

# 4. Create log directory if needed
echo "4. Setting up log directories..."
sudo mkdir -p /var/log
sudo touch /var/log/flow_confluence.log /var/log/flow_confluence_error.log
sudo chown pharma5:pharma5 /var/log/flow_confluence*.log

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Services configured to auto-start:"
echo "  - flow_confluence_proxy (FlowAlgo scraper)"
echo "  - docker (Docker daemon)"
echo "  - Docker Swarm services (unified_api, unified_ui, etc.)"
echo ""
echo "To check status:"
echo "  systemctl status flow_confluence_proxy"
echo "  docker service ls"
