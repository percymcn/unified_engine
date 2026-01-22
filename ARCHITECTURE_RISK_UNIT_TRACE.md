# Architecture Risk Unit Trace Report

**Date**: 2025-01-05  
**Review Type**: READ-ONLY Architecture Verification  
**Objective**: Verify if stop loss/take profit unit conversion (pips/points/percent → absolute price) is already implemented

---

## Executive Summary

**FINDING**: Unit conversion is **NOT implemented** for execution.

**Evidence**:
- Position sizing service converts price → pips (for calculation only)
- No conversion from pips/points/percent → price (for execution)
- All executors expect absolute price values
- Signal processor passes stop_loss/take_profit directly without conversion

**Status**: ⚠️ **UNSAFE** - UI will send pips/points/percent that backend interprets as absolute prices

---

## Data Flow Trace

### Entry Point: Webhook Signal

**File**: `app/routers/webhooks.py`

**Lines**: 103-104 (TradingView webhook)

```python
stop_loss=Decimal(str(payload["stop_loss"])) if payload.get("stop_loss") else None,
take_profit=Decimal(str(payload["take_profit"])) if payload.get("take_profit") else None,
```

**Unit Expected**: Absolute price (Decimal/float)  
**Conversion**: None - values passed through as-is  
**Source**: TradingView webhook payload

**Evidence from GSD Blueprint** (`03_API_SURFACE.md` line 184-185):
```json
"stop_loss": 1.0800,
"take_profit": 1.0950
```
These are absolute price values, not pips/points.

---

### Signal Processing Layer

**File**: `app/services/signal_processor.py`

**Lines**: 853-854

```python
stop_loss=signal_request.stop_loss,
take_profit=signal_request.take_profit,
```

**Unit Expected**: Absolute price (float)  
**Conversion**: None - values passed directly to OrderRequest  
**Entry Price Source**: `signal_request.price` (from webhook payload)

**Position Sizing Calculation** (Lines 595-601):
- Converts price → pips for **internal calculation only**
- Used for risk-based position sizing
- **NOT used for execution**

```python
stop_loss_pips = sizing_service.calculate_stop_loss_pips(
    signal_request.price,      # Entry price
    signal_request.stop_loss,  # Stop loss price
    specs.digits
)
```

**Key Finding**: Conversion is **one-way only** (price → pips), not reverse (pips → price).

---

## Per-Broker Analysis

### 1. TradeLocker

**Executor File**: `app/brokers/tradelocker_executor.py`  
**SDK Wrapper File**: `app/brokers/tradelocker_sdk_wrapper.py`  
**Adapter File**: `app/infrastructure/adapters/tradelocker_adapter.py`

#### Entry Price Source
- **Signal**: `signal_request.price` (from webhook)
- **Market Quote**: Not fetched before order placement
- **Current Price**: Not used for SL/TP conversion

#### Expected SL/TP Format
- **SDK Mode** (Line 357-358): Absolute price (float)
- **Brand API Mode** (Line 408-409): Absolute price (float)
- **SDK Wrapper** (Line 215-216): Supports `stop_loss_type` and `take_profit_type` ('absolute' or 'offset')
- **Executor Usage**: Always uses 'absolute' (default), never passes offset type

#### Conversion Location
- **File**: None
- **Function**: None
- **Status**: **NO CONVERSION**

#### UI Input Compatibility
- **UI Sends**: Pips (0.1 precision, 1-1000 range)
- **Backend Expects**: Absolute price
- **Mismatch**: ✅ **YES**

#### Safety Assessment
**UNSAFE** - UI pips will be interpreted as absolute prices (e.g., 50 pips → $50 price)

---

### 2. Tradovate

**Executor File**: `app/brokers/tradovate_executor.py`  
**Adapter File**: `app/infrastructure/adapters/tradovate_adapter.py`

#### Entry Price Source
- **Signal**: `signal_request.price` (from webhook)
- **Market Quote**: Not fetched before order placement
- **Current Price**: Not used for SL/TP conversion

#### Expected SL/TP Format
- **API Field**: `stopPrice` (Line 413, 460)
- **Unit**: Absolute price (float)
- **Note**: Tradovate API uses `stopPrice` field name, not `stop_loss`

#### Conversion Location
- **File**: None
- **Function**: None
- **Status**: **NO CONVERSION**

#### UI Input Compatibility
- **UI Sends**: Points (0.25 precision, 0.25-500 range)
- **Backend Expects**: Absolute price
- **Mismatch**: ✅ **YES**

#### Safety Assessment
**UNSAFE** - UI points will be interpreted as absolute prices (e.g., 25 points → $25 price)

---

### 3. MT4

**Executor File**: `app/brokers/mt4_executor.py`  
**Adapter File**: `app/infrastructure/adapters/mt4_adapter.py`

#### Entry Price Source
- **Signal**: `signal_request.price` (from webhook)
- **Market Quote**: Not fetched before order placement
- **Current Price**: Not used for SL/TP conversion

#### Expected SL/TP Format
- **SDK Mode** (Line 324-325): Absolute price (float)
- **Manager API Mode** (Line 425-426): `sl` and `tp` fields as absolute price (float)
- **MetaAPI SDK**: Expects absolute price values

#### Conversion Location
- **File**: None
- **Function**: None
- **Status**: **NO CONVERSION**

#### UI Input Compatibility
- **UI Sends**: Pips (0.1 precision, 1-1000 range)
- **Backend Expects**: Absolute price
- **Mismatch**: ✅ **YES**

#### Safety Assessment
**UNSAFE** - UI pips will be interpreted as absolute prices

---

### 4. MT5

**Executor File**: `app/brokers/mt5_executor.py`  
**Adapter File**: `app/infrastructure/adapters/mt5_adapter.py`

#### Entry Price Source
- **Signal**: `signal_request.price` (from webhook)
- **Market Quote**: Not fetched before order placement
- **Current Price**: Not used for SL/TP conversion

#### Expected SL/TP Format
- **SDK Mode** (Line 325-326): Absolute price (float)
- **Manager API Mode** (Line 449-450): `sl` and `tp` fields as absolute price (float)
- **MetaAPI SDK**: Expects absolute price values

#### Conversion Location
- **File**: None
- **Function**: None
- **Status**: **NO CONVERSION**

#### UI Input Compatibility
- **UI Sends**: Pips (0.1 precision, 1-1000 range)
- **Backend Expects**: Absolute price
- **Mismatch**: ✅ **YES**

#### Safety Assessment
**UNSAFE** - UI pips will be interpreted as absolute prices

---

### 5. ProjectX / TopStep

**Executor File**: `app/brokers/projectx_executor.py`  
**Adapter File**: `app/infrastructure/adapters/topstep_adapter.py`

#### Entry Price Source
- **Signal**: `signal_request.price` (from webhook)
- **Market Quote**: Not fetched before order placement
- **Current Price**: Not used for SL/TP conversion

#### Expected SL/TP Format
- **SDK Mode** (Line 338-339): Unit unclear from code, likely absolute price
- **Gateway API Mode** (Line 393-396): `stopLoss` and `takeProfit` as float
- **API Documentation**: Not found in executor code

#### Conversion Location
- **File**: None
- **Function**: None
- **Status**: **NO CONVERSION**

#### UI Input Compatibility
- **UI Sends**: Percent (0.01 precision, 0.1-10% range)
- **Backend Expects**: Unclear (likely absolute price or percentage of entry)
- **Mismatch**: ✅ **YES** (ambiguous - unit not documented)

#### Safety Assessment
**AMBIGUOUS** - Backend unit unclear, but likely expects price or percentage of entry price, not account balance percentage

---

## Conversion Logic Analysis

### Existing Conversion (Price → Pips)

**File**: `app/domain/services/position_sizing_service.py`  
**Function**: `calculate_stop_loss_pips()` (Lines 156-185)

**Purpose**: Convert absolute price difference to pips for position sizing calculation

**Usage**: 
- Called in `signal_processor.py` line 597
- Used ONLY for risk-based position sizing calculation
- **NOT used for execution**

**Formula**:
```python
distance = abs(entry_price - stop_loss_price)
pips = (distance / pip_size) * multiplier
```

**Direction**: Price → Pips (one-way only)

---

### Missing Conversion (Pips/Points/Percent → Price)

**Required But Not Found**:
- Pips → Price conversion
- Points → Price conversion  
- Percent → Price conversion

**Where It Should Be**:
- Signal processor (before OrderRequest creation)
- OR API layer (when receiving signal)
- OR Adapter layer (when converting to broker format)

**Current State**: **NOT IMPLEMENTED**

---

## TradeLocker SDK Offset Support

**Discovery**: TradeLocker SDK wrapper supports offset-based stop loss/take profit

**File**: `app/brokers/tradelocker_sdk_wrapper.py`  
**Lines**: 217-218, 232-233, 256-257

**Parameters**:
- `stop_loss_type: str = "absolute"` or `"offset"`
- `take_profit_type: str = "absolute"` or `"offset"`

**Status**: 
- SDK wrapper **supports** offset mode
- Executor **does NOT use** offset mode (always defaults to "absolute")
- Line 357-358: Executor passes only `stop_loss` and `take_profit` values, not types

**Implication**: TradeLocker SDK has native offset support, but it's not being utilized by the executor.

---

## Entry Price Availability

### Where Entry Price Comes From

1. **Webhook Payload**: `payload.get("price")` (Line 102 in webhooks.py)
2. **Signal Request**: `signal_request.price` (from webhook)
3. **Market Quote**: **NOT fetched** before order placement

### Entry Price Usage

- **Position Sizing**: Used to calculate stop loss pips (Line 598)
- **Order Execution**: Passed directly to broker as order price
- **SL/TP Conversion**: **NOT used** - no conversion happens

### Missing Entry Price Scenarios

- **Market Orders**: Entry price may be `None` or current market price
- **Limit Orders**: Entry price is limit price
- **No Price Signal**: If signal doesn't include price, conversion cannot happen

---

## Summary Table

| Broker | Entry Price Source | Expected SL/TP Unit | Conversion Location | UI Sends | Compatible? | Safety |
|--------|-------------------|---------------------|---------------------|----------|-------------|--------|
| **TradeLocker** | `signal_request.price` | Absolute price | None | Pips | ❌ No | **UNSAFE** |
| **Tradovate** | `signal_request.price` | Absolute price | None | Points | ❌ No | **UNSAFE** |
| **MT4** | `signal_request.price` | Absolute price | None | Pips | ❌ No | **UNSAFE** |
| **MT5** | `signal_request.price` | Absolute price | None | Pips | ❌ No | **UNSAFE** |
| **ProjectX** | `signal_request.price` | Unclear (likely price) | None | Percent | ❌ No | **AMBIGUOUS** |
| **TopStep** | `signal_request.price` | Unclear (likely price) | None | Percent | ❌ No | **AMBIGUOUS** |

---

## Key Findings

### 1. No Conversion Layer Exists

**Evidence**:
- Signal processor passes `stop_loss`/`take_profit` directly (Line 853-854)
- All executors receive absolute price values
- No conversion functions found in codebase
- Position sizing service converts price → pips (calculation only), not reverse

### 2. TradeLocker SDK Has Offset Support (Unused)

**Evidence**:
- SDK wrapper supports `stop_loss_type='offset'` (Line 217-218)
- Executor never uses offset mode (always defaults to 'absolute')
- This capability exists but is not utilized

### 3. Entry Price Available But Not Used for Conversion

**Evidence**:
- Entry price available as `signal_request.price`
- Used for position sizing calculation
- **NOT used** for SL/TP unit conversion

### 4. GSD Blueprint Confirms Absolute Price Expectation

**Evidence**:
- `03_API_SURFACE.md` shows examples with absolute prices (1.0800, 1.0950)
- No mention of pips/points/percent in API documentation
- Verification document mentions "SL/TP: fixed pips, fixed price, percentage" but only for calculation, not execution

---

## Architecture Verification Result

**Question**: Is stop loss/take profit unit conversion already implemented?

**Answer**: **NO**

**Reasoning**:
1. Position sizing service converts price → pips (one-way, calculation only)
2. No reverse conversion (pips/points/percent → price) exists
3. All executors expect absolute price values
4. Signal processor passes values through unchanged
5. TradeLocker SDK offset support exists but is unused

**Conclusion**: The system architecture does NOT include unit conversion for execution. UI changes that send pips/points/percent will result in incorrect order execution.

---

## Files Reviewed

### GSD Blueprints
- `.gsd/blueprint/02_DOMAIN_MODEL.md` - Domain entities, no unit conversion mentioned
- `.gsd/blueprint/03_API_SURFACE.md` - API examples show absolute prices
- `.gsd/blueprint/04_BROKER_WIRING.md` - Broker integration details, no conversion mentioned
- `.gsd/blueprint/05_DATA_FLOWS.md` - Data flow diagrams, no conversion step
- `.gsd/blueprint/10_BROKER_CREDENTIAL_SCHEMAS.md` - Credential schemas only

### Backend Code
- `app/routers/webhooks.py` - Webhook handlers, no conversion
- `app/services/signal_processor.py` - Signal processing, passes values through
- `app/domain/services/position_sizing_service.py` - Price → pips conversion (calculation only)
- `app/brokers/tradelocker_executor.py` - TradeLocker execution
- `app/brokers/tradovate_executor.py` - Tradovate execution
- `app/brokers/mt4_executor.py` - MT4 execution
- `app/brokers/mt5_executor.py` - MT5 execution
- `app/brokers/projectx_executor.py` - ProjectX execution
- `app/brokers/tradelocker_sdk_wrapper.py` - SDK wrapper with offset support (unused)
- `app/infrastructure/adapters/*.py` - Adapters, no conversion

### Planning Documents
- `.planning/phases/24-enhanced-features-monetization-v2/24-VERIFICATION.md` - Mentions "SL/TP: fixed pips" but verification shows calculation-only usage

---

## Recommendations

### Immediate Actions

1. **DO NOT** deploy UI changes until conversion layer is implemented
2. **Document** the mismatch clearly for development team
3. **Plan** conversion service implementation

### Implementation Notes (For Future)

**Required Conversion Formulas**:

**TradeLocker/MT4/MT5 (Pips → Price)**:
```
stop_loss_price = entry_price ± (pips × pip_size)
where pip_size = 0.0001 for 4-digit, 0.00001 for 5-digit symbols
```

**Tradovate (Points → Price)**:
```
stop_loss_price = entry_price ± (points × tick_size)
where tick_size depends on contract (requires contract specs lookup)
```

**ProjectX/TopStep (Percent → Price)**:
```
stop_loss_price = entry_price × (1 ± percent/100)
OR
price_distance = (entry_price × percent/100)
stop_loss_price = entry_price ± price_distance
```

**Entry Price Source**:
- Use `signal_request.price` if provided
- Otherwise fetch current market quote before conversion
- For market orders, use fill price after execution

---

**Report Generated**: 2025-01-05  
**Reviewer**: Architecture Verification Agent  
**Method**: READ-ONLY code and documentation analysis
