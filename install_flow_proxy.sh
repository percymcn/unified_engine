#!/bin/bash
#
# Installation script for FlowAlgo Confluence Webhook Proxy
# Usage: bash install_flow_proxy.sh
#

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   FlowAlgo Confluence Webhook Proxy - Installation        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "✗ Python 3 not found. Install it first:"
    echo "  sudo apt update && sudo apt install python3 python3-pip"
    exit 1
fi
echo "✓ Python 3 found"
echo ""

# Install dependencies
echo "Installing Python dependencies..."
pip3 install --user playwright flask python-dotenv requests
echo "✓ Dependencies installed"
echo ""

# Install Playwright browsers
echo "Installing Playwright Chromium browser..."
python3 -m playwright install chromium
echo "✓ Chromium installed"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.flow_example .env
    echo "⚠ IMPORTANT: Edit .env and add your FlowAlgo credentials!"
    echo "  nano .env"
    echo ""
else
    echo "✓ .env file exists"
    echo ""
fi

# Make scripts executable
echo "Making scripts executable..."
chmod +x flow_confluence_proxy.py test_flow_proxy.py
echo "✓ Scripts are executable"
echo ""

# Test run (optional)
read -p "Run a test to verify installation? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting test run (Ctrl+C to stop)..."
    echo "You should see login attempt and scraping logs..."
    echo ""
    sleep 2
    timeout 30 python3 flow_confluence_proxy.py || echo "Test run completed (or timed out)"
    echo ""
fi

# Offer systemd setup
read -p "Install as systemd service? (requires sudo) (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing systemd service..."
    sudo cp flow_confluence_proxy.service /etc/systemd/system/
    sudo systemctl daemon-reload
    echo "✓ Service installed"
    echo ""

    read -p "Enable and start service now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl enable flow_confluence_proxy
        sudo systemctl start flow_confluence_proxy
        echo "✓ Service started"
        echo ""
        sleep 2
        echo "Service status:"
        sudo systemctl status flow_confluence_proxy --no-pager
    fi
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   Installation Complete!                                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure your credentials:"
echo "   nano .env"
echo "   # Set FLOW_EMAIL, FLOW_PASS, MYTRADEFLOW_WEBHOOK"
echo ""
echo "2. Test the proxy:"
echo "   python3 test_flow_proxy.py"
echo ""
echo "3. Start the service:"
echo "   Manual: python3 flow_confluence_proxy.py"
echo "   Systemd: sudo systemctl start flow_confluence_proxy"
echo ""
echo "4. Check logs:"
echo "   tail -f confluence.log"
echo "   sudo journalctl -u flow_confluence_proxy -f"
echo ""
echo "5. Configure TradingView webhook:"
echo "   URL: http://$(hostname -I | awk '{print $1}'):9001/filter"
echo ""
echo "See FLOW_PROXY_README.md for full documentation."
echo ""
