# Research Summary: v1.2 Full Broker Integration

**Researched:** 2026-01-22
**Domain:** Trading Broker API Integration
**Milestone:** v1.2 (subsequent to shipped v1.1)

## Executive Summary

v1.2 focuses on hardening broker integrations for production reliability. The key decision is to **remove the project-x-py SDK** and use direct httpx calls to ProjectX Gateway API - the existing codebase already has this fallback implemented. TradeLocker continues using the official SDK with the async wrapper pattern.

**Critical findings:**

1. **ProjectX: Use httpx, not SDK** — The project-x-py SDK adds complexity (TradingSuite lifecycle, per-instrument connections) without benefit. The httpx fallback code already exists and is simpler.

2. **TradeLocker SDK works well** — The existing `TradeLockerSDKWrapper` with `ThreadPoolExecutor` is the right pattern. Just needs hardening for production.

3. **Token management is the #1 risk** — ProjectX JWT expires in 24h. Must implement proactive refresh before expiry to prevent missed trades.

4. **Contract caching needs short TTL** — Futures contracts roll over; cached contract IDs go stale. Use 4-hour TTL maximum.

5. **Test & Connect UX is table stakes** — Users expect to verify credentials before saving. Without it, they won't trust the platform.

## Key Stack Decisions

| Component | Decision | Rationale |
|-----------|----------|-----------|
| ProjectX HTTP | `httpx` 0.27.x | Already used, native async, clean API |
| TradeLocker | `tradelocker` SDK | Official package, handles auth internally |
| Retry logic | `tenacity` | Standard retry patterns, already available |
| Token storage | In-memory with refresh | Simple, token not sensitive (credentials are) |

## Architecture Summary

```
Signal Webhook
     │
     ▼
ProcessSignalUseCase
     │
     ├─► TopstepAdapter (httpx → ProjectX Gateway API)
     │        │
     │        ├─ TokenManager (proactive refresh)
     │        └─ ContractCache (4h TTL)
     │
     └─► TradeLockerAdapter (SDK wrapper)
              │
              ├─ TradeLockerSDKWrapper (ThreadPoolExecutor)
              └─ InstrumentCache (symbol → instrument_id)
```

## Critical Pitfalls to Avoid

| Pitfall | Severity | Prevention |
|---------|----------|------------|
| Token expiry mid-trade | CRITICAL | Refresh 1 hour before 24h expiry |
| Order rejection loops | CRITICAL | Retry only transient errors, max 3 attempts |
| Demo/Live confusion | CRITICAL | Store environment explicitly, clear UI badges |
| Rate limiting | HIGH | Semaphore, respect 429 Retry-After |
| Futures rollover | HIGH | Short cache TTL (4h), refresh on error |

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| httpx for ProjectX | HIGH | Already implemented, tested |
| TradeLocker SDK wrapper | HIGH | Pattern works, needs polish |
| Token refresh | HIGH | Standard JWT handling |
| Account UI | MEDIUM | Design clear, implementation TBD |
| Symbol mapping | MEDIUM | Futures rollover needs testing |

---

## Implications for Roadmap

Based on research, the planned 5-phase structure is confirmed:

### Phase 25: Bug Fix Verification
**Rationale:** Verify v1.1 bug fixes (auth cookies, risk page, WebSocket) before adding new features. Quick phase to establish baseline.
- Verify auth cookie fix
- Verify risk page loading
- Verify WebSocket heartbeat
- **Risk level:** Low — verification only

### Phase 26: ProjectX Gateway Integration
**Rationale:** Remove SDK complexity, harden httpx implementation. ProjectX is simpler than TradeLocker, making it a good first target.
- Remove project-x-py SDK dependency
- Extract `ProjectXTokenManager` class
- Implement proactive token refresh (1h buffer)
- Add `ContractCache` with 4h TTL
- Add retry logic with tenacity (transient errors only)
- Add rate limiting protection (semaphore)
- **Addresses:** Token expiry, rate limiting pitfalls
- **Risk level:** Medium — refactoring existing code

### Phase 27: TradeLocker SDK Integration
**Rationale:** SDK already works; phase focuses on production hardening.
- Add `InstrumentCache` for symbol → instrument_id mapping
- Implement SDK state recovery (reinitialize on errors)
- Add WebSocket reconnection with exponential backoff
- Improve error message pass-through
- Handle partial fills correctly
- **Addresses:** SDK state corruption, error swallowing pitfalls
- **Risk level:** Low-Medium — enhancing working code

### Phase 28: Account Selection & Routing
**Rationale:** UI changes depend on solid backend. This phase adds Test & Connect flow and environment indicators.
- Credential input forms (per-broker fields)
- Test Connection endpoint and UI flow
- Environment selector (Demo/Live) with clear badges
- Account list with status indicators
- Multi-account selection checkboxes
- Selection persistence
- **Addresses:** Demo/Live confusion pitfall
- **Risk level:** Medium — new UI features

### Phase 29: Symbol Mapping Enhancement
**Rationale:** Polish phase for symbol handling, especially futures contracts.
- Unified `SymbolMapper` class
- TradingView → Broker symbol mapping
- Futures contract rollover handling
- Cache invalidation on mapping errors
- **Addresses:** Contract ID mismatch pitfall
- **Risk level:** Low — refinement layer

### Phase Ordering Rationale

1. **Bug fixes first (25)** — Establish working baseline
2. **ProjectX before TradeLocker (26→27)** — ProjectX is simpler, validates patterns
3. **Backend before UI (26-27→28)** — Solid broker connections before UI
4. **Symbol mapping last (29)** — Polish, existing mapping works

### Research Flags for Phases

| Phase | Research Status | Notes |
|-------|-----------------|-------|
| 25 | Not needed | Simple verification |
| 26 | Complete | Use PITFALLS.md for token/rate limit handling |
| 27 | Complete | Use PITFALLS.md for SDK recovery patterns |
| 28 | Complete | Use FEATURES.md for UX patterns |
| 29 | Partial | May need runtime testing for rollover timing |

---

## Open Questions

1. **Contract rollover timing** — When exactly do ProjectX contracts roll? Need to test with demo account near expiration.

2. **WebSocket necessity** — TradeLocker WebSocket is for real-time updates. Is it needed for signal routing, or just nice-to-have?

3. **Multi-account performance** — If user has 10 accounts, do we route signals sequentially or in parallel? Parallel is faster but may hit rate limits.

4. **Error notification** — Should failed trades trigger email/webhook notifications? Not in current requirements but users may expect it.

---

## Files in This Research

| File | Purpose |
|------|---------|
| STACK.md | HTTP clients, SDKs, libraries, versions |
| FEATURES.md | Table stakes vs differentiator features, UX patterns |
| ARCHITECTURE.md | Adapter patterns, data flow, build order |
| PITFALLS.md | Common mistakes, prevention strategies, severity |
| SUMMARY.md | This file — executive summary + roadmap implications |

---
*Synthesized: 2026-01-22 for v1.2 milestone*
