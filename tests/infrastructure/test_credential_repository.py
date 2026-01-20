"""Tests for credential repository."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from cryptography.fernet import Fernet

from app.infrastructure.repositories.credential_repository import CredentialRepository


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_encryption():
    """Mock encryption service."""
    with patch('app.infrastructure.repositories.credential_repository.get_encryption_service') as mock:
        service = MagicMock()
        service.encrypt_dict = MagicMock(return_value="encrypted_data")
        service.decrypt_dict = MagicMock(return_value={"api_key": "secret"})
        mock.return_value = service
        yield service


class TestCredentialRepository:
    """Test credential repository operations."""

    @pytest.mark.asyncio
    async def test_create_encrypts_data(self, mock_session, mock_encryption):
        """Verify create encrypts credential data."""
        repo = CredentialRepository(mock_session)

        await repo.create(
            credential_id="cred-123",
            user_id=1,
            name="Test API Key",
            credential_type="api_key",
            service="tradelocker",
            credential_data={"api_key": "secret123"}
        )

        # Verify encryption was called
        mock_encryption.encrypt_dict.assert_called_once_with({"api_key": "secret123"})
        # Verify session.add was called
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_decrypted_data_updates_access_count(self, mock_session, mock_encryption):
        """Verify get_decrypted_data updates access tracking."""
        # Setup mock credential
        mock_credential = MagicMock()
        mock_credential.encrypted_data = "encrypted_data"
        mock_credential.access_count = 0
        mock_credential.last_accessed = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_credential)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CredentialRepository(mock_session)
        data = await repo.get_decrypted_data("cred-123")

        # Verify decryption was called
        mock_encryption.decrypt_dict.assert_called_once_with("encrypted_data")
        # Verify access count was incremented
        assert mock_credential.access_count == 1
        assert mock_credential.last_accessed is not None

    @pytest.mark.asyncio
    async def test_rotate_re_encrypts_data(self, mock_session, mock_encryption):
        """Verify rotate encrypts new credential data."""
        mock_credential = MagicMock()
        mock_credential.last_rotated = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_credential)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CredentialRepository(mock_session)
        await repo.rotate("cred-123", {"new_api_key": "new_secret"})

        # Verify new data was encrypted
        mock_encryption.encrypt_dict.assert_called_with({"new_api_key": "new_secret"})
        # Verify last_rotated was updated
        assert mock_credential.last_rotated is not None

    @pytest.mark.asyncio
    async def test_list_by_user_filters_correctly(self, mock_session, mock_encryption):
        """Verify list_by_user applies filters correctly."""
        mock_creds = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_creds)))
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CredentialRepository(mock_session)
        credentials = await repo.list_by_user(user_id=1, service="tradelocker", active_only=True)

        # Verify session.execute was called
        mock_session.execute.assert_called_once()
        # Verify correct number of credentials returned
        assert len(credentials) == 2

    @pytest.mark.asyncio
    async def test_delete_removes_credential(self, mock_session, mock_encryption):
        """Verify delete removes credential from database."""
        mock_credential = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_credential)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CredentialRepository(mock_session)
        success = await repo.delete("cred-123")

        # Verify deletion was called
        mock_session.delete.assert_called_once_with(mock_credential)
        assert success is True

    @pytest.mark.asyncio
    async def test_soft_delete_deactivates_credential(self, mock_session, mock_encryption):
        """Verify soft_delete sets is_active to False."""
        mock_credential = MagicMock()
        mock_credential.is_active = True
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_credential)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CredentialRepository(mock_session)
        success = await repo.soft_delete("cred-123")

        # Verify is_active was set to False
        assert mock_credential.is_active is False
        assert success is True
