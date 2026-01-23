# Phase 6: Smoke Tests

**Date:** January 23, 2026  
**Phase:** 6 - Smoke Test Execution

## Smoke Test Scripts

- `scripts/smoke_webhooks.sh` - Webhook endpoint tests
- `scripts/smoke_signal_intelligence.sh` - Signal Intelligence guard layer tests

## Test Execution

### Webhook Smoke Tests

```bash
$ export API_URL="http://localhost:3012"
$ ./scripts/smoke_webhooks.sh
```

### Signal Intelligence Smoke Tests

```bash
$ export API_URL="http://localhost:3012"
$ ./scripts/smoke_signal_intelligence.sh
```

## Test Results

### 1. Broker Mismatch (403 + broker_mismatch log)
- Expected: HTTP 403
- Actual: (captured)
- discard_bin entry: (check if created)

### 2. Stale Signal (SKIP)
- Expected: Signal skipped
- Actual: (captured)

### 3. Valid Broker Key Routing
- Expected: Routes correctly
- Actual: (captured)

## Findings

- All tests pass: Yes/No
- Any failures
- discard_bin verification
## Webhook Smoke Tests
```bash
=== Webhook Smoke Tests ===

1. Test TradingView Webhook (should process or guard)
POST http://localhost:3012/api/v1/webhooks/tradingview
