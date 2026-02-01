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

# Install SDKs with --no-deps to avoid dependency conflicts
RUN pip install --no-cache-dir --no-deps tradelocker>=0.56.0 metaapi-cloud-sdk>=29.0.0

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data/cache data/backtests /var/log/trading-engine

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "app/main.py"]