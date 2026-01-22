---
phase: 21
plan: 01
subsystem: accounts
tags: [multi-account, position-sizing, risk-limits, grouping, routing]
depends_on:
  requires: [20-04]
  provides: [account-settings-api, account-groups-api, per-account-risk-limits]
  affects: [21-02, 21-03, 22-xx]
tech-stack:
  added: []
  patterns: [per-entity-settings, cascade-update]
key-files:
  created:
    - alembic/versions/009_add_account_settings_and_groups.py
    - app/application/dto/account_settings_dto.py
    - app/application/dto/account_group_dto.py
    - app/application/use_cases/update_account_settings.py
    - app/application/use_cases/manage_account_groups.py
    - app/infrastructure/repositories/account_group_repository.py
    - app/routers/account_groups.py
  modified:
    - app/models/database_models.py
    - app/routers/accounts.py
    - app/main.py
    - app/infrastructure/container.py
    - app/infrastructure/repositories/__init__.py
    - app/application/use_cases/__init__.py
    - app/application/dto/__init__.py
decisions:
  - id: group-caching
    choice: Cache group_name and group_color in TradingAccount
    rationale: Avoid joins for list queries, update via cascade when group changes
  - id: group-delete-cascade
    choice: Set accounts.group_id to NULL on group deletion
    rationale: Preserve accounts, don't orphan data
  - id: settings-partial-update
    choice: Only update provided (non-None) fields
    rationale: Standard PATCH semantics, avoids accidental resets
metrics:
  duration: 7m 9s
  completed: 2026-01-21
---

# Phase 21 Plan 01: Multi-Account Backend Infrastructure Summary

Per-account position sizing, risk limits, and account grouping infrastructure for multi-account trading support.

## One-Liner

Extended TradingAccount with position sizing modes, risk limits, and AccountGroup model for organizing accounts with full CRUD API.

## What Was Built

### 1. Database Schema Extensions (Task 1-2)

**TradingAccount new columns:**
- Position sizing: `position_sizing_mode` (fixed/percent_balance/percent_equity/risk_based), `fixed_lot_size`, `percent_of_balance`, `percent_of_equity`, `risk_percent_per_trade`
- Risk limits: `max_position_size`, `max_daily_loss`, `max_daily_loss_pct`, `max_drawdown_pct`, `max_open_positions`, `max_daily_trades`, `trade_cooldown_seconds`
- Grouping: `group_id` (FK), `group_name` (cached), `group_color` (cached)
- Routing: `is_signal_enabled`, `signal_priority`

**AccountGroup model:**
- `id`, `user_id`, `name`, `description`, `color`, `icon`, `is_active`
- Bidirectional relationship with TradingAccount

### 2. DTOs (Task 3)

**Account Settings DTOs:**
- `PositionSizingMode` enum: fixed, percent_balance, percent_equity, risk_based
- `AccountSettingsRequest` / `AccountSettingsResponse`
- `GetAccountSettingsRequest`

**Account Group DTOs:**
- `CreateAccountGroupRequest`, `UpdateAccountGroupRequest`, `DeleteAccountGroupRequest`
- `GetAccountGroupsRequest`, `AddAccountToGroupRequest`, `RemoveAccountFromGroupRequest`
- `AccountGroupResponse`, `AccountGroupListResponse`, `AccountGroupOperationResponse`

### 3. Use Cases (Task 4-5)

**Account Settings:**
- `UpdateAccountSettingsUseCase` - Updates only provided fields, validates ranges
- `GetAccountSettingsUseCase` - Retrieves current settings with ownership check

**Account Groups:**
- `CreateAccountGroupUseCase`, `GetAccountGroupsUseCase`, `GetAccountGroupUseCase`
- `UpdateAccountGroupUseCase` - Cascades name/color changes to accounts
- `DeleteAccountGroupUseCase` - Sets accounts' group_id to NULL
- `AddAccountToGroupUseCase`, `RemoveAccountFromGroupUseCase`

### 4. API Routes (Task 6)

**Account Settings (`/api/v1/accounts/{id}/settings`):**
```
GET  /{account_id}/settings  - Get current settings
PUT  /{account_id}/settings  - Update settings (partial)
```

**Account Groups (`/api/v1/account-groups`):**
```
GET    /                           - List all groups
GET    /{group_id}                 - Get single group
POST   /                           - Create group
PUT    /{group_id}                 - Update group
DELETE /{group_id}                 - Delete group
POST   /{group_id}/accounts/{id}   - Add account to group
DELETE /{group_id}/accounts/{id}   - Remove account from group
```

## Key Design Decisions

1. **Cached Group Info**: Stored `group_name` and `group_color` directly in TradingAccount to avoid joins when listing accounts. Updates cascade from AccountGroup to TradingAccount on group modification.

2. **Partial Updates**: Settings API only updates fields that are provided (non-None), following standard PATCH semantics. This prevents accidental resets of unspecified fields.

3. **Cascade Delete**: Deleting a group sets `group_id` to NULL for all associated accounts rather than deleting the accounts. Accounts are preserved but unassigned.

4. **Position Sizing Modes**: Four modes supported - fixed lot size, percentage of balance, percentage of equity, and risk-based (percentage of account at risk per trade).

## Deviations from Plan

None - plan executed exactly as written.

## Commits

1. `22be179` - feat(21-01): add per-account settings and AccountGroup model
2. `9fa8eae` - feat(21-01): add account settings and group DTOs
3. `8c995ad` - feat(21-01): add update account settings use case
4. `fa7aa67` - feat(21-01): add account group CRUD use cases and repository
5. `16bd8b8` - feat(21-01): add account settings and groups API routes

## Verification Results

All must-haves verified:
1. TradingAccount has position sizing columns (5 columns)
2. TradingAccount has risk limit columns (7 columns)
3. AccountGroup model exists with user relationship
4. Account settings can be updated via API
5. Account groups can be created, listed, updated, deleted
6. Accounts can be assigned to groups

## Next Phase Readiness

Phase 21 Plan 02 (Signal Routing Configuration) can proceed:
- TradingAccount has `is_signal_enabled` and `signal_priority` columns
- Account grouping infrastructure in place
- Settings API ready for routing configuration

Phase 22 (Risk Management) prerequisites met:
- Per-account risk limit columns available
- Position sizing modes ready for use in risk calculations
