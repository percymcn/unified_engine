"""
Tests for Tradovate Token Service

Tests token storage, retrieval, and refresh functionality.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
import httpx

from app.services.tradovate_token_service import (
    TradovateTokenService,
    get_tradovate_token_service,
    REFRESH_BUFFER_SECONDS,
)
from app.models.database_models import TradingAccount, BrokerType, AccountType


class TestTradovateTokenService:
    """Test suite for TradovateTokenService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = MagicMock()
        return db

    @pytest.fixture
    def mock_account(self):
        """Create a mock TradingAccount."""
        account = MagicMock(spec=TradingAccount)
        account.id = 1
        account.user_id = 100
        account.broker = BrokerType.TRADOVATE
        account.account_type = AccountType.DEMO
        account.access_token = None
        account.refresh_token = None
        account.token_expires_at = None
        account.oauth_environment = None
        account.is_active = True
        return account

    @pytest.fixture
    def service(self, mock_db):
        """Create a TradovateTokenService instance."""
        return TradovateTokenService(mock_db)

    @patch("app.services.tradovate_token_service.encrypt")
    def test_store_tokens_encrypts_access_token(self, mock_encrypt, service, mock_account, mock_db):
        """Test that store_tokens encrypts the access token."""
        mock_encrypt.return_value = "encrypted_access"

        service.store_tokens(
            account=mock_account,
            access_token="test_access_token",
            refresh_token=None,
            expires_in=3600,
            environment="demo",
        )

        mock_encrypt.assert_any_call("test_access_token")
        assert mock_account.access_token == "encrypted_access"
        mock_db.commit.assert_called_once()

    @patch("app.services.tradovate_token_service.encrypt")
    def test_store_tokens_encrypts_refresh_token(self, mock_encrypt, service, mock_account, mock_db):
        """Test that store_tokens encrypts the refresh token."""
        mock_encrypt.side_effect = lambda x: f"encrypted_{x}"

        service.store_tokens(
            account=mock_account,
            access_token="access",
            refresh_token="refresh",
            expires_in=3600,
            environment="live",
        )

        assert mock_encrypt.call_count == 2
        assert mock_account.refresh_token == "encrypted_refresh"

    @patch("app.services.tradovate_token_service.encrypt")
    def test_store_tokens_sets_expiry(self, mock_encrypt, service, mock_account):
        """Test that store_tokens sets token expiry correctly."""
        mock_encrypt.return_value = "encrypted"
        expires_in = 3600  # 1 hour

        before = datetime.utcnow()
        service.store_tokens(
            account=mock_account,
            access_token="token",
            refresh_token=None,
            expires_in=expires_in,
            environment="demo",
        )
        after = datetime.utcnow()

        expected_min = before + timedelta(seconds=expires_in)
        expected_max = after + timedelta(seconds=expires_in)

        assert expected_min <= mock_account.token_expires_at <= expected_max

    @patch("app.services.tradovate_token_service.encrypt")
    def test_store_tokens_sets_environment(self, mock_encrypt, service, mock_account):
        """Test that store_tokens sets the OAuth environment."""
        mock_encrypt.return_value = "encrypted"

        service.store_tokens(
            account=mock_account,
            access_token="token",
            refresh_token=None,
            expires_in=3600,
            environment="live",
        )

        assert mock_account.oauth_environment == "live"

    @patch("app.services.tradovate_token_service.decrypt")
    def test_get_access_token_decrypts_correctly(self, mock_decrypt, service, mock_account):
        """Test that get_access_token decrypts the token."""
        mock_decrypt.return_value = "decrypted_token"
        mock_account.access_token = "encrypted_token"
        mock_account.token_expires_at = datetime.utcnow() + timedelta(hours=1)

        result = service.get_access_token(mock_account)

        mock_decrypt.assert_called_once_with("encrypted_token")
        assert result == "decrypted_token"

    def test_get_access_token_returns_none_when_no_token(self, service, mock_account):
        """Test that get_access_token returns None when no token exists."""
        mock_account.access_token = None

        result = service.get_access_token(mock_account)

        assert result is None

    def test_needs_refresh_returns_false_when_no_expiry(self, service, mock_account):
        """Test that _needs_refresh returns False when no expiry is set."""
        mock_account.token_expires_at = None

        result = service._needs_refresh(mock_account)

        assert result is False

    def test_needs_refresh_returns_true_when_expiring_soon(self, service, mock_account):
        """Test that _needs_refresh returns True when token expires within buffer."""
        # Token expires in 2 minutes (less than 5-minute buffer)
        mock_account.token_expires_at = datetime.utcnow() + timedelta(minutes=2)

        result = service._needs_refresh(mock_account)

        assert result is True

    def test_needs_refresh_returns_false_when_not_expiring(self, service, mock_account):
        """Test that _needs_refresh returns False when token is not expiring soon."""
        # Token expires in 1 hour (well beyond 5-minute buffer)
        mock_account.token_expires_at = datetime.utcnow() + timedelta(hours=1)

        result = service._needs_refresh(mock_account)

        assert result is False

    def test_needs_refresh_returns_true_when_expired(self, service, mock_account):
        """Test that _needs_refresh returns True when token is already expired."""
        mock_account.token_expires_at = datetime.utcnow() - timedelta(minutes=5)

        result = service._needs_refresh(mock_account)

        assert result is True

    @patch("app.services.tradovate_token_service.decrypt")
    @patch("app.services.tradovate_token_service.encrypt")
    @patch("httpx.Client")
    def test_refresh_token_calls_correct_endpoint(
        self, mock_client_class, mock_encrypt, mock_decrypt, service, mock_account, mock_db
    ):
        """Test that _refresh_token calls the correct Tradovate API endpoint."""
        mock_decrypt.return_value = "refresh_token_value"
        mock_encrypt.return_value = "encrypted_new_token"
        mock_account.refresh_token = "encrypted_refresh"
        mock_account.oauth_environment = "demo"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "accessToken": "new_access_token",
            "expiresIn": 3600,
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        result = service._refresh_token(mock_account)

        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "demo.tradovateapi.com" in call_args[0][0]
        assert "/auth/renewaccesstoken" in call_args[0][0]

    @patch("app.services.tradovate_token_service.decrypt")
    @patch("httpx.Client")
    def test_refresh_token_returns_false_on_failure(
        self, mock_client_class, mock_decrypt, service, mock_account
    ):
        """Test that _refresh_token returns False when API returns error."""
        mock_decrypt.return_value = "refresh_token_value"
        mock_account.refresh_token = "encrypted_refresh"
        mock_account.oauth_environment = "demo"

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        result = service._refresh_token(mock_account)

        assert result is False

    def test_refresh_token_returns_false_when_no_refresh_token(self, service, mock_account):
        """Test that _refresh_token returns False when no refresh token exists."""
        mock_account.refresh_token = None

        result = service._refresh_token(mock_account)

        assert result is False

    @patch("app.services.tradovate_token_service.decrypt")
    @patch("app.services.tradovate_token_service.encrypt")
    @patch("httpx.Client")
    def test_refresh_token_uses_live_endpoint(
        self, mock_client_class, mock_encrypt, mock_decrypt, service, mock_account
    ):
        """Test that _refresh_token uses live endpoint for live accounts."""
        mock_decrypt.return_value = "refresh_token_value"
        mock_encrypt.return_value = "encrypted"
        mock_account.refresh_token = "encrypted_refresh"
        mock_account.oauth_environment = "live"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "accessToken": "new_token",
            "expiresIn": 3600,
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        service._refresh_token(mock_account)

        call_args = mock_client.post.call_args
        assert "live.tradovateapi.com" in call_args[0][0]


class TestTradovateTokenServiceAsync:
    """Test async methods of TradovateTokenService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = MagicMock()
        return db

    @pytest.fixture
    def mock_account(self):
        """Create a mock TradingAccount."""
        account = MagicMock(spec=TradingAccount)
        account.id = 1
        account.refresh_token = "encrypted_refresh"
        account.oauth_environment = "demo"
        return account

    @pytest.fixture
    def service(self, mock_db):
        """Create a TradovateTokenService instance."""
        return TradovateTokenService(mock_db)

    @pytest.mark.asyncio
    @patch("app.services.tradovate_token_service.decrypt")
    @patch("app.services.tradovate_token_service.encrypt")
    @patch("httpx.AsyncClient")
    async def test_refresh_token_async_success(
        self, mock_client_class, mock_encrypt, mock_decrypt, service, mock_account
    ):
        """Test async token refresh success."""
        mock_decrypt.return_value = "refresh_token_value"
        mock_encrypt.return_value = "encrypted_new_token"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "accessToken": "new_access_token",
            "expiresIn": 3600,
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await service.refresh_token_async(mock_account)

        assert result is True

    @pytest.mark.asyncio
    async def test_refresh_token_async_no_refresh_token(self, service, mock_account):
        """Test async refresh returns False when no refresh token."""
        mock_account.refresh_token = None

        result = await service.refresh_token_async(mock_account)

        assert result is False


class TestFactoryFunction:
    """Test the factory function."""

    def test_get_tradovate_token_service_returns_instance(self):
        """Test that factory function returns TradovateTokenService instance."""
        mock_db = MagicMock()

        result = get_tradovate_token_service(mock_db)

        assert isinstance(result, TradovateTokenService)
        assert result.db is mock_db
