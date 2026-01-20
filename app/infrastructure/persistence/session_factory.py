"""
Async session factory for SQLAlchemy.

Wraps existing database.py setup for use in Unit of Work pattern.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.db.database import async_engine


class SessionFactory:
    """
    Factory for creating async SQLAlchemy sessions.

    Provides a consistent interface for session creation that can be
    mocked in tests or configured with different engines.
    """

    def __init__(self, engine=None):
        """
        Initialize session factory.

        Args:
            engine: Optional async engine. Defaults to global async_engine from database.py
        """
        self._engine = engine or async_engine
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Allow continued access to entities after commit
            autoflush=False,  # Manual control over when to flush
            autocommit=False,  # Explicit transaction management
        )

    def create_session(self) -> AsyncSession:
        """
        Create a new async database session.

        Returns:
            AsyncSession: New async SQLAlchemy session
        """
        return self._session_factory()
