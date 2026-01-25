from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create synchronous database engine (existing code)
# For Postgres: use connection pooling; for SQLite: single-threaded mode
_is_sqlite = "sqlite" in settings.DATABASE_URL
_engine_kwargs = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,  # Verify connections before using them
}

if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Postgres pooling configuration
    _engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    _engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

# Create async database engine (for new infrastructure layer)
# Convert DATABASE_URL to async dialect if needed
async_database_url = settings.DATABASE_URL
if async_database_url.startswith("postgresql://"):
    async_database_url = async_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif async_database_url.startswith("sqlite:///"):
    async_database_url = async_database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

# Create async engine with graceful degradation for missing drivers
# This allows alembic migrations to run without asyncpg/aiosqlite installed
_async_engine_kwargs = {
    "echo": settings.DEBUG,
    "future": True,
}
if not _is_sqlite:
    # Postgres async pooling configuration
    _async_engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    _async_engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW

try:
    async_engine = create_async_engine(async_database_url, **_async_engine_kwargs)
except ModuleNotFoundError as e:
    logger.warning(f"Async database driver not available: {e}. Async operations will not work.")
    async_engine = None

# Create session factory (synchronous - existing code)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create async session factory (for new infrastructure layer)
if async_engine:
    AsyncSessionLocal = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
else:
    AsyncSessionLocal = None

# Create base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()

def get_db():
    """Database dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_session():
    """Async database dependency for FastAPI"""
    if not AsyncSessionLocal:
        raise RuntimeError("Async database engine not available. Install asyncpg or aiosqlite.")

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def init_db():
    """Initialize database with all tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def drop_db():
    """Drop all database tables"""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Database drop failed: {e}")
        raise