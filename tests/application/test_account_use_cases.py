"""
Account Use Case Tests

Tests GetAccountsUseCase, ConnectAccountUseCase, SyncAccountUseCase
using mock port implementations.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock

from app.domain.enums import BrokerType, AccountType
from app.application.dto.account_dto import (
    GetAccountsRequest,
    ConnectAccountRequest,
    SyncAccountRequest,
    CreateAccountRequest,
)
from app.application.use_cases.manage_accounts import (
    GetAccountsUseCase,
    GetAccountUseCase,
    ConnectAccountUseCase,
    SyncAccountUseCase,
    CreateAccountUseCase,
)

from tests.application import (
    InMemoryAccountRepository,
    InMemoryPositionRepository,
    InMemoryOrderRepository,
    MockBrokerPort,
    create_test_account,
)


@pytest.fixture
def account_repo():
    return InMemoryAccountRepository()


@pytest.fixture
def position_repo():
    return InMemoryPositionRepository()


@pytest.fixture
def order_repo():
    return InMemoryOrderRepository()


@pytest.fixture
def broker_port():
    return MockBrokerPort()


class TestGetAccountsUseCase:
    """Tests for GetAccountsUseCase"""

    @pytest.mark.asyncio
    async def test_get_accounts_for_user(self, account_repo):
        # Create accounts for different users
        acc1 = create_test_account(account_id="acc-1", user_id=1)
        acc2 = create_test_account(account_id="acc-2", user_id=1)
        acc3 = create_test_account(account_id="acc-3", user_id=2)
        await account_repo.save(acc1)
        await account_repo.save(acc2)
        await account_repo.save(acc3)

        use_case = GetAccountsUseCase(account_repository=account_repo)
        request = GetAccountsRequest(user_id=1)
        response = await use_case.execute(request)

        assert response.total == 2
        assert all(a.id.startswith("acc-") for a in response.accounts)

    @pytest.mark.asyncio
    async def test_get_accounts_filter_by_broker(self, account_repo):
        acc1 = create_test_account(account_id="acc-mt5", user_id=1, broker=BrokerType.MT5)
        acc2 = create_test_account(account_id="acc-mt4", user_id=1, broker=BrokerType.MT4)
        await account_repo.save(acc1)
        await account_repo.save(acc2)

        use_case = GetAccountsUseCase(account_repository=account_repo)
        request = GetAccountsRequest(user_id=1, broker=BrokerType.MT5)
        response = await use_case.execute(request)

        assert response.total == 1
        assert response.accounts[0].broker == BrokerType.MT5


class TestGetAccountUseCase:
    """Tests for GetAccountUseCase"""

    @pytest.mark.asyncio
    async def test_get_account_found(self, account_repo):
        account = create_test_account()
        await account_repo.save(account)

        use_case = GetAccountUseCase(account_repository=account_repo)
        dto = await use_case.execute("test-account")

        assert dto is not None
        assert dto.id == "test-account"
        assert dto.balance == Decimal("10000")

    @pytest.mark.asyncio
    async def test_get_account_not_found(self, account_repo):
        use_case = GetAccountUseCase(account_repository=account_repo)
        dto = await use_case.execute("nonexistent")

        assert dto is None


class TestConnectAccountUseCase:
    """Tests for ConnectAccountUseCase"""

    @pytest.mark.asyncio
    async def test_connect_account_success(self, account_repo, broker_port):
        account = create_test_account(is_connected=False)
        await account_repo.save(account)

        use_case = ConnectAccountUseCase(
            account_repository=account_repo,
            brokers={BrokerType.MT5: broker_port},
        )

        request = ConnectAccountRequest(account_id="test-account")
        response = await use_case.execute(request)

        assert response.is_connected is True
        assert response.balance is not None
        assert response.error is None

    @pytest.mark.asyncio
    async def test_connect_account_not_found(self, account_repo, broker_port):
        use_case = ConnectAccountUseCase(
            account_repository=account_repo,
            brokers={BrokerType.MT5: broker_port},
        )

        request = ConnectAccountRequest(account_id="nonexistent")
        response = await use_case.execute(request)

        assert response.is_connected is False
        assert "not found" in response.error.lower()


class TestSyncAccountUseCase:
    """Tests for SyncAccountUseCase"""

    @pytest.mark.asyncio
    async def test_sync_account_success(self, account_repo, position_repo, order_repo, broker_port):
        account = create_test_account(is_connected=True)
        await account_repo.save(account)
        await broker_port.connect()

        use_case = SyncAccountUseCase(
            account_repository=account_repo,
            position_repository=position_repo,
            order_repository=order_repo,
            brokers={BrokerType.MT5: broker_port},
        )

        request = SyncAccountRequest(account_id="test-account")
        response = await use_case.execute(request)

        assert response.account_id == "test-account"
        assert response.balance is not None
        assert response.synced_at is not None


class TestCreateAccountUseCase:
    """Tests for CreateAccountUseCase ensuring persistence commits."""

    @pytest.mark.asyncio
    async def test_creating_account_commits_session(self):
        saved_account = create_test_account(account_id="test-account", user_id=1)

        mock_account_repo = AsyncMock()
        mock_account_repo.save = AsyncMock(return_value=saved_account)
        mock_account_repo._session = AsyncMock()
        mock_account_repo._session.commit = AsyncMock()

        mock_credential_repo = AsyncMock()
        mock_credential_repo.create = AsyncMock()

        use_case = CreateAccountUseCase(
            account_repository=mock_account_repo,
            credential_repository=mock_credential_repo,
        )

        request = CreateAccountRequest(
            user_id=1,
            broker=BrokerType.MT4,
            account_type=AccountType.DEMO,
            credentials={},
            account_id="test-account",
            currency="USD",
            leverage=100,
            server="test-account-server",
        )

        response = await use_case.execute(request)

        mock_account_repo._session.commit.assert_awaited_once()
        assert response.account_id == saved_account.id.value
