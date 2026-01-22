# Backend Risk Unit Conversion - Smoke Test

This document provides smoke test commands to verify that backend risk unit conversion is working correctly.

## Overview

The backend now converts broker-specific risk units (pips/points/percent) to absolute prices before execution. This ensures compatibility with broker APIs that require absolute price values.

## Test Scenarios

### 1. Signal with Absolute Prices (No Conversion Needed)

If a signal already contains absolute SL/TP prices, they are used as-is.

```bash
curl -X POST http://localhost:8765/api/v1/webhooks/signal/YOUR_WEBHOOK_KEY \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "EURUSD",
    "action": "buy",
    "quantity": 0.1,
    "price": 1.0850,
    "stop_loss": 1.0800,
    "take_profit": 1.0900
  }'
```

**Expected**: Order executes with SL=1.0800, TP=1.0900 (no conversion)

### 2. Signal Without SL/TP (Uses Account Defaults)

If a signal doesn't include SL/TP, account defaults are applied and converted.

**Prerequisites**:
- Account must have `default_stop_loss` and `default_take_profit` in `extra_metadata.risk_defaults`
- Example account settings (stored in `extra_metadata`):
  ```json
  {
    "risk_defaults": {
      "default_stop_loss": 50,
      "default_take_profit": 100
    }
  }
  ```

**Test Command**:
```bash
curl -X POST http://localhost:8765/api/v1/webhooks/signal/YOUR_WEBHOOK_KEY \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "EURUSD",
    "action": "buy",
    "quantity": 0.1,
    "price": 1.0850
  }'
```

**Expected Behavior**:
- For TradeLocker/MT4/MT5 (pips mode):
  - SL: 1.0850 - (50 * 0.0001) = 1.0800
  - TP: 1.0850 + (100 * 0.0001) = 1.0950
- Conversion logged: "Converted default stop loss 50 pips to absolute price 1.0800"

### 3. Tradovate Points Conversion

For Tradovate (points mode), defaults are converted using tick size.

**Test Command**:
```bash
curl -X POST http://localhost:8765/api/v1/webhooks/signal/YOUR_WEBHOOK_KEY \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "ES",
    "action": "buy",
    "quantity": 1,
    "price": 4500.00
  }'
```

**Expected** (with default_stop_loss=10 points, tick_size=0.25):
- SL: 4500.00 - (10 * 0.25) = 4497.50
- Conversion logged: "Converted default stop loss 10 points to absolute price 4497.50"

### 4. ProjectX Percent Conversion

For ProjectX/TopStep (percent mode), defaults are converted as percentage of entry price.

**Test Command**:
```bash
curl -X POST http://localhost:8765/api/v1/webhooks/signal/YOUR_WEBHOOK_KEY \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "EURUSD",
    "action": "buy",
    "quantity": 0.1,
    "price": 1.0850
  }'
```

**Expected** (with default_stop_loss=2.0 percent):
- SL: 1.0850 - (1.0850 * 0.02) = 1.0633
- Conversion logged: "Converted default stop loss 2.0 percent to absolute price 1.0633"

## Verification Steps

1. **Check Logs**: Look for conversion log messages:
   ```
   Converted default stop loss {value} {unit} to absolute price {price}
   Converted default take profit {value} {unit} to absolute price {price}
   ```

2. **Check Order Execution**: Verify that orders are placed with absolute price SL/TP values

3. **Check Error Handling**: If entry price cannot be determined, order should fail with clear error:
   ```
   Cannot determine entry price for {symbol}. Signal price is missing and quote fetch failed.
   ```

## Unit Tests

Run the unit tests to verify conversion logic:

```bash
cd /home/pharma5/unified_engine
python3 -m pytest tests/test_risk_unit_converter.py -v
```

**Expected**: All 14 tests pass

## Notes

- Conversion only applies when signal doesn't already have SL/TP values
- Entry price is required for conversion (from signal.price or broker quote)
- If entry price cannot be determined, conversion fails and order is not placed
- Defaults are read from `account.extra_metadata.risk_defaults`
- Broker unit mode is determined automatically based on broker type:
  - TradeLocker, MT4, MT5, TruForex: PIPS
  - Tradovate: POINTS
  - ProjectX, TopStep: PERCENT

## Troubleshooting

**Issue**: Conversion not happening
- Check that account has defaults in `extra_metadata.risk_defaults`
- Verify signal doesn't already have SL/TP values
- Check logs for conversion messages

**Issue**: Entry price missing
- Ensure signal includes `price` field
- Or broker executor has `get_quote()` method implemented
- Check logs for quote fetch errors

**Issue**: Wrong conversion values
- Verify broker type matches expected unit mode
- Check symbol specs (digits, tick_size) are correct
- Review conversion formulas in `risk_unit_converter.py`
