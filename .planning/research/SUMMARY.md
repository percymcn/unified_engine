# Research Summary: Unified Trading Engine Refactor

**Project:** Trading Signal Routing Engine
**Research Date:** 2026-01-19
**Documents:** 4 research files (STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md)

## Executive Synthesis

This research establishes a solid foundation for refactoring the Unified Trading Engine from organic growth to clean hexagonal architecture. Key findings converge on these principles:

1. **Fix tests before refactoring** — 90/101 failing tests = no safety net. Phase 2 is mandatory.
2. **Domain-first, database-last** — Domain entities have zero external imports. Database adapters come after use cases.
3. **Circuit breakers are critical** — Trading systems need per-broker failure isolation (3 failures → 30s open circuit).
4. **SSE > WebSocket for trading data** — Unidirectional updates (market data, signals) use SSE for 50% lower overhead.
5. **Stay in your lane** — This is a routing dashboard, not a trading platform. Don't build charting or strategy tools.

## Stack Decisions

| Layer | Technology | Version | Rationale |
|-------|------------|---------|-----------|
| Backend Framework | FastAPI | 0.104.1+ | Keep existing, async/await for all I/O |
| Validation | Pydantic | 2.12.5 | Rust core, 2-5x faster than v1 |
| ORM | SQLAlchemy | 2.0+ | Async engine, repository pattern |
| DI Container | dependency-injector | 4.48.3 | Hexagonal architecture, non-HTTP contexts |
| Cache | redis (not aioredis) | 4.x+ | aioredis is deprecated, use `from redis import asyncio` |
| Frontend Framework | Next.js | 14 (App Router) | SSR, shadcn native, API routes for BFF |
| UI Components | shadcn/ui | Latest | Tailwind-based, dark mode ready |
| State Management | Zustand + TanStack Query | 4.x + v5 | Client state + server state separation |
| Charts | Tremor | Latest | Built on Recharts, 80% less code for dashboards |

## Architecture Structure

```
app/
├── domain/                     # Zero external imports
│   ├── entities/               # Signal, Order, Position, Account
│   ├── value_objects/          # Symbol, Price, Quantity
│   ├── services/               # RiskCalculator, SignalValidator
│   └── ports/                  # BrokerPort, SignalRepository (Protocol)
├── application/                # Use cases orchestrating domain
│   ├── use_cases/              # ProcessSignalUseCase, ExecuteOrderUseCase
│   ├── ports/                  # Port interfaces (alternate location)
│   └── dto/                    # Data transfer objects
├── infrastructure/             # All external dependencies
│   ├── adapters/
│   │   ├── inbound/            # FastAPI routers, WebSocket handlers
│   │   └── outbound/           # Broker executors, repositories, cache
│   └── di_container.py         # Dependency injection setup
└── main.py                     # Application entry point
```

**Key rules:**
- Domain imports: Only stdlib and other domain modules
- Application imports: Domain + port interfaces
- Infrastructure imports: Everything (domain, application, external libs)

## Feature Priorities

### Phase 1 MVP (Table Stakes)
- Real-time signal feed
- Per-broker execution status with errors
- Broker health monitoring
- Trade log with filtering
- Account balance per broker
- Pause/resume controls
- Alert notifications (browser)

### Phase 2+ Differentiators
- Comprehensive audit trail
- Multi-account aggregation
- Performance analytics
- Webhook replay/testing
- Pre-trade risk checks

### Anti-Features (Don't Build)
- Charting (TradingView does this)
- Strategy builder/backtesting
- Social/copy trading network
- News feeds, economic calendars
- Paper trading (use broker sandboxes)

## Critical Risks (Immediate Attention)

| Risk | Phase | Mitigation |
|------|-------|------------|
| **aioredis deprecation crash** | 1 | Replace with `from redis import asyncio as redis` |
| **Missing API keys crash service** | 1 | Graceful degradation, log ERROR but continue |
| **90% test failure rate** | 2 | BLOCKS Phase 3 — fix all tests before refactoring |
| **No kill switch** | 1 | Redis key `TRADING_DISABLED`, webhook checks first |
| **No circuit breakers** | 5 | Per-broker: 3 failures → 30s open circuit |
| **In-memory credentials** | 6 | Encrypted database storage, key from env |
| **WebSocket memory leak** | 8 | Heartbeat 30s/60s timeout, max 5 connections/user |
| **Hardcoded API keys** | 1 | Remove from source, env/secrets only |

## Migration Strategy

1. **Phase 1 (Stability):** Fix crashes ONLY. No refactoring.
2. **Phase 2 (Tests):** Get 101/101 tests passing. No refactoring.
3. **Phase 3-5 (Architecture):** One bounded context at a time:
   - Extract domain (Signal, Risk) from SignalProcessor
   - Move BaseExecutor to application/ports
   - Refactor executors one-by-one (TradeLocker → TopStep → ...)
4. **Phase 6 (Security):** Credentials to encrypted DB, encryption key from Docker secrets
5. **Phase 7-9 (UI):** Incremental Next.js migration:
   - Phase 7: Shell + auth
   - Phase 8: Dashboard only
   - Phase 9: Config pages
6. **Phase 10 (Deploy):** Docker Swarm with secrets, health checks, rollback plan

## Key Implementation Patterns

### Port Interface (Python Protocol)
```python
from typing import Protocol
from domain.entities import Signal, Order

class BrokerPort(Protocol):
    async def place_order(self, signal: Signal) -> Order: ...
    async def get_account_info(self) -> Account: ...
```

### Use Case
```python
class ProcessSignalUseCase:
    def __init__(self, signal_repo: SignalRepository, broker: BrokerPort):
        self.signal_repo = signal_repo
        self.broker = broker

    async def execute(self, signal_data: dict) -> dict:
        signal = Signal.from_dict(signal_data)
        if not signal.validate():
            return {"success": False, "error": "Invalid signal"}
        await self.signal_repo.save(signal)
        order = await self.broker.place_order(signal)
        return {"success": True, "order_id": order.id}
```

### FastAPI Dependency Injection
```python
def get_process_signal_use_case(
    repo: SignalRepository = Depends(get_signal_repository),
    broker: BrokerPort = Depends(get_broker_adapter)
) -> ProcessSignalUseCase:
    return ProcessSignalUseCase(repo, broker)
```

## Research Confidence

| Document | Confidence | Valid Until |
|----------|------------|-------------|
| STACK.md | HIGH | ~60 days (Python stable, Next.js faster-moving) |
| FEATURES.md | MEDIUM | ~60 days (validate with users) |
| ARCHITECTURE.md | HIGH | ~30 days (stable patterns) |
| PITFALLS.md | HIGH | ~30 days (stable anti-patterns) |

## Open Questions for Phase Planning

1. **Broker API capabilities:** What execution status detail do TradeLocker, TopStep, Tradovate, MT4, MT5 APIs expose?
2. **Multi-account priority:** What % of users need aggregation vs single-account? (Affects Phase 2/3 priority)
3. **WebSocket message rate:** Current production rate affects Phase 8 batching strategy
4. **Existing retry logic:** Need to audit broker executors before Phase 5 circuit breaker design

---

## Next Action

Research complete. Ready for Phase 1 planning.

**Recommended:** `/gsd:plan-phase 1`

Phase 1 success criteria:
1. Backend starts without aioredis import errors
2. Backend starts without broker initialization crashes (even with missing API keys)
3. NATS connection failure doesn't crash the service
4. No hardcoded API keys in source code

---
*Research synthesized: 2026-01-19*
