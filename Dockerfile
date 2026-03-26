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
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --timeout=300 --retries=3 -r requirements.txt

# Install metaapi-cloud-sdk and its dependencies (install fully for all MetaAPI functionality)
# Note: python-socketio/python-engineio versions already compatible in requirements.txt
RUN pip install --no-cache-dir metaapi-cloud-sdk>=29.0.0 tradelocker>=0.56.0

# Install pandas-ta with its dependencies except numpy
# pandas-ta requires numpy<2.3 but we need numpy>=2.3.2 for project-x-py
# Install numba first (pandas-ta dependency), then pandas-ta with --no-deps
RUN pip install --no-cache-dir numba && \
    pip install --no-cache-dir --no-deps pandas-ta>=0.3.14b0

# Patch ProjectX SDK models.py - fix dataclass field ordering error
# The SDK has fields without defaults after fields with defaults (int | None implies default=None)
# This causes: TypeError: non-default argument 'updateTimestamp' follows default argument
RUN MODELS_FILE=$(python -c "import project_x_py; print(project_x_py.__file__.replace('__init__.py', 'models.py'))") && \
    if [ -f "$MODELS_FILE" ]; then \
        sed -i 's/updateTimestamp: str$/updateTimestamp: str = ""/' "$MODELS_FILE" && \
        echo "Patched ProjectX SDK models.py: added default to updateTimestamp fields"; \
    fi

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