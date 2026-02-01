"""
Database connection and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator
import os
from urllib.parse import urlparse, urlunparse

def get_database_url() -> str:
    """
    Get DATABASE_URL, injecting password from Docker secret if needed
    """
    url = os.getenv("DATABASE_URL", "sqlite:///./unified_engine.db")

    # If URL already has a password or is SQLite, return as-is
    if url.startswith("sqlite") or "@" not in url:
        return url

    parsed = urlparse(url)

    # If password is already in URL, return as-is
    if parsed.password:
        return url

    # Try to read password from Docker secret
    db_password = None
    try:
        with open("/run/secrets/db_password", "r") as f:
            db_password = f.read().strip()
    except FileNotFoundError:
        # Not in Docker Swarm, try environment variable
        db_password = os.getenv("DATABASE_PASSWORD", "")

    if db_password:
        # Inject password into URL
        # Format: postgresql://user:password@host:port/db
        netloc = f"{parsed.username}:{db_password}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        new_url = urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        return new_url

    return url

# Database URL from environment or default to SQLite
DATABASE_URL = get_database_url()

# Create engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables
    """
    from app.models.database_models import Base
    Base.metadata.create_all(bind=engine)
    print("✓ Database initialized successfully")
