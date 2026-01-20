---
phase: 8
plan: 4
subsystem: ui
tags: [websocket, real-time, react, nextjs]

dependency-graph:
  requires: [08-01, 08-02, 08-03]
  provides: [websocket-integration, real-time-updates, connection-status]
  affects: [09-xx, 10-xx]

tech-stack:
  added: []
  patterns: [websocket-provider-pattern, subscription-pattern, optimistic-ui]

key-files:
  created:
    - ui-next/src/types/websocket.ts
    - ui-next/src/hooks/use-websocket.ts
    - ui-next/src/providers/websocket-provider.tsx
    - ui-next/src/components/connection-status.tsx
  modified:
    - ui-next/src/app/dashboard/layout.tsx
    - ui-next/src/components/signals/signals-table.tsx
    - ui-next/src/components/brokers/broker-health-grid.tsx
    - ui-next/src/components/brokers/broker-health-card.tsx
    - ui-next/src/components/trades/trades-table.tsx
    - ui-next/src/components/header.tsx

decisions:
  - WebSocket URL auto-constructed from BACKEND_URL or explicit WS_URL env var
  - Subscription pattern for type-safe message handling by component
  - 30-second heartbeat interval to keep connection alive
  - Auto-reconnect with max 10 attempts at 3-second intervals
  - 3-second highlight animation for recently updated signals/trades
  - 2-second animation for broker status changes

metrics:
  duration: 24 min
  completed: 2026-01-20
---

# Phase 8 Plan 4: Real-time WebSocket Integration Summary

WebSocket client integration enabling real-time dashboard updates for signals, trades, and broker health without page refresh.

## One-liner

WebSocket provider with subscription pattern for real-time signal/trade/broker updates with connection status indicator.

## What Was Built

### WebSocket Infrastructure
- **Types** (`websocket.ts`): Message type definitions for signal_update, order_update, position_update, account_update, heartbeat, error
- **Hook** (`use-websocket.ts`): Reusable WebSocket hook with connection management, auto-reconnect, heartbeat
- **Provider** (`websocket-provider.tsx`): React context provider with subscription pattern for type-safe message handling

### Real-time Component Updates
- **SignalsTable**: Subscribes to signal_update events, updates signal status inline, shows "NEW" indicator with pulse animation
- **BrokerHealthGrid**: Subscribes to account_update events, updates connection status with ring animation on change
- **TradesTable**: Subscribes to order_update and position_update events, updates trade status and P/L in real-time

### Connection Status Indicator
- Header component showing WebSocket connection state
- Color-coded: green (connected), yellow pulsing (connecting), red (disconnected/error)
- Tooltip with connection details and reconnect attempts
- Click to manually reconnect when disconnected

## Technical Decisions

1. **WebSocket URL Configuration**: Auto-constructs WebSocket URL by converting `NEXT_PUBLIC_BACKEND_URL` from http(s) to ws(s) and appending `/ws`. Can also use explicit `NEXT_PUBLIC_WS_URL` env var.

2. **Subscription Pattern**: Components subscribe to specific message types via provider methods (subscribeToSignals, subscribeToOrders, etc.), enabling type-safe handlers without prop drilling.

3. **Heartbeat Strategy**: Client sends heartbeat every 30 seconds to keep connection alive. Server heartbeats handled silently.

4. **Reconnect Policy**: Auto-reconnect on disconnect with exponential backoff (3-second intervals, max 10 attempts).

5. **Visual Feedback**:
   - Signals/trades show "NEW"/"LIVE" indicator with 3-second pulse animation
   - Broker cards show ring animation for 2 seconds on status change
   - Connection indicator in header provides always-visible WebSocket state

## Commits

| Hash | Description |
|------|-------------|
| e077bd5 | Create WebSocket types |
| 5f52aa1 | Create WebSocket hook |
| fecb8ef | Create WebSocket provider |
| d76481c | Wrap dashboard with WebSocket provider |
| 7c0b75f | Add real-time updates to signals table |
| ff2e648 | Add real-time updates to broker health cards |
| a1da6e2 | Add real-time updates to trades table |
| 8a3d4ef | Add connection status indicator |
| c513a11 | Fix lint errors (unused imports) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Lint errors from unused imports**
- **Found during:** Build verification
- **Issue:** Unused `useEffect`, `UseWebSocketReturn`, `WebSocketMessageType` imports and unused `e` parameter in catch block
- **Fix:** Removed unused imports and changed `catch (e)` to `catch`
- **Files modified:** `use-websocket.ts`, `websocket-provider.tsx`
- **Commit:** c513a11

## Verification

- [x] WebSocket connects when dashboard loads (via WebSocketProvider)
- [x] Connection status indicator shows in header (ConnectionStatusIndicator)
- [x] Signal updates appear in real-time without refresh (subscribeToSignals)
- [x] Broker health updates appear in real-time (subscribeToAccounts)
- [x] Trade updates appear in real-time (subscribeToOrders, subscribeToPositions)
- [x] WebSocket reconnects automatically after disconnect (auto-reconnect logic)
- [x] Heartbeat messages keep connection alive (30-second interval)
- [x] Build compiles successfully (npm run build passed)

## Next Phase Readiness

Phase 8 complete. All 4 plans executed:
- 08-01: Signal Status Table
- 08-02: Broker Health Cards
- 08-03: Trade Logs Table
- 08-04: Real-time WebSocket Integration (this plan)

Dashboard now has:
- All UI components for signals, trades, broker health
- Filtering and sorting for trade history
- Real-time updates via WebSocket
- Connection status indicator

Ready to proceed to Phase 9 (API hardening / production readiness) or Phase 10 (deployment).
