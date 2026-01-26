#!/bin/bash
# TradeFlow Comprehensive Health Check Script
# Monitors all critical system components

set -e

echo "=== TradeFlow System Health Check ==="

# Initialize health status
OVERALL_HEALTH="OK"
FAILED_CHECKS=()

# Function to check service health
check_service() {
    local service_name=$1
    local check_command=$2
    local expected_result=${3:-"200"}
    
    echo "Checking $service_name..."
    
    if eval "$check_command" >/dev/null 2>&1; then
        echo "✅ $service_name: OK"
        return 0
    else
        echo "❌ $service_name: FAILED"
        FAILED_CHECKS+=("$service_name")
        OVERALL_HEALTH="FAILED"
        return 1
    fi
}

# Function to check database connectivity
check_database() {
    echo "Checking database connectivity..."
    
    python3 -c "
import psycopg2
import os
from urllib.parse import urlparse

# Try to get database URL from environment
db_url = os.getenv('DATABASE_URL', 'postgresql://trading_user:trading_password@localhost:5432/trading_db')

try:
    parsed = urlparse(db_url)
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path[1:],
        user=parsed.username,
        password=parsed.password
    )
    
    # Test a simple query
    cursor = conn.cursor()
    cursor.execute('SELECT 1')
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0] == 1:
        print('✅ Database: OK')
        exit(0)
    else:
        print('❌ Database: Query failed')
        exit(1)
        
except Exception as e:
    print(f'❌ Database: {e}')
    exit(1)
" || {
        FAILED_CHECKS+=("Database")
        OVERALL_HEALTH="FAILED"
    }
}

# Function to check Redis connectivity
check_redis() {
    echo "Checking Redis connectivity..."
    
    python3 -c "
import redis
import os

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

try:
    r = redis.from_url(redis_url)
    r.ping()
    print('✅ Redis: OK')
    exit(0)
except Exception as e:
    print(f'❌ Redis: {e}')
    exit(1)
" || {
        FAILED_CHECKS+=("Redis")
        OVERALL_HEALTH="FAILED"
    }
}

# Function to check backend API
check_backend_api() {
    local backend_url=${1:-"http://localhost:8765"}
    
    echo "Checking backend API at $backend_url..."
    
    if curl -s -f "$backend_url/health" >/dev/null 2>&1; then
        echo "✅ Backend API: OK"
        return 0
    else
        echo "❌ Backend API: FAILED"
        FAILED_CHECKS+=("Backend API")
        OVERALL_HEALTH="FAILED"
        return 1
    fi
}

# Function to check frontend
check_frontend() {
    local frontend_url=${1:-"http://localhost:3456"}
    
    echo "Checking frontend at $frontend_url..."
    
    if curl -s -f "$frontend_url" >/dev/null 2>&1; then
        echo "✅ Frontend: OK"
        return 0
    else
        echo "❌ Frontend: FAILED"
        FAILED_CHECKS+=("Frontend")
        OVERALL_HEALTH="FAILED"
        return 1
    fi
}

# Function to check critical endpoints
check_critical_endpoints() {
    local backend_url=${1:-"http://localhost:8765"}
    
    echo "Checking critical endpoints..."
    
    # Check health endpoint
    if curl -s -f "$backend_url/health" >/dev/null 2>&1; then
        echo "✅ Health endpoint: OK"
    else
        echo "❌ Health endpoint: FAILED"
        FAILED_CHECKS+=("Health Endpoint")
        OVERALL_HEALTH="FAILED"
    fi
    
    # Check dashboard stats endpoint (will fail without auth, but should not 500)
    local status_code=$(curl -s -o /dev/null -w "%{http_code}" "$backend_url/api/dashboard/stats" || echo "000")
    if [ "$status_code" = "401" ] || [ "$status_code" = "403" ]; then
        echo "✅ Dashboard stats endpoint: OK (auth required)"
    elif [ "$status_code" = "200" ]; then
        echo "✅ Dashboard stats endpoint: OK (public access)"
    else
        echo "❌ Dashboard stats endpoint: FAILED (status: $status_code)"
        FAILED_CHECKS+=("Dashboard Stats Endpoint")
        OVERALL_HEALTH="FAILED"
    fi
    
    # Check signals endpoint
    status_code=$(curl -s -o /dev/null -w "%{http_code}" "$backend_url/api/v1/signals" || echo "000")
    if [ "$status_code" = "401" ] || [ "$status_code" = "403" ]; then
        echo "✅ Signals endpoint: OK (auth required)"
    elif [ "$status_code" = "200" ]; then
        echo "✅ Signals endpoint: OK (public access)"
    else
        echo "❌ Signals endpoint: FAILED (status: $status_code)"
        FAILED_CHECKS+=("Signals Endpoint")
        OVERALL_HEALTH="FAILED"
    fi
}

# Function to check disk space
check_disk_space() {
    echo "Checking disk space..."
    
    local usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$usage" -lt 85 ]; then
        echo "✅ Disk space: OK (${usage}%)"
    else
        echo "❌ Disk space: CRITICAL (${usage}%)"
        FAILED_CHECKS+=("Disk Space")
        OVERALL_HEALTH="FAILED"
    fi
}

# Function to check memory usage
check_memory() {
    echo "Checking memory usage..."
    
    local mem_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    
    if [ "$mem_usage" -lt 90 ]; then
        echo "✅ Memory usage: OK (${mem_usage}%)"
    else
        echo "❌ Memory usage: CRITICAL (${mem_usage}%)"
        FAILED_CHECKS+=("Memory Usage")
        OVERALL_HEALTH="FAILED"
    fi
}

# Main health check execution
echo "Starting comprehensive health check..."
echo "================================"

# Check system resources
check_disk_space
check_memory
echo ""

# Check services
check_database
check_redis
echo ""

# Check application services
check_backend_api
check_frontend
echo ""

# Check API endpoints
check_critical_endpoints
echo ""

# Summary
echo "================================"
echo "Health Check Summary:"
echo "Overall Status: $OVERALL_HEALTH"

if [ "$OVERALL_HEALTH" = "OK" ]; then
    echo "🎉 All systems operational!"
    echo ""
    echo "✅ TradeFlow is ready for production"
    exit 0
else
    echo "❌ Failed checks: ${FAILED_CHECKS[*]}"
    echo ""
    echo "🚨 Please address the following issues before deploying:"
    for check in "${FAILED_CHECKS[@]}"; do
        echo "   - $check"
    done
    echo ""
    echo "💡 Run individual checks for more details:"
    echo "   ./scripts/health_check_all.sh --database"
    echo "   ./scripts/health_check_all.sh --backend"
    echo "   ./scripts/health_check_all.sh --frontend"
    exit 1
fi