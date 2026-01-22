# Backend Risk Compatibility Report

**Date**: 2025-01-05  
**Review Type**: PASS 2 - Backend Verification  
**Scope**: Verification of backend execution logic compatibility with broker-aware UI risk inputs

---

## Executive Summary

**CRITICAL MISMATCH DETECTED**: The backend expects **absolute price values** for stop loss and take profit, while the new UI allows users to input values in **pips, points, or percent** depending on broker.

**Status**: ⚠️ **RISK** - Backend cannot directly consume UI risk profile values without conversion layer.

---

## Per-Broker Analysis

### 1. TradeLocker

**File**: `app/brokers/tradelocker_executor.py`

**Stop Loss / Take Profit**:
- **Expected Unit**: Absolute price (float)
- **Lines**: 357-358 (SDK mode), 408-409 (Brand API mode)
- **Conversion**: None
- **Backend Behavior**: Passes `stop_loss` and `take_profit` directly to SDK/API as float values
- **UI Profile**: Pips (0.1 precision, 1-1000 range)
- **Mismatch**: ✅ **YES** - UI sends pips, backend expects price

**Position Size**:
- **Expected Unit**: Lots (float)
- **Lines**: 353 (SDK), 406 (Brand API)
- **Conversion**: None
- **Backend Behavior**: Passes `quantity` directly as float
- **UI Profile**: Lots (0.01 step, 0.01-100 range)
- **Mismatch**: ❌ **NO** - Compatible

**Notes**:
- SDK wrapper (`tradelocker_sdk_wrapper.py`) does not perform unit conversion
- Brand API expects raw price values

---

### 2. Tradovate

**File**: `app/brokers/tradovate_executor.py`

**Stop Loss / Take Profit**:
- **Expected Unit**: Absolute price (float)
- **Lines**: 413 (`stopPrice`), 460 (`stopPrice` in modifications)
- **Conversion**: None
- **Backend Behavior**: Uses `stopPrice` field (not `stop_loss`) - expects absolute price
- **UI Profile**: Points (0.25 precision, 0.25-500 range)
- **Mismatch**: ✅ **YES** - UI sends points, backend expects price

**Position Size**:
- **Expected Unit**: Contracts (integer)
- **Lines**: 411 (`orderQty`)
- **Conversion**: None
- **Backend Behavior**: Passes quantity as integer (contracts)
- **UI Profile**: Contracts (1 step, 1-100 range)
- **Mismatch**: ⚠️ **PARTIAL** - UI allows float, backend expects int (may auto-convert)

**Notes**:
- Tradovate API uses `stopPrice` field name (not `stop_loss`)
- No conversion from points to price

---

### 3. MT4

**File**: `app/brokers/mt4_executor.py`

**Stop Loss / Take Profit**:
- **Expected Unit**: Absolute price (float)
- **Lines**: 324-325 (SDK mode), 425-426 (httpx/Manager API mode as `sl`/`tp`)
- **Conversion**: None
- **Backend Behavior**: Passes `stop_loss`/`take_profit` directly to SDK or `sl`/`tp` to Manager API
- **UI Profile**: Pips (0.1 precision, 1-1000 range)
- **Mismatch**: ✅ **YES** - UI sends pips, backend expects price

**Position Size**:
- **Expected Unit**: Lots (float)
- **Lines**: 323 (SDK), 423 (httpx)
- **Conversion**: None
- **Backend Behavior**: Passes `volume`/`quantity` directly as float
- **UI Profile**: Lots (0.01 step, 0.01-100 range)
- **Mismatch**: ❌ **NO** - Compatible

**Notes**:
- MetaAPI SDK expects absolute price values
- Manager API uses `sl` and `tp` field names

---

### 4. MT5

**File**: `app/brokers/mt5_executor.py`

**Stop Loss / Take Profit**:
- **Expected Unit**: Absolute price (float)
- **Lines**: 325-326 (SDK mode), 449-450 (httpx/Manager API mode as `sl`/`tp`)
- **Conversion**: None
- **Backend Behavior**: Identical to MT4 - passes absolute price values
- **UI Profile**: Pips (0.1 precision, 1-1000 range)
- **Mismatch**: ✅ **YES** - UI sends pips, backend expects price

**Position Size**:
- **Expected Unit**: Lots (float)
- **Lines**: 324 (SDK), 447 (httpx)
- **Conversion**: None
- **Backend Behavior**: Passes `volume`/`quantity` directly as float
- **UI Profile**: Lots (0.01 step, 0.01-100 range)
- **Mismatch**: ❌ **NO** - Compatible

**Notes**:
- Same behavior as MT4 executor

---

### 5. ProjectX / TopStep

**File**: `app/brokers/projectx_executor.py`

**Stop Loss / Take Profit**:
- **Expected Unit**: Absolute price (float) OR percentage (unclear from code)
- **Lines**: 338-339 (SDK mode), 393-396 (httpx mode as `stopLoss`/`takeProfit`)
- **Conversion**: None
- **Backend Behavior**: Passes values directly - unit unclear from executor code
- **UI Profile**: Percent (0.01 precision, 0.1-10% range)
- **Mismatch**: ✅ **YES** - UI sends percent, backend unit unclear but likely expects price

**Position Size**:
- **Expected Unit**: Contracts/Size (integer)
- **Lines**: 330 (SDK as `size=int(order.quantity)`), 388 (httpx as `size=int(order.quantity)`)
- **Conversion**: Converts to integer
- **Backend Behavior**: Converts quantity to integer before sending
- **UI Profile**: Lots (0.01 step, 0.01-50 range)
- **Mismatch**: ⚠️ **PARTIAL** - Backend converts to int, may lose precision

**Notes**:
- ProjectX SDK and API expect integer size values
- Stop loss/take profit unit not clearly documented in executor

---

## Signal Processor Analysis

**File**: `app/services/signal_processor.py`

**Stop Loss / Take Profit Handling**:
- **Lines**: 853-854 - Passes `stop_loss` and `take_profit` directly from signal to order request
- **Lines**: 595-601 - Converts stop_loss to pips ONLY for position sizing calculation (internal use)
- **Conversion**: None for execution - only for internal risk-based position sizing

**Position Size Handling**:
- **Lines**: 128, 851 - Uses `quantity` from signal request
- **Lines**: 564-617 - Calculates position size based on account settings (risk-based sizing)
- **Conversion**: Position sizing service adjusts to broker specs (lot_step, min/max) but does not convert units

**Key Finding**: Signal processor does NOT convert pips/points/percent to price. It expects signals to already contain absolute price values.

---

## Position Sizing Service Analysis

**File**: `app/domain/services/position_sizing_service.py`

**Stop Loss Conversion**:
- **Lines**: 156-185 - `calculate_stop_loss_pips()` converts price difference to pips
- **Purpose**: Internal calculation for risk-based position sizing ONLY
- **NOT used for**: Broker execution - this is calculation-only

**Position Size Adjustment**:
- **Lines**: 141-154 - `_adjust_to_specs()` rounds to broker lot_step and enforces min/max
- **Purpose**: Ensures position size matches broker constraints
- **Unit**: Works with lots (no unit conversion)

---

## Adapters and Mappers Analysis

**Files Reviewed**:
- `app/infrastructure/adapters/tradelocker_adapter.py`
- `app/infrastructure/adapters/tradovate_adapter.py`
- `app/infrastructure/mappers/order_mapper.py`

**Findings**:
- **No unit conversion** in adapters - they pass values through directly
- **No normalization** of stop_loss/take_profit units
- Adapters convert between domain entities and executor primitives, but do not change units

---

## Summary Table

| Broker | Stop Loss Unit (Backend) | Stop Loss Unit (UI) | Mismatch | Take Profit Unit (Backend) | Take Profit Unit (UI) | Mismatch | Position Size Unit (Backend) | Position Size Unit (UI) | Mismatch |
|--------|---------------------------|---------------------|----------|----------------------------|-----------------------|----------|------------------------------|-------------------------|----------|
| **TradeLocker** | Absolute price | Pips | ✅ **YES** | Absolute price | Pips | ✅ **YES** | Lots (float) | Lots | ❌ No |
| **Tradovate** | Absolute price | Points | ✅ **YES** | Absolute price | Points | ✅ **YES** | Contracts (int) | Contracts | ⚠️ Partial* |
| **MT4** | Absolute price | Pips | ✅ **YES** | Absolute price | Pips | ✅ **YES** | Lots (float) | Lots | ❌ No |
| **MT5** | Absolute price | Pips | ✅ **YES** | Absolute price | Pips | ✅ **YES** | Lots (float) | Lots | ❌ No |
| **ProjectX** | Unclear (likely price) | Percent | ✅ **YES** | Unclear (likely price) | Percent | ✅ **YES** | Contracts (int) | Lots | ⚠️ Partial** |
| **TopStep** | Unclear (likely price) | Percent | ✅ **YES** | Unclear (likely price) | Percent | ✅ **YES** | Contracts (int) | Lots | ⚠️ Partial** |

\* Tradovate: UI allows float, backend expects int (may work due to auto-conversion)  
\** ProjectX/TopStep: Backend converts to int, may lose precision from UI's 0.01 step

---

## Critical Issues

### 1. Stop Loss / Take Profit Unit Mismatch

**Problem**: 
- UI allows users to input stop loss/take profit in broker-specific units (pips, points, percent)
- Backend executors expect absolute price values
- No conversion layer exists between UI and execution

**Impact**: 
- ⚠️ **HIGH RISK** - Orders will be placed with incorrect stop loss/take profit values
- Example: User enters "50 pips" for EURUSD, backend receives "50.0" as price → order will have SL at $50 instead of 50 pips from entry

**Evidence**:
- All executors pass `stop_loss`/`take_profit` directly to broker APIs without conversion
- Signal processor (line 853-854) passes values through unchanged
- Position sizing service converts to pips ONLY for internal calculation, not for execution

### 2. Position Size Precision (ProjectX/TopStep)

**Problem**:
- UI allows 0.01 step for ProjectX/TopStep
- Backend converts to integer (line 330, 388 in projectx_executor.py)
- Precision loss: 0.01 lots becomes 0 contracts

**Impact**:
- ⚠️ **MEDIUM RISK** - Small position sizes may be rounded to 0 or 1, losing precision

---

## Where Conversion Should Happen

**Current State**: No conversion exists

**Required Location**: 
1. **Signal Processor** (`app/services/signal_processor.py`) - Before creating OrderRequest
2. **OR** - **API Layer** (`app/api/`) - When receiving signal from UI
3. **OR** - **Adapter Layer** (`app/infrastructure/adapters/`) - When converting to broker format

**Recommended**: Signal Processor or dedicated conversion service, as it has access to:
- Symbol specifications (digits, pip size)
- Current market price
- Broker type

---

## Conversion Requirements

### For Stop Loss / Take Profit:

**TradeLocker / MT4 / MT5 (Pips → Price)**:
```
price = entry_price ± (pips × pip_size)
where pip_size = 0.0001 for 4-digit, 0.00001 for 5-digit symbols
```

**Tradovate (Points → Price)**:
```
price = entry_price ± (points × tick_size)
where tick_size depends on contract (e.g., 0.25 for ES, 0.01 for NQ)
```

**ProjectX / TopStep (Percent → Price)**:
```
price = entry_price × (1 ± percent/100)
OR
price_distance = (account_balance × percent/100) / position_size
price = entry_price ± price_distance
```

### For Position Size:

**ProjectX / TopStep (Lots → Contracts)**:
- Already handled: Backend converts to int
- Issue: May lose precision for fractional lots

---

## Recommendations

### Immediate Actions Required:

1. **DO NOT** deploy UI changes to production until conversion layer is implemented
2. **Add conversion service** to transform UI units to backend price values
3. **Update signal processor** to apply conversions before creating OrderRequest
4. **Add validation** to ensure converted values are within broker limits

### Implementation Priority:

1. **HIGH**: Stop Loss / Take Profit conversion (all brokers)
2. **MEDIUM**: Position size integer conversion validation (ProjectX/TopStep)
3. **LOW**: Add unit metadata to signal/order models for debugging

---

## Files Requiring Changes (Future Implementation)

**DO NOT MODIFY NOW** - This is a READ-ONLY review:

1. `app/services/signal_processor.py` - Add conversion before OrderRequest creation
2. `app/domain/services/position_sizing_service.py` - Extend to handle unit conversion
3. `app/models/pydantic_schemas.py` - Add unit metadata fields (optional)
4. New file: `app/services/risk_unit_converter.py` - Dedicated conversion service

---

## Safety Assessment

**Current State**: ⚠️ **UNSAFE FOR PRODUCTION**

**Reason**: UI will send pips/points/percent values that backend will interpret as absolute prices, causing incorrect order execution.

**Mitigation Required**: Conversion layer MUST be implemented before UI changes go live.

---

## Conclusion

The backend execution logic is **NOT compatible** with the new broker-aware UI risk inputs without a conversion layer. All brokers expect absolute price values for stop loss and take profit, while the UI now allows users to input values in broker-specific units (pips, points, percent).

**Status**: ⚠️ **RISK** - Requires conversion implementation before production deployment.

---

**Report Generated**: 2025-01-05  
**Reviewer**: AI Code Review Agent  
**Scope**: Backend executor and signal processing logic only
