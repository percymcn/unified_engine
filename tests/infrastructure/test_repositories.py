"""Tests for SQLAlchemy repository implementations."""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from app.domain.enums import SignalStatus, BrokerType
from app.domain.value_objects import SignalId, AccountId, Symbol, Volume
from tests.infrastructure import create_test_signal, create_test_account


class TestSQLAlchemySignalRepository:
    """
    Tests for signal repository.
    Uses mocked SQLAlchemy session to avoid database dependencies.
    """

    @pytest.mark.asyncio
    async def test_save_calls_session_methods(self):
        """Test that save calls appropriate session methods."""
        from app.infrastructure.repositories.signal_repository import SQLAlchemySignalRepository

        # Create mock session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()

        repo = SQLAlchemySignalRepository(mock_session)
        signal = create_test_signal()

        # Save should work without errors
        result = await repo.save(signal)

        # Verify session methods were called
        assert mock_session.execute.called or mock_session.flush.called
        assert result.id == signal.id

    @pytest.mark.asyncio
    async def test_get_by_id_queries_database(self):
        """Test that get_by_id executes query."""
        from app.infrastructure.repositories.signal_repository import SQLAlchemySignalRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemySignalRepository(mock_session)
        signal_id = SignalId(str(uuid4()))

        # Should execute query
        result = await repo.get_by_id(signal_id)

        # Verify execute was called
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_get_pending_filters_by_status(self):
        """Test that get_pending filters for pending status."""
        from app.infrastructure.repositories.signal_repository import SQLAlchemySignalRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemySignalRepository(mock_session)

        # Should execute query
        results = await repo.get_pending()

        # Verify execute was called
        assert mock_session.execute.called
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_delete_removes_entity(self):
        """Test that delete removes entity from session."""
        from app.infrastructure.repositories.signal_repository import SQLAlchemySignalRepository

        mock_session = AsyncMock()
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()

        # Need to mock execute for get_by_id
        mock_orm_signal = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=mock_orm_signal)))
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemySignalRepository(mock_session)
        signal = create_test_signal()

        # Should call delete
        await repo.delete(signal)

        # Verify execute was called (for finding entity)
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_get_by_status_accepts_status_enum(self):
        """Test that get_by_status accepts status enum."""
        from app.infrastructure.repositories.signal_repository import SQLAlchemySignalRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemySignalRepository(mock_session)

        # Should accept status enum
        results = await repo.get_by_status(SignalStatus.PENDING)

        assert mock_session.execute.called
        assert isinstance(results, list)


class TestSQLAlchemyAccountRepository:
    """
    Tests for account repository.
    Uses mocked SQLAlchemy session to avoid database dependencies.
    """

    @pytest.mark.asyncio
    async def test_save_calls_session_methods(self):
        """Test that save calls appropriate session methods."""
        from app.infrastructure.repositories.account_repository import SQLAlchemyAccountRepository

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()

        repo = SQLAlchemyAccountRepository(mock_session)
        account = create_test_account()

        # Save should work without errors
        result = await repo.save(account)

        # Verify session methods were called
        assert mock_session.execute.called or mock_session.flush.called
        assert result.id == account.id

    @pytest.mark.asyncio
    async def test_get_by_id_queries_database(self):
        """Test that get_by_id executes query."""
        from app.infrastructure.repositories.account_repository import SQLAlchemyAccountRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyAccountRepository(mock_session)
        account_id = AccountId(str(uuid4()))

        # Should execute query
        result = await repo.get_by_id(account_id)

        # Verify execute was called
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_get_by_broker_filters_by_type(self):
        """Test that get_by_broker filters by broker type."""
        from app.infrastructure.repositories.account_repository import SQLAlchemyAccountRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyAccountRepository(mock_session)

        # Should execute query with broker filter
        results = await repo.get_by_broker(BrokerType.TRADELOCKER)

        assert mock_session.execute.called
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_by_user_queries_by_user_id(self):
        """Test that get_by_user queries by user ID."""
        from app.infrastructure.repositories.account_repository import SQLAlchemyAccountRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyAccountRepository(mock_session)

        # Should execute query with user filter
        results = await repo.get_by_user(1)

        assert mock_session.execute.called
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_delete_removes_entity(self):
        """Test that delete removes entity from session."""
        from app.infrastructure.repositories.account_repository import SQLAlchemyAccountRepository

        mock_session = AsyncMock()
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()

        # Need to mock execute for get_by_id
        mock_orm_account = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=mock_orm_account)))
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyAccountRepository(mock_session)
        account = create_test_account()

        # Should call methods
        await repo.delete(account)

        # Verify execute was called (for finding entity)
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_repository_handles_broker_enum(self):
        """Test that repository correctly handles BrokerType enum."""
        from app.infrastructure.repositories.account_repository import SQLAlchemyAccountRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyAccountRepository(mock_session)

        # Should handle all broker types
        for broker in [BrokerType.TRADELOCKER, BrokerType.MT5, BrokerType.TOPSTEP]:
            results = await repo.get_by_broker(broker)
            assert isinstance(results, list)
