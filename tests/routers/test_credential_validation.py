"""Tests for service-specific credential data validation.

Covers CredentialManager.validate_credential_data, which performs structural
validation of a decrypted credential payload against the requirements of its
credential type.
"""
import pytest

from app.routers.credential_router import CredentialManager


@pytest.fixture
def manager() -> CredentialManager:
    # validate_credential_data does not touch the repository, so None is fine.
    return CredentialManager(repository=None)


class TestValidateCredentialData:
    """Structural validation per credential type."""

    def test_api_key_valid(self, manager):
        assert manager.validate_credential_data("api_key", {"api_key": "abc123"}) == []

    def test_api_key_accepts_aliases(self, manager):
        assert manager.validate_credential_data("api_key", {"key": "abc123"}) == []
        assert manager.validate_credential_data("api_key", {"apiKey": "abc123"}) == []

    def test_api_key_missing_returns_error(self, manager):
        errors = manager.validate_credential_data("api_key", {"unrelated": "x"})
        assert len(errors) == 1
        assert "api_key" in errors[0]

    def test_password_requires_username_and_password(self, manager):
        assert manager.validate_credential_data(
            "password", {"username": "u", "password": "p"}
        ) == []

    def test_password_accepts_field_aliases(self, manager):
        assert manager.validate_credential_data(
            "password", {"login": "u", "secret": "p"}
        ) == []

    def test_password_missing_password_reports_only_that_group(self, manager):
        errors = manager.validate_credential_data("password", {"username": "u"})
        assert len(errors) == 1
        assert "password" in errors[0]

    def test_password_missing_both_reports_two_errors(self, manager):
        errors = manager.validate_credential_data("password", {"unrelated": "x"})
        assert len(errors) == 2

    def test_token_valid_with_aliases(self, manager):
        assert manager.validate_credential_data("token", {"token": "t"}) == []
        assert manager.validate_credential_data("token", {"access_token": "t"}) == []

    def test_oauth_valid(self, manager):
        assert manager.validate_credential_data("oauth", {"access_token": "t"}) == []

    def test_certificate_valid(self, manager):
        assert manager.validate_credential_data(
            "certificate", {"certificate": "-----BEGIN-----"}
        ) == []

    def test_empty_data_is_invalid(self, manager):
        errors = manager.validate_credential_data("api_key", {})
        assert errors == ["Credential data is empty"]

    def test_non_dict_data_is_invalid(self, manager):
        errors = manager.validate_credential_data("api_key", None)
        assert errors == ["Credential data is empty"]

    def test_blank_value_treated_as_missing(self, manager):
        errors = manager.validate_credential_data("api_key", {"api_key": "   "})
        assert len(errors) == 1
        assert "api_key" in errors[0]

    def test_unknown_type_only_checks_non_emptiness(self, manager):
        # Unconstrained type: any non-empty payload passes.
        assert manager.validate_credential_data("custom_type", {"anything": "x"}) == []
        # But an empty payload still fails.
        assert manager.validate_credential_data("custom_type", {}) == [
            "Credential data is empty"
        ]
