---
phase: 8
plan: 3
subsystem: ui-dashboard
tags: [next.js, react, trades, filtering, table, date-picker, shadcn]

dependency-graph:
  requires: [08-01, 08-02]
  provides: [trade-logs-table, trade-filters, date-range-picker]
  affects: [08-04]

tech-stack:
  added: []
  patterns: [bff-proxy, filter-state-management, date-range-selection]

key-files:
  created:
    - ui-next/src/types/trade.ts
    - ui-next/src/lib/api/trades.ts
    - ui-next/src/components/trades/trade-status-badge.tsx
    - ui-next/src/components/trades/trade-filters.tsx
    - ui-next/src/components/trades/trades-table.tsx
    - ui-next/src/components/ui/date-range-picker.tsx
    - ui-next/src/components/ui/popover.tsx
    - ui-next/src/components/ui/table.tsx
    - ui-next/src/components/ui/calendar.tsx
    - ui-next/src/components/ui/select.tsx
    - ui-next/src/app/api/trades/route.ts
    - ui-next/src/app/dashboard/trades/page.tsx
  modified: []

decisions:
  - DateRangePicker wraps shadcn Calendar with Popover for unified date range selection
  - TradeFilters uses controlled state with onChange callback for filter updates
  - Broker names displayed as friendly names (mt4 -> MetaTrader 4)
  - P/L column color-coded green/red with +/- prefix formatting
  - Side column (buy/sell) also color-coded for quick visual scanning
  - Filters re-fetch trades on change (no debouncing for immediate feedback)

metrics:
  duration: 17min
  completed: 2026-01-20
---

# Phase 8 Plan 3: Trade Logs Table Summary

Trade logs table with date, broker, and status filtering for trade history review.

## What Was Built

### Trade Types (Task 1)
- `Trade` interface with full trade properties (id, symbol, side, quantity, prices, P/L, status, broker, timestamps)
- `TradeStatus` type union: 'open' | 'closed' | 'pending' | 'cancelled'
- `TradeFilters` interface for filter state (dateFrom, dateTo, broker, status)

### Trade Service (Task 2)
- `getTrades()` function fetches from `/api/trades` BFF route
- Builds query string from TradeFilters object
- Handles 'all' value filtering (doesn't send to backend)

### Trade Status Badge (Task 3)
- Green badge for closed trades with profit
- Red badge for closed trades with loss
- Yellow badge for open trades
- Gray/outline badges for pending/cancelled

### Trade Filters Component (Task 4)
- DateRangePicker for date range selection (from/to)
- Broker dropdown (All, MT4, MT5, TradeLocker, Tradovate, TopStep)
- Status dropdown (All, Open, Closed, Pending, Cancelled)
- Reset button appears when any filter is active
- Controlled component with onChange callback

### Trades Table (Task 5)
- Columns: Symbol, Side, Qty, Entry, Exit, P/L, Status, Broker, Opened, Closed
- P/L formatted with +$/-$ prefix and color coding
- Side color coded (green buy, red sell)
- Sorted by opened_at descending
- Empty state with helpful message

### Trades API Route (Task 6)
- BFF route at `/api/trades`
- Proxies to backend `/api/v1/trades`
- Forwards filter query params (date_from, date_to, broker, status)
- Extracts auth token from httpOnly cookies

### Trades Dashboard Page (Task 7)
- Title "Trade History" with description
- TradeFilters component for filtering
- TradesTable component for display
- Refresh button with loading spinner
- Re-fetches when filters change

### Date Picker Components (Task 8)
- shadcn Calendar component (react-day-picker v9)
- shadcn Select component (@radix-ui/react-select)
- shadcn Popover component for calendar dropdown
- DateRangePicker wrapper combining Calendar + Popover

## Key Implementation Details

### Filter State Management
```typescript
const [filters, setFilters] = useState<TradeFiltersType>({});

// Re-fetch when filters change
useEffect(() => {
  fetchTrades();
}, [fetchTrades]);
```

### P/L Formatting
```typescript
const formatProfitLoss = (pnl: number | undefined) => {
  if (pnl === undefined) return '-';
  const formatted = pnl.toFixed(2);
  return pnl >= 0 ? `+$${formatted}` : `-$${Math.abs(pnl).toFixed(2)}`;
};
```

### Date Range to Filter Conversion
```typescript
const handleDateRangeChange = (range: DateRange | undefined) => {
  onFiltersChange({
    ...filters,
    dateFrom: range?.from?.toISOString().split('T')[0],
    dateTo: range?.to?.toISOString().split('T')[0],
  });
};
```

## Verification Checklist

- [x] Navigate to /dashboard/trades shows trades table
- [x] Table displays trades from backend (or empty state if none)
- [x] Filter by date range works (DateRangePicker)
- [x] Filter by broker works (Select dropdown)
- [x] Filter by status works (Select dropdown)
- [x] Reset filters button clears all filters
- [x] P/L column shows green/red colors
- [x] Page is protected (middleware handles auth redirect)
- [x] Build succeeds with no TypeScript errors

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| dbc7773 | feat | create trade types |
| 08008d7 | feat | create trade service |
| a1c9b6f | feat | create trade status badge component |
| 13572ea | feat | create trade filters component |
| 063d465 | feat | create trades table component |
| 19977ef | feat | create trades page API route |
| c324778 | feat | create trades dashboard page |
| 372e555 | feat | add date picker and select components |

## Next Phase Readiness

### Ready for 08-04 (WebSocket Integration)
- Trades table component ready for real-time updates
- Open trades can be updated via WebSocket
- Filter state preserved during updates

### Future Enhancements
- Pagination for large trade history
- CSV export functionality
- Trade detail modal
