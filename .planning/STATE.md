# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-19)

**Core value:** Reliable signal-to-trade execution across all configured brokers with zero missed signals.
**Current focus:** Phase 7 - UI Foundation (in progress)

## Current Position

Phase: 7 of 10 (UI Foundation) - IN PROGRESS
Plan: 1/5 complete
Status: Plan 07-01 complete
Last activity: 2026-01-20 - Completed 07-01-PLAN.md

Progress: ████████░░ 68%

### Phase 7 Plans - IN PROGRESS
| Plan | Title | Wave | Status |
|------|-------|------|--------|
| 01 | Next.js Foundation | 1 | Complete |
| 02 | Auth Pages | 1 | Pending |
| 03 | Dashboard Layout | 2 | Pending |
| 04 | Account Management | 2 | Pending |
| 05 | Signal Display | 3 | Pending |

### Phase 6 Plans - COMPLETE
| Plan | Title | Wave | Status |
|------|-------|------|--------|
| 01 | Encryption Key Management | 1 | Complete |
| 02 | Credential Database Model | 1 | Complete |
| 03 | Credential Repository Migration | 2 | Complete |
| 04 | OAuth Token Encryption | 2 | Complete |
| 05 | API Key Bcrypt Hashing | 2 | Complete |
| 06 | Security Integration Tests | 3 | Complete |

### Phase 6 Wave Structure
- **Wave 1** (parallel): Plans 01, 02 - Foundation (encryption service + DB model)
- **Wave 2** (parallel): Plans 03, 04, 05 - Implementation (credential repo, OAuth, API keys)
- **Wave 3**: Plan 06 - Verification (integration tests)

### Phase 5 Plans - COMPLETE
| Plan | Title | Wave | Status |
|------|-------|------|--------|
| 01 | Infrastructure Package Structure | 1 | Complete |
| 02 | Entity Mappers | 1 | Complete |
| 03 | SQLAlchemy Repositories | 2 | Complete |
| 04 | Unit of Work Implementation | 2 | Complete |
| 05 | Event Publishers | 2 | Complete |
| 06 | TradeLocker Adapter | 3 | Complete |
| 07 | TopStep Adapter | 3 | Complete |
| 08 | Tradovate Adapter | 3 | Complete |
| 09 | MT4 Adapter | 3 | Complete |
| 10 | MT5 Adapter | 3 | Complete |
| 11 | DI Container | 4 | Complete |
| 12 | Infrastructure Tests | 4 | Complete |
| 13 | Fix Test Infrastructure (gap) | 5 | Complete |
| 14 | Fix Container Bug (gap) | 5 | Complete |

### Phase 4 Plans - COMPLETE
| Plan | Title | Wave | Status |
|------|-------|------|--------|
| 01 | Application Package Structure | 1 | Complete |
| 02 | Application DTOs | 1 | Complete |
| 03 | Signal Use Cases | 2 | Complete |
| 04 | Trade Use Cases | 2 | Complete |
| 05 | Account Use Cases | 3 | Complete |
| 06 | Application Services | 3 | Complete |
| 07 | Application Tests | 4 | Complete |

### Phase 3 Plans - COMPLETE
| Plan | Title | Wave | Status |
|------|-------|------|--------|
| 01 | Domain Package Structure | 1 | Complete |
| 02 | Domain Enums and Value Objects | 2 | Complete |
| 03 | Trading Domain Entities | 3 | Complete |
| 04 | Account & Position Entities | 3 | Complete |
| 05 | Port Interfaces | 4 | Complete |
| 06 | Domain Services | 5 | Complete |
| 07 | Domain Tests | 6 | Complete |

### Phase 2 Plans - COMPLETE
| Plan | Title | Wave | Status |
|------|-------|------|--------|
| 01 | Test Infrastructure Setup | 1 | Complete |
| 02 | Fix Test Collection Errors | 1 | Complete |
| 03 | Fix Test Failures | 2 | Complete |
| 04 | Add Broker Error Tests | 2 | Complete |
| 05 | Verify Test Infrastructure | 3 | Complete |

### Phase 1 Plans - COMPLETE
| Plan | Title | Wave | Status |
|------|-------|------|--------|
| 01 | Fix aioredis Deprecated Import | 1 | Complete |
| 02 | Fix Broker Executor Initialization | 1 | Complete |
| 03 | Remove Hardcoded Test API Key | 1 | Complete |
| 04 | Verify Phase 1 Stability Fixes | 2 | Complete |

## Performance Metrics

**Velocity:**
- Total plans completed: 44
- Average duration: ~6.7 min/plan
- Total execution time: ~306 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 4 | 20 min | 5 min |
| 2 | 5 | 25 min | 5 min |
| 3 | 7 | 43 min | 6.1 min |
| 4 | 7 | 33 min | 4.7 min |
| 5 | 14 | 100 min | 7.1 min |
| 6 | 6 | 48 min | 8.0 min |
| 7 | 1 | 37 min | 37 min |

**Recent Trend:**
- Last 5 plans: 6-04, 6-05, 6-06, 7-01
- Trend: Phase 7 started with UI foundation (37 min - npm install heavy)

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Full hexagonal architecture chosen over minimal cleanup
- Self-hosted JWT auth (no Supabase)
- Next.js 14 with shadcn/ui for new UI
- All 5 broker integrations must work
- Domain layer strictly isolated from FastAPI, SQLAlchemy, and all frameworks (03-01)
- Domain exceptions include context dict for rich error information (03-01)
- Three-tier exception hierarchy: DomainException -> Category -> Specific (03-01)
- All enums inherit from (str, Enum) for automatic JSON serialization (03-02)
- Money uses Decimal for precise financial calculations (03-02)
- All value objects are frozen (immutable) dataclasses (03-02)
- Symbol and Currency auto-normalize to uppercase in __post_init__ (03-02)
- Order filled_volume uses Decimal instead of Volume to support zero values (03-03)
- Account.free_margin is Decimal property (can be negative during margin calls) (03-04)
- Position.unrealized_pnl is Decimal property (can be negative for losses) (03-04)
- Money value object remains strictly non-negative for balances; calculated values use Decimal (03-04)
- BrokerPort mirrors BaseExecutor but uses domain types (Symbol, Volume, Price, OrderId) (03-05)
- Repository interfaces use domain entities as return types (Signal, Trade, Order, etc.) (03-05)
- All ports are ABC with @abstractmethod - no implementation code in domain layer (03-05)
- SignalService routes signals to connected accounts through BrokerPort interface (03-06)
- TradeService performs margin checks before placing orders through broker (03-06)
- Domain services publish events through EventPort for observability (03-06)
- All service dependencies injected through constructor (no global state) (03-06)
- Mock ports implemented as concrete classes, not unittest.Mock objects (03-07)
- Domain tests verify business rules and invariants, not just happy paths (03-07)
- In-memory repositories use Dict for predictable test state management (03-07)
- DTOs are frozen dataclasses for immutability (04-02)
- DTOs validate input in __post_init__ using ValueError (04-02)
- DTOs use domain enums but not domain entities directly (04-02)
- DTOs use primitive types (str, Decimal) not value objects (Symbol, Volume) (04-02)
- Use cases instantiate domain services directly with injected ports (04-03)
- Use cases return error DTOs instead of raising exceptions (04-03)
- Query use cases separated from command use cases (CQRS-lite) (04-03)
- DTO conversion logic contained in use cases via private methods (04-03)
- PlaceOrderUseCase validates account.is_active and is_connected before placing orders (04-04)
- ClosePositionUseCase supports partial closes via optional volume parameter (04-04)
- Read-only use cases (GetPositions, GetTrades) use repositories directly without TradeService (04-04)
- Use cases map domain exceptions to DTO error responses for graceful degradation (04-04)
- ConnectAccountUseCase retrieves broker account info and updates state in single atomic operation (04-05)
- SyncAccountUseCase counts positions and orders from broker for summary statistics (04-05)
- GetAccountsUseCase supports filtering by broker type and active status (04-05)
- UnitOfWork is abstract base class (no SQLAlchemy implementation in application layer) (04-06)
- UnitOfWork provides access to all 5 repository types (signals, trades, orders, accounts, positions) (04-06)
- UnitOfWork supports async context manager protocol for automatic cleanup (04-06)
- UnitOfWorkFactory enables use cases to obtain new UoW instances without knowing implementation (04-06)
- Infrastructure layer package structure follows hexagonal architecture principles (05-01)
- Each infrastructure subpackage reserved for specific adapter types (broker, repository, event, persistence) (05-01)
- Infrastructure layer depends on domain, never the reverse (05-01)
- Mappers handle field name differences between ORM and domain (quantity->volume, entry_price->open_price) (05-02)
- Enum mapping uses explicit dictionaries for clarity and maintainability (05-02)
- Money value objects use abs() for non-negative constraint, preserve sign in calculations (05-02)
- Status can be inferred from timestamps when ORM lacks explicit status field (05-02)
- OrderType combines ORM OrderType + OrderSide (MARKET+BUY -> BUY, LIMIT+SELL -> SELL_LIMIT) (05-02)
- SQLAlchemy repositories implement repository ports using async session (05-03)
- Repositories use mappers for bidirectional ORM<->Domain conversion (05-03)
- Repository methods raise DomainException subclasses for consistency with domain layer (05-03)
- UnitOfWork manages transaction lifecycle with async context manager (05-04)
- UnitOfWork provides unified access to all 5 repository types (05-04)
- Database session created per request/operation, not singleton (05-04)
- UnitOfWork lazy-initializes repositories to avoid unnecessary object creation (05-04)
- All repositories share same SQLAlchemy session for transactional consistency (05-04)
- SessionFactory accepts optional engine parameter for testing flexibility (05-04)
- Added async_engine to database.py alongside sync engine for backward compatibility (05-04)
- MT4Adapter stores account_id internally from authenticate() credentials (05-09)
- MT4 cmd integers (0-5) mapped to domain OrderType enum for type safety (05-09)
- Broker adapters handle both dict and Pydantic model responses from executors (05-09)
- Broker adapters raise domain exceptions for consistent error contracts (05-09)
- MT5Adapter wraps MT5Executor without duplicating API logic (05-10)
- Credentials passed via authenticate() with account_id for multi-account support (05-10)
- Domain exceptions raised for broker errors (BrokerConnectionError, InvalidOrderError, etc.) (05-10)
- Adapter pattern uses _executor instance variable and _to_domain_* conversion methods (05-10)
- TopStep uses ProjectXExecutor (TopStep accessed via ProjectX Gateway API) (05-07)
- TopstepAdapter wraps ProjectXExecutor for domain value object conversion (05-07)
- Websockets module required for ProjectX Gateway real-time updates (05-07)
- Container provides repositories directly to use cases (not UnitOfWork in constructors) (05-11)
- New session created per request via _get_repositories() helper method (05-11)
- Event publisher is CompositeEventPublisher with NATS primary, Redis fallback (05-11)
- All 5 broker adapters registered in container by BrokerType enum (05-11)
- Global container instance accessed via get_container() function (05-11)
- Container lifecycle integrated with FastAPI startup/shutdown events (05-11)
- Container shutdown uses await for adapter.is_connected() async method (05-14)
- Container shutdown wraps each disconnect in try/except for graceful degradation (05-14)
- Don't import container at module level in app/infrastructure/__init__.py to prevent model conflicts (05-13)
- Defer app.main import to fixture scope in test conftest to avoid loading routes at module level (05-13)
- Infrastructure test fixtures use mocks to isolate from full app imports (05-13)
- Fernet symmetric encryption (AES-128-CBC with HMAC) chosen for credential storage (06-01)
- EncryptionService is singleton initialized once at startup with environment key (06-01)
- Application fails fast if CREDENTIAL_ENCRYPTION_KEY missing or invalid format (06-01)
- Encryption key must be 32 bytes URL-safe base64 (standard Fernet format) (06-01)
- Convenience functions provided: encrypt(), decrypt(), encrypt_dict(), decrypt_dict() (06-01)
- Credential model uses String(36) for UUID primary keys for maximum DB compatibility (06-02)
- Encrypted_data stored as Text column containing Fernet-encrypted JSON (06-02)
- Lifecycle tracking via rotation_days and last_rotated timestamps for key rotation (06-02)
- Soft delete pattern with is_active boolean for credential lifecycle management (06-02)
- Composite index on user_id and service for efficient credential lookups (06-02)
- Async engine creation wrapped in try/except for graceful degradation without drivers (06-02)
- CredentialRepository uses centralized encryption service for all encrypt/decrypt operations (06-03)
- Repository pattern applied to credential persistence with SQLAlchemy async session (06-03)
- Dependency injection used for CredentialManager with per-request session lifecycle (06-03)
- Audit logs kept in-memory for now, credential persistence prioritized (06-03)
- AsyncSessionLocal factory with expire_on_commit=False for proper async session management (06-03)
- Bcrypt hashing for API keys instead of SHA256 (rainbow table protection) (06-05)
- Iterate active keys for bcrypt verification (can't do direct hash lookup) (06-05)
- Breaking change: existing SHA256 hashes won't verify (documented migration path) (06-05)
- OAuth tokens encrypted at service layer before database storage (06-04)
- Static helper methods (_encrypt_token, _decrypt_token) for consistent token encryption (06-04)
- get_decrypted_tokens() returns tuple for future authenticated API calls (06-04)
- Empty/None OAuth tokens handled gracefully without encryption (06-04)
- All SQLAlchemy models use extend_existing=True for test isolation (06-06)
- Security tests organized by requirement (SEC-XX) for clear traceability (06-06)
- 14 integration tests verify encryption, persistence, OAuth, and bcrypt requirements (06-06)
- Next.js 14.2.35 (not 15) for stability (07-01)
- shadcn/ui new-york style with slate base color (07-01)
- Dark theme in :root (default), light in .light class (07-01)
- Cyan/teal primary accent (hsl 160 84% 39%) (07-01)
- className='dark' on html element for explicit dark mode (07-01)

### Pending Todos

None yet.

### Blockers/Concerns

From CONCERNS.md codebase audit:
- ~~aioredis deprecated (causes crash) - Phase 1~~ FIXED
- ~~Hardcoded encryption key - Phase 6 (Plan 01)~~ FIXED
- ~~90/101 tests failing - Phase 2~~ FIXED (173 tests now collected)
- ~~In-memory credential storage - Phase 6 (Plan 02)~~ FIXED (database model + migration created)
- ~~credential_router.py uses in-memory dict and runtime Fernet.generate_key() - Phase 6 (Plan 03)~~ FIXED (database repository with env key)
- Alembic has multiple heads (001 and 002) - may need merging in future
- asyncpg not installed (gracefully degraded, async operations won't work)
- npm audit shows 3 high severity vulnerabilities in ui-next (eslint-related, dev-only)

## Session Continuity

Last session: 2026-01-20
Stopped at: Completed 07-01-PLAN.md
Resume file: None
Next: Execute plan 07-02 (Auth Pages)
