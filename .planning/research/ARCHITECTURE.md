# Architecture Research: Hexagonal Architecture for Trading Signal Routing System

**Researched:** 2026-01-19
**Domain:** Python/FastAPI trading signal routing and broker execution
**Overall Confidence:** HIGH

## Question

How should a hexagonal architecture be structured for a trading signal routing system in Python/FastAPI? Specifically:
1. What are the domain, application, and infrastructure layers?
2. How do ports and adapters work in Python/FastAPI?
3. What's the recommended directory structure?
4. How to handle dependency injection?

## Executive Summary

Hexagonal architecture (also known as Ports and Adapters) separates business logic from external dependencies through abstract interfaces. For a trading signal routing system, this means:

- **Domain layer** contains pure business logic (signal validation rules, risk calculations, trading strategies) with zero external dependencies
- **Application layer** orchestrates workflows (signal processing pipeline, order execution flow) without implementing how
- **Infrastructure layer** contains all adapters (broker executors, database repos, FastAPI endpoints, Redis cache)
- **Ports** are Python Protocols or ABCs defining contracts between layers
- **Dependency injection** via FastAPI's `Depends()` system or dedicated containers like `dependency-injector`

**Key insight for trading systems:** Your existing `BaseExecutor` ABC is already a port pattern - it just needs to be moved to the domain layer and have implementations treated as adapters.

**Migration strategy:** Start with domain extraction (signal validation, risk rules), then invert broker dependencies, finally migrate endpoints. Build order: Domain → Ports → Application → Adapters.

## Findings

### 1. Hexagonal Architecture Layers

#### Domain Layer

**Contents:**
- **Entities:** Core business objects (Signal, Order, Position, Account, RiskProfile)
- **Value Objects:** Immutable concepts (Price, Quantity, Symbol, OrderType)
- **Domain Services:** Pure business logic (RiskCalculator, PositionSizer, SignalValidator)
- **Domain Events:** Business state changes (SignalReceived, OrderExecuted, RiskLimitExceeded)
- **Ports (Interfaces):** Abstract contracts for external interactions

**Rules:**
- **ZERO external imports** - No SQLAlchemy, no FastAPI, no Redis, no HTTP libraries
- **No infrastructure concerns** - No database queries, no API calls, no file I/O
- Depends only on standard library and other domain modules
- Contains all "how to do" logic - the money-making business rules

**Example Structure:**
```python
# domain/entities/signal.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from domain.value_objects import Symbol, Price, Quantity, OrderAction

@dataclass
class Signal:
    """Core signal entity - pure domain model"""
    id: str
    symbol: Symbol
    action: OrderAction
    quantity: Quantity
    price: Optional[Price]
    stop_loss: Optional[Price]
    take_profit: Optional[Price]
    source: str
    created_at: datetime

    def validate(self) -> bool:
        """Domain validation logic"""
        if self.quantity.value <= 0:
            return False
        if self.stop_loss and self.stop_loss.value >= self.price.value:
            return False
        return True

# domain/services/risk_calculator.py
class RiskCalculator:
    """Pure business logic - no external dependencies"""

    def calculate_position_risk(
        self,
        entry_price: Price,
        stop_loss: Price,
        quantity: Quantity,
        account_balance: float
    ) -> float:
        """Calculate risk as percentage of account"""
        risk_amount = abs(entry_price.value - stop_loss.value) * quantity.value
        return (risk_amount / account_balance) * 100

    def is_within_risk_limits(
        self,
        risk_percentage: float,
        max_risk_per_trade: float
    ) -> bool:
        """Pure business rule - no dependencies"""
        return risk_percentage <= max_risk_per_trade
```

**For your trading system:**
- Signal validation rules (stop loss logic, position size validation)
- Risk management calculations (max position size, daily loss limits)
- Trading strategy logic (signal interpretation, order type mapping)
- Position management rules (modify, close, partial close logic)

#### Application Layer (Use Cases)

**Contents:**
- **Use Case Classes:** One class per business operation (ProcessSignal, ExecuteOrder, ValidateAccount)
- **Application Services:** Orchestrate multiple use cases (SignalRouter)
- **DTOs (Data Transfer Objects):** Simplified data structures for inter-layer communication
- **Port Interfaces:** Define what infrastructure capabilities are needed

**Rules:**
- Knows "what to do" but not "how to do it"
- Depends on domain layer (uses entities, calls domain services)
- Depends on port interfaces (not concrete implementations)
- Coordinates workflow but delegates business logic to domain
- No direct infrastructure imports (imports ports, not adapters)

**Example Structure:**
```python
# application/use_cases/process_signal.py
from typing import Protocol
from domain.entities import Signal
from domain.services import RiskCalculator
from application.ports.outbound import SignalRepository, BrokerPort

class ProcessSignalUseCase:
    """Application service - orchestrates workflow"""

    def __init__(
        self,
        signal_repo: SignalRepository,  # Port interface
        broker: BrokerPort,              # Port interface
        risk_calculator: RiskCalculator  # Domain service
    ):
        self.signal_repo = signal_repo
        self.broker = broker
        self.risk_calculator = risk_calculator

    async def execute(self, signal_data: dict) -> dict:
        """Orchestrate signal processing workflow"""
        # 1. Create domain entity
        signal = Signal.from_dict(signal_data)

        # 2. Validate using domain logic
        if not signal.validate():
            return {"success": False, "error": "Invalid signal"}

        # 3. Persist using port
        await self.signal_repo.save(signal)

        # 4. Check risk using domain service
        account = await self.broker.get_account_info()
        risk = self.risk_calculator.calculate_position_risk(
            signal.price, signal.stop_loss, signal.quantity, account.balance
        )

        if not self.risk_calculator.is_within_risk_limits(risk, 2.0):
            return {"success": False, "error": "Risk limits exceeded"}

        # 5. Execute via broker port
        result = await self.broker.place_order(signal)

        # 6. Update status
        signal.mark_executed(result.order_id)
        await self.signal_repo.update(signal)

        return {"success": True, "order_id": result.order_id}
```

**For your trading system:**
- ProcessSignal use case (validation → risk check → execution → logging)
- ProcessWebhook use case (parse → validate → route to ProcessSignal)
- ManagePosition use case (modify SL/TP, close position)
- ValidateBrokerConnection use case

#### Infrastructure Layer (Adapters)

**Contents:**
- **Inbound Adapters (Driving):** FastAPI routers, webhook handlers, CLI commands
- **Outbound Adapters (Driven):** Database repositories, broker executors, cache clients, external APIs
- **Configuration:** Settings, environment variables, DI container setup
- **Framework Code:** FastAPI app setup, middleware, exception handlers

**Rules:**
- Implements port interfaces defined in application/domain
- Contains all external dependencies (SQLAlchemy, httpx, Redis)
- Translates between external formats and domain models
- Never imported by domain or application layers

**Example Structure:**
```python
# infrastructure/adapters/outbound/mt4_broker_adapter.py
import httpx
from application.ports.outbound import BrokerPort
from domain.entities import Signal, Order
from domain.value_objects import OrderResult

class MT4BrokerAdapter(BrokerPort):
    """Adapter implementing broker port for MT4"""

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = httpx.AsyncClient()

    async def place_order(self, signal: Signal) -> OrderResult:
        """Translate domain model to MT4 API call"""
        mt4_payload = {
            "symbol": signal.symbol.value,
            "cmd": 0 if signal.action.is_buy else 1,
            "volume": signal.quantity.value,
            "price": signal.price.value if signal.price else 0,
            "sl": signal.stop_loss.value if signal.stop_loss else 0,
            "tp": signal.take_profit.value if signal.take_profit else 0,
        }

        response = await self.client.post(
            f"{self.base_url}/order",
            json=mt4_payload,
            headers=self._auth_headers()
        )

        # Translate external response to domain model
        return OrderResult(
            order_id=response.json()["ticket"],
            status="executed" if response.json()["success"] else "failed"
        )

    async def get_account_info(self) -> Account:
        """Fetch account data and convert to domain entity"""
        response = await self.client.get(...)
        return Account.from_api_response(response.json())

# infrastructure/adapters/outbound/sqlalchemy_signal_repository.py
from sqlalchemy.orm import Session
from application.ports.outbound import SignalRepository
from domain.entities import Signal
from infrastructure.persistence.models import SignalModel

class SQLAlchemySignalRepository(SignalRepository):
    """Database adapter implementing repository port"""

    def __init__(self, session: Session):
        self.session = session

    async def save(self, signal: Signal) -> None:
        """Translate domain entity to database model"""
        db_signal = SignalModel(
            id=signal.id,
            symbol=signal.symbol.value,
            action=signal.action.value,
            quantity=signal.quantity.value,
            # ... map all fields
        )
        self.session.add(db_signal)
        await self.session.commit()

    async def find_by_id(self, signal_id: str) -> Signal:
        """Load from DB and convert to domain entity"""
        db_signal = self.session.query(SignalModel).filter_by(id=signal_id).first()
        return Signal.from_db_model(db_signal)

# infrastructure/adapters/inbound/fastapi_signal_router.py
from fastapi import APIRouter, Depends
from application.use_cases import ProcessSignalUseCase
from infrastructure.di_container import get_process_signal_use_case

router = APIRouter()

@router.post("/signals")
async def receive_signal(
    payload: dict,
    use_case: ProcessSignalUseCase = Depends(get_process_signal_use_case)
):
    """Inbound adapter - translates HTTP to application layer"""
    result = await use_case.execute(payload)
    return {"success": result["success"], "order_id": result.get("order_id")}
```

**For your trading system:**
- FastAPI routers (signals, webhooks, trades, accounts) - inbound adapters
- BaseExecutor implementations (MT4Executor, MT5Executor, etc.) - outbound adapters
- SQLAlchemy repositories (SignalRepository, AccountRepository) - outbound adapters
- Redis cache adapter - outbound adapter
- WebSocket connection manager - outbound adapter

### 2. Ports and Adapters Pattern

#### Port Types

**Driving Ports (Input Ports / Primary Ports):**
- Entry points to application
- Expose application features to outside world
- Examples: REST API interface, CLI interface, webhook receiver
- In your system: Signal ingestion, trade execution requests, account queries

**Driven Ports (Output Ports / Secondary Ports):**
- Used by application to interact with external systems
- Abstract persistence, external APIs, third-party services
- Examples: Database interface, broker API interface, notification service
- In your system: Broker execution, database persistence, cache access

#### Python Implementation Patterns

**Option 1: Protocol (Structural Typing - Recommended for Python)**

```python
# application/ports/outbound/broker_port.py
from typing import Protocol, List
from domain.entities import Signal, Order, Position, Account

class BrokerPort(Protocol):
    """Port for broker interactions using structural typing"""

    async def connect(self) -> bool:
        """Establish connection to broker"""
        ...

    async def place_order(self, signal: Signal) -> Order:
        """Execute trading signal"""
        ...

    async def get_positions(self) -> List[Position]:
        """Retrieve current positions"""
        ...

    async def get_account_info(self) -> Account:
        """Get account details"""
        ...
```

**Benefits:**
- Duck typing - no explicit inheritance needed
- Retrofitting - existing classes can satisfy protocol without modification
- Better alignment with Python's dynamic nature
- Type checker support (mypy, pyright)

**Option 2: Abstract Base Class (Nominal Typing - Your Current Approach)**

```python
# application/ports/outbound/broker_port.py
from abc import ABC, abstractmethod
from typing import List
from domain.entities import Signal, Order, Position, Account

class BrokerPort(ABC):
    """Port for broker interactions using ABC"""

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to broker"""
        pass

    @abstractmethod
    async def place_order(self, signal: Signal) -> Order:
        """Execute trading signal"""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Retrieve current positions"""
        pass

    @abstractmethod
    async def get_account_info(self) -> Account:
        """Get account details"""
        pass
```

**Benefits:**
- Runtime enforcement - Python raises TypeError if abstract methods not implemented
- Explicit contract - clear inheritance hierarchy
- Familiar to developers from statically-typed languages

**Recommendation for Trading System:**
Use **Protocol** for port definitions (modern Python 3.8+) but keep ABC for your existing BaseExecutor temporarily during migration to avoid breaking changes. Migrate to Protocol after adapters are separated.

#### FastAPI-Specific Considerations

**Dependency Injection Integration:**

```python
# infrastructure/dependencies.py
from fastapi import Depends
from sqlalchemy.orm import Session
from application.use_cases import ProcessSignalUseCase
from application.ports.outbound import BrokerPort, SignalRepository
from infrastructure.adapters.outbound import MT4BrokerAdapter, SQLAlchemySignalRepository
from infrastructure.database import get_db

def get_signal_repository(db: Session = Depends(get_db)) -> SignalRepository:
    """Dependency provider for signal repository"""
    return SQLAlchemySignalRepository(db)

def get_broker_adapter() -> BrokerPort:
    """Dependency provider for broker"""
    # Could select broker based on configuration
    return MT4BrokerAdapter(api_key="...", api_secret="...")

def get_process_signal_use_case(
    signal_repo: SignalRepository = Depends(get_signal_repository),
    broker: BrokerPort = Depends(get_broker_adapter)
) -> ProcessSignalUseCase:
    """Compose use case with dependencies"""
    from domain.services import RiskCalculator
    return ProcessSignalUseCase(signal_repo, broker, RiskCalculator())

# In router:
@router.post("/signals")
async def receive_signal(
    payload: dict,
    use_case: ProcessSignalUseCase = Depends(get_process_signal_use_case)
):
    result = await use_case.execute(payload)
    return result
```

**Testing Benefits:**

```python
# tests/test_signal_processing.py
import pytest
from unittest.mock import AsyncMock
from application.use_cases import ProcessSignalUseCase

@pytest.fixture
def mock_broker():
    """Mock broker port for testing"""
    broker = AsyncMock()
    broker.place_order.return_value = Order(order_id="123", status="executed")
    return broker

async def test_signal_processing(mock_broker, mock_signal_repo):
    """Test use case with mocked dependencies"""
    use_case = ProcessSignalUseCase(mock_signal_repo, mock_broker, RiskCalculator())

    result = await use_case.execute({
        "symbol": "EURUSD",
        "action": "buy",
        "quantity": 0.1
    })

    assert result["success"] is True
    mock_broker.place_order.assert_called_once()
```

### 3. Directory Structure

#### Recommended Structure for Trading System

```
app/
├── domain/                          # Core business logic - NO external dependencies
│   ├── __init__.py
│   ├── entities/                    # Rich domain models
│   │   ├── __init__.py
│   │   ├── signal.py               # Signal entity
│   │   ├── order.py                # Order entity
│   │   ├── position.py             # Position entity
│   │   └── account.py              # Account entity
│   ├── value_objects/               # Immutable value types
│   │   ├── __init__.py
│   │   ├── symbol.py               # Symbol value object
│   │   ├── price.py                # Price value object
│   │   ├── quantity.py             # Quantity value object
│   │   └── order_type.py           # OrderType enum
│   ├── services/                    # Domain services (pure logic)
│   │   ├── __init__.py
│   │   ├── risk_calculator.py      # Risk calculation logic
│   │   ├── position_sizer.py       # Position sizing logic
│   │   └── signal_validator.py     # Signal validation rules
│   ├── events/                      # Domain events
│   │   ├── __init__.py
│   │   ├── signal_received.py
│   │   ├── order_executed.py
│   │   └── risk_limit_exceeded.py
│   └── exceptions/                  # Domain exceptions
│       ├── __init__.py
│       ├── invalid_signal.py
│       └── risk_limit_error.py
│
├── application/                     # Use cases and orchestration
│   ├── __init__.py
│   ├── use_cases/                   # Application services
│   │   ├── __init__.py
│   │   ├── process_signal.py       # ProcessSignalUseCase
│   │   ├── process_webhook.py      # ProcessWebhookUseCase
│   │   ├── execute_order.py        # ExecuteOrderUseCase
│   │   └── manage_position.py      # ManagePositionUseCase
│   ├── ports/                       # Port interfaces
│   │   ├── __init__.py
│   │   ├── inbound/                 # Driving ports (inputs)
│   │   │   ├── __init__.py
│   │   │   └── signal_service.py   # Interface for signal ingestion
│   │   └── outbound/                # Driven ports (outputs)
│   │       ├── __init__.py
│   │       ├── broker_port.py      # Broker execution interface
│   │       ├── signal_repository.py # Signal persistence interface
│   │       ├── account_repository.py
│   │       ├── cache_port.py       # Cache interface
│   │       └── notification_port.py # Notification interface
│   └── dto/                         # Data transfer objects
│       ├── __init__.py
│       ├── signal_dto.py
│       └── order_dto.py
│
├── infrastructure/                  # External adapters and frameworks
│   ├── __init__.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── inbound/                 # Driving adapters (entry points)
│   │   │   ├── __init__.py
│   │   │   ├── fastapi_routers/    # HTTP API adapters
│   │   │   │   ├── __init__.py
│   │   │   │   ├── signal_router.py
│   │   │   │   ├── webhook_router.py
│   │   │   │   ├── trade_router.py
│   │   │   │   └── account_router.py
│   │   │   └── websocket/           # WebSocket adapter
│   │   │       └── connection_manager.py
│   │   └── outbound/                # Driven adapters (implementations)
│   │       ├── __init__.py
│   │       ├── brokers/             # Broker execution adapters
│   │       │   ├── __init__.py
│   │       │   ├── mt4_adapter.py
│   │       │   ├── mt5_adapter.py
│   │       │   ├── tradelocker_adapter.py
│   │       │   ├── tradovate_adapter.py
│   │       │   └── projectx_adapter.py
│   │       ├── persistence/         # Database adapters
│   │       │   ├── __init__.py
│   │       │   ├── models/          # SQLAlchemy models
│   │       │   │   ├── __init__.py
│   │       │   │   ├── signal_model.py
│   │       │   │   ├── account_model.py
│   │       │   │   └── trade_model.py
│   │       │   ├── repositories/    # Repository implementations
│   │       │   │   ├── __init__.py
│   │       │   │   ├── signal_repository_impl.py
│   │       │   │   └── account_repository_impl.py
│   │       │   └── database.py      # DB connection
│   │       ├── cache/               # Cache adapters
│   │       │   ├── __init__.py
│   │       │   └── redis_adapter.py
│   │       └── notifications/       # Notification adapters
│   │           └── email_adapter.py
│   ├── config/                      # Configuration
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── logging.py
│   └── di_container.py              # Dependency injection container
│
├── main.py                          # FastAPI application entry point
└── bootstrap.py                     # Application bootstrapping

tests/
├── unit/
│   ├── domain/                      # Domain logic tests (pure, no mocks)
│   ├── application/                 # Use case tests (mocked ports)
│   └── infrastructure/              # Adapter tests (may use test doubles)
├── integration/                     # Integration tests
└── e2e/                            # End-to-end tests
```

#### Key Directory Principles

1. **Dependency Direction:** Always flows inward (infrastructure → application → domain)
2. **Import Rules:**
   - Domain imports: Only standard library and other domain modules
   - Application imports: Domain + port interfaces
   - Infrastructure imports: Everything (domain, application, external libs)
3. **Test Organization:** Mirrors source structure
4. **Flat When Possible:** Avoid over-nesting within layers

### 4. Dependency Injection

#### Option 1: FastAPI Native Depends (Recommended for Start)

**Pros:**
- Built into FastAPI
- Simple for HTTP endpoints
- Good for small to medium projects
- Type-safe with IDE support

**Cons:**
- Tied to request lifecycle
- Harder to use outside FastAPI context (CLI, background tasks)
- Manual wiring for complex graphs

**Implementation:**

```python
# infrastructure/dependencies.py
from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from application.use_cases import ProcessSignalUseCase
from application.ports.outbound import BrokerPort, SignalRepository
from infrastructure.adapters.outbound.brokers import MT4Adapter
from infrastructure.adapters.outbound.persistence import SignalRepositoryImpl
from infrastructure.persistence.database import SessionLocal

def get_db() -> Generator[Session, None, None]:
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_signal_repository(
    db: Session = Depends(get_db)
) -> SignalRepository:
    return SignalRepositoryImpl(db)

def get_broker(broker_type: str = "mt4") -> BrokerPort:
    """Factory for broker adapters"""
    if broker_type == "mt4":
        return MT4Adapter()
    elif broker_type == "mt5":
        return MT5Adapter()
    # ... etc

def get_process_signal_use_case(
    repo: SignalRepository = Depends(get_signal_repository),
    broker: BrokerPort = Depends(get_broker)
) -> ProcessSignalUseCase:
    return ProcessSignalUseCase(repo, broker)

# In router:
@router.post("/signals")
async def process_signal(
    signal_data: dict,
    use_case: ProcessSignalUseCase = Depends(get_process_signal_use_case)
):
    return await use_case.execute(signal_data)
```

**Testing Override:**

```python
# tests/conftest.py
from fastapi.testclient import TestClient
from app.main import app
from tests.mocks import MockBrokerAdapter

def get_mock_broker():
    return MockBrokerAdapter()

app.dependency_overrides[get_broker] = get_mock_broker

client = TestClient(app)
```

#### Option 2: dependency-injector Library (Recommended for Complex Systems)

**Pros:**
- Framework-agnostic
- Powerful configuration (singleton, factory, etc.)
- Easy to use in non-HTTP contexts
- Reduces boilerplate by 25% (2025 fintech case study)

**Cons:**
- Additional dependency
- Learning curve
- More setup code

**Implementation:**

```python
# infrastructure/di_container.py
from dependency_injector import containers, providers
from infrastructure.adapters.outbound.brokers import MT4Adapter, MT5Adapter
from infrastructure.adapters.outbound.persistence import SignalRepositoryImpl
from infrastructure.persistence.database import Database
from application.use_cases import ProcessSignalUseCase

class Container(containers.DeclarativeContainer):
    """DI container configuration"""

    config = providers.Configuration()

    # Database
    database = providers.Singleton(
        Database,
        db_url=config.database.url
    )

    # Repositories
    signal_repository = providers.Factory(
        SignalRepositoryImpl,
        session_factory=database.provided.session
    )

    # Brokers
    mt4_broker = providers.Factory(
        MT4Adapter,
        api_key=config.brokers.mt4.api_key,
        api_secret=config.brokers.mt4.api_secret
    )

    mt5_broker = providers.Factory(
        MT5Adapter,
        api_key=config.brokers.mt5.api_key
    )

    # Use Cases
    process_signal_use_case = providers.Factory(
        ProcessSignalUseCase,
        signal_repository=signal_repository,
        broker=mt4_broker  # Or use factory to select
    )

# main.py
from infrastructure.di_container import Container

container = Container()
container.config.from_yaml("config.yml")

# FastAPI integration
from fastapi import FastAPI, Depends
from dependency_injector.wiring import inject, Provide

app = FastAPI()

@app.post("/signals")
@inject
async def process_signal(
    signal_data: dict,
    use_case: ProcessSignalUseCase = Depends(Provide[Container.process_signal_use_case])
):
    return await use_case.execute(signal_data)

# Wire container to modules
container.wire(modules=[__name__])
```

**Non-HTTP Usage:**

```python
# cli.py
from infrastructure.di_container import Container

def main():
    container = Container()
    container.config.from_yaml("config.yml")

    # Can use outside FastAPI context
    use_case = container.process_signal_use_case()
    result = asyncio.run(use_case.execute({...}))
```

#### Option 3: Manual Factory Pattern (Simplest)

**Pros:**
- No magic
- Explicit and readable
- Zero dependencies

**Cons:**
- More boilerplate
- Manual management

**Implementation:**

```python
# infrastructure/factories.py
from typing import Dict
from application.ports.outbound import BrokerPort
from infrastructure.adapters.outbound.brokers import (
    MT4Adapter, MT5Adapter, TradeLockerAdapter
)

class BrokerFactory:
    """Factory for creating broker adapters"""

    @staticmethod
    def create(broker_type: str, config: Dict) -> BrokerPort:
        if broker_type == "mt4":
            return MT4Adapter(
                api_key=config["api_key"],
                api_secret=config["api_secret"]
            )
        elif broker_type == "mt5":
            return MT5Adapter(api_key=config["api_key"])
        # ... etc
        else:
            raise ValueError(f"Unknown broker: {broker_type}")

# bootstrap.py
from infrastructure.factories import BrokerFactory
from infrastructure.adapters.outbound.persistence import SignalRepositoryImpl
from application.use_cases import ProcessSignalUseCase

class ApplicationServices:
    """Container for application services"""

    def __init__(self, config: dict):
        self.db_session = create_db_session(config["database_url"])
        self.signal_repo = SignalRepositoryImpl(self.db_session)
        self.broker = BrokerFactory.create(
            config["broker_type"],
            config["broker_config"]
        )
        self.process_signal_use_case = ProcessSignalUseCase(
            self.signal_repo,
            self.broker
        )

# main.py
services = ApplicationServices(config)

@app.post("/signals")
async def process_signal(signal_data: dict):
    return await services.process_signal_use_case.execute(signal_data)
```

#### Recommendation for Your Trading System

**Phase 1 (Initial Migration):** Use **FastAPI Depends** - minimal changes, leverages existing patterns
**Phase 2 (Stabilization):** Introduce **dependency-injector** - better separation, easier testing, supports background tasks
**Phase 3 (Optimization):** Keep dependency-injector but optimize container configuration

### 5. Migration Strategy: Layered to Hexagonal

#### Current State Analysis

Your system already has good separation:
- **Routers** → Will become inbound adapters
- **Services** (SignalProcessor) → Will split into domain services + use cases
- **Brokers** (BaseExecutor implementations) → Already adapters! Just need to move interface to domain
- **Models** → Will split into domain entities + database models

#### Migration Steps (Incremental, Non-Breaking)

**Step 1: Extract Domain Layer (Week 1)**

Create pure domain models without external dependencies:

```python
# domain/entities/signal.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Signal:
    """Pure domain model - no SQLAlchemy, no Pydantic"""
    symbol: str
    action: str
    quantity: float
    price: float | None
    stop_loss: float | None
    take_profit: float | None

    def validate(self) -> tuple[bool, str]:
        """Pure business logic"""
        if self.quantity <= 0:
            return False, "Quantity must be positive"
        if self.action not in ["buy", "sell"]:
            return False, "Invalid action"
        return True, ""

# domain/services/risk_calculator.py
class RiskCalculator:
    """Pure business logic - extracted from SignalProcessor"""

    def calculate_risk_percentage(
        self,
        entry: float,
        stop_loss: float,
        quantity: float,
        account_balance: float
    ) -> float:
        risk_amount = abs(entry - stop_loss) * quantity
        return (risk_amount / account_balance) * 100

    def is_within_limits(self, risk_pct: float, max_risk: float) -> bool:
        return risk_pct <= max_risk
```

**What to move from `signal_processor.py`:**
- Extract `_check_risk_limits` logic → `domain/services/risk_calculator.py`
- Extract `_validate_signal` business rules → `domain/services/signal_validator.py`
- Extract `_map_action_to_order_type` → `domain/value_objects/order_type.py`

**Step 2: Define Ports (Week 1-2)**

Move `BaseExecutor` to become a port interface:

```python
# application/ports/outbound/broker_port.py (formerly app/brokers/base_executor.py)
from typing import Protocol
from domain.entities import Signal, Order, Position, Account

class BrokerPort(Protocol):
    """Port interface for broker execution"""

    async def connect(self) -> bool: ...
    async def place_order(self, signal: Signal) -> Order: ...
    async def get_positions(self) -> list[Position]: ...
    async def get_account_info(self) -> Account: ...
    async def modify_position(self, position_id: str, stop_loss: float, take_profit: float) -> dict: ...

# application/ports/outbound/signal_repository.py (NEW)
from typing import Protocol
from domain.entities import Signal

class SignalRepository(Protocol):
    """Port for signal persistence"""

    async def save(self, signal: Signal) -> str: ...
    async def find_by_id(self, signal_id: str) -> Signal | None: ...
    async def update_status(self, signal_id: str, status: str) -> None: ...
```

**Step 3: Create Adapters (Week 2)**

Refactor existing executors to implement ports:

```python
# infrastructure/adapters/outbound/brokers/mt4_adapter.py (formerly app/brokers/mt4_executor.py)
from application.ports.outbound import BrokerPort
from domain.entities import Signal, Order

class MT4Adapter(BrokerPort):  # Implements port
    """Adapter for MT4 broker - wraps existing MT4Executor logic"""

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret

    async def place_order(self, signal: Signal) -> Order:
        """Convert domain Signal to MT4 API call"""
        # Existing logic from MT4Executor
        # But now receives domain entity, returns domain entity
        mt4_response = await self._call_mt4_api(signal)
        return Order.from_mt4_response(mt4_response)
```

Create repository adapters:

```python
# infrastructure/adapters/outbound/persistence/signal_repository_impl.py
from sqlalchemy.orm import Session
from application.ports.outbound import SignalRepository
from domain.entities import Signal
from infrastructure.persistence.models import SignalModel

class SignalRepositoryImpl(SignalRepository):
    """SQLAlchemy implementation of signal repository"""

    def __init__(self, session: Session):
        self.session = session

    async def save(self, signal: Signal) -> str:
        """Translate domain entity to database model"""
        db_signal = SignalModel.from_domain(signal)
        self.session.add(db_signal)
        await self.session.commit()
        return str(db_signal.id)

    async def find_by_id(self, signal_id: str) -> Signal | None:
        db_signal = self.session.query(SignalModel).filter_by(id=signal_id).first()
        return Signal.from_db_model(db_signal) if db_signal else None
```

**Step 4: Create Use Cases (Week 2-3)**

Extract orchestration logic from `SignalProcessor`:

```python
# application/use_cases/process_signal.py
from application.ports.outbound import BrokerPort, SignalRepository
from domain.services import RiskCalculator, SignalValidator

class ProcessSignalUseCase:
    """Extracted from SignalProcessor.process_signal()"""

    def __init__(
        self,
        signal_repo: SignalRepository,
        broker: BrokerPort,
        risk_calculator: RiskCalculator,
        validator: SignalValidator
    ):
        self.signal_repo = signal_repo
        self.broker = broker
        self.risk_calculator = risk_calculator
        self.validator = validator

    async def execute(self, signal_data: dict) -> dict:
        """Orchestrate signal processing workflow"""
        # 1. Create domain entity
        signal = Signal.from_dict(signal_data)

        # 2. Validate (domain logic)
        is_valid, error = self.validator.validate(signal)
        if not is_valid:
            return {"success": False, "error": error}

        # 3. Persist via repository port
        signal_id = await self.signal_repo.save(signal)

        # 4. Check risk (domain logic)
        account = await self.broker.get_account_info()
        risk = self.risk_calculator.calculate_risk_percentage(
            signal.price, signal.stop_loss, signal.quantity, account.balance
        )

        if not self.risk_calculator.is_within_limits(risk, 2.0):
            await self.signal_repo.update_status(signal_id, "rejected")
            return {"success": False, "error": "Risk limits exceeded"}

        # 5. Execute via broker port
        order = await self.broker.place_order(signal)

        # 6. Update status
        await self.signal_repo.update_status(signal_id, "executed")

        return {"success": True, "signal_id": signal_id, "order_id": order.id}
```

**Step 5: Refactor Routers (Week 3)**

Convert routers to inbound adapters:

```python
# infrastructure/adapters/inbound/fastapi_routers/signal_router.py (formerly app/routers/webhooks.py)
from fastapi import APIRouter, Depends
from application.use_cases import ProcessSignalUseCase
from infrastructure.dependencies import get_process_signal_use_case

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])

@router.post("/")
async def receive_signal(
    payload: dict,
    use_case: ProcessSignalUseCase = Depends(get_process_signal_use_case)
):
    """Inbound adapter - delegates to use case"""
    result = await use_case.execute(payload)

    # Translate use case result to HTTP response
    if result["success"]:
        return {
            "status": "success",
            "signal_id": result["signal_id"],
            "order_id": result["order_id"]
        }
    else:
        return {
            "status": "error",
            "message": result["error"]
        }
```

**Step 6: Setup DI Container (Week 3)**

```python
# infrastructure/dependencies.py
from fastapi import Depends
from sqlalchemy.orm import Session
from application.use_cases import ProcessSignalUseCase
from application.ports.outbound import BrokerPort, SignalRepository
from infrastructure.adapters.outbound.brokers import MT4Adapter
from infrastructure.adapters.outbound.persistence import SignalRepositoryImpl
from infrastructure.persistence.database import get_db

def get_signal_repository(db: Session = Depends(get_db)) -> SignalRepository:
    return SignalRepositoryImpl(db)

def get_broker(broker_type: str = "mt4") -> BrokerPort:
    # Could load from config or user settings
    return MT4Adapter(api_key="...", api_secret="...")

def get_process_signal_use_case(
    repo: SignalRepository = Depends(get_signal_repository),
    broker: BrokerPort = Depends(get_broker)
) -> ProcessSignalUseCase:
    from domain.services import RiskCalculator, SignalValidator
    return ProcessSignalUseCase(repo, broker, RiskCalculator(), SignalValidator())
```

**Step 7: Update Main App (Week 4)**

```python
# main.py
from fastapi import FastAPI
from infrastructure.adapters.inbound.fastapi_routers import (
    signal_router,
    webhook_router,
    trade_router
)

app = FastAPI(title="Unified Trading Engine")

# Include inbound adapters
app.include_router(signal_router.router)
app.include_router(webhook_router.router)
app.include_router(trade_router.router)

# Lifespan for initializing connections
@app.on_event("startup")
async def startup():
    # Initialize broker connections
    pass

@app.on_event("shutdown")
async def shutdown():
    # Cleanup connections
    pass
```

#### Hybrid Phase Management

During migration, you'll have both old and new code:

```python
# Keep old signal_processor.py temporarily
# Gradually route new features through use cases
# Old endpoints can still use SignalProcessor
# New endpoints use ProcessSignalUseCase

# After all endpoints migrated, deprecate SignalProcessor
```

**Decision Log:**
Document why certain code is hexagonal while other isn't:
```markdown
# Architecture Decision Record: Partial Hexagonal Migration

## Status: In Progress (Phase 2 of 4)

## Hexagonal Components:
- Signal processing (domain + use cases)
- Broker execution (ports + adapters)

## Still Layered:
- Authentication (low complexity, stable)
- Analytics (CRUD-like, will migrate in Phase 3)

## Rationale:
Focusing migration on high-value, complex domains first.
```

## Build Order

Recommended sequence for building hexagonal architecture from scratch OR migrating:

### 1. Domain Layer (Week 1)
**Build first because:** Zero external dependencies, can develop in isolation
- Entities (Signal, Order, Position, Account)
- Value Objects (Symbol, Price, Quantity, OrderType)
- Domain Services (RiskCalculator, SignalValidator, PositionSizer)
- Domain Events (SignalReceived, OrderExecuted)

**Dependencies:** None
**Testing:** Pure unit tests, no mocks needed

### 2. Application Ports (Week 1-2)
**Build second because:** Define contracts before implementations
- Outbound ports (BrokerPort, SignalRepository, CachePort)
- Inbound ports (SignalService interface)

**Dependencies:** Domain layer only
**Testing:** Not directly testable (interfaces)

### 3. Application Use Cases (Week 2)
**Build third because:** Implements business workflows using domain + ports
- ProcessSignalUseCase
- ProcessWebhookUseCase
- ExecuteOrderUseCase
- ManagePositionUseCase

**Dependencies:** Domain layer + Port interfaces
**Testing:** Unit tests with mocked ports

### 4. Infrastructure - Outbound Adapters (Week 2-3)
**Build fourth because:** Use cases need implementations to work
- Broker adapters (MT4Adapter, MT5Adapter, etc.)
- Repository implementations (SignalRepositoryImpl)
- Cache adapter (RedisAdapter)

**Dependencies:** Application ports + external libraries
**Testing:** Integration tests with test doubles (TestContainers, mocks)

### 5. Infrastructure - Inbound Adapters (Week 3)
**Build fifth because:** Entry points need complete pipeline underneath
- FastAPI routers (signal, webhook, trade endpoints)
- WebSocket handlers

**Dependencies:** Use cases + FastAPI
**Testing:** API tests, end-to-end tests

### 6. Dependency Injection Setup (Week 3-4)
**Build sixth because:** Wires everything together
- DI container configuration
- FastAPI dependency providers
- Bootstrap logic

**Dependencies:** All layers
**Testing:** Integration tests verifying wiring

### 7. Main Application Entry Point (Week 4)
**Build last because:** Composes entire application
- FastAPI app initialization
- Router registration
- Lifespan management

**Dependencies:** Everything
**Testing:** Full end-to-end tests

### Build Order Rationale

**Inside-Out Strategy:**
- Start with pure business logic (domain) - no external dependencies = easiest to test
- Define contracts (ports) before implementations
- Build use cases that orchestrate domain logic
- Add infrastructure last (most likely to change)

**Testing Pyramid:**
- Many domain tests (fast, isolated)
- Moderate use case tests (mocked dependencies)
- Fewer adapter tests (integration with external systems)
- Few e2e tests (full stack)

**Dependency Flow:**
```
Main App
  ↓
Inbound Adapters (FastAPI routers)
  ↓
Use Cases
  ↓
Domain Services + Outbound Ports
  ↓
Outbound Adapters (Brokers, Repos)
```

Build from bottom (domain) to top (main app).

### Migration Build Order

For brownfield migration (your case):

1. **Extract domain entities** (non-breaking, parallel to existing)
2. **Create ports** (move BaseExecutor to application layer)
3. **Implement adapters** (refactor existing executors to implement ports)
4. **Create use cases** (extract from SignalProcessor)
5. **Refactor routers** (use use cases via DI)
6. **Delete old code** (remove SignalProcessor after full migration)

## Confidence Assessment

| Area | Confidence | Rationale |
|------|------------|-----------|
| Layer definitions | HIGH | AWS official docs + multiple consistent sources |
| Port/Adapter pattern | HIGH | Official hexagonal architecture resources + Python examples |
| Directory structure | HIGH | AWS prescriptive guidance + established Python projects |
| FastAPI DI integration | HIGH | Official FastAPI patterns + 2025 production examples |
| Migration strategy | MEDIUM | Derived from general refactoring guidance, not trading-specific |
| Build order | HIGH | Logical dependency analysis + DDD best practices |

## Sources

### Primary Sources (HIGH Confidence)

- [AWS Prescriptive Guidance: Structure Python project in hexagonal architecture](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/structure-a-python-project-in-hexagonal-architecture-using-aws-lambda.html)
- [Hexagonal Architecture in Python - Szymon Miks](https://blog.szymonmiks.pl/p/hexagonal-architecture-in-python/)
- [One design pattern for FastAPI web applications - LSST](https://sqr-072.lsst.io/)
- [From Layered to Hexagonal Architecture in 2 Steps - Codeartify](https://codeartify.substack.com/p/from-layered-to-hexagonal-architecture)
- [Modern Python Interfaces: ABC, Protocol, or Both? - Medium (Nov 2025)](https://tconsta.medium.com/python-interfaces-abc-protocol-or-both-3c5871ea6642)

### Secondary Sources (MEDIUM Confidence)

- [Hexagonal Architecture in Python - Medium (Szymon Miks)](https://medium.com/@miks.szymon/hexagonal-architecture-in-python-e16a8646f000)
- [Building Maintainable Python Applications with Hexagonal Architecture and DDD - DEV Community](https://dev.to/hieutran25/building-maintainable-python-applications-with-hexagonal-architecture-and-domain-driven-design-chp)
- [Layered Architecture & Dependency Injection in FastAPI - DEV Community (May 2025)](https://dev.to/markoulis/layered-architecture-dependency-injection-a-recipe-for-clean-and-testable-fastapi-code-3ioo)
- [Hexagonal FastAPI - Moritz Althaus (Jan 2025)](https://moldhouse.de/posts/hexagonal-fastapi/)
- [GitHub: szymon6927/hexagonal-architecture-python](https://github.com/szymon6927/hexagonal-architecture-python)
- [GitHub: ShahriyarR/hexagonal-fastapi-jobboard](https://github.com/ShahriyarR/hexagonal-fastapi-jobboard)
- [GitHub: marcosvs98/hexagonal-architecture-with-python](https://github.com/marcosvs98/hexagonal-architecture-with-python)

### Tertiary Sources (Community Insights)

- [Ports and Adapters in Python - Code Like A Girl](https://code.likeagirl.io/ports-and-adapters-in-python-domain-driven-design-patterns-2c8c5a3171c8)
- [Hexagonal Architecture: Principles and Benefits - Aalpha (2025)](https://www.aalpha.net/blog/hexagonal-architecture/)
- [Refactoring to Hexagonal Architecture - Learn Hexagonal Architecture](https://learnhexagonalarchitecture.com/)
- [Are You Using Hexagonal Architecture, or Just Dependency Injection? - DEV (2025)](https://dev.to/stevenstuartm/are-you-using-hexagonal-architecture-or-just-dependency-injection-29ja)

## Research Metadata

**Research Date:** 2026-01-19
**Valid Until:** 2026-02-19 (30 days - relatively stable architectural patterns)
**Tools Used:** WebSearch, WebFetch
**Verification:** Cross-referenced AWS official guidance with multiple Python/FastAPI implementations
