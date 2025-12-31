#!/bin/bash

# Unified Trading Engine Startup Script
set -e

echo "🚀 Starting Unified Trading Engine..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run ./install.sh first"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please configure your environment"
    exit 1
fi

# Start services in background
echo "🔧 Starting background services..."

# Start Redis (if not running)
if ! pgrep -x "redis-server" > /dev/null; then
    echo "📦 Starting Redis..."
    redis-server --daemonize yes
fi

# Start Celery worker
echo "🔄 Starting Celery worker..."
celery -A app.tasks.celery_app worker --loglevel=info --detach

# Start Flower (Celery monitoring)
echo "🌸 Starting Flower..."
celery -A app.tasks.celery_app flower --port=5555 --detach

# Start Prometheus (if available)
if command -v prometheus &> /dev/null; then
    echo "📊 Starting Prometheus..."
    prometheus --config.file=prometheus.yml --detach 2>/dev/null || true
fi

# Start the main FastAPI application
echo "🌐 Starting FastAPI server..."
echo ""
echo "🎯 Services are starting up:"
echo "- API Server: http://localhost:8000"
echo "- API Docs: http://localhost:8000/docs"
echo "- Flower (Celery): http://localhost:5555"
echo "- Grafana: http://localhost:3001 (if configured)"
echo ""
echo "📝 Logs are being written to the logs/ directory"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    pkill -f "celery.*worker" || true
    pkill -f "celery.*flower" || true
    echo "✅ Services stopped"
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Start the FastAPI app
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload