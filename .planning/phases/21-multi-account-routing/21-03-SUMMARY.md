---
phase: 21
plan: 03
type: frontend
subsystem: accounts-ui
tags: [react, next.js, account-management, routing-ui, position-sizing]
depends_on:
  requires: [21-01, 21-02]
  provides: [account-settings-ui, account-groups-ui, routing-config-ui]
  affects: [22-xx, 23-xx]
tech-stack:
  added: ["@radix-ui/react-tabs", "@radix-ui/react-radio-group"]
  patterns: [settings-forms, group-management, routing-ui]
key-files:
  created:
    - ui-next/src/app/dashboard/settings/accounts/[id]/settings/page.tsx
    - ui-next/src/app/dashboard/settings/groups/page.tsx
    - ui-next/src/components/accounts/account-settings-form.tsx
    - ui-next/src/components/settings/account-group-card.tsx
    - ui-next/src/components/settings/account-group-form.tsx
    - ui-next/src/components/settings/manage-group-accounts-dialog.tsx
    - ui-next/src/components/webhooks/routing-config.tsx
    - ui-next/src/components/ui/tabs.tsx
    - ui-next/src/components/ui/radio-group.tsx
  modified:
    - ui-next/src/types/account.ts
    - ui-next/src/types/routing.ts
    - ui-next/src/lib/api/accounts.ts
    - ui-next/src/components/accounts/account-list.tsx
    - ui-next/src/components/accounts/account-card.tsx
    - ui-next/src/components/routing/webhook-config-form.tsx
    - ui-next/src/components/sidebar.tsx
decisions:
  - id: "routing-strategy-ui"
    choice: "RadioGroup selection with conditional sections"
    rationale: "Clear visual separation of 4 routing strategies"
  - id: "account-settings-tabs"
    choice: "Tabs component for Position Sizing, Risk Limits, Routing"
    rationale: "Logical grouping reduces cognitive load"
  - id: "group-management"
    choice: "Separate groups page with manage dialog"
    rationale: "Keep accounts list focused, groups as organizational layer"
metrics:
  duration: "~25 minutes"
  completed: "2026-01-21"
  tasks: 6/6
---

# Phase 21 Plan 03: Account & Routing UI Summary

UI components for multi-account configuration with position sizing controls and signal routing setup

## One-liner

Account settings UI with position sizing modes, risk limits, group management, and 4 routing strategies (all/specific/rules/default)

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Account API client extensions | 4e99db5 |
| 2 | Account settings page with tabs | 4e99db5 |
| 3 | Account groups management page | 39ff48d |
| 4 | Enhanced accounts list with grouping | 59d888c, 3a5b987 |
| 5 | Routing configuration in webhook settings | 3a5b987, 05da534 |
| 6 | Sidebar navigation link for groups | f8ffd6a |

## Key Deliverables

### Account Settings Page
- Dynamic route `/settings/accounts/[id]/settings`
- Three-tab layout: Position Sizing, Risk Limits, Signal Routing
- Position sizing modes: Fixed, Percent Balance, Percent Equity, Risk-Based
- Risk limits: max position, daily loss, drawdown, trades, cooldown
- Signal enable/disable with priority control
- Group assignment dropdown

### Account Groups Management
- Full CRUD at `/settings/groups`
- Color picker (10 colors) and icon selector (6 icons)
- Live preview of group appearance
- Manage accounts dialog for bulk assignment
- Account count display on cards

### Routing Configuration
- Four strategies: All Accounts, Specific Accounts, Rules-Based, Default Only
- Conditional UI sections based on selected strategy
- Account checkbox list for specific_accounts mode
- Rules builder for rules_based mode
- Fallback account for failed rule matches

### Enhanced Account List
- Group filter tabs (All, per-group, Ungrouped)
- Group badge on account cards with color indicator
- Signal status indicator (Zap/ZapOff icons)
- Settings button linking to account settings page

## New Types Added

```typescript
// Account settings structure
interface AccountSettings {
  accountId: number;
  positionSizing: { mode, fixedLotSize, percentOfBalance, ... };
  riskLimits: { maxPositionSize, maxDailyLoss, maxDrawdownPct, ... };
  grouping: { groupId, groupName, groupColor };
  routing: { isSignalEnabled, signalPriority };
}

// Routing strategy type
type RoutingStrategy = 'all_accounts' | 'specific_accounts' | 'rules_based' | 'default_only';
```

## API Functions Added

- `getAccountSettings(accountId)` - Fetch account settings
- `updateAccountSettings(accountId, settings)` - Update settings
- `getAccountGroups()` - List all groups
- `createAccountGroup(data)` - Create new group
- `updateAccountGroup(id, data)` - Update group
- `deleteAccountGroup(id)` - Delete group
- `addAccountToGroup(groupId, accountId)` - Assign account
- `removeAccountFromGroup(groupId, accountId)` - Unassign account

## Dependencies Added

- `@radix-ui/react-tabs` - Tab component
- `@radix-ui/react-radio-group` - Radio group for strategy selection

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- [x] TypeScript compiles with no errors in new code
- [x] Account settings page accessible at `/settings/accounts/[id]/settings`
- [x] Groups page accessible at `/settings/groups`
- [x] Routing configuration integrated into webhook form
- [x] Sidebar has Account Groups link

## Next Phase Readiness

Ready for Phase 22 (Signal Processing Enhancements):
- Position sizing modes ready for signal executor to consume
- Risk limits available for pre-trade validation
- Account groups enable batch operations on accounts
- Routing strategies configured through UI
