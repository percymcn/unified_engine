#!/bin/bash

# Unified Trading Engine Installation Script
set -e

echo "🚀 Installing Unified Trading Engine..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.9+ required. Found: $python_version"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs data/cache data/backtests

# Set environment variables
echo "🔧 Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️ Please edit .env file with your configuration"
fi

# Run database migrations
echo "🗄️ Setting up database..."
alembic upgrade head

# Create admin user
echo "👤 Creating admin user..."
python scripts/create_admin.py

echo "✅ Installation complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Edit .env file with your settings"
echo "2. Start the engine: ./start.sh"
echo "3. Visit http://localhost:8000/docs"
echo ""
echo "📊 Monitoring will be available at:"
echo "- Grafana: http://localhost:3001"
echo "- Flower: http://localhost:5555"