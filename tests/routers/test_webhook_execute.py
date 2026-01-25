"""
Tests for /api/v1/webhook/execute endpoint.

Tests the standardized TradingView webhook execution flow:
1. Valid webhook_key lookup
2. Invalid webhook_key rejection
3. Guard evaluation (execute/skip/warn/pause)
4. Signal and ExecutionLog persistence
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Import the router
from app.routers.webhook_execute import router, TradingViewPayload, ExecuteResponse
from app.db.database import get_db


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock()
    db.query = Mock(return_value=db)
    db.filter = Mock(return_value=db)
    db.first = Mock(return_value=None)
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


@pytest.fixture
def app_with_router(mock_db):
    """Create test app with webhook router and mocked dependencies."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/webhook")

    # Override the database dependency
    app.dependency_overrides[get_db] = lambda: mock_db

    return app


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
    async def test_missing_webhook_key_returns_422(self, app_with_router, mock_db):
        """Test that missing webhook_key returns 422."""
        with patch("app.routers.webhook_execute.get_db", return_value=mock_db):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_router),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/webhook/execute",
                    json={"action": "buy", "symbol": "EURUSD"}
                )
                assert response.status_code == 422
                assert "webhook_key" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_action_returns_422(self, app_with_router, mock_db):
        """Test that invalid action returns 422."""
        with patch("app.routers.webhook_execute.get_db", return_value=mock_db):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_router),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/webhook/execute",
                    json={
                        "webhook_key": "test-key",
                        "action": "invalid",
                        "symbol": "EURUSD"
                    }
                )
                assert response.status_code == 422
                assert "action" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_missing_symbol_returns_422(self, app_with_router, mock_db):
        """Test that missing symbol returns 422."""
        with patch("app.routers.webhook_execute.get_db", return_value=mock_db):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_router),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/webhook/execute",
                    json={
                        "webhook_key": "test-key",
                        "action": "buy"
                    }
                )
                assert response.status_code == 422
                assert "symbol" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_webhook_key_returns_403(self, app_with_router, mock_db, mock_account):
        """Test that invalid webhook_key returns 403."""
        # Mock account not found
        mock_db.first.return_value = None

        with patch("app.routers.webhook_execute.get_db", return_value=mock_db):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_router),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/webhook/execute",
                    json={
                        "webhook_key": "invalid-key",
                        "action": "buy",
                        "symbol": "EURUSD"
                    }
                )
                assert response.status_code == 403
                assert "webhook_key" in response.json()["detail"].lower()


class TestGuardDecisions:
    """Test guard decision handling."""

    @pytest.fixture
    def app_with_account(self, mock_db, mock_account):
        """Create test app with account found."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/webhook")

        # Set up mock to return account
        mock_db.first.return_value = mock_account

        app.dependency_overrides[get_db] = lambda: mock_db
        return app

    @pytest.mark.asyncio
    async def test_guard_skip_returns_rejected(
        self, app_with_account, mock_db, mock_account, mock_container
    ):
        """Test that guard SKIP returns rejected status."""
        from app.services.signal_intelligence_guard import GuardDecision

        mock_guard_result = Mock()
        mock_guard_result.decision = GuardDecision.SKIP
        mock_guard_result.annotations = {"discard_reason": "stale_signal"}
        mock_guard_result.modal_data = None

        with patch("app.routers.webhook_execute.SignalIntelligenceGuard") as MockGuard, \
             patch("app.routers.webhook_execute.get_container", return_value=mock_container):

            guard_instance = Mock()
            guard_instance.evaluate = AsyncMock(return_value=mock_guard_result)
            MockGuard.return_value = guard_instance

            async with AsyncClient(
                transport=ASGITransport(app=app_with_account),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/webhook/execute",
                    json={
                        "webhook_key": "test-key",
                        "action": "buy",
                        "symbol": "EURUSD"
                    }
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "rejected"
                assert data["guard_decision"] == "skip"
                assert data["success"] is False

    @pytest.mark.asyncio
    async def test_guard_warn_returns_awaiting_confirmation(
        self, app_with_account, mock_db, mock_account, mock_container
    ):
        """Test that guard WARN returns awaiting_confirmation status."""
        from app.services.signal_intelligence_guard import GuardDecision

        mock_guard_result = Mock()
        mock_guard_result.decision = GuardDecision.WARN_MODAL_REQUIRED
        mock_guard_result.annotations = {"history_tag": "momentum_warning"}
        mock_guard_result.modal_data = {"warning_type": "momentum"}

        with patch("app.routers.webhook_execute.SignalIntelligenceGuard") as MockGuard, \
             patch("app.routers.webhook_execute.get_container", return_value=mock_container):

            guard_instance = Mock()
            guard_instance.evaluate = AsyncMock(return_value=mock_guard_result)
            MockGuard.return_value = guard_instance

            async with AsyncClient(
                transport=ASGITransport(app=app_with_account),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/webhook/execute",
                    json={
                        "webhook_key": "test-key",
                        "action": "buy",
                        "symbol": "EURUSD"
                    }
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "awaiting_confirmation"
                assert data["guard_decision"] == "warn"
                assert data["modal_data"] is not None


class TestExecutionFlow:
    """Test full execution flow."""

    @pytest.fixture
    def app_with_account(self, mock_db, mock_account):
        """Create test app with account found."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/webhook")

        # Set up mock to return account
        mock_db.first.return_value = mock_account

        app.dependency_overrides[get_db] = lambda: mock_db
        return app

    @pytest.mark.asyncio
    async def test_successful_execution(
        self, app_with_account, mock_db, mock_account, mock_container
    ):
        """Test successful signal execution."""
        from app.services.signal_intelligence_guard import GuardDecision

        mock_guard_result = Mock()
        mock_guard_result.decision = GuardDecision.EXECUTE
        mock_guard_result.annotations = {}
        mock_guard_result.modal_data = None

        with patch("app.routers.webhook_execute.SignalIntelligenceGuard") as MockGuard, \
             patch("app.routers.webhook_execute.get_container", return_value=mock_container):

            guard_instance = Mock()
            guard_instance.evaluate = AsyncMock(return_value=mock_guard_result)
            MockGuard.return_value = guard_instance

            async with AsyncClient(
                transport=ASGITransport(app=app_with_account),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/webhook/execute",
                    json={
                        "webhook_key": "test-key",
                        "action": "buy",
                        "symbol": "EURUSD",
                        "quantity": 0.1,
                        "sl": 1.0800,
                        "tp": 1.0900
                    }
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["status"] == "executed"
                assert data["guard_decision"] == "execute"
                assert data["account_id"] == 1
                assert data["broker"] == "projectx"


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
