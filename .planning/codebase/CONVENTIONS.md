# Coding Conventions

**Analysis Date:** 2026-01-19

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` (e.g., `signal_processor.py`, `base_executor.py`)
- Test files: `test_*.py` (e.g., `test_api.py`, `test_brokers.py`)
- Router files: `*_router.py` or `*s.py` (e.g., `funnel_router.py`, `trades.py`)
- Executor classes: `*_executor.py` (e.g., `mt4_executor.py`, `tradovate_executor.py`)

**Functions:**
- Async functions: `async def snake_case()` - all API endpoints and I/O operations
- Sync functions: `def snake_case()` - utilities and helpers
- Private functions: Leading underscore `def _private_function()` (e.g., `_log_signal`, `_validate_signal`)

**Variables:**
- Local variables: `snake_case` (e.g., `signal_id`, `execution_result`, `mock_response`)
- Constants: `UPPER_SNAKE_CASE` in settings (e.g., `DATABASE_URL`, `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Configuration keys: lowercase strings (e.g., `"api_key"`, `"account_number"`)

**Classes:**
- Classes: `PascalCase` (e.g., `SignalProcessor`, `MT4Executor`, `BaseExecutor`)
- Pydantic models: `PascalCase` (e.g., `UserCreate`, `SignalRequest`, `OrderResponse`)
- SQLAlchemy models: `PascalCase` (e.g., `User`, `Account`, `Trade`)
- Enums: `PascalCase` with `UPPER_CASE` values (e.g., `BrokerType.MT4`, `OrderStatus.PENDING`)

**Types:**
- Enums inherit from `str, enum.Enum` or `str, Enum` for Pydantic compatibility
- Type annotations used throughout: `Dict[str, Any]`, `List[Dict[str, Any]]`, `Optional[str]`

## Code Style

**Formatting:**
- No automated formatter detected (no `.prettierrc`, `.black`, or similar config)
- Indentation: 4 spaces (Python standard)
- Line length: Varies, typically ~100-120 characters
- Blank lines: Two blank lines between top-level definitions

**Linting:**
- No linter configuration files detected (no `.flake8`, `.pylintrc`, or similar)
- Code follows PEP 8 conventions by observation

**Type Hints:**
- Extensive use of type annotations from `typing` module
- All function signatures include parameter types and return types
- Async functions annotated with return types (e.g., `async def connect(self) -> bool:`)

## Import Organization

**Order:**
1. Standard library imports (alphabetically)
2. Third-party imports (alphabetically)
3. Blank line
4. Local/app imports (grouped by category)

**Pattern observed in `app/main.py`:**
```python
# Standard library
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

# Third-party
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Core imports
from app.core.config import settings
from app.core.websocket_manager import ws_manager

# Router imports
from app.routers.auth import router as auth_router
```

**Path Aliases:**
- Absolute imports: `from app.models.schemas import UserCreate`
- Relative imports: Not used - all imports are absolute from `app.*`
- Test imports: `sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))` for parent directory access

**Import Style:**
- Routers imported as: `from app.routers.auth import router as auth_router`
- Models imported directly: `from app.models.models import User, Account`
- Config always imported as: `from app.core.config import settings`

## Error Handling

**Patterns:**

**FastAPI HTTP Exceptions:**
```python
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Account not found"
)
```

**Try-Except with Logging:**
```python
try:
    # Operation
    result = await broker.connect()
except Exception as e:
    logger.error(f"Error initializing {broker_name}: {e}")
    return False
```

**Validation Errors:**
- Pydantic handles validation automatically
- Custom validators use `@field_validator` decorator (e.g., `parse_log_max_size`)
- Config validation raises `ValueError` for critical misconfigurations

**Error Responses:**
- Structured error responses with `detail` field
- Status codes from `fastapi.status` constants
- Database errors caught and logged before raising HTTPException

## Logging

**Framework:** Python's built-in `logging` module with custom structured logging setup

**Setup Pattern:**
```python
import logging

logger = logging.getLogger(__name__)
```

**Patterns:**
- Info: `logger.info("✅ Database tables created")`
- Warning: `logger.warning("⚠️  Event emitter initialization timed out")`
- Error: `logger.error(f"❌ Failed to start application: {e}")`
- Debug: Used for detailed operational info

**Emojis in Logs:**
- Used extensively for visual clarity: ✅ (success), ❌ (error), ⚠️ (warning), 🚀 (startup), 🛑 (shutdown)

**Structured Logging:**
- Custom logging setup in `app/core/logging_config.py`
- Settings: `LOG_LEVEL`, `LOG_FILE`, `LOG_MAX_SIZE`, `LOG_BACKUP_COUNT`

## Comments

**Docstrings:**
- Module-level docstrings present on most files
- Function docstrings: Brief description of purpose
- Class docstrings: Present on base classes and major components

**Pattern:**
```python
def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate user with username and password"""
    # Implementation
```

**Inline Comments:**
- Used sparingly for complex logic
- TODO comments present for planned features (e.g., `# TODO: Implement order retrieval in broker executors`)

**TODO Comments:**
- Format: `# TODO: Description`
- Found in routers for unimplemented features
- Integration TODOs for external services (email, messaging, scheduling)

## Function Design

**Size:**
- Endpoint functions: 10-50 lines average
- Service methods: 20-100 lines
- Utility functions: 5-20 lines
- Large files: Broker executors and routers (400-550 lines)

**Parameters:**
- FastAPI dependency injection: `Depends(get_db)`, `Depends(get_current_user)`
- Type-annotated parameters throughout
- Optional parameters use `Optional[Type] = None`
- Default values for query parameters (e.g., `skip: int = 0, limit: int = 100`)

**Return Values:**
- Type-annotated return types on all functions
- Pydantic models for API responses: `response_model=List[TradeSchema]`
- Dict responses for internal methods: `Dict[str, Any]`
- Boolean for success/failure: `-> bool`

**Async/Await:**
- All API endpoints are async
- All database operations use sync SQLAlchemy (not async)
- External API calls use `aiohttp` or `httpx` with async
- Broker executors are fully async

## Module Design

**Exports:**
- Routers: `router = APIRouter()` then imported in main
- Services: Classes instantiated as singletons (e.g., `signal_processor = SignalProcessor()`)
- Models: All models exported from module directly

**Barrel Files:**
- Not used - imports are explicit from submodules

**Directory Structure:**
- `app/routers/`: API endpoint definitions
- `app/services/`: Business logic
- `app/brokers/`: Broker integrations (all inherit from `BaseExecutor`)
- `app/models/`: Data models (SQLAlchemy and Pydantic)
- `app/core/`: Configuration, security, middleware

## Database Patterns

**ORM:**
- SQLAlchemy ORM with declarative base
- Session management via `get_db()` dependency
- Models use `Column`, `relationship`, `ForeignKey`

**Schema Pattern:**
```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
```

**Pydantic Config:**
```python
class Config:
    from_attributes = True  # Pydantic v2 (was orm_mode in v1)
```

**Query Pattern:**
```python
trades = db.query(Trade).join(Account).filter(
    Account.user_id == current_user.id
).offset(skip).limit(limit).all()
```

## API Design

**Router Registration:**
```python
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
```

**Endpoint Signatures:**
```python
@router.get("/", response_model=List[TradeSchema])
async def get_trades(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
```

**Authentication:**
- JWT tokens via `python-jose`
- Bearer token in header via `HTTPBearer()`
- Current user injection via `Depends(get_current_user)`

## Configuration

**Settings Management:**
- Pydantic Settings in `app/core/config.py`
- Environment variables with defaults
- Validation via `@field_validator`

**Pattern:**
```python
class Settings(BaseSettings):
    APP_NAME: str = "Unified Trading Engine"
    DATABASE_URL: str = "postgresql://..."

    model_config = SettingsConfigDict(env_file=".env")
```

**Usage:**
```python
from app.core.config import settings

settings.DATABASE_URL
```

---

*Convention analysis: 2026-01-19*
