# Live Wiring Status: TradeLocker + ProjectX

**Date:** 2026-01-22
**Branch:** `wire-brokers-tradelocker-projectx-20260122`
**Status:** Ready for live testing

---

## System Status

| Component | Status | Port |
|-----------|--------|------|
| Backend | GREEN | 8765 |
| UI | GREEN | 3456 |
| Redis | Connected | 6379 |
| Database | SQLite (absolute path) | - |

---

## TradeLocker Wiring

### Status: COMPLETE

| Feature | Status | Notes |
|---------|--------|-------|
| SDK Mode | READY | username/password/server |
| Brand API Mode | READY | api_key + environment_url |
| GATESFX Detection | READY | Auto-forces Brand API |
| Test Connection | READY | Clear error messages |
| Account Discovery | READY | Returns account list |
| UI Form | READY | Dynamic field detection |

### Auth Modes

**SDK Mode (default):**
```json
{
  "broker": "tradelocker",
  "credentials": {
    "username": "your-email@example.com",
    "password": "your-password",
    "server": "Demo Server",
    "environment": "https://demo.tradelocker.com"
  }
}
```

**Brand API Mode (GATESFX or when api_key provided):**
```json
{
  "broker": "tradelocker",
  "credentials": {
    "api_key": "your-brand-api-key",
    "server": "GATESFX",
    "environment_url": "https://live.tradelocker.com"
  }
}
```

### How to Test via UI

1. Navigate to **Settings > Accounts**
2. Click **Add Account**
3. Select **TradeLocker**
4. For SDK mode: Enter email, password, server (e.g., "Demo Server")
5. For Brand API (GATESFX): Enter server as "GATESFX" - form will show Brand API alert
6. Click **Test Connection**
7. If successful, select discovered accounts
8. Click **Add Account**

---

## ProjectX/TopStep Wiring

### Status: COMPLETE

| Feature | Status | Notes |
|---------|--------|-------|
| SDK Mode | READY | username + api_key |
| httpx Fallback | READY | Uses gateway API |
| Test Connection | READY | Clear error messages |
| Account Discovery | READY | Manual add if empty |
| UI Form | READY | Shows username + apiKey |

### Auth Mode

```json
{
  "broker": "projectx",
  "credentials": {
    "username": "your-topstep-username",
    "api_key": "your-api-key"
  }
}
```

### How to Test via UI

1. Navigate to **Settings > Accounts**
2. Click **Add Account**
3. Select **ProjectX** or **TopStep**
4. Enter username and API key
5. Click **Test Connection**
6. If no accounts discovered: use manual account ID
7. Click **Add Account**

---

## Risk Defaults

### Status: COMPLETE

| Feature | Status | Notes |
|---------|--------|-------|
| UI Input | READY | Broker-aware units (pips/points/percent) |
| Storage | READY | Stored in broker units in DB |
| Conversion | READY | At execution time via `RiskUnitConverter` |

### Broker Unit Modes

| Broker | Default Unit |
|--------|--------------|
| TradeLocker | pips |
| ProjectX | percent |
| Tradovate | points |
| MT4/MT5 | pips |

### Conversion at Execution

When a signal is processed with an entry price, the `SignalProcessor` converts:
- `defaultStopLoss` (broker units) → absolute SL price
- `defaultTakeProfit` (broker units) → absolute TP price

Formula for pips: `price = entry ± (pips × pipSize)`
Formula for percent: `price = entry × (1 ± percent/100)`

---

## Known Limitations

### Authentication

- Account endpoints require JWT authentication
- Use UI session or get token via `/api/v1/auth/login`
- curl without auth returns 401

### SDK Availability

- TradeLocker SDK: `pip install tradelocker`
- ProjectX SDK: `pip install project-x-py`
- Both work with httpx fallback if SDK not installed

### Discovery

- ProjectX: May return empty accounts - UI prompts manual add
- TradeLocker SDK: Requires correct server name

---

## Test Commands

### Backend Health
```bash
curl http://127.0.0.1:8765/health
# Expected: {"status":"healthy","redis":"connected",...}
```

### Unit Tests
```bash
# Connection tests (25 tests)
python3 -m pytest tests/test_connection_test.py -q

# Risk converter tests (14 tests)
python3 -m pytest tests/test_risk_unit_converter.py -v
```

### UI Build
```bash
cd ui-next && npm run build -- --no-lint
```

---

## Live Testing Checklist

### TradeLocker (requires credentials)

- [ ] SDK mode test connection
- [ ] SDK mode account discovery
- [ ] SDK mode add account
- [ ] GATESFX Brand API mode (if applicable)
- [ ] Signal with risk defaults executes correctly

### ProjectX/TopStep (requires credentials)

- [ ] Test connection
- [ ] Account discovery (or manual add)
- [ ] Add account
- [ ] Signal execution

---

## Files Changed (from main)

**Backend:**
- `app/application/use_cases/test_connection.py` - Brand API detection, ProjectX fixes
- `app/routers/accounts.py` - Discovery improvements
- `app/domain/services/risk_unit_converter.py` - Risk conversion
- `app/services/signal_processor.py` - Execution-time conversion

**UI:**
- `ui-next/src/components/accounts/account-form.tsx` - Dynamic Brand API
- `ui-next/src/lib/brokers/credentialSchemas.ts` - Field schemas
- `ui-next/src/lib/brokers/riskUnitConverter.ts` - UI risk converter

**Tests:**
- `tests/test_connection_test.py` - 25+ tests
- `tests/test_risk_unit_converter.py` - 14 tests

**Docs:**
- `docs/WIRING_REPORT.md` - Complete wiring details
- `docs/SMOKE_TESTS.md` - Test commands
- `docs/LIVE_WIRING_STATUS.md` - This file

---

## Next Steps

1. **TradeLocker Live Test**: Provide SDK credentials (email/password/server) or Brand API key
2. **ProjectX Live Test**: Provide username + api_key
3. **Signal Execution Test**: Send test signal to verify SL/TP conversion

---

*Generated: 2026-01-22*
