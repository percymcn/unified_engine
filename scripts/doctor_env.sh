#!/bin/bash
# doctor_env.sh - ENV Doctor: Single source of truth for required ENV vars
# Analyzes broker configurations and reports missing vars, connection status

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/detect_backend_port.sh"

# Auto-detect backend port if API_URL not set
if [ -z "$API_URL" ]; then
    API_URL=$(detect_backend_port)
fi

# Redact secrets (show first 6 + last 4 chars)
redact_secret() {
    local secret="$1"
    if [ -z "$secret" ]; then
        echo "(empty)"
    elif [ ${#secret} -le 10 ]; then
        echo "***REDACTED***"
    else
        echo "${secret:0:6}...${secret: -4}"
    fi
}

# Check if backend is running
check_backend() {
    if curl -s -f --max-time 2 "$API_URL/health" > /dev/null 2>&1; then
        echo "✅ Running on $API_URL"
        return 0
    else
        echo "❌ Not responding on $API_URL"
        return 1
    fi
}

# Check database
check_database() {
    if [ -f ".env" ]; then
        DB_URL=$(grep "^DATABASE_URL=" .env 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
        if [ -n "$DB_URL" ]; then
            if echo "$DB_URL" | grep -q "sqlite"; then
                DB_FILE=$(echo "$DB_URL" | sed 's|sqlite:///||' | sed 's|sqlite://||')
                if [ -f "$DB_FILE" ]; then
                    echo "✅ SQLite: $DB_FILE ($(du -h "$DB_FILE" 2>/dev/null | cut -f1 || echo 'unknown size'))"
                else
                    echo "⚠️  SQLite: $DB_FILE (file not found)"
                fi
            else
                echo "✅ PostgreSQL: $(echo "$DB_URL" | sed 's|.*@||' | sed 's|/.*||')"
            fi
        else
            echo "⚠️  DATABASE_URL not set"
        fi
    else
        echo "⚠️  .env file not found"
    fi
}

# Check broker configuration
check_broker() {
    local broker_name="$1"
    shift
    local required_vars=("$@")
    
    local missing_vars=()
    local present_vars=()
    local values=()
    
    for var in "${required_vars[@]}"; do
        if [ -f ".env" ]; then
            value=$(grep "^${var}=" .env 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
        else
            value=""
        fi
        
        if [ -z "$value" ] || [ "$value" = "your-${var,,}" ] || [ "$value" = "None" ]; then
            missing_vars+=("$var")
        else
            present_vars+=("$var")
            values+=("$var=$(redact_secret "$value")")
        fi
    done
    
    if [ ${#missing_vars[@]} -eq ${#required_vars[@]} ]; then
        echo "DISABLED"
        echo "  Missing: ${missing_vars[*]}"
    elif [ ${#missing_vars[@]} -eq 0 ]; then
        echo "CONFIGURED"
        echo "  Set: ${present_vars[*]}"
        for val in "${values[@]}"; do
            echo "    $val"
        done
    else
        echo "PARTIAL"
        echo "  Set: ${present_vars[*]}"
        echo "  Missing: ${missing_vars[*]}"
    fi
}

echo "=== ENV Doctor ==="
echo ""
echo "Backend Status:"
check_backend
echo ""

echo "Database:"
check_database
echo ""

echo "Broker Configurations:"
echo ""

# MT4
echo "MT4 (MetaAPI SDK):"
check_broker "mt4_sdk" METAAPI_TOKEN METAAPI_ACCOUNT_ID
echo ""

echo "MT4 (Manager API fallback):"
check_broker "mt4_manager" MT4_MANAGER_LOGIN MT4_MANAGER_PASSWORD
echo ""

# MT5
echo "MT5 (MetaAPI SDK):"
check_broker "mt5_sdk" METAAPI_TOKEN METAAPI_ACCOUNT_ID
echo ""

echo "MT5 (Manager API fallback):"
check_broker "mt5_manager" MT5_MANAGER_LOGIN MT5_MANAGER_PASSWORD
echo ""

# TradeLocker
echo "TradeLocker (SDK):"
check_broker "tradelocker_sdk" TRADELOCKER_USERNAME TRADELOCKER_PASSWORD TRADELOCKER_SERVER
echo ""

echo "TradeLocker (Brand API fallback):"
check_broker "tradelocker_brand" TRADELOCKER_API_KEY
echo ""

# Tradovate
# Note: OAuth mode doesn't require user-provided credentials (handled via redirect)
# Platform-level OAuth config (TRADOVATE_CLIENT_ID/SECRET) is separate from user credentials
echo "Tradovate (Password mode):"
check_broker "tradovate_password" TRADOVATE_USER_ID TRADOVATE_PASSWORD
echo ""

# ProjectX
echo "ProjectX (SDK):"
check_broker "projectx_sdk" PROJECT_X_USERNAME PROJECT_X_API_KEY
echo ""

echo "ProjectX (Legacy API):"
check_broker "projectx_legacy" PROJECTX_API_TOKEN
echo ""

echo "OAuth Providers:"
if [ -f ".env" ]; then
    if grep -q "^GOOGLE_CLIENT_ID=" .env 2>/dev/null && ! grep -q "^GOOGLE_CLIENT_ID=your-google-client-id" .env 2>/dev/null; then
        echo "  ✅ Google OAuth configured"
    else
        echo "  ❌ Google OAuth not configured"
    fi
else
    echo "  ⚠️  .env file not found"
fi
echo ""

echo "=== Summary ==="
echo "Run with API_URL=<url> to check specific backend"
echo "See docs/ENV_REFERENCE.md for complete ENV var documentation"
