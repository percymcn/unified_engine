# Broker Wiring Report: TradeLocker + ProjectX

**Date:** 2026-01-22  
**Branch:** `wire-brokers-tradelocker-projectx-20260122`  
**Goal:** Wire TradeLocker + ProjectX end-to-end for "Test Connection" + "Add Account" functionality

---

## STEP 0: Baseline Setup ✅

- Created branch: `wire-brokers-tradelocker-projectx-20260122`
- Created report file: `docs/WIRING_REPORT.md`

---

## STEP 1: Endpoint and Flow Mapping ✅

### Backend Endpoints Found

1. **`POST /api/v1/accounts/test-connection`**
   - Location: `app/routers/accounts.py:107`
   - Uses: `TestConnectionUseCase` (from container)
   - Request body: `{ broker: str, credentials: dict }`
   - Response: `{ success: bool, status: str, message: str, details: dict, detected_format?, symbol_map?, sample_symbols? }`

2. **`POST /api/v1/accounts/discover`**
   - Location: `app/routers/accounts.py:164`
   - Inline logic (not using use case)
   - Request body: `{ broker: str, credentials: dict }`
   - Response: `{ accounts: List[DiscoveredAccount], message?: str }`

3. **`POST /api/v1/accounts`** (Create Account)
   - Location: `app/routers/accounts.py:628`
   - Uses: `CreateAccountUseCase` (from container)
   - Request: `AccountCreate` schema
   - Response: `{ id: int, broker: str, is_active: bool, message: str }`

### Service/Use Case Flow

**Test Connection Flow:**
- Router → `TestConnectionUseCase.execute()` → Broker-specific `_test_*()` method
- TradeLocker: `_test_tradelocker()` in `app/application/use_cases/test_connection.py:127`
- ProjectX: `_test_projectx()` in `app/application/use_cases/test_connection.py:382`

**Discovery Flow:**
- Router → Inline executor construction → `executor.get_accounts()`
- TradeLocker: Lines 193-220 in `accounts.py` - constructs `TradeLockerExecutor` with credentials
- ProjectX: Lines 222-227 in `accounts.py` - constructs `ProjectXExecutor` with username + api_key

**Create Account Flow:**
- Router → `CreateAccountUseCase.execute()` → (need to check implementation)

### Executor Details

**TradeLocker Executor** (`app/brokers/tradelocker_executor.py`):
- Supports dual auth:
  - SDK mode: username + password + server + environment_url
  - Brand API mode: api_key + api_url
- Availability check: `_sdk_available` OR `_brand_api_available`
- Initialization tries SDK first, falls back to Brand API

**ProjectX Executor** (`app/brokers/projectx_executor.py`):
- Supports: username + api_key
- Uses SDK service if available, falls back to httpx
- Initialization: SDK first, then httpx fallback

### Current Issues Identified

1. **TradeLocker Brand API Requirements:**
   - Test connection supports Brand API (line 193-250 in test_connection.py)
   - BUT: No detection of broker-specific requirements (e.g., GATESFX requiring Brand API)
   - Missing: Server/environment-based auth mode detection
   - Missing: Clear error when Brand API required but username/password provided

2. **ProjectX:**
   - Test connection looks good (username + api_key)
   - Discovery uses executor.get_accounts() - need to verify this works

3. **Discovery Endpoint:**
   - TradeLocker: Credential handling looks complex (lines 198-220)
   - ProjectX: Simple construction (lines 224-227)

### Next Steps

- [ ] Step 2: TradeLocker dual auth improvements
- [ ] Step 3: ProjectX verification and fixes
- [ ] Step 4: UI form alignment
- [ ] Step 5: Smoke tests
- [ ] Step 6: Guardrails

---

## Commands Run

```bash
# Branch creation
git checkout -b wire-brokers-tradelocker-projectx-20260122

# Endpoint search
grep -r "test-connection" app/
grep -r "/api/v1/accounts" app/
```

---

**Status:** Step 1 Complete - Ready for Step 2
