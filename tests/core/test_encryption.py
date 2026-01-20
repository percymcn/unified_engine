"""Tests for encryption service."""
import pytest
import os
from unittest.mock import patch
from cryptography.fernet import Fernet


class TestEncryptionService:
    """Test encryption service initialization and operations."""

    def test_missing_key_raises_error(self):
        """Verify service fails fast when key is missing."""
        # Clear any cached instance
        from app.core import encryption
        encryption.EncryptionService._instance = None

        with patch.object(encryption.settings, 'CREDENTIAL_ENCRYPTION_KEY', ''):
            with pytest.raises(encryption.EncryptionKeyMissingError) as exc:
                encryption.EncryptionService()

            assert "CREDENTIAL_ENCRYPTION_KEY" in str(exc.value)
            assert "required" in str(exc.value).lower()

    def test_invalid_key_raises_error(self):
        """Verify service fails fast when key is invalid."""
        from app.core import encryption
        encryption.EncryptionService._instance = None

        with patch.object(encryption.settings, 'CREDENTIAL_ENCRYPTION_KEY', 'not-a-valid-key'):
            with pytest.raises(encryption.EncryptionKeyMissingError) as exc:
                encryption.EncryptionService()

            assert "Invalid" in str(exc.value)

    def test_valid_key_initializes_successfully(self):
        """Verify service initializes with valid Fernet key."""
        from app.core import encryption
        encryption.EncryptionService._instance = None

        valid_key = Fernet.generate_key().decode()

        with patch.object(encryption.settings, 'CREDENTIAL_ENCRYPTION_KEY', valid_key):
            service = encryption.EncryptionService()
            assert service._cipher is not None

    def test_encrypt_decrypt_roundtrip(self):
        """Verify encrypt/decrypt returns original data."""
        from app.core import encryption
        encryption.EncryptionService._instance = None

        valid_key = Fernet.generate_key().decode()

        with patch.object(encryption.settings, 'CREDENTIAL_ENCRYPTION_KEY', valid_key):
            service = encryption.EncryptionService()

            original = "sensitive-api-key-12345"
            encrypted = service.encrypt(original)
            decrypted = service.decrypt(encrypted)

            assert decrypted == original
            assert encrypted != original  # Ensure it was actually encrypted

    def test_encrypt_decrypt_dict_roundtrip(self):
        """Verify dict encryption returns original data."""
        from app.core import encryption
        encryption.EncryptionService._instance = None

        valid_key = Fernet.generate_key().decode()

        with patch.object(encryption.settings, 'CREDENTIAL_ENCRYPTION_KEY', valid_key):
            service = encryption.EncryptionService()

            original = {"api_key": "secret123", "password": "hunter2"}
            encrypted = service.encrypt_dict(original)
            decrypted = service.decrypt_dict(encrypted)

            assert decrypted == original

    def test_wrong_key_fails_decryption(self):
        """Verify decryption fails with wrong key."""
        from app.core import encryption

        # Encrypt with key 1
        encryption.EncryptionService._instance = None
        key1 = Fernet.generate_key().decode()
        with patch.object(encryption.settings, 'CREDENTIAL_ENCRYPTION_KEY', key1):
            service1 = encryption.EncryptionService()
            encrypted = service1.encrypt("secret")

        # Try to decrypt with key 2
        encryption.EncryptionService._instance = None
        key2 = Fernet.generate_key().decode()
        with patch.object(encryption.settings, 'CREDENTIAL_ENCRYPTION_KEY', key2):
            service2 = encryption.EncryptionService()

            with pytest.raises(encryption.EncryptionError) as exc:
                service2.decrypt(encrypted)

            assert "invalid token" in str(exc.value).lower()
