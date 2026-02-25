# Use the official Python 3.12 slim image (required for project-x-py>=3.5.0)
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEABLE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install metaapi-cloud-sdk and its dependencies (install fully for all MetaAPI functionality)
# Note: python-socketio/python-engineio versions already compatible in requirements.txt
RUN pip install --no-cache-dir metaapi-cloud-sdk>=29.0.0 tradelocker>=0.56.0

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data/cache data/backtests /var/log/trading-engine

# Expose port
EXPOSE 8000

# Health check - Increased resilience for external API timeouts
# interval: Check every 45s (was 30s) - gives more time between checks
# timeout: Wait up to 25s for response (was 10s) - handles slow external API calls
# start-period: Wait 60s before first check (was 5s) - allows full initialization
# retries: 5 attempts before marking unhealthy (was 3) - more tolerant of transient issues
HEALTHCHECK --interval=45s --timeout=25s --start-period=60s --retries=5 \
    CMD curl -f --max-time 20 http://localhost:8000/health || exit 1

# Default command
CMD ["python", "app/main.py"]