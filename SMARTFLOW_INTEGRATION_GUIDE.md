# SmartFlow - Symbol Mapping & Signal Routing Integration Guide

**Date**: 2026-03-06
**Status**: SmartFlow can be integrated with existing routing infrastructure

---

## Summary

✅ **Time Filter Updated**: Now starts at **9:30am EST** (market open) instead of 10am
✅ **Symbol Mapping**: Infrastructure EXISTS and ready for SmartFlow integration
✅ **Signal Routing**: Multi-account routing system AVAILABLE but NOT YET integrated with SmartFlow

---

## 1. Time Filter Update ✅ DEPLOYED

### What Changed
- Time filter now supports **minute-level precision**
- Default window: **9:30am - 3:00pm EST** (was 10am-3pm)
- Database migration 036 applied
- New image: `smartflow-930` deployed

### Database Changes
```sql
-- New columns added:
time_filter_start_hour: 9    (was 10)
time_filter_start_minute: 30 (NEW)
time_filter_end_hour: 15
time_filter_end_minute: 0    (NEW)
```

### Verification
```sql
SELECT time_filter_start_hour, time_filter_start_minute,
       time_filter_end_hour, time_filter_end_minute
FROM smartflow_config WHERE user_id=56;

-- Result:
-- start: 9:30am ✅
-- end: 3:00pm ✅
```

---

## 2. Symbol Mapping System (EXISTS - Not Yet Integrated)

### What You Have
Your system includes a comprehensive **SymbolNormalizationService** that:

#### Features
- ✅ **TradingView → Broker mapping** (MNQ1! → NAS100, ES1! → US500, etc.)
- ✅ **Fuzzy matching** for unknown symbols
- ✅ **User-defined aliases** for custom mappings
- ✅ **Auto-detected aliases** with caching
- ✅ **Multi-broker support** (TradeLocker, Tradovate, ProjectX, MT5)

#### Pre-configured Mappings
```python
# Micro Futures → CFD Equivalents
'MNQ1!' → {'tradelocker': 'NAS100', 'tradovate': 'MNQ', 'projectx': 'MNQ'}
'MES1!' → {'tradelocker': 'US500', 'tradovate': 'MES', 'projectx': 'MES'}
'MYM1!' → {'tradelocker': 'US30', 'tradovate': 'MYM', 'projectx': 'MYM'}

# E-mini Futures
'NQ1!' → {'tradovate': 'NQ', 'projectx': 'NQ'}
'ES1!' → {'tradovate': 'ES', 'projectx': 'ES'}

# Commodities
'GC1!' → {'tradelocker': 'XAUUSD', 'tradovate': 'GC', 'projectx': 'GC'}
'CL1!' → {'tradelocker': 'USOIL', 'tradovate': 'CL', 'projectx': 'CL'}

# CFD → Futures
'US30' → {'tradovate': 'YM', 'projectx': 'YM', 'tradelocker': 'US30'}
'NAS100' → {'tradovate': 'NQ', 'projectx': 'NQ', 'tradelocker': 'NAS100'}
```

#### How It Works
```python
from app.domain.services.symbol_normalization_service import SymbolNormalizationService

service = SymbolNormalizationService()

# Normalize symbol (strip suffixes)
base = service.normalize_symbol("US30.pro")  # Returns "US30"

# Get known mapping
target = service.get_known_mapping("MNQ1!", "tradelocker")  # Returns "NAS100"

# Resolve with fuzzy matching
resolved = await service.resolve_symbol(
    user_id=56,
    source_symbol="NQ1!",
    broker_type="tradovate",
    available_symbols=["NQ", "MNQ", "ES", "MES"],
    alias_repository=repo
)
# Returns: "NQ"
```

### Current SmartFlow Mapping
SmartFlow has its own **simpler mapping** for leveraged ETFs:

```python
# app/services/smartflow_service.py
leveraged_etf_map = {
    'SPY': {'buy': 'SPXL', 'sell': 'SPXU'},  # 3x leveraged SPY
    'QQQ': {'buy': 'TQQQ', 'sell': 'SQQQ'},  # 3x leveraged QQQ
    'IWM': {'buy': 'TNA', 'sell': 'TZA'}     # 3x leveraged IWM
}
```

### Integration Opportunity
**SmartFlow could use SymbolNormalizationService** to:
1. Map flow tickers (SPY/QQQ/IWM) to broker-specific symbols
2. Support user-defined aliases for custom broker accounts
3. Auto-detect and cache successful mappings
4. Enable multi-broker signal delivery

---

## 3. Signal Routing System (EXISTS - Not Yet Integrated)

### What You Have
Your system includes **AccountRoutingService** for multi-account routing:

#### Routing Strategies
1. **all_accounts**: Send signal to all signal-enabled accounts
2. **specific_accounts**: Send to pre-defined account list
3. **rules_based**: Route by symbol/strategy/action patterns
4. **default_only**: Send to one default account

#### Features
- ✅ **Symbol filtering** (wildcards supported: "SPY", "ES*", etc.)
- ✅ **Action filtering** (buy/sell/close)
- ✅ **Priority ordering** (signal_priority field)
- ✅ **WebhookConfig integration**
- ✅ **Account groups**

#### Example Routing Rules
```python
# Route ES signals to futures account, SPY signals to stock account
routing_rules = [
    {
        "name": "Futures trades",
        "symbols": ["ES*", "NQ*", "MES*", "MNQ*"],
        "account_ids": [123],  # Tradovate account
    },
    {
        "name": "Stock trades",
        "symbols": ["SPY", "QQQ", "IWM"],
        "account_ids": [456],  # TradeLocker account
    }
]
```

### Current SmartFlow Routing
SmartFlow currently uses **simple webhook URLs**:
- Posts to `webhook_urls` list (configured per user)
- No account-level routing
- No symbol-based filtering
- Single webhook format for all signals

### Integration Opportunity
**SmartFlow could use AccountRoutingService** to:
1. Route signals to different accounts based on symbol
2. Support multiple brokers simultaneously
3. Apply account-specific risk limits
4. Enable advanced routing rules

---

## 4. How to Integrate (NOT YET DONE)

### Option A: Full Integration (Recommended)

**Changes needed in SmartFlow:**

```python
# app/services/smartflow_service.py

from app.domain.services.symbol_normalization_service import SymbolNormalizationService
from app.domain.services.account_routing_service import AccountRoutingService

class SmartFlowService:
    def __init__(self):
        # ... existing code ...
        self.symbol_service = SymbolNormalizationService()

    async def send_signal(self, signal: SmartFlowSignal, user_id: int, db: Session):
        """Send signal using multi-account routing"""

        # 1. Resolve accounts to trade on
        from app.domain.services.account_routing_service import AccountRoutingService
        routing_service = AccountRoutingService(db)

        # Use first webhook_key as routing key (or dedicated SmartFlow webhook_key)
        webhook_key = self.webhook_urls[0] if self.webhook_urls else None

        routing_decision = routing_service.resolve_accounts(
            webhook_key=webhook_key,
            symbol=signal.ticker,
            action=signal.action
        )

        if not routing_decision.is_valid:
            logger.warning(f"No accounts found for signal: {signal.ticker} {signal.action}")
            return

        # 2. Resolve symbol for each account's broker
        for account in routing_decision.accounts:
            # Get broker's available symbols
            available_symbols = await get_broker_symbols(account.broker_type)

            # Resolve symbol for this broker
            resolved_symbol = await self.symbol_service.resolve_and_cache(
                user_id=user_id,
                source_symbol=signal.ticker,
                broker_type=account.broker_type,
                available_symbols=available_symbols,
                alias_repository=alias_repo
            )

            if not resolved_symbol:
                logger.warning(f"Could not resolve {signal.ticker} for {account.broker_type}")
                continue

            # 3. Execute signal on broker
            await execute_signal(
                account_id=account.id,
                symbol=resolved_symbol,
                action=signal.action,
                score=signal.score,
                confidence=signal.confidence
            )
```

### Option B: Minimal Integration (Symbol Mapping Only)

**Just add symbol resolution without changing routing:**

```python
class SmartFlowService:
    def __init__(self):
        # ... existing code ...
        self.symbol_service = SymbolNormalizationService()
        self.default_broker = "tradelocker"  # Or from config

    def map_ticker(self, ticker: str) -> str:
        """Map flow ticker to broker symbol"""
        # Use known mappings
        mapped = self.symbol_service.get_known_mapping(ticker, self.default_broker)
        if mapped:
            return mapped

        # Fallback to existing logic
        if ticker == "SPY":
            return self.leveraged_etf_map['SPY']['buy'] if self.enable_leveraged_etfs else "MES"
        elif ticker == "QQQ":
            return "NQ"
        # ... etc
```

---

## 5. Current SmartFlow Workflow

```
FlowAlgo Data
    ↓
SmartFlow Service
    ↓
Sentiment Calculation (FSS)
    ↓
Filter Checks (EMA, RSI, Volume, Time, Fib)
    ↓
Confidence Scoring (0-100%)
    ↓
Signal Generation
    ↓
Ticker Mapping (SPY→MES, QQQ→NQ, IWM→RTY)
    ↓
Post to webhook_urls[] ← CURRENTLY HERE
```

### With Symbol Mapping Integration

```
FlowAlgo Data
    ↓
SmartFlow Service
    ↓
... (same filtering) ...
    ↓
Signal Generation
    ↓
SymbolNormalizationService ← NEW
  - Map to broker-specific symbols
  - Use user aliases if defined
  - Cache successful mappings
    ↓
Post to webhook_urls[]
```

### With Full Routing Integration

```
FlowAlgo Data
    ↓
SmartFlow Service
    ↓
... (same filtering) ...
    ↓
Signal Generation
    ↓
AccountRoutingService ← NEW
  - Resolve target accounts
  - Apply routing rules
  - Filter by symbol/action
    ↓
FOR EACH Account:
  SymbolNormalizationService ← NEW
    - Map to account's broker format
    ↓
  Execute on Broker
```

---

## 6. Benefits of Integration

### Symbol Mapping Benefits
- ✅ Support multiple brokers automatically
- ✅ User-defined custom mappings
- ✅ Fuzzy matching for new symbols
- ✅ Cached resolutions for performance

### Signal Routing Benefits
- ✅ Trade on multiple accounts simultaneously
- ✅ Route futures signals to Tradovate, stocks to TradeLocker
- ✅ Apply account-specific filters
- ✅ Different risk limits per account
- ✅ Advanced rules (e.g., "only SPY calls to account A")

---

## 7. Current Status

### What Works Now ✅
- Time filter: 9:30am-3:00pm EST
- Symbol mapping system: Available but not integrated
- Signal routing system: Available but not integrated
- SmartFlow: Works with simple webhook posting

### What Needs Integration ⏳
1. **Symbol Mapping**:
   - Add SymbolNormalizationService to SmartFlow
   - Map tickers based on user's broker type
   - Support user-defined aliases

2. **Signal Routing**:
   - Use AccountRoutingService instead of webhook_urls
   - Support multi-account trading
   - Apply routing rules

---

## 8. Quick Answer to Your Question

**Q: Does SmartFlow support symbol mapping and signal routing?**

**A**: Yes and No.

✅ **Infrastructure EXISTS**:
- SymbolNormalizationService: Comprehensive mapping (MNQ1!→NAS100, etc.)
- AccountRoutingService: Multi-account routing with rules

❌ **NOT YET INTEGRATED with SmartFlow**:
- SmartFlow uses simple ticker mapping (SPY→MES)
- SmartFlow posts to webhook_urls[] directly
- No account-level routing yet

**To Enable**:
- Option A: Full integration (multi-account + symbol mapping)
- Option B: Minimal integration (just symbol mapping)
- Both require code changes in smartflow_service.py

---

## 9. Recommendation

**For Now**: SmartFlow works as-is with:
- 9:30am market open ✅
- Simple futures mapping (SPY→MES, QQQ→NQ)
- Webhook posting

**Later**: Consider integrating if you need:
- Multiple brokers (Tradovate + TradeLocker simultaneously)
- Account-specific routing (futures vs stocks)
- User-defined symbol aliases

---

## 10. Files Referenced

**Symbol Mapping**:
- `/app/domain/services/symbol_normalization_service.py` (375 lines)
- `/app/infrastructure/repositories/symbol_alias_repository.py`
- `/app/domain/entities/symbol_alias.py`

**Signal Routing**:
- `/app/domain/services/account_routing_service.py` (315 lines)
- `/app/webhooks/signal_router.py` (364 lines)
- `/app/routers/webhook_execute.py`

**SmartFlow**:
- `/app/services/smartflow_service.py` (current simple mapping)
- `/app/routers/smartflow.py` (API endpoints)

---

*Guide created: 2026-03-06T04:30:00Z*
*Time filter: ✅ Updated to 9:30am*
*Symbol mapping: ⏳ Available for integration*
*Signal routing: ⏳ Available for integration*
