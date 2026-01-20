"""Tests for API key bcrypt hashing."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from app.routers.api_keys import hash_api_key, generate_api_key, pwd_context


class TestApiKeyHashing:
    """Test API key hashing with bcrypt."""

    def test_hash_api_key_uses_bcrypt(self):
        """Verify hash_api_key produces bcrypt hash."""
        api_key = generate_api_key()
        hashed = hash_api_key(api_key)

        # Bcrypt hashes start with $2b$ (or $2a$, $2y$)
        assert hashed.startswith("$2")
        # Bcrypt hashes are 60 characters
        assert len(hashed) == 60

    def test_hash_api_key_produces_unique_hashes(self):
        """Verify same key produces different hashes (due to salt)."""
        api_key = generate_api_key()

        hash1 = hash_api_key(api_key)
        hash2 = hash_api_key(api_key)

        # Bcrypt produces different hashes for same input due to random salt
        assert hash1 != hash2

    def test_hash_can_be_verified(self):
        """Verify hashed key can be verified with pwd_context."""
        api_key = generate_api_key()
        hashed = hash_api_key(api_key)

        # Verification should succeed
        assert pwd_context.verify(api_key, hashed) is True

        # Wrong key should fail
        assert pwd_context.verify("wrong_key", hashed) is False

    def test_generate_api_key_format(self):
        """Verify generated API key format."""
        api_key = generate_api_key()

        # Should start with prefix
        assert api_key.startswith("ue_")
        # Should be reasonably long (prefix + 43 chars from secrets.token_urlsafe(32))
        assert len(api_key) > 40

    def test_sha256_hash_not_used(self):
        """Verify SHA256 is not used (would produce 64-char hex string)."""
        api_key = generate_api_key()
        hashed = hash_api_key(api_key)

        # SHA256 produces 64-char hex, bcrypt produces 60-char hash
        assert len(hashed) != 64
        # SHA256 hex contains only 0-9a-f, bcrypt contains special chars
        assert "$" in hashed
