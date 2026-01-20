"""Tests for OAuth token encryption."""
import pytest
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet

from app.services.oauth_service import OAuthService


@pytest.fixture
def mock_encryption():
    """Mock encryption service with valid key."""
    valid_key = Fernet.generate_key().decode()

    with patch('app.services.oauth_service.encrypt') as mock_encrypt, \
         patch('app.services.oauth_service.decrypt') as mock_decrypt:

        # Make encrypt return a different string (simulating encryption)
        mock_encrypt.side_effect = lambda x: f"encrypted_{x}"
        mock_decrypt.side_effect = lambda x: x.replace("encrypted_", "")

        yield mock_encrypt, mock_decrypt


class TestOAuthEncryption:
    """Test OAuth token encryption."""

    def test_encrypt_token_encrypts_value(self, mock_encryption):
        """Verify _encrypt_token calls encryption service."""
        mock_encrypt, _ = mock_encryption

        result = OAuthService._encrypt_token("test_access_token")

        mock_encrypt.assert_called_once_with("test_access_token")
        assert result == "encrypted_test_access_token"

    def test_encrypt_token_handles_empty(self, mock_encryption):
        """Verify _encrypt_token handles empty tokens."""
        result = OAuthService._encrypt_token("")
        assert result == ""

        result = OAuthService._encrypt_token(None)
        assert result is None

    def test_decrypt_token_decrypts_value(self, mock_encryption):
        """Verify _decrypt_token calls decryption service."""
        _, mock_decrypt = mock_encryption

        result = OAuthService._decrypt_token("encrypted_test_token")

        mock_decrypt.assert_called_once_with("encrypted_test_token")
        assert result == "test_token"

    def test_get_decrypted_tokens_returns_both(self, mock_encryption):
        """Verify get_decrypted_tokens returns both tokens."""
        mock_oauth_account = MagicMock()
        mock_oauth_account.access_token = "encrypted_access"
        mock_oauth_account.refresh_token = "encrypted_refresh"

        access, refresh = OAuthService.get_decrypted_tokens(mock_oauth_account)

        assert access == "access"
        assert refresh == "refresh"

    def test_get_decrypted_tokens_handles_no_refresh(self, mock_encryption):
        """Verify get_decrypted_tokens handles missing refresh token."""
        mock_oauth_account = MagicMock()
        mock_oauth_account.access_token = "encrypted_access"
        mock_oauth_account.refresh_token = None

        access, refresh = OAuthService.get_decrypted_tokens(mock_oauth_account)

        assert access == "access"
        assert refresh is None
