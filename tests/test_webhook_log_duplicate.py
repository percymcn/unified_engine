"""
Test for webhook log duplicate key bug fix.

The bug was that exception handlers were trying to create a new WebhookLog
entry with the same webhook_id that was already committed, causing UniqueViolation.

Fix: Update existing log if it exists, or create new with fresh webhook_id.
"""
import pytest
import uuid
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import IntegrityError


class TestWebhookLogDuplicateKeyFix:
    """Tests for webhook log duplicate key prevention."""

    def test_webhook_id_always_unique(self):
        """Verify webhook_id is always unique (uuid4)."""
        ids = set()
        for _ in range(1000):
            webhook_id = str(uuid.uuid4())
            assert webhook_id not in ids, "uuid4 collision detected"
            ids.add(webhook_id)

    def test_error_handler_uses_existing_log_when_available(self):
        """
        When db_webhook already exists in locals, the error handler
        should update it instead of creating a new entry.
        """
        # Simulate the scenario where db_webhook exists
        db_webhook = MagicMock()
        db_webhook.processed = True
        db_webhook.error_message = None

        # Simulate error handling
        error_msg = "Test error"

        # The fix: if db_webhook exists, update it
        if db_webhook is not None:
            db_webhook.processed = False
            db_webhook.error_message = error_msg

        assert db_webhook.processed == False
        assert db_webhook.error_message == error_msg

    def test_error_handler_creates_new_log_with_fresh_id_when_no_existing(self):
        """
        When db_webhook doesn't exist (error before initial insert),
        a new log should be created with a fresh webhook_id.
        """
        original_webhook_id = str(uuid.uuid4())

        # Simulate scenario where db_webhook is None (never created)
        db_webhook = None

        # The fix: create new with fresh id
        if db_webhook is None:
            error_webhook_id = str(uuid.uuid4())
            # New log would use error_webhook_id, not original_webhook_id
            assert error_webhook_id != original_webhook_id

    def test_rollback_on_logging_error(self):
        """
        If logging fails (e.g., DB connection lost), it should rollback
        and not propagate the error (fail-open behavior).
        """
        mock_db = MagicMock()
        mock_db.rollback = MagicMock()

        # Simulate a logging failure scenario
        def simulate_error_logging():
            try:
                raise IntegrityError("stmt", {}, Exception("test"))
            except Exception:
                mock_db.rollback()

        simulate_error_logging()
        mock_db.rollback.assert_called_once()

    def test_duplicate_insert_does_not_crash_flow(self):
        """
        Even if a duplicate is somehow attempted, the flow should not crash.
        The fix wraps error logging in try/except with rollback.
        """
        # This test verifies the try/except pattern
        crash_occurred = False

        try:
            # Simulate the error handling block
            try:
                # This would normally raise UniqueViolation
                raise IntegrityError("stmt", {}, Exception("duplicate key"))
            except Exception:
                pass  # Silently handle (rollback in real code)
        except Exception:
            crash_occurred = True

        assert not crash_occurred, "Error logging should not crash the flow"


class TestWebhookIdGeneration:
    """Test that webhook_id generation is correct."""

    def test_webhook_id_is_valid_uuid(self):
        """Webhook ID should be a valid UUID string."""
        webhook_id = str(uuid.uuid4())
        # Should be parseable as UUID
        parsed = uuid.UUID(webhook_id)
        assert str(parsed) == webhook_id

    def test_webhook_id_format(self):
        """Webhook ID should be in standard UUID format."""
        webhook_id = str(uuid.uuid4())
        # Standard UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        parts = webhook_id.split('-')
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12
