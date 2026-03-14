# SmartFlow → TradeFlow Routing Integration

**Date**: 2026-03-06
**Status**: ✅ DEPLOYED - SmartFlow now supports routing

---

## Summary

✅ **SmartFlow now posts signals in TradingView format**
✅ **Automatically uses your existing routing infrastructure**
✅ **No UI changes needed - just add a webhook_key to config**

---

## What Changed

SmartFlow signals now flow through your existing `webhook_execute` endpoint, which means:

- ✅ **Multi-account routing** (all_accounts, specific_accounts, rules_based)
- ✅ **Symbol normalization** (MES → broker-specific format per account)
- ✅ **Account filtering** (route futures to Tradovate, stocks to TradeLocker)
- ✅ **All existing routing rules** apply to SmartFlow

---

## How It Works

```
SmartFlow Service
    ↓
Generates Signal (BUY MES, FSS=8.5, Confidence=85%)
    ↓
Checks webhook_urls format:
  - If webhook_key (abc123): Use routing ✅
  - If full URL (http://...): Use legacy format
    ↓
Post to /api/v1/webhook/execute
{
  "webhook_key": "abc123...",
  "action": "buy",
  "symbol": "MES",
  "comment": "SmartFlow: FSS=8.5, Confidence=85%..."
}
    ↓
webhook_execute.py (existing endpoint)
    ↓
AccountRoutingService
  - Resolves webhook_key to target accounts
  - Applies routing strategy (all_accounts, rules_based, etc.)
    ↓
FOR EACH Account:
  SymbolNormalizationService
    - Maps MES to broker format (MES for Tradovate, US500 for TradeLocker, etc.)
    ↓
  Execute trade on broker
```

---

## Setup Steps

### Option 1: Create Webhook via UI (Easiest)

1. **Navigate to Webhook Config**:
   - Go to TradeFlow dashboard → Webhooks/Routing section

2. **Create New Webhook Config**:
   - Click "Add Webhook"
   - Name: "SmartFlow Signals"
   - Routing Strategy: Choose one:
     - `all_accounts`: Send to all signal-enabled accounts
     - `specific_accounts`: Only to specific accounts (select from list)
     - `rules_based`: Apply symbol/action rules
     - `default_only`: Just default account

3. **Configure Routing Rules** (if rules_based):
   ```json
   [
     {
       "name": "Futures to Tradovate",
       "symbols": ["MES", "NQ", "MYM", "RTY", "GC"],
       "account_ids": [123]
     },
     {
       "name": "Stocks to TradeLocker",
       "symbols": ["SPY", "QQQ", "IWM"],
       "account_ids": [456]
     }
   ]
   ```

4. **Copy Webhook Key**:
   - After creating, you'll see a webhook_key like: `sf_abc123def456ghi789`
   - Copy this key

5. **Update SmartFlow Config**:
   ```bash
   curl -X PUT https://mytradeflow.app/api/v1/smartflow/config \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "enabled": true,
       "webhook_urls": ["sf_abc123def456ghi789"],
       "enable_golden_sweeps": true,
       "enable_price_confirmation": true,
       "enable_rsi_filter": true,
       "enable_time_filter": true,
       "min_confidence_score": 70
     }'
   ```

**That's it!** SmartFlow signals will now route through your multi-account system.

---

### Option 2: Create Webhook via API

```bash
# 1. Create WebhookConfig
curl -X POST https://mytradeflow.app/api/v1/webhooks/configs \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SmartFlow Signals",
    "description": "Routes SmartFlow signals to trading accounts",
    "routing_strategy": "all_accounts",
    "is_active": true
  }'

# Response will include:
{
  "id": 1,
  "webhook_key": "sf_abc123def456ghi789",  # ← Copy this
  "name": "SmartFlow Signals",
  "routing_strategy": "all_accounts",
  ...
}

# 2. Configure SmartFlow to use this webhook_key
curl -X PUT https://mytradeflow.app/api/v1/smartflow/config \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "webhook_urls": ["sf_abc123def456ghi789"],  # ← Use the key
    "enable_golden_sweeps": true,
    "min_confidence_score": 70
  }'
```

---

### Option 3: Direct Database Insert (Advanced)

```sql
-- 1. Create webhook config
INSERT INTO webhook_configs (
    user_id, webhook_key, name, routing_strategy, is_active, created_at
) VALUES (
    56,
    'sf_' || md5(random()::text || clock_timestamp()::text)::text,  -- Random key
    'SmartFlow Signals',
    'all_accounts',  -- or 'specific_accounts', 'rules_based', 'default_only'
    true,
    NOW()
) RETURNING webhook_key;

-- Copy the returned webhook_key

-- 2. Update SmartFlow config
UPDATE smartflow_config
SET webhook_urls = '["your_webhook_key_here"]'::jsonb
WHERE user_id = 56;
```

---

## Routing Strategies Explained

### 1. `all_accounts` (Simplest)
Send SmartFlow signal to **all** signal-enabled accounts:

```json
{
  "routing_strategy": "all_accounts"
}
```

**Use When**: You want every signal on all accounts (futures AND stocks)

---

### 2. `specific_accounts`
Send only to specific accounts:

```json
{
  "routing_strategy": "specific_accounts",
  "specific_account_ids": [123, 456]
}
```

**Use When**: You have dedicated accounts for SmartFlow (e.g., only your Tradovate account)

---

### 3. `rules_based` (Most Powerful)
Route by symbol/action patterns:

```json
{
  "routing_strategy": "rules_based",
  "routing_rules": [
    {
      "name": "Futures only",
      "symbols": ["MES", "NQ", "MYM", "RTY", "GC", "CL"],
      "account_ids": [123]
    },
    {
      "name": "Leveraged ETFs",
      "symbols": ["SPXL", "SPXU", "TQQQ", "SQQQ", "TNA", "TZA"],
      "account_ids": [456]
    },
    {
      "name": "Only buy signals to conservative account",
      "actions": ["buy"],
      "account_ids": [789]
    }
  ]
}
```

**Use When**: Different symbols go to different accounts (e.g., futures to Tradovate, ETFs to TradeLocker)

---

### 4. `default_only`
Send only to your default account:

```json
{
  "routing_strategy": "default_only",
  "default_account_id": 123
}
```

**Use When**: Testing or you only want SmartFlow on one account

---

## Symbol Mapping (Automatic)

SmartFlow sends symbols like `MES`, `NQ`, `SPXL`. Your `SymbolNormalizationService` automatically maps them:

### Example Mappings
```
SmartFlow Symbol → Tradovate → TradeLocker
─────────────────────────────────────────
MES              → MES      → US500
NQ               → NQ       → NAS100
MYM              → MYM      → US30
GC               → GC       → XAUUSD
SPXL             → SPXL     → (not available, skip)
```

### Custom Mappings
If you want custom mappings, create symbol aliases:

```sql
INSERT INTO symbol_aliases (user_id, source_symbol, broker_type, target_symbol)
VALUES
  (56, 'MES', 'tradelocker', 'US500.pro'),  -- Custom suffix
  (56, 'NQ', 'mt5', 'NAS100.raw');          -- Custom broker format
```

---

## Testing

### 1. Test Webhook Creation
```bash
# Check webhook exists
curl https://mytradeflow.app/api/v1/webhooks/configs \
  -H "Authorization: Bearer YOUR_TOKEN"

# Should see your SmartFlow webhook in the list
```

### 2. Test SmartFlow Config
```bash
# Check SmartFlow is configured
curl https://mytradeflow.app/api/v1/smartflow/config \
  -H "Authorization: Bearer YOUR_TOKEN"

# Look for:
{
  "enabled": true,
  "webhook_urls": ["sf_abc123..."],  # ← Your webhook_key
  ...
}
```

### 3. Test Routing (Manual Signal)
```bash
# Send a test signal through the webhook
curl -X POST https://mytradeflow.app/api/v1/webhook/execute \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_key": "sf_abc123...",  # Your key
    "action": "buy",
    "symbol": "MES",
    "quantity": 0.01,
    "comment": "Test SmartFlow routing"
  }'

# Check if signal reached your accounts
```

### 4. Test Live (During Market Hours)
```bash
# Enable SmartFlow
# Wait for market to open (9:30am EST)
# Watch logs:
docker logs -f [container_id] | grep SmartFlow

# Look for:
# "✅ SmartFlow → webhook_key sf_abc123... → BUY MES (FSS=8.5, Conf=85%)"

# Check dashboard for executed trades on routed accounts
```

---

## Example Workflow

### Conservative Setup (All Accounts)
```bash
# 1. Create webhook for all accounts
curl -X POST /api/v1/webhooks/configs -d '{
  "name": "SmartFlow Conservative",
  "routing_strategy": "all_accounts"
}'
# Returns: webhook_key = "sf_abc123..."

# 2. Configure SmartFlow with conservative preset
curl -X PUT /api/v1/smartflow/config -d '{
  "enabled": true,
  "webhook_urls": ["sf_abc123..."],
  "enable_golden_sweeps": true,
  "enable_price_confirmation": true,
  "enable_rsi_filter": true,
  "enable_time_filter": true,
  "min_confidence_score": 70
}'

# 3. SmartFlow generates signal
# Signal: BUY MES (FSS=8.5, Confidence=85%)

# 4. Routes to ALL signal-enabled accounts
# Tradovate account #123: BUY MES (futures)
# TradeLocker account #456: BUY US500 (CFD equivalent)
```

### Advanced Setup (Rules-Based)
```bash
# 1. Create webhook with symbol routing rules
curl -X POST /api/v1/webhooks/configs -d '{
  "name": "SmartFlow Advanced",
  "routing_strategy": "rules_based",
  "routing_rules": [
    {
      "name": "Micro futures to Tradovate",
      "symbols": ["MES", "MNQ", "MYM", "M2K"],
      "account_ids": [123]
    },
    {
      "name": "Leveraged ETFs to TradeLocker",
      "symbols": ["SPXL", "TQQQ", "TNA", "SPXU", "SQQQ", "TZA"],
      "account_ids": [456]
    }
  ]
}'
# Returns: webhook_key = "sf_xyz789..."

# 2. Configure SmartFlow with aggressive preset
curl -X PUT /api/v1/smartflow/config -d '{
  "enabled": true,
  "webhook_urls": ["sf_xyz789..."],
  "enable_leveraged_etfs": true,  # ← Will generate SPXL/TQQQ signals
  "enable_golden_sweeps": true,
  "enable_price_confirmation": true,
  "min_confidence_score": 75
}'

# 3. SmartFlow generates leveraged ETF signal
# Signal: BUY SPXL (based on SPY flows with enable_leveraged_etfs)

# 4. Routes via rules
# Rule matches: "Leveraged ETFs to TradeLocker"
# TradeLocker account #456: BUY SPXL
# Tradovate account #123: SKIPPED (not in rule)
```

---

## Monitoring

### Watch Routing in Action
```bash
# SmartFlow logs (signal generation)
docker logs -f [api_container] | grep "SmartFlow"

# Look for:
# "✅ SmartFlow → webhook_key sf_abc... → BUY MES (FSS=8.5, Conf=85%)"

# Routing logs (account resolution)
docker logs -f [api_container] | grep "Routing"

# Look for:
# "Routing decision: rules_based → 2 accounts (Futures to Tradovate)"

# Execution logs (broker trades)
docker logs -f [api_container] | grep "ExecutionLog"

# Look for:
# "ExecutionLog created: account_id=123, symbol=MES, action=BUY, status=pending"
```

### Dashboard Monitoring
1. Navigate to Signals page
2. Filter by source="SmartFlow"
3. Check which accounts executed
4. Verify symbols mapped correctly per broker

---

## Backward Compatibility

SmartFlow still supports **legacy webhook URLs** for custom integrations:

```json
{
  "webhook_urls": ["https://discord.com/api/webhooks/..."]  # ← Full URL
}
```

When SmartFlow sees a full `http://` or `https://` URL, it posts the old format:
```json
{
  "ticker": "MES",
  "action": "buy",
  "score": 8.5,
  "confidence": 85,
  "reason": "FSS=8.5 | Confidence=85% | Price✓ | RSI: 45"
}
```

This ensures existing Discord/Slack/custom webhooks still work.

---

## Troubleshooting

### Issue: "No accounts found for signal"
**Cause**: Webhook_key not configured or inactive

**Fix**:
```bash
# Check webhook exists and is active
SELECT * FROM webhook_configs WHERE webhook_key = 'your_key';

# If inactive, enable it:
UPDATE webhook_configs SET is_active = true WHERE webhook_key = 'your_key';
```

### Issue: "Could not resolve symbol MES for tradelocker"
**Cause**: Symbol not in broker's available symbols or no alias defined

**Fix**:
```sql
-- Create symbol alias
INSERT INTO symbol_aliases (user_id, source_symbol, broker_type, target_symbol)
VALUES (56, 'MES', 'tradelocker', 'US500');
```

### Issue: "Routing returned 422: Invalid action"
**Cause**: SmartFlow action not in ['buy', 'sell', 'close']

**Fix**: Check SmartFlow logs for generated action. Should only be buy/sell/close.

### Issue: Signals not executing
**Causes**:
1. Circuit breaker triggered
2. Max daily trades reached
3. Symbol blocked on account
4. Account not signal-enabled

**Fix**:
```bash
# Check account settings
SELECT id, account_name, is_signal_enabled, blocked_symbols, max_daily_trades
FROM trading_accounts WHERE user_id = 56;

# Enable signals if needed
UPDATE trading_accounts SET is_signal_enabled = true WHERE id = 123;
```

---

## Summary

✅ **SmartFlow is now integrated with your routing system**
✅ **No code changes needed - just configure a webhook_key**
✅ **All your existing routing rules apply to SmartFlow**
✅ **Symbol mapping happens automatically per broker**

**Next Steps**:
1. Create a webhook config (via UI or API)
2. Add webhook_key to SmartFlow config
3. Enable SmartFlow
4. Watch signals route to your accounts during market hours

---

*Guide created: 2026-03-06T04:45:00Z*
*SmartFlow routing: ✅ DEPLOYED*
*Time filter: ✅ 9:30am market open*
*Ready for testing during market hours*
