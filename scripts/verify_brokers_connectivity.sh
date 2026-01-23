#!/bin/bash
# verify_brokers_connectivity.sh - Smoke test for broker connectivity
# Tests actual connection attempts for configured brokers

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/detect_backend_port.sh"

# Auto-detect backend port if API_URL not set
if [ -z "$API_URL" ]; then
    API_URL=$(detect_backend_port)
fi

echo "=== Broker Connectivity Verification ==="
echo "API URL: $API_URL"
echo ""

# Check backend health first
echo "Test 0: Backend Health"
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_URL/health" 2>&1 || echo "HTTP_CODE:000")
HEALTH_HTTP=$(echo "$HEALTH_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
if [ "$HEALTH_HTTP" = "200" ]; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend health check failed (HTTP $HEALTH_HTTP)"
    echo "   Cannot verify broker connectivity without backend"
    exit 1
fi
echo ""

# Check MetaApi if configured
if [ -f ".env" ]; then
    METAAPI_TOKEN=$(grep "^METAAPI_TOKEN=" .env 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
    METAAPI_ACCOUNT_ID=$(grep "^METAAPI_ACCOUNT_ID=" .env 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
    
    if [ -n "$METAAPI_TOKEN" ] && [ "$METAAPI_TOKEN" != "your-metaapi-token" ] && [ -n "$METAAPI_ACCOUNT_ID" ]; then
        echo "Test 1: MetaAPI Authentication"
        echo "  Token: $(echo "$METAAPI_TOKEN" | sed 's/\(.\{6\}\).*\(.\{4\}\)/\1...\2/')"
        echo "  Account ID: $METAAPI_ACCOUNT_ID"
        
        # Try to ping MetaAPI (if curl available)
        METAAPI_PING=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
            -H "auth-token: $METAAPI_TOKEN" \
            "https://mt-client-api-v1.agiliumtrade.agiliumtrade.ai/users/current" \
            2>&1 || echo "HTTP_CODE:000")
        METAAPI_HTTP=$(echo "$METAAPI_PING" | grep "HTTP_CODE:" | cut -d: -f2)
        
        if [ "$METAAPI_HTTP" = "200" ]; then
            echo "  ✅ MetaAPI authentication successful"
        elif [ "$METAAPI_HTTP" = "401" ] || [ "$METAAPI_HTTP" = "403" ]; then
            echo "  ❌ MetaAPI authentication failed (HTTP $METAAPI_HTTP)"
            echo "     Check METAAPI_TOKEN is valid at https://app.metaapi.cloud/token"
        else
            echo "  ⚠️  MetaAPI endpoint returned HTTP $METAAPI_HTTP"
            echo "     Network/DNS issue or endpoint changed"
        fi
    else
        echo "Test 1: MetaAPI Authentication"
        echo "  ⚠️  MetaAPI not configured (METAAPI_TOKEN or METAAPI_ACCOUNT_ID missing)"
    fi
    echo ""
    
    # Check Tradovate OAuth
    TRADOVATE_CLIENT_ID=$(grep "^TRADOVATE_CLIENT_ID=" .env 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
    TRADOVATE_CLIENT_SECRET=$(grep "^TRADOVATE_CLIENT_SECRET=" .env 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
    
    if [ -n "$TRADOVATE_CLIENT_ID" ] && [ "$TRADOVATE_CLIENT_ID" != "your_tradovate_client_id" ]; then
        echo "Test 2: Tradovate OAuth Provider"
        echo "  ✅ Tradovate OAuth configured (Client ID: $(echo "$TRADOVATE_CLIENT_ID" | sed 's/\(.\{6\}\).*\(.\{4\}\)/\1...\2/'))"
        echo "  Note: OAuth flow requires user interaction, cannot test automatically"
    else
        echo "Test 2: Tradovate OAuth Provider"
        echo "  ⚠️  Tradovate OAuth not configured"
    fi
    echo ""
    
    # Check TradeLocker
    TRADELOCKER_USERNAME=$(grep "^TRADELOCKER_USERNAME=" .env 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
    TRADELOCKER_API_KEY=$(grep "^TRADELOCKER_API_KEY=" .env 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
    
    if [ -n "$TRADELOCKER_USERNAME" ] || [ -n "$TRADELOCKER_API_KEY" ]; then
        echo "Test 3: TradeLocker Configuration"
        if [ -n "$TRADELOCKER_USERNAME" ]; then
            echo "  ✅ TradeLocker SDK credentials configured"
        fi
        if [ -n "$TRADELOCKER_API_KEY" ]; then
            echo "  ✅ TradeLocker Brand API key configured"
        fi
        echo "  Note: Actual connection requires SDK initialization"
    else
        echo "Test 3: TradeLocker Configuration"
        echo "  ⚠️  TradeLocker not configured"
    fi
    echo ""
    
    # Check ProjectX
    PROJECT_X_USERNAME=$(grep "^PROJECT_X_USERNAME=" .env 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
    PROJECT_X_API_KEY=$(grep "^PROJECT_X_API_KEY=" .env 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
    
    if [ -n "$PROJECT_X_USERNAME" ] && [ -n "$PROJECT_X_API_KEY" ]; then
        echo "Test 4: ProjectX Configuration"
        echo "  ✅ ProjectX SDK credentials configured"
        echo "  Note: Actual connection requires SDK initialization"
    else
        echo "Test 4: ProjectX Configuration"
        echo "  ⚠️  ProjectX not configured"
    fi
else
    echo "⚠️  .env file not found, cannot check broker configurations"
fi

echo ""
echo "=== Summary ==="
echo "For detailed broker status, run: ./scripts/doctor_env.sh"
echo "For backend broker status, check: $API_URL/api/v1/admin/system/env-doctor (owner-only)"
