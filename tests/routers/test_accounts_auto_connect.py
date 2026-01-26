"""
Tests for auto-connect behavior on account creation.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.application.dto.account_dto import ConnectAccountResponse
from app.models.schemas import AccountCreate
from app.routers.accounts import create_account


@pytest.fixture
def mock_db():
    db = Mock()
    db.commit = Mock()
    query = Mock()
    db.query.return_value = query
    query.filter.return_value = query
    query.order_by.return_value = query
    return db


@pytest.fixture
def mock_user():
    user = Mock()
    user.id = 42
    return user


@pytest.mark.asyncio
async def test_create_account_auto_connects_with_credentials(
    mock_db, mock_user
):
    mock_account = Mock()
    mock_account.id = 100
    mock_account.user_id = 42
    mock_account.account_number = "acc-100"
    mock_account.broker = Mock(value="tradelocker")
    mock_account.account_type = Mock(value="demo")
    mock_account.currency = "USD"
    mock_account.leverage = 100
    mock_account.balance = 0.0
    mock_account.equity = 0.0
    mock_account.margin = 0.0
    mock_account.free_margin = 0.0
    mock_account.is_active = True
    mock_account.is_connected = False
    mock_account.last_sync = None
    mock_account.created_at = None
    mock_account.webhook_key = None
    mock_account.enabled_broker_account_ids = []
    mock_account.default_broker_account_id = None
    mock_account.discovered_accounts_cache = None

    mock_db.query.return_value.first.return_value = mock_account
    mock_db.query.return_value.order_by.return_value.first.return_value = mock_account

    mock_create_use_case = Mock()
    mock_create_use_case.execute = AsyncMock(return_value=Mock(
        account_id="acc-100",
        broker=Mock(value="tradelocker"),
        is_active=True,
        error=None,
        auto_aliases_created=0,
    ))

    mock_connect_use_case = Mock()
    mock_connect_use_case.execute = AsyncMock(return_value=ConnectAccountResponse(
        account_id="100",
        is_connected=True,
        balance=None,
        equity=None,
        error=None,
    ))

    mock_container = Mock()
    mock_container.create_account_use_case.return_value = mock_create_use_case
    mock_container.connect_account_use_case.return_value = mock_connect_use_case

    with patch("app.routers.accounts.get_container", return_value=mock_container):
        account = AccountCreate(
            account_id="acc-100",
            broker="tradelocker",
            account_type="demo",
            currency="USD",
            broker_config={
                "username": "user@example.com",
                "password": "secret",
                "server": "Demo Server",
            },
        )
        result = await create_account(
            request=Mock(),
            account=account,
            current_user=mock_user,
            db=mock_db,
        )

    assert result["id"] == 100
    assert mock_connect_use_case.execute.call_count == 1
