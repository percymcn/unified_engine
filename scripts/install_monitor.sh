#!/bin/bash
# Installation script for Unified Monitor Service
# Run this with: sudo bash scripts/install_monitor.sh

set -e

echo "Installing Unified Trading Engine Monitor Service..."

# Create log directory
mkdir -p /var/log/unified_engine
chown -R pharma5:pharma5 /var/log/unified_engine

# Copy systemd service file
cat > /etc/systemd/system/unified-monitor.service << 'EOF'
[Unit]
Description=Unified Trading Engine Auto-Monitor and Healing Service
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/home/pharma5/unified_engine
ExecStart=/usr/bin/python3 /home/pharma5/unified_engine/scripts/monitor_and_heal.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Resource limits
CPUQuota=20%
MemoryLimit=512M

# Logging
SyslogIdentifier=unified-monitor

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable service to start on boot
systemctl enable unified-monitor.service

echo "✓ Service installed and enabled"
echo ""
echo "To start the monitor service:"
echo "  sudo systemctl start unified-monitor"
echo ""
echo "To check status:"
echo "  sudo systemctl status unified-monitor"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u unified-monitor -f"
echo "  or"
echo "  tail -f /var/log/unified_engine/monitor.log"
