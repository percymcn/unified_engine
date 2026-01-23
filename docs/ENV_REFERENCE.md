# Environment Variables Reference

Complete reference for all environment variables used in the Unified Trading Engine.

## Quick Start

**Check your ENV configuration:**
```bash
./scripts/doctor_env.sh
```

**Verify broker connectivity:**
```bash
./scripts/verify_brokers_connectivity.sh
```

**Common trap:** Verification scripts default to port 8765. If your backend runs on a different port, set `API_URL`:
```bash
API_URL=http://localhost:8000 ./scripts/verify_oauth_providers.sh
```

---

## Core Configuration

### Application
- `APP_NAME` - Application name (default: "Unified Trading Engine")
- `APP_VERSION` - Version string
- `DEBUG` - Enable debug mode (default: false)
- `ENVIRONMENT` - Environment: "development" or "production"

### Server
- `HOST` - Server host (default: "0.0.0.0")
- `PORT` - Server port (default: 8000)
- `RELOAD` - Enable auto-reload (default: true)

### Security
- `SECRET_KEY` - **REQUIRED** - Application secret key
- `JWT_SECRET_KEY` - JWT signing key (falls back to SECRET_KEY if not set)
- `CREDENTIAL_ENCRYPTION_KEY` - **REQUIRED** - Encryption key for broker credentials

### Database
- `DATABASE_URL` - Database connection URL
  - PostgreSQL: `postgresql://user:password@host:port/dbname`
  - SQLite: `sqlite:///path/to/database.db`
- `DATABASE_PASSWORD` - Database password (loaded from secrets if available)

### Redis
- `REDIS_URL` - Redis connection URL (default: "redis://localhost:6379")
- `REDIS_CACHE_TTL` - Cache TTL in seconds (default: 3600)

---

## Broker Configurations

### MT4 / MT5 (MetaAPI SDK - Preferred)

**Required for SDK mode:**
- `METAAPI_TOKEN` - MetaAPI API token from https://app.metaapi.cloud/token
- `METAAPI_ACCOUNT_ID` - MetaAPI account ID (UUID format)

**Optional:**
- `METAAPI_APPLICATION` - Application name (default: "tradeflow")

**Fallback: Manager API mode**
- `MT4_MANAGER_HOST` / `MT5_MANAGER_HOST` - Manager API host
- `MT4_MANAGER_PORT` / `MT5_MANAGER_PORT` - Manager API port
- `MT4_MANAGER_LOGIN` / `MT5_MANAGER_LOGIN` - Manager login
- `MT4_MANAGER_PASSWORD` / `MT5_MANAGER_PASSWORD` - Manager password

**Code references:**
- `app/brokers/mt4_executor.py` - MT4 executor
- `app/brokers/mt5_executor.py` - MT5 executor
- `app/services/metaapi_sdk_service.py` - MetaAPI SDK wrapper

**Verification:**
```bash
# Check if configured
./scripts/doctor_env.sh | grep -A 5 "MT4\|MT5"

# Test connectivity (if configured)
./scripts/verify_brokers_connectivity.sh
```

---

### TradeLocker

**SDK mode (preferred):**
- `TRADELOCKER_USERNAME` - TradeLocker username/email
- `TRADELOCKER_PASSWORD` - TradeLocker password
- `TRADELOCKER_SERVER` - Server name (e.g., "Demo Server")
- `TRADELOCKER_ENVIRONMENT` - SDK environment URL (default: "https://demo.tradelocker.com")

**Brand API mode (fallback):**
- `TRADELOCKER_API_KEY` - Brand API key

**Code references:**
- `app/brokers/tradelocker_executor.py` - TradeLocker executor
- `app/brokers/tradelocker_sdk_wrapper.py` - SDK wrapper

**Verification:**
```bash
./scripts/doctor_env.sh | grep -A 5 "TradeLocker"
```

---

### Tradovate

**OAuth mode (preferred):**
- `TRADOVATE_CLIENT_ID` - OAuth client ID
- `TRADOVATE_CLIENT_SECRET` - OAuth client secret
- `TRADOVATE_OAUTH_REDIRECT_URI` - OAuth redirect URI
- `TRADOVATE_OAUTH_ENVIRONMENT` - "demo" or "live"

**Password mode (fallback):**
- `TRADOVATE_USER_ID` - User ID
- `TRADOVATE_PASSWORD` - Password

**Code references:**
- `app/brokers/tradovate_executor.py` - Tradovate executor
- `app/routers/tradovate_oauth.py` - OAuth router

**Verification:**
```bash
./scripts/doctor_env.sh | grep -A 5 "Tradovate"
```

---

### ProjectX / TopStep

**SDK mode (preferred):**
- `PROJECT_X_USERNAME` - TopStep username/email
- `PROJECT_X_API_KEY` - TopStep API key
- `PROJECT_X_ACCOUNT_NAME` - Optional account name to select

**Legacy API mode (fallback):**
- `PROJECTX_API_TOKEN` - Legacy API token

**Code references:**
- `app/brokers/projectx_executor.py` - ProjectX executor
- `app/services/projectx_sdk_service.py` - SDK wrapper

**Verification:**
```bash
./scripts/doctor_env.sh | grep -A 5 "ProjectX"
```

---

## OAuth Configuration

### Google OAuth
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `GOOGLE_REDIRECT_URI` - Redirect URI (default: "https://tradeflow.fluxeo.net/api/auth/google/callback")

**Code references:**
- `app/routers/oauth.py` - OAuth router
- `app/services/oauth_service.py` - OAuth service
- `ui-next/src/app/api/auth/google/callback/route.ts` - Frontend callback

**Verification:**
```bash
./scripts/verify_oauth_providers.sh
```

### GitHub OAuth (Optional)
- `GITHUB_CLIENT_ID` - GitHub OAuth client ID
- `GITHUB_CLIENT_SECRET` - GitHub OAuth client secret

### Microsoft OAuth (Optional)
- `MICROSOFT_CLIENT_ID` - Microsoft OAuth client ID
- `MICROSOFT_CLIENT_SECRET` - Microsoft OAuth client secret

---

## Stripe / Billing

- `STRIPE_SECRET_KEY` - Stripe secret key
- `STRIPE_PUBLISHABLE_KEY` - Stripe publishable key
- `STRIPE_WEBHOOK_SECRET` - Webhook secret
- `FRONTEND_URL` - Frontend URL for redirects (default: "https://tradeflow.fluxeo.net")

**Code references:**
- `app/services/stripe_service.py` - Stripe service
- `app/routers/billing.py` - Billing router

---

## Admin Configuration

- `OWNER_ADMIN_EMAILS` - Comma-separated list of owner/admin emails for `/__owner` access

**Code references:**
- `app/routers/admin.py` - Admin router
- `app/core/config.py` - Settings class

---

## Verification Scripts

All verification scripts support `API_URL` environment variable to override default port detection:

```bash
# Auto-detect backend port
./scripts/doctor_env.sh

# Use specific backend URL
API_URL=http://localhost:8000 ./scripts/doctor_env.sh
```

**Available scripts:**
- `scripts/doctor_env.sh` - ENV doctor (broker status, missing vars)
- `scripts/verify_oauth_providers.sh` - OAuth providers check
- `scripts/verify_brokers_connectivity.sh` - Broker connectivity test
- `scripts/verify_pricing_consistency.sh` - Pricing consistency check
- `scripts/verify_owner_admin.sh` - Admin dashboard security check

---

## Common Issues

### "Broker disabled: no credentials configured"
- Check `./scripts/doctor_env.sh` to see which vars are missing
- Ensure `.env` file exists and contains required variables
- Verify variable names match exactly (case-sensitive)

### "MetaAPI authentication failed"
- Verify `METAAPI_TOKEN` is valid at https://app.metaapi.cloud/token
- Check `METAAPI_ACCOUNT_ID` matches account in MetaAPI dashboard
- Ensure account is provisioned and active

### "Verification script can't connect to backend"
- Backend may be running on different port
- Set `API_URL` explicitly: `API_URL=http://localhost:8000 ./scripts/doctor_env.sh`
- Check backend is running: `curl http://localhost:8765/health`

### "redirect_uri_mismatch" (OAuth)
- Ensure `GOOGLE_REDIRECT_URI` matches exactly in Google Cloud Console
- For production: `https://tradeflow.fluxeo.net/api/auth/google/callback`
- For development: `http://localhost:3456/api/auth/google/callback`

---

## Environment File Location

- `.env` - Main environment file (not committed to git)
- `.env.example` - Example file with all variables (committed)
- `.env.local` - Local overrides (not committed)

**Never commit `.env` files containing secrets!**

---

## Getting Help

1. Run ENV doctor: `./scripts/doctor_env.sh`
2. Check broker connectivity: `./scripts/verify_brokers_connectivity.sh`
3. View admin dashboard: `/__owner` (owner-only)
4. Check backend endpoint: `/api/v1/admin/system/env-doctor` (owner-only)
