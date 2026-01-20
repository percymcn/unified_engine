"""
Centralized Encryption Service

Provides secure encryption/decryption for sensitive data using Fernet.
Requires CREDENTIAL_ENCRYPTION_KEY environment variable.
"""
import base64
import json
import logging
from typing import Any, Dict
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""
    pass


class EncryptionKeyMissingError(Exception):
    """Raised when encryption key is not configured."""
    pass


class EncryptionService:
    """
    Centralized encryption service for credential storage.

    Uses Fernet symmetric encryption (AES-128-CBC with HMAC).
    Key must be 32 bytes, URL-safe base64 encoded.
    """

    _instance = None
    _cipher = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize the cipher with the encryption key."""
        key = settings.CREDENTIAL_ENCRYPTION_KEY

        if not key:
            raise EncryptionKeyMissingError(
                "CREDENTIAL_ENCRYPTION_KEY environment variable is required. "
                "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )

        try:
            # Validate key format (must be 32 bytes, URL-safe base64)
            key_bytes = key.encode() if isinstance(key, str) else key
            decoded = base64.urlsafe_b64decode(key_bytes)
            if len(decoded) != 32:
                raise ValueError(f"Key must be 32 bytes, got {len(decoded)}")

            self._cipher = Fernet(key_bytes)
            logger.info("Encryption service initialized successfully")

        except Exception as e:
            raise EncryptionKeyMissingError(
                f"Invalid CREDENTIAL_ENCRYPTION_KEY: {e}. "
                "Key must be 32 bytes, URL-safe base64 encoded. "
                "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )

    def encrypt(self, data: str) -> str:
        """
        Encrypt a string value.

        Args:
            data: Plain text string to encrypt

        Returns:
            Encrypted string (base64 encoded)

        Raises:
            EncryptionError: If encryption fails
        """
        if not self._cipher:
            raise EncryptionError("Encryption service not initialized")

        try:
            encrypted = self._cipher.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt data: {e}")

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt an encrypted string value.

        Args:
            encrypted_data: Encrypted string (base64 encoded)

        Returns:
            Decrypted plain text string

        Raises:
            EncryptionError: If decryption fails (invalid token or wrong key)
        """
        if not self._cipher:
            raise EncryptionError("Encryption service not initialized")

        try:
            decrypted = self._cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except InvalidToken:
            logger.error("Decryption failed: invalid token (wrong key or corrupted data)")
            raise EncryptionError("Failed to decrypt: invalid token or wrong encryption key")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Failed to decrypt data: {e}")

    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """
        Encrypt a dictionary (JSON serializable).

        Args:
            data: Dictionary to encrypt

        Returns:
            Encrypted string
        """
        json_data = json.dumps(data)
        return self.encrypt(json_data)

    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt to a dictionary.

        Args:
            encrypted_data: Encrypted string

        Returns:
            Decrypted dictionary
        """
        json_data = self.decrypt(encrypted_data)
        return json.loads(json_data)


def get_encryption_service() -> EncryptionService:
    """Get the singleton encryption service instance."""
    return EncryptionService()


# Convenience functions
def encrypt(data: str) -> str:
    """Encrypt a string."""
    return get_encryption_service().encrypt(data)


def decrypt(encrypted_data: str) -> str:
    """Decrypt an encrypted string."""
    return get_encryption_service().decrypt(encrypted_data)


def encrypt_dict(data: Dict[str, Any]) -> str:
    """Encrypt a dictionary."""
    return get_encryption_service().encrypt_dict(data)


def decrypt_dict(encrypted_data: str) -> Dict[str, Any]:
    """Decrypt to dictionary."""
    return get_encryption_service().decrypt_dict(encrypted_data)
