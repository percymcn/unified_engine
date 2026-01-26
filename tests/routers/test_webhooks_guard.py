"""
Tests for the TradingView guard layer helpers.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.application.dto.signal_dto import ProcessSignalRequest
from app.domain.enums import SignalAction, SignalSource
from app.services.signal_intelligence_guard import GuardDecision
from app.routers.webhooks import evaluate_guard_layer


class DummyGuardResult:
    def __init__(self):
        self.decision = GuardDecision.WARN_MODAL_REQUIRED
        self.modal_data: Dict[str, Any] = {"reason": "test"}
        self.annotations: Dict[str, Any] = {
            "history_tag": "momentum_warning",
            "reason_detail": "detail",
            "warning_type": "guard_warning",
            "guard_rule": "momentum",
            "message": "Manual review required",
        }


class DummyGuard:
    def __init__(self, result):
        self._result = result

    async def evaluate(self, *args, **kwargs):
        return self._result


@pytest.mark.asyncio
async def test_tradingview_guard_returns_pending_confirmation():
    guard_result = DummyGuardResult()
    dummy_guard = DummyGuard(guard_result)

    command = ProcessSignalRequest(
        source=SignalSource.TRADINGVIEW,
        symbol="EURUSD",
        action=SignalAction.BUY,
        volume=Decimal("1.0"),
        price=Decimal("1.12"),
        stop_loss=Decimal("1.10"),
        take_profit=Decimal("1.15"),
        target_account_ids=[],
        comment="test",
        strategy_id="strat-1",
        strategy_name="Strategy",
        raw_payload={"ticker": "EURUSD"},
    )

    with patch("app.services.signal_intelligence_guard.SignalIntelligenceGuard", return_value=dummy_guard):
        result = await evaluate_guard_layer(
            db=Mock(),
            command=command,
            source=SignalSource.TRADINGVIEW,
            action=SignalAction.BUY,
            user_id=1,
            account_ids=[1],
            accounts_by_id={},
            start_time=datetime.utcnow(),
            webhook_id="webhook-1"
        )

    assert result["status"] == "pending_confirmation"
    assert isinstance(result["signal_id"], str)
    assert result["guard_reason"] == "momentum_warning"
    assert result["guard_decision"] == "warn"
