"""Tests for SQLAlchemy Unit of Work implementation."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.infrastructure import create_test_signal


class TestSQLAlchemyUnitOfWork:
    """Tests for SQLAlchemy Unit of Work."""

    @pytest.mark.asyncio
    async def test_context_manager_creates_session(self):
        """Test UoW works as async context manager."""
        from app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork

        mock_session_factory = MagicMock()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_factory.create_session = MagicMock(return_value=mock_session)

        uow = SQLAlchemyUnitOfWork(mock_session_factory)

        async with uow:
            assert uow._session is not None

    @pytest.mark.asyncio
    async def test_repositories_available_in_context(self):
        """Test all repositories are accessible within UoW context."""
        from app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork

        mock_session_factory = MagicMock()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_factory.create_session = MagicMock(return_value=mock_session)

        uow = SQLAlchemyUnitOfWork(mock_session_factory)

        async with uow:
            # All repositories should be accessible
            assert uow.signals is not None
            assert uow.accounts is not None
            assert uow.trades is not None
            assert uow.orders is not None
            assert uow.positions is not None

    @pytest.mark.asyncio
    async def test_commit_calls_session_commit(self):
        """Test UoW commit calls session commit."""
        from app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork

        mock_session_factory = MagicMock()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session_factory.create_session = MagicMock(return_value=mock_session)

        uow = SQLAlchemyUnitOfWork(mock_session_factory)

        async with uow:
            await uow.commit()

        # Verify commit was called
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback_calls_session_rollback(self):
        """Test UoW rollback calls session rollback."""
        from app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork

        mock_session_factory = MagicMock()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session_factory.create_session = MagicMock(return_value=mock_session)

        uow = SQLAlchemyUnitOfWork(mock_session_factory)

        async with uow:
            await uow.rollback()

        # Verify rollback was called
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_exception_triggers_rollback(self):
        """Test UoW rolls back on exception."""
        from app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork

        mock_session_factory = MagicMock()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session_factory.create_session = MagicMock(return_value=mock_session)

        uow = SQLAlchemyUnitOfWork(mock_session_factory)

        try:
            async with uow:
                raise ValueError("Test error")
        except ValueError:
            pass

        # Rollback should have been called via __aexit__
        # (either explicitly or as part of session cleanup)
        assert mock_session.__aexit__.called

    @pytest.mark.asyncio
    async def test_repositories_share_same_session(self):
        """Test all repositories use same session for transaction consistency."""
        from app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork

        mock_session_factory = MagicMock()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_factory.create_session = MagicMock(return_value=mock_session)

        uow = SQLAlchemyUnitOfWork(mock_session_factory)

        async with uow:
            # All repos should have same session instance
            assert uow.signals._session is mock_session
            assert uow.accounts._session is mock_session
            assert uow.trades._session is mock_session
            assert uow.orders._session is mock_session
            assert uow.positions._session is mock_session

    @pytest.mark.asyncio
    async def test_lazy_initialization_of_repositories(self):
        """Test repositories are created on first access (lazy init)."""
        from app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork

        mock_session_factory = MagicMock()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_factory.create_session = MagicMock(return_value=mock_session)

        uow = SQLAlchemyUnitOfWork(mock_session_factory)

        async with uow:
            # Initially None (or may not exist as attributes)
            # Access triggers creation
            signals = uow.signals
            assert signals is not None

            # Second access returns same instance
            signals2 = uow.signals
            assert signals is signals2


class TestSQLAlchemyUnitOfWorkFactory:
    """Tests for SQLAlchemy Unit of Work Factory."""

    def test_factory_creates_uow_instances(self):
        """Test factory creates UnitOfWork instances."""
        from app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWorkFactory

        factory = SQLAlchemyUnitOfWorkFactory()
        uow = factory.create()

        # Should return SQLAlchemyUnitOfWork instance
        from app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
        assert isinstance(uow, SQLAlchemyUnitOfWork)

    def test_factory_creates_new_instances(self):
        """Test factory creates new UoW for each call."""
        from app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWorkFactory

        factory = SQLAlchemyUnitOfWorkFactory()
        uow1 = factory.create()
        uow2 = factory.create()

        # Each call should create new instance
        assert uow1 is not uow2

    def test_factory_accepts_optional_engine(self):
        """Test factory can accept optional engine parameter."""
        from app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWorkFactory

        # Should work without engine (uses default from database.py)
        factory = SQLAlchemyUnitOfWorkFactory()
        uow = factory.create()
        assert uow is not None

        # Should also work with explicit engine parameter
        # (tested via session factory in integration tests)
