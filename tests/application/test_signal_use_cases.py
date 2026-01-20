"""
Signal Use Case Tests

Tests ProcessSignalUseCase, GetSignalUseCase, ListSignalsUseCase
using mock port implementations.
"""
import pytest
from decimal import Decimal

from app.domain.enums import SignalSource, SignalAction, SignalStatus, BrokerType
from app.application.dto.signal_dto import ProcessSignalRequest, SignalListRequest
from app.application.use_cases.process_signal import ProcessSignalUseCase
from app.application.use_cases.get_signals import GetSignalUseCase, ListSignalsUseCase

from tests.application import (
    InMemorySignalRepository,
    InMemoryAccountRepository,
    MockBrokerPort,
    InMemoryEventPort,
    create_test_account,
)


@pytest.fixture
def signal_repo():
    return InMemorySignalRepository()


@pytest.fixture
def account_repo():
    repo = InMemoryAccountRepository()
    return repo


@pytest.fixture
def broker_port():
    return MockBrokerPort()


@pytest.fixture
def event_port():
    return InMemoryEventPort()


class TestProcessSignalUseCase:
    """Tests for ProcessSignalUseCase"""

    @pytest.mark.asyncio
    async def test_process_buy_signal_success(self, signal_repo, account_repo, broker_port, event_port):
        # Setup: Create connected account
        account = create_test_account()
        await account_repo.save(account)
        await broker_port.connect()

        # Create use case
        use_case = ProcessSignalUseCase(
            signal_repository=signal_repo,
            account_repository=account_repo,
            brokers={BrokerType.MT5: broker_port},
            event_port=event_port,
        )

        # Execute with DTO
        request = ProcessSignalRequest(
            source=SignalSource.TRADINGVIEW,
            symbol="EURUSD",
            action=SignalAction.BUY,
            volume=Decimal("1.0"),
        )
        response = await use_case.execute(request)

        # Verify response is DTO
        assert response.signal_id != ""
        assert response.status == SignalStatus.PROCESSED
        assert response.executions == 1
        assert len(response.errors) == 0

    @pytest.mark.asyncio
    async def test_process_signal_no_accounts_skipped(self, signal_repo, account_repo, broker_port, event_port):
        # No accounts in repo
        use_case = ProcessSignalUseCase(
            signal_repository=signal_repo,
            account_repository=account_repo,
            brokers={BrokerType.MT5: broker_port},
            event_port=event_port,
        )

        request = ProcessSignalRequest(
            source=SignalSource.TRADINGVIEW,
            symbol="EURUSD",
            action=SignalAction.BUY,
            volume=Decimal("1.0"),
        )
        response = await use_case.execute(request)

        assert response.status == SignalStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_process_signal_validation_error(self, signal_repo, account_repo, broker_port, event_port):
        # BUY without volume should fail at DTO level
        with pytest.raises(ValueError, match="Volume required"):
            ProcessSignalRequest(
                source=SignalSource.TRADINGVIEW,
                symbol="EURUSD",
                action=SignalAction.BUY,
                volume=None,
            )


class TestGetSignalUseCase:
    """Tests for GetSignalUseCase"""

    @pytest.mark.asyncio
    async def test_get_signal_found(self, signal_repo, account_repo, broker_port, event_port):
        # Create a signal through ProcessSignalUseCase
        account = create_test_account()
        await account_repo.save(account)
        await broker_port.connect()

        process_uc = ProcessSignalUseCase(
            signal_repository=signal_repo,
            account_repository=account_repo,
            brokers={BrokerType.MT5: broker_port},
            event_port=event_port,
        )
        request = ProcessSignalRequest(
            source=SignalSource.TRADINGVIEW,
            symbol="EURUSD",
            action=SignalAction.BUY,
            volume=Decimal("1.0"),
        )
        response = await process_uc.execute(request)

        # Now get it
        get_uc = GetSignalUseCase(signal_repository=signal_repo)
        signal_dto = await get_uc.execute(response.signal_id)

        assert signal_dto is not None
        assert signal_dto.id == response.signal_id
        assert signal_dto.symbol == "EURUSD"

    @pytest.mark.asyncio
    async def test_get_signal_not_found(self, signal_repo):
        get_uc = GetSignalUseCase(signal_repository=signal_repo)
        signal_dto = await get_uc.execute("nonexistent")

        assert signal_dto is None


class TestListSignalsUseCase:
    """Tests for ListSignalsUseCase"""

    @pytest.mark.asyncio
    async def test_list_signals_empty(self, signal_repo):
        use_case = ListSignalsUseCase(signal_repository=signal_repo)
        request = SignalListRequest(limit=10)
        response = await use_case.execute(request)

        assert response.total == 0
        assert len(response.signals) == 0

    @pytest.mark.asyncio
    async def test_list_signals_returns_dtos(self, signal_repo, account_repo, broker_port, event_port):
        # Create some signals
        account = create_test_account()
        await account_repo.save(account)
        await broker_port.connect()

        process_uc = ProcessSignalUseCase(
            signal_repository=signal_repo,
            account_repository=account_repo,
            brokers={BrokerType.MT5: broker_port},
            event_port=event_port,
        )

        for i in range(3):
            request = ProcessSignalRequest(
                source=SignalSource.TRADINGVIEW,
                symbol=f"EURUSD",
                action=SignalAction.BUY,
                volume=Decimal("1.0"),
            )
            await process_uc.execute(request)

        # List them
        list_uc = ListSignalsUseCase(signal_repository=signal_repo)
        request = SignalListRequest(status=SignalStatus.PROCESSED)
        response = await list_uc.execute(request)

        assert response.total == 3
        assert all(s.status == SignalStatus.PROCESSED for s in response.signals)
