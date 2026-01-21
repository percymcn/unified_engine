---
phase: "20"
plan: "01"
subsystem: "symbol-mapping"
tags: ["symbol-normalization", "aliases", "fuzzy-matching", "signal-processing"]
dependencies:
  requires: []
  provides: ["SymbolNormalizationService", "SymbolAliasRepository", "symbol_aliases table"]
  affects: ["20-02", "20-03"]
tech-stack:
  added: []
  patterns: ["Repository pattern", "Domain service", "Fuzzy matching"]
key-files:
  created:
    - "app/domain/entities/symbol_alias.py"
    - "app/domain/services/symbol_normalization_service.py"
    - "app/domain/ports/symbol_alias_repository_port.py"
    - "app/infrastructure/repositories/symbol_alias_repository.py"
    - "alembic/versions/006_add_symbol_alias.py"
    - "tests/test_symbol_normalization.py"
  modified:
    - "app/domain/entities/__init__.py"
    - "app/domain/services/__init__.py"
    - "app/domain/ports/__init__.py"
    - "app/infrastructure/repositories/__init__.py"
    - "app/models/models.py"
    - "app/services/signal_processor.py"
decisions: []
metrics:
  duration: "10 minutes"
  completed: "2026-01-21"
---

# Phase 20 Plan 01: Symbol Normalization Service Summary

**One-liner:** TradingView symbol normalization with suffix stripping, known mappings, and fuzzy matching integrated into signal processing.

## What Was Built

### 1. SymbolAlias Domain Entity
Created `app/domain/entities/symbol_alias.py` with:
- User-specific symbol mappings (user_id, source_symbol, broker_type, target_symbol)
- Auto-detection flag for system-generated aliases
- Validation for valid brokers (tradelocker, mt4, mt5, tradovate, projectx, topstep)
- Normalization (source uppercase, broker lowercase)
- Update and mark_auto_detected methods

### 2. SymbolNormalizationService
Created `app/domain/services/symbol_normalization_service.py` with:

**Suffix Stripping Patterns:**
- Broker suffixes: `.pro`, `.raw`, `.std`, `.mini`, `.micro`
- Spread betting: `_SB`, `.SB`
- Delimited futures: `ES_25`, `NQ-25`
- CME front month codes: `NQH25` (H/M/U/Z months)
- PRESERVES valid symbols like `US30` (number is part of symbol)

**Known Static Mappings:**
| TradingView | Tradovate | ProjectX |
|-------------|-----------|----------|
| US30, DJ30, DOW | YM | YM |
| US500, SPX500, SPX | ES | ES |
| NAS100, USTEC, NDX | NQ | NQ |
| XAUUSD, GOLD | GC | GC |
| USOIL, WTIUSD | CL | CL |

**Resolution Order:**
1. User-defined aliases (highest priority)
2. Auto-detected aliases
3. Known static mappings
4. Fuzzy matching against available symbols (0.8 threshold)

### 3. SymbolAliasRepository
Created port interface and SQLAlchemy implementation:
- `get_by_user_and_broker()` - Get all aliases for user/broker
- `get_alias()` - Get specific alias
- `create()`, `update()`, `delete()` - CRUD operations
- `get_auto_detected()`, `get_user_defined()` - Filter by type
- Proper user isolation via user_id filtering

### 4. Database Migration
Created `alembic/versions/006_add_symbol_alias.py`:
- `symbol_aliases` table with user_id, source_symbol, broker_type, target_symbol
- Unique constraint on (user_id, source_symbol, broker_type)
- Indexes for efficient lookups

### 5. Signal Processor Integration
Modified `app/services/signal_processor.py`:
- Added `SymbolNormalizationService` initialization
- Added `_resolve_symbol_for_broker()` method
- Modified `_validate_signal()` to resolve symbols before validation
- Graceful degradation: falls back to original symbol if resolution fails
- Logs resolution attempts for debugging

### 6. Unit Tests
Created `tests/test_symbol_normalization.py` with 43 tests:
- Suffix stripping tests (10 tests)
- Variation generation tests (4 tests)
- Known mappings tests (6 tests)
- Fuzzy matching tests (7 tests)
- SymbolAlias entity tests (8 tests)
- Async resolution tests (8 tests)

## Verification Results

| Must-Have | Status |
|-----------|--------|
| SymbolAlias table exists with proper schema | PASS |
| SymbolNormalizationService normalizes symbols correctly | PASS |
| Symbol resolution uses alias lookup before fuzzy matching | PASS |
| Signal processor resolves symbols before broker execution | PASS |
| Unit tests cover normalization and resolution logic | PASS (43 tests) |

```bash
# Migration verified
python3 -m alembic upgrade 006_add_symbol_alias
# INFO: Running upgrade 005_add_token_expiry -> 006_add_symbol_alias

# Tests verified
python3 -m pytest tests/test_symbol_normalization.py -v
# 43 passed in 0.20s
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed overly aggressive suffix patterns**
- **Found during:** Task 4 (test execution)
- **Issue:** Pattern `[_-]?\d{2}$` was stripping "30" from "US30"
- **Fix:** Changed to only strip delimited futures codes and CME month codes
- **Files modified:** `symbol_normalization_service.py`

## Commits

| Hash | Description |
|------|-------------|
| 8955665 | Task 1: SymbolAlias entity and migration |
| d432960 | Tasks 2-3: Service and repository |
| 751d27c | Task 4: Signal processor integration + tests |

## Next Phase Readiness

**20-02 (Symbol Auto-Detection)** can proceed:
- SymbolNormalizationService provides `resolve_and_cache()` method
- Repository supports creating auto-detected aliases
- Infrastructure for caching resolutions is in place

**20-03 (Symbol Mapping UI)** can proceed:
- API endpoint needs to be created for CRUD operations
- SymbolAliasRepository provides all needed operations

## Files Created/Modified

**Created:**
- `app/domain/entities/symbol_alias.py` (129 lines)
- `app/domain/services/symbol_normalization_service.py` (360 lines)
- `app/domain/ports/symbol_alias_repository_port.py` (180 lines)
- `app/infrastructure/repositories/symbol_alias_repository.py` (236 lines)
- `alembic/versions/006_add_symbol_alias.py` (51 lines)
- `tests/test_symbol_normalization.py` (341 lines)

**Modified:**
- `app/domain/entities/__init__.py` (+2 lines)
- `app/domain/services/__init__.py` (+6 lines)
- `app/domain/ports/__init__.py` (+2 lines)
- `app/infrastructure/repositories/__init__.py` (+2 lines)
- `app/models/models.py` (+29 lines)
- `app/services/signal_processor.py` (+75 lines)
