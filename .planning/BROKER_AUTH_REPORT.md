# BROKER AUTH REPORT

**Date:** 2026-01-23 18:50 UTC
**Phase:** PHASE 4 - Broker Auth Smoke Test Harness

---

## Summary

Created read-only broker authentication smoke test harness. Tests authentication and connection without placing trades.

---

## Scripts Created

### 1. `scripts/broker_auth_smoke.sh`

**Purpose:** Shell wrapper for Python smoke test script

**Usage:**
```bash
./scripts/broker_auth_smoke.sh [broker]
```

**Brokers:**
- `mt4` - Test MT4 authentication
- `mt5` - Test MT5 authentication
- `tradelocker` - Test TradeLocker authentication
- `tradovate` - Test Tradovate authentication
- `projectx` - Test ProjectX authentication
- `all` - Test all configured brokers (default)

**Example:**
```bash
# Test all brokers
./scripts/broker_auth_smoke.sh

# Test specific broker
./scripts/broker_auth_smoke.sh tradelocker
```

---

### 2. `scripts/broker_auth_smoke.py`

**Purpose:** Python script that performs actual authentication tests

**Features:**
- Reads credentials from environment variables only
- Tests `authenticate()` method
- Tests `connect()` method
- Fetches account info (read-only, no trades)
- Prints PASS/FAIL/SKIP with reasons
- Cleans up connections after test

**Test Flow:**
1. Check environment variables for broker credentials
2. Create executor instance
3. Call `authenticate()` - must return `True`
4. Call `connect()` - must return `True`
5. Call `get_account_info()` - must return account data
6. Disconnect and cleanup

---

## Environment Variables Contract

### MT4 / MT5

```bash
# Required
export MT4_API_KEY="your_api_key"
export MT4_API_SECRET="your_api_secret"
export MT4_ACCOUNT_NUMBER="your_account_number"

export MT5_API_KEY="your_api_key"
export MT5_API_SECRET="your_api_secret"
export MT5_ACCOUNT_NUMBER="your_account_number"
```

### TradeLocker

```bash
# Required
export TRADELOCKER_API_KEY="your_api_key"
export TRADELOCKER_API_SECRET="your_api_secret"

# Optional (for Brand API mode)
export TRADELOCKER_USERNAME="your_username"
```

### Tradovate

```bash
# Required
export TRADOVATE_ACCESS_TOKEN="your_oauth_token"

# Optional
export TRADOVATE_ACCOUNT_ID="your_account_id"
```

### ProjectX

```bash
# Required
export PROJECTX_API_KEY="your_api_key"
export PROJECTX_API_SECRET="your_api_secret"

# Optional
export PROJECTX_ACCOUNT_ID="your_account_id"
```

---

## Usage Examples

### Test All Brokers

```bash
# Set environment variables for brokers you want to test
export TRADELOCKER_API_KEY="..."
export TRADELOCKER_API_SECRET="..."

# Run test
./scripts/broker_auth_smoke.sh all
```

**Output:**
```
=== Broker Auth Smoke Test ===
Broker: all

--- Testing MT4 ---
  [1/3] Authenticating...
        ⏭️  SKIP: Missing environment variables (check MT4_*)

--- Testing MT5 ---
  [1/3] Authenticating...
        ⏭️  SKIP: Missing environment variables (check MT5_*)

--- Testing TradeLocker ---
  [1/3] Authenticating...
        ✅ Authentication successful
  [2/3] Connecting...
        ✅ Connection successful
  [3/3] Fetching account info...
        ✅ Account info retrieved
        Balance: 10000.0, Equity: 10000.0
  Result: PASS: All checks passed

=== Summary ===
⏭️  MT4: SKIP: Missing environment variables
⏭️  MT5: SKIP: Missing environment variables
✅ TradeLocker: PASS: All checks passed

Total: 1 passed, 2 skipped, 0 failed
```

### Test Single Broker

```bash
export TRADELOCKER_API_KEY="..."
export TRADELOCKER_API_SECRET="..."

./scripts/broker_auth_smoke.sh tradelocker
```

---

## Test Results Interpretation

### PASS ✅
- All authentication steps succeeded
- Account info retrieved successfully
- Broker is properly configured and accessible

### SKIP ⏭️
- Missing environment variables
- Broker not configured for testing
- **Not an error** - test skipped intentionally

### FAIL ❌
- Authentication failed
- Connection failed
- Account info fetch failed
- Exception during test

**Common Failure Reasons:**
- Invalid credentials
- Network connectivity issues
- Broker API unavailable
- Account not accessible
- SDK dependencies missing

---

## Safety Guarantees

### Read-Only Operations
- ✅ `authenticate()` - No side effects
- ✅ `connect()` - No side effects
- ✅ `get_account_info()` - Read-only query
- ❌ **NO** `place_order()` calls
- ❌ **NO** trade execution
- ❌ **NO** account modifications

### Error Handling
- Catches and reports exceptions
- Cleans up connections on failure
- Does not crash on missing env vars (SKIP instead)

---

## Integration with CI/CD

### Example GitHub Actions

```yaml
- name: Test Broker Auth
  env:
    TRADELOCKER_API_KEY: ${{ secrets.TRADELOCKER_API_KEY }}
    TRADELOCKER_API_SECRET: ${{ secrets.TRADELOCKER_API_SECRET }}
  run: |
    ./scripts/broker_auth_smoke.sh tradelocker
```

### Exit Codes
- `0` - All tests passed or skipped
- `1` - At least one test failed

---

## Dependencies

### Python Packages
- `asyncio` (standard library)
- Broker executor classes from `app.brokers.*`

### System Requirements
- Python 3.8+
- Access to broker APIs (network)
- Valid broker credentials (env vars)

---

## Troubleshooting

### Import Errors
```
❌ ERROR: Failed to import broker executors
```
**Solution:** Ensure PYTHONPATH includes project root:
```bash
export PYTHONPATH="$PWD:$PYTHONPATH"
```

### Missing Credentials
```
SKIP: Missing environment variables
```
**Solution:** Set required environment variables for broker (see contract above)

### Authentication Failures
```
FAIL: authenticate() returned False
```
**Solution:** 
- Verify credentials are correct
- Check broker API status
- Verify account is active
- Check network connectivity

---

## Files Created

| File | Purpose | Executable |
|------|---------|------------|
| `scripts/broker_auth_smoke.sh` | Shell wrapper | ✅ Yes |
| `scripts/broker_auth_smoke.py` | Python test script | ✅ Yes |

---

## Related Documentation

- Broker Executors: `app/brokers/*_executor.py`
- Base Executor: `app/brokers/base_executor.py`
- Other Smoke Tests: `scripts/smoke_*.sh`

---

*Generated: 2026-01-23 18:50 UTC*
