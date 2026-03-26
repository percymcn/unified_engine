# Session Notes 2026-03-20
## SmartFlow System - Major Work Done

### Fixes Applied
- UW market tide parser fixed (list/dict handler)
- SignalR reconnect handlers registered
- 649 stale DB records cleaned
- Strategy engines improved (MR/Trend/Breakout)
- OpenClaw blocking filter removed from signal chain
- Webhook routing fixed (user_id mismatch)
- MT5 symbol mapping added (US500.pro, NAS100.pro etc)
- AI-only crypto mode enabled (BTCUSD, ETHUSD, 60s scan)
- Account 81 (ProjectX) at max positions (9/10) - normal
- Market hours: 9:30-4:00 EST with AI-only crypto 24/7

### Key Details
- SmartFlow webhook key: SFFT_4eb332cb75f633e949152790ecce0431
- Internal router key: ZuAxYEW-MJHD0QJc7yBgqlK9rFZqO5mzYAf-Co1eHZk
- DB user for accounts: user_id=2 (securepharma11)
- Accounts: 81=ProjectX(max full), 82=MT5-3091187, 83=MT5-3084709
- FloAlgo proxy: PID running, scrapes every 30s, 131 flows/cycle

### Remaining Issues
- Position sync "ChunkedIteratorResult" warning (non-fatal)
- Account 81 max positions - will clear after market closes
- Weekend: AI-only crypto mode enabled, should auto-run
