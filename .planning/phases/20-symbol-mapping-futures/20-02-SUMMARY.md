# Phase 20 Plan 02: Symbol Auto-Detection Summary

## One-liner
Automatic broker symbol format detection on connection with pattern-based mapping and auto-alias generation.

## What Was Built

### BrokerSymbolFormat Model
Database table to persist detected symbol patterns per account:
- `detected_patterns`: JSON with suffix, prefix, case, confidence
- `sample_symbols`: First 20 broker symbols for UI preview
- `common_symbols_map`: Pre-built mappings (EURUSD -> EURUSD.pro)
- One-to-one relationship with Account

### SymbolFormatDetector Service
Domain service that analyzes broker symbols to detect naming patterns:
- Detects common suffixes (.pro, .raw, .std, .mini, .micro)
- Detects prefix patterns (t, m, mini, micro)
- Detects case patterns (upper, lower, mixed)
- Builds symbol mappings from reference symbols
- Confidence scoring for detection quality

### Connection Test Integration
Updated test_connection use case to detect symbols on successful connection:
- TradeLocker SDK/Brand API: Gets instruments and detects format
- Tradovate: Gets contracts after authentication
- ProjectX/TopStep: Gets contracts via SDK or httpx
- MT4/MT5: Gets symbols via MetaAPI SDK or Manager API
- Returns `detected_format`, `symbol_map`, `sample_symbols` in response

### Auto-Alias Generation
Automatically creates symbol aliases when account is created:
- Bulk creation from symbol_map
- Skips existing aliases (user-defined take priority)
- Only creates aliases where source != target
- Returns count of created aliases
- Repository methods: `bulk_create_auto_aliases()`, `delete_auto_detected()`

## Files Changed

### New Files
- `app/domain/services/symbol_format_detector.py` - Pattern detection service
- `alembic/versions/007_add_broker_symbol_format.py` - Migration
- `tests/test_symbol_detection.py` - 28 unit tests

### Modified Files
- `app/models/models.py` - Added BrokerSymbolFormat model
- `app/application/dto/account_dto.py` - Added detection fields to DTOs
- `app/application/use_cases/test_connection.py` - Symbol detection on success
- `app/application/use_cases/manage_accounts.py` - Auto-alias creation
- `app/domain/ports/symbol_alias_repository_port.py` - New methods
- `app/infrastructure/repositories/symbol_alias_repository.py` - Implementation
- `app/infrastructure/container.py` - Added symbol_alias_repository
- `app/models/schemas.py` - Extended AccountCreate
- `app/routers/accounts.py` - Pass detection data, return alias count

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Pattern-based detection over explicit configuration | Reduces manual setup, works across brokers |
| Confidence scoring for detection quality | UI can warn when low confidence |
| User aliases take priority over auto-detected | User customizations always override system |
| Don't fail account creation if alias creation fails | Graceful degradation |
| 20 sample symbols for preview | Balance between useful preview and response size |

## Test Results

```
28 passed in 0.66s
```

Tests cover:
- Suffix detection (.pro, .raw, .std)
- Case detection (upper, lower, mixed)
- Symbol map building
- Symbol matching (exact, fuzzy)
- Edge cases (empty, single, numbers)
- Model structure
- DTO fields

## Verification Checklist

- [x] BrokerSymbolFormat table exists (migration created)
- [x] SymbolFormatDetector correctly identifies common suffixes
- [x] Connection test returns detected format information
- [x] Auto-aliases created when account is connected
- [x] Auto-detected aliases used in symbol resolution

## API Changes

### POST /accounts/test-connection Response
Now includes on successful connection:
```json
{
  "success": true,
  "status": "connected",
  "message": "...",
  "detected_format": {"suffix": ".pro", "case": "upper", "confidence": 0.95},
  "symbol_map": {"EURUSD": "EURUSD.pro", "US30": "US30.pro"},
  "sample_symbols": ["EURUSD.pro", "GBPUSD.pro", ...]
}
```

### POST /accounts Request
Now accepts symbol detection data:
```json
{
  "account_id": "...",
  "broker": "tradelocker",
  "detected_format": {...},
  "symbol_map": {...},
  "sample_symbols": [...]
}
```

### POST /accounts Response
Includes alias count when aliases created:
```json
{
  "id": "...",
  "broker": "tradelocker",
  "is_active": true,
  "auto_aliases_created": 15,
  "message": "Account created with 15 auto-detected symbol aliases"
}
```

## Phase 20 Progress

- [x] 20-01: Symbol Normalization Service (SYM-01, SYM-04)
- [x] 20-02: Symbol Auto-Detection (SYM-03) - THIS PLAN
- [ ] 20-03: Symbol Mapping UI (SYM-02)
- [ ] 20-04: Futures Contract Support (SYM-05, SYM-06)

## Duration

Started: 2026-01-21T20:46:16Z
Completed: 2026-01-21T20:55:51Z
Duration: ~10 minutes
