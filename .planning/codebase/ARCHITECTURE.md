# Architecture

**Analysis Date:** 2026-01-19

## Pattern Overview

**Overall:** Layered Service-Oriented Architecture with Broker Abstraction Pattern

**Key Characteristics:**
- FastAPI-based REST API with WebSocket support
- Multi-broker trading system with unified abstraction layer
- Signal-driven execution model with webhook integration
- Async-first design for concurrent broker operations
- SQLAlchemy ORM with PostgreSQL for persistence
- Redis for caching and session management

## Layers

**Presentation Layer:**
- Purpose: HTTP endpoints and WebSocket connections
- Location: `app/routers/`
- Contains: FastAPI routers, request/response models, authentication middleware
- Depends on: Service layer, core utilities, database models
- Used by: External clients (UI, webhooks, API consumers)

**Service Layer:**
- Purpose: Business logic and broker orchestration
- Location: `app/services/`
- Contains: Signal processing, strategy execution, notification services, OAuth handlers
- Depends on: Broker executors, data access layer, cache layer
- Used by: Routers, background tasks

**Broker Abstraction Layer:**
- Purpose: Unified interface for multi-broker trading operations
- Location: `app/brokers/`
- Contains: Base executor class and broker-specific implementations (MT4, MT5, TradeLocker, Tradovate, ProjectX)
- Depends on: External broker APIs, core configuration
- Used by: Signal processor service

**Data Access Layer:**
- Purpose: Database operations and model definitions
- Location: `app/models/`, `app/db/`
- Contains: SQLAlchemy models, Pydantic schemas, database session management
- Depends on: SQLAlchemy, PostgreSQL
- Used by: Services, routers

**Core Layer:**
- Purpose: Cross-cutting concerns and shared utilities
- Location: `app/core/`
- Contains: Configuration, security, logging, WebSocket management, event emitter, middleware, RBAC
- Depends on: Environment variables, external services (NATS, Redis)
- Used by: All layers

**Cache Layer:**
- Purpose: Fast data access and session storage
- Location: `app/cache/`
- Contains: Redis client wrapper
- Depends on: Redis server
- Used by: Services, signal processor

**Task Layer:**
- Purpose: Background job processing
- Location: `app/tasks/`
- Contains: Celery app, trading tasks
- Depends on: Celery, Redis
- Used by: Services for async operations

## Data Flow

**Webhook Signal Flow:**

1. External webhook (TradingView/TrailHacker) → `app/webhooks/signal_router.py` → `/api/v1/webhook/signal`
2. Request validated and logged → `WebhookLog` model persisted to database
3. Payload parsed → converted to `SignalRequest` schema
4. Signal routed to `SignalProcessor` → `app/services/signal_processor.py`
5. Signal validated (broker connectivity, account, symbol, risk limits)
6. Signal persisted to database → `Signal` model with status "pending"
7. Signal converted to `OrderRequest` and routed to appropriate broker executor
8. Broker executor places order via broker-specific API
9. Order response captured → signal status updated to "executed" or "failed"
10. WebSocket notification sent to connected clients via `websocket_manager`

**Manual Trade Flow:**

1. User authentication → JWT token validation in `app/routers/auth.py`
2. REST endpoint called → `app/routers/unified_router.py` or broker-specific router
3. Request validated → `OrderRequest` schema
4. Request forwarded to broker executor directly
5. Trade executed → response returned synchronously
6. Trade logged to `Trade` model in database

**State Management:**
- Session state: JWT tokens validated per-request, sessions stored in Redis
- Broker connections: Maintained in-memory by `SignalProcessor` singleton
- Database state: PostgreSQL provides ACID transactions for all trading records
- Cache state: Redis stores temporary data with TTL (signals, sessions, quotes)

## Key Abstractions

**BaseExecutor:**
- Purpose: Abstract base class defining broker interface contract
- Examples: `app/brokers/base_executor.py`
- Pattern: Abstract base class with template methods (`connect()`, `place_order()`, `get_positions()`, etc.)

**SignalProcessor:**
- Purpose: Central orchestration point for all trading signals
- Examples: `app/services/signal_processor.py`
- Pattern: Singleton service managing broker pool and signal queue

**WebSocket Manager:**
- Purpose: Real-time bidirectional communication with clients
- Examples: `app/core/websocket_manager.py`
- Pattern: Connection manager with pub/sub capabilities

**Event Emitter:**
- Purpose: Distributed event bus for system-wide notifications
- Examples: `app/core/event_emitter.py`
- Pattern: NATS-based pub/sub with graceful fallback to logging

## Entry Points

**FastAPI Application:**
- Location: `app/main.py`
- Triggers: uvicorn server startup (`python -m uvicorn app.main:app`)
- Responsibilities: App lifecycle management, middleware registration, router inclusion, database initialization, broker connection setup

**CLI Server Launcher:**
- Location: `run_backend.py`
- Triggers: Direct Python execution (`python run_backend.py`)
- Responsibilities: Dynamic port discovery, environment setup, uvicorn subprocess management

**Celery Worker:**
- Location: `app/tasks/celery_app.py`
- Triggers: Celery worker command (`celery -A app.tasks.celery_app worker`)
- Responsibilities: Background task processing (not heavily utilized in current implementation)

**Database Migrations:**
- Location: `alembic/`
- Triggers: Alembic CLI (`alembic upgrade head`)
- Responsibilities: Schema versioning and migration execution

## Error Handling

**Strategy:** Layered exception handling with structured logging

**Patterns:**
- Router level: HTTPException raised with appropriate status codes, caught by FastAPI exception handlers
- Service level: Try-except blocks with error logging, return error dicts with `{"success": False, "error": message}`
- Broker level: Connection errors caught and logged, graceful degradation (other brokers continue working)
- Global handlers: Custom exception handlers in `app/main.py` return JSONResponse with request_id, timestamp, error details

## Cross-Cutting Concerns

**Logging:** Structured logging via `app/core/logging_config.py` with JSON format in production, console format in development

**Validation:** Pydantic schemas for all API requests/responses (`app/models/pydantic_schemas.py`), SQLAlchemy models validate database constraints

**Authentication:** JWT-based authentication with refresh tokens, API key authentication for webhooks, OAuth2 integration for third-party providers (`app/routers/auth.py`, `app/services/oauth_service.py`)

---

*Architecture analysis: 2026-01-19*
