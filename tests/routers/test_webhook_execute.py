"""
Tests for /api/v1/webhook/execute endpoint.

Tests the standardized TradingView webhook execution flow:
1. Valid webhook_key lookup
2. Invalid webhook_key rejection
3. Guard evaluation (execute/skip/warn/pause)
4. Signal and ExecutionLog persistence
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json
import uuid
from types import SimpleNamespace

from fastapi import HTTPException

from app.routers.webhook_execute import (
    TradingViewPayload,
    ExecuteResponse,
    execute_tradingview_signal,
)


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock()
    db.query = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def mock_account():
    """Mock TradingAccount with proper broker enum."""
    account = Mock()
    account.id = 1
    account.user_id = 2
    # Mock broker as an enum with .value
    broker_mock = Mock()
    broker_mock.value = "projectx"
    account.broker = broker_mock
    account.webhook_key = "test-webhook-key"
    account.is_active = True
    account.margin = 1000.0
    return account


@pytest.fixture
def mock_container():
    """Mock DI container."""
    container = Mock()
    use_case = AsyncMock()
    use_case.execute = AsyncMock(return_value=Mock(
        signal_id="1",
        status=Mock(value="executed"),
        executions=1,
        errors=[]
    ))
    container.process_signal_use_case = Mock(return_value=use_case)
    return container


class FakeRequest:
    """Minimal request stub for webhook_execute tests."""
    def __init__(self, payload):
        self._payload = payload
        self.client = SimpleNamespace(host="test-client")
        self.headers = {"user-agent": "pytest"}

    async def json(self):
        return self._payload


class TestTradingViewPayload:
    """Test payload validation."""

    def test_valid_payload(self):
        """Test valid TradingView payload."""
        payload = TradingViewPayload(
            webhook_key="test-key",
            action="buy",
            symbol="EURUSD",
            quantity=0.1,
            sl=1.0800,
            tp=1.0900
        )
        assert payload.webhook_key == "test-key"
        assert payload.action == "buy"
        assert payload.symbol == "EURUSD"
        assert payload.quantity == 0.1

    def test_minimal_payload(self):
        """Test minimal valid payload (only required fields)."""
        payload = TradingViewPayload(
            webhook_key="test-key",
            action="sell",
            symbol="GBPUSD"
        )
        assert payload.quantity == 0.01  # Default
        assert payload.sl is None
        assert payload.tp is None

    def test_close_action(self):
        """Test close action payload."""
        payload = TradingViewPayload(
            webhook_key="test-key",
            action="close",
            symbol="USDJPY"
        )
        assert payload.action == "close"


class TestWebhookExecuteEndpoint:
    """Test webhook/execute endpoint behavior."""

    @pytest.mark.asyncio
    async def test_missing_webhook_key_returns_422(self, mock_db):
        """Test that missing webhook_key returns 422."""
        request = FakeRequest({"action": "buy", "symbol": "EURUSD"})
        with pytest.raises(HTTPException) as exc_info:
            await execute_tradingview_signal(request=request, db=mock_db)
        assert exc_info.value.status_code == 422
        assert "webhook_key" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_invalid_action_returns_422(self, mock_db):
        """Test that invalid action returns 422."""
        request = FakeRequest({
            "webhook_key": "test-key",
            "action": "invalid",
            "symbol": "EURUSD",
        })
        with pytest.raises(HTTPException) as exc_info:
            await execute_tradingview_signal(request=request, db=mock_db)
        assert exc_info.value.status_code == 422
        assert "action" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_missing_symbol_returns_422(self, mock_db):
        """Test that missing symbol returns 422."""
        request = FakeRequest({
            "webhook_key": "test-key",
            "action": "buy",
        })
        with pytest.raises(HTTPException) as exc_info:
            await execute_tradingview_signal(request=request, db=mock_db)
        assert exc_info.value.status_code == 422
        assert "symbol" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_invalid_webhook_key_returns_403(self, mock_db, mock_account):
        """Test that invalid webhook_key returns 403."""
        query = Mock()
        mock_db.query.return_value = query
        query.filter.return_value = query
        query.first.return_value = None

        request = FakeRequest({
            "webhook_key": "invalid-key",
            "action": "buy",
            "symbol": "EURUSD",
        })
        with pytest.raises(HTTPException) as exc_info:
            await execute_tradingview_signal(request=request, db=mock_db)
        assert exc_info.value.status_code == 403
        assert "webhook_key" in str(exc_info.value.detail).lower()


class TestGuardDecisions:
    """Test guard decision handling."""

    @pytest.mark.asyncio
    async def test_guard_skip_returns_rejected(
        self, mock_db, mock_account, mock_container
    ):
        """Test that guard SKIP returns rejected status."""
        from app.services.signal_intelligence_guard import GuardDecision

        mock_guard_result = Mock()
        mock_guard_result.decision = GuardDecision.SKIP
        mock_guard_result.annotations = {"discard_reason": "stale_signal"}
        mock_guard_result.modal_data = None

        account_query = Mock()
        account_query.filter.return_value = account_query
        account_query.first.return_value = mock_account

        def query_side_effect(model):
            return account_query

        mock_db.query.side_effect = query_side_effect

        with patch("app.routers.webhook_execute.SignalIntelligenceGuard") as MockGuard, \
             patch("app.routers.webhook_execute.get_container", return_value=mock_container):

            guard_instance = Mock()
            guard_instance.evaluate = AsyncMock(return_value=mock_guard_result)
            MockGuard.return_value = guard_instance

            response = await execute_tradingview_signal(
                request=FakeRequest({
                    "webhook_key": "test-key",
                    "action": "buy",
                    "symbol": "EURUSD",
                }),
                db=mock_db,
            )

            assert response.status == "rejected"
            assert response.guard_decision == "skip"
            assert response.success is False

    @pytest.mark.asyncio
    async def test_guard_warn_returns_pending_confirmation(
        self, mock_db, mock_account, mock_container
    ):
        """Test that guard WARN returns pending_confirmation status."""
        from app.services.signal_intelligence_guard import GuardDecision
        from app.models.models import Signal as SignalORM

        mock_guard_result = Mock()
        mock_guard_result.decision = GuardDecision.WARN_MODAL_REQUIRED
        mock_guard_result.annotations = {"history_tag": "momentum_warning"}
        mock_guard_result.modal_data = {"warning_type": "momentum"}

        account_query = Mock()
        account_query.filter.return_value = account_query
        account_query.first.return_value = mock_account
        signal_query = Mock()
        signal_query.filter.return_value = signal_query
        signal_query.first.return_value = None

        def query_side_effect(model):
            if model.__name__ == "TradingAccount":
                return account_query
            if model.__name__ == "Signal":
                return signal_query
            return Mock()

        mock_db.query.side_effect = query_side_effect

        with patch("app.routers.webhook_execute.SignalIntelligenceGuard") as MockGuard, \
             patch("app.routers.webhook_execute.get_container", return_value=mock_container):

            guard_instance = Mock()
            guard_instance.evaluate = AsyncMock(return_value=mock_guard_result)
            MockGuard.return_value = guard_instance

            response = await execute_tradingview_signal(
                request=FakeRequest({
                    "webhook_key": "test-key",
                    "action": "buy",
                    "symbol": "EURUSD",
                }),
                db=mock_db,
            )

            assert response.status == "pending_confirmation"
            assert response.guard_decision == "warn"
            assert response.modal_data is not None
            assert any(
                isinstance(call.args[0], SignalORM)
                for call in mock_db.add.call_args_list
                if call.args
            )


class TestExecutionFlow:
    """Test full execution flow."""

    @pytest.mark.asyncio
    async def test_successful_execution(
        self, mock_db, mock_account, mock_container
    ):
        """Test successful signal execution."""
        from app.services.signal_intelligence_guard import GuardDecision

        mock_guard_result = Mock()
        mock_guard_result.decision = GuardDecision.EXECUTE
        mock_guard_result.annotations = {}
        mock_guard_result.modal_data = None

        account_query = Mock()
        account_query.filter.return_value = account_query
        account_query.first.return_value = mock_account

        def query_side_effect(model):
            return account_query

        mock_db.query.side_effect = query_side_effect

        with patch("app.routers.webhook_execute.SignalIntelligenceGuard") as MockGuard, \
             patch("app.routers.webhook_execute.get_container", return_value=mock_container):

            guard_instance = Mock()
            guard_instance.evaluate = AsyncMock(return_value=mock_guard_result)
            MockGuard.return_value = guard_instance

            response = await execute_tradingview_signal(
                request=FakeRequest({
                    "webhook_key": "test-key",
                    "action": "buy",
                    "symbol": "EURUSD",
                    "quantity": 0.1,
                    "sl": 1.0800,
                    "tp": 1.0900,
                }),
                db=mock_db,
            )

            assert response.success is True
            assert response.status == "executed"
            assert response.guard_decision == "execute"
            assert response.account_id == 1
            assert response.broker == "projectx"


class TestResponseSchema:
    """Test response schema validation."""

    def test_execute_response_model(self):
        """Test ExecuteResponse model."""
        response = ExecuteResponse(
            success=True,
            signal_id="123",
            status="executed",
            webhook_id="uuid-1234",
            account_id=1,
            broker="projectx",
            errors=[],
            guard_decision="execute",
            guard_reason=None,
            modal_data=None,
            processing_time_ms=100
        )

        assert response.success is True
        assert response.signal_id == "123"
        assert response.status == "executed"
        assert response.processing_time_ms == 100

    def test_execute_response_with_errors(self):
        """Test ExecuteResponse with errors."""
        response = ExecuteResponse(
            success=False,
            signal_id="456",
            status="failed",
            webhook_id="uuid-5678",
            errors=["Broker connection failed", "Timeout"]
        )

        assert response.success is False
        assert len(response.errors) == 2
        assert "Broker connection failed" in response.errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
