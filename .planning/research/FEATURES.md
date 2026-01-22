# Features Research: v1.2 Broker Integration

## Executive Summary

For broker integration UX, the key features are: clear connection status, "Test & Connect" verification flow, multi-account selection with checkboxes, and credential security. The existing UI has basic scaffolding; v1.2 needs to enhance reliability and user confidence.

## Table Stakes Features

### Broker Connection

These are must-have features - users will abandon without them:

| Feature | Complexity | Description |
|---------|------------|-------------|
| Credential input form | Simple | API key, username, password fields per broker |
| Environment selector | Simple | Demo vs Live dropdown |
| Connection status indicator | Simple | Green/yellow/red dot with text |
| Test connection button | Medium | Verify credentials before saving |
| Error message display | Simple | Clear feedback on connection failures |
| Secure credential storage | Medium | Fernet encryption (already implemented) |

**Credential Input Patterns by Broker:**

| Broker | Fields Required |
|--------|-----------------|
| ProjectX/TopStep | Username, API Key |
| TradeLocker | Email, Password, Server |

### Account Management

| Feature | Complexity | Description |
|---------|------------|-------------|
| List connected accounts | Simple | Table showing all broker accounts |
| Account details view | Simple | Balance, equity, margin display |
| Remove account | Simple | Delete with confirmation dialog |
| Refresh account status | Simple | Manual "Refresh" button |
| Auto-refresh on page load | Simple | Fetch fresh data on mount |

### Account Selection for Signals

| Feature | Complexity | Description |
|---------|------------|-------------|
| Checkbox multi-select | Simple | Select which accounts receive signals |
| "Select All" / "Deselect All" | Simple | Bulk selection controls |
| Per-broker grouping | Simple | Accounts grouped by broker type |
| Selection persistence | Simple | Remember selections across sessions |
| Active indicator | Simple | Show which accounts are currently selected |

## Differentiator Features

These are nice-to-have features that improve UX but aren't blocking:

### Advanced Connection UX

| Feature | Complexity | Description |
|---------|------------|-------------|
| Connection wizard | Medium | Step-by-step onboarding flow |
| Credential validation hints | Medium | Real-time field validation |
| "Remember last server" | Simple | Persist TradeLocker server selection |
| Bulk import accounts | Complex | Import multiple accounts at once |
| OAuth flow for Tradovate | Complex | Already implemented (v1.1) |

### Account Monitoring

| Feature | Complexity | Description |
|---------|------------|-------------|
| Real-time balance updates | Medium | WebSocket push for account changes |
| Connection health history | Medium | Log of connection events |
| Auto-reconnect | Medium | Automatic reconnection on failure |
| Email alerts on disconnect | Complex | Notification system integration |

### Position Display

| Feature | Complexity | Description |
|---------|------------|-------------|
| Open positions per account | Medium | Show current holdings |
| P&L display | Medium | Unrealized profit/loss |
| Position close button | Medium | Manual position management |

## Anti-Features

Things to deliberately NOT build:

| Anti-Feature | Reason |
|--------------|--------|
| Manual trading UI | Tradeflow is signal routing, not a trading platform |
| Chart widgets | Use TradingView for charting |
| Complex order types | Signals define order type; UI just routes |
| Paper trading simulation | Use broker's demo environment instead |
| Social trading / copy trading | Out of scope for signal routing engine |
| Mobile app | Web-first, responsive design sufficient |

## Feature Dependencies

```
Credential Input → Test Connection → Save Account
       ↓
Account List → Account Selection → Signal Routing
       ↓
Position Display (optional, requires account connection)
```

**Build order implications:**
1. First: Credential forms and storage
2. Second: Test & Connect flow
3. Third: Account list and selection UI
4. Fourth: Position/balance display (optional polish)

## Complexity Assessment

| Feature | Complexity | Dependencies | Notes |
|---------|------------|--------------|-------|
| Credential form | Simple | None | Different fields per broker |
| Test connection | Medium | Backend API | Calls broker, returns status |
| Account list | Simple | Credential storage | Read from DB |
| Account selection | Simple | Account list | Checkboxes + persistence |
| Connection status | Simple | Test connection | UI state management |
| Real-time updates | Medium | WebSocket | Backend push to frontend |
| Position display | Medium | Broker API | Per-account position fetch |

## UX Patterns from Industry

### Test & Connect Flow

Best practice from trading platforms:

1. User enters credentials
2. User clicks "Test Connection"
3. UI shows loading spinner
4. Backend attempts authentication
5. On success: Green checkmark, "Connect" button enabled
6. On failure: Red X with error message
7. User clicks "Connect" to save account

### Account Status Display

```
┌─────────────────────────────────────────────┐
│ ProjectX - TopStep Demo Account             │
│ Status: ● Connected                         │
│ Balance: $50,000.00  |  Equity: $50,250.00  │
│ Last sync: 2 minutes ago  [Refresh]         │
│ ☑ Receive signals                           │
└─────────────────────────────────────────────┘
```

### Multi-Account Selection

```
Signal Routing Configuration
─────────────────────────────
☑ Select All  |  ☐ Deselect All

ProjectX / TopStep
  ☑ Demo Account - $50,000
  ☐ Live Account - $25,000

TradeLocker
  ☑ Demo Server - $100,000
  ☐ Live Server - $10,000

[Save Configuration]
```

---
*Researched: 2026-01-22 for v1.2 milestone*
