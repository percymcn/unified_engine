"""
Tests for Signal Intelligence Guard Layer

Tests cover:
- Staleness skip logic
- Momentum counter increments + warn trigger
- Chop detection
- Exposure guard freeze
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from app.services.signal_intelligence_guard import (
    SignalIntelligenceGuard,
    GuardDecision,
    GuardResult
)
from app.domain.entities.signal import Signal
from app.domain.value_objects import SignalId, Symbol, Volume, Price
from app.domain.enums import SignalAction, SignalSource
from app.models.database_models import MomentumSettings, SignalCounter


@pytest.fixture
def mock_db():
    """Create mock database session"""
    db = Mock(spec=Session)
    db.query = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    return db


@pytest.fixture
def default_settings():
    """Default momentum settings"""
    settings = Mock(spec=MomentumSettings)
    settings.warn_at = 6
    settings.auto_breakeven = False
    settings.pause_on_chop = True
    settings.max_exposure = 5000.0
    settings.auto_pause_on_exposure = True
    settings.allow_hedge = False
    settings.staleness_enabled = True
    settings.staleness_seconds = 5
    settings.force_old_signals = False
    settings.discard_flush_interval = "24h"
    return settings


@pytest.fixture
def test_signal():
    """Create test signal entity"""
    return Signal(
        id=SignalId("test-signal-123"),
        source=SignalSource.TRADINGVIEW,
        symbol=Symbol("EURUSD"),
        action=SignalAction.BUY,
        volume=Volume(Decimal("0.01")),
        price=Price(Decimal("1.1000")),
        stop_loss=None,
        take_profit=None,
        target_accounts=[],
        comment="Test signal",
        strategy_id="test_strategy",
        strategy_name="Test Strategy",
        raw_payload={"ticker": "EURUSD", "action": "buy", "timestamp": datetime.utcnow().isoformat()}
    )


class TestStalenessGuard:
    """Test sg-002: Time-Lock & Staleness"""

    @pytest.mark.asyncio
    async def test_fresh_signal_passes(self, mock_db, default_settings, test_signal):
        """Fresh signal should pass staleness check"""
        guard = SignalIntelligenceGuard(mock_db)
        guard._get_momentum_settings = Mock(return_value=default_settings)
        
        # Signal with recent timestamp
        test_signal.raw_payload = {
            "ticker": "EURUSD",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        result = await guard._check_staleness(test_signal, default_settings, user_id=1)
        assert result.decision == GuardDecision.EXECUTE

    @pytest.mark.asyncio
    async def test_stale_signal_skipped(self, mock_db, default_settings, test_signal):
        """Stale signal should be skipped"""
        guard = SignalIntelligenceGuard(mock_db)
        guard._get_momentum_settings = Mock(return_value=default_settings)
        guard._discard_signal = AsyncMock()
        
        # Signal with old timestamp (10 seconds ago)
        old_time = (datetime.utcnow() - timedelta(seconds=10)).isoformat()
        test_signal.raw_payload = {
            "ticker": "EURUSD",
            "timestamp": old_time
        }
        
        result = await guard._check_staleness(test_signal, default_settings, user_id=1)
        assert result.decision == GuardDecision.SKIP
        assert result.annotations["discard_reason"] == "stale"
        guard._discard_signal.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_old_signals_bypasses(self, mock_db, default_settings, test_signal):
        """force_old_signals should bypass staleness check"""
        default_settings.force_old_signals = True
        
        guard = SignalIntelligenceGuard(mock_db)
        guard._get_momentum_settings = Mock(return_value=default_settings)
        
        # Even with old timestamp
        old_time = (datetime.utcnow() - timedelta(seconds=10)).isoformat()
        test_signal.raw_payload = {"timestamp": old_time}
        
        result = await guard._check_staleness(test_signal, default_settings, user_id=1)
        assert result.decision == GuardDecision.EXECUTE


class TestMomentumGuard:
    """Test sg-001: Signal Momentum Guard"""

    @pytest.mark.asyncio
    async def test_first_signal_sets_bias(self, mock_db, default_settings, test_signal):
        """First signal should set bias"""
        guard = SignalIntelligenceGuard(mock_db)
        guard._get_momentum_settings = Mock(return_value=default_settings)
        
        # No existing counter
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = await guard._check_momentum(
            test_signal, default_settings, user_id=1, session_key="1:EURUSD:test"
        )
        
        assert result.decision == GuardDecision.EXECUTE
        assert mock_db.add.called  # Counter should be created

    @pytest.mark.asyncio
    async def test_same_direction_resets_momentum(self, mock_db, default_settings, test_signal):
        """Same direction signal should reset opposite momentum"""
        guard = SignalIntelligenceGuard(mock_db)
        guard._get_momentum_settings = Mock(return_value=default_settings)
        
        # Existing counter with same bias
        counter = Mock(spec=SignalCounter)
        counter.current_bias = "buy"
        counter.opposite_momentum = 3
        counter.last8_pattern = "BBB"
        counter.chop_mode = False
        mock_db.query.return_value.filter.return_value.first.return_value = counter
        
        result = await guard._check_momentum(
            test_signal, default_settings, user_id=1, session_key="1:EURUSD:test"
        )
        
        assert result.decision == GuardDecision.EXECUTE
        assert counter.opposite_momentum == 0  # Should be reset

    @pytest.mark.asyncio
    async def test_opposite_direction_increments(self, mock_db, default_settings, test_signal):
        """Opposite direction should increment counter"""
        guard = SignalIntelligenceGuard(mock_db)
        guard._get_momentum_settings = Mock(return_value=default_settings)
        
        # Existing counter with different bias
        counter = Mock(spec=SignalCounter)
        counter.current_bias = "sell"
        counter.opposite_momentum = 2
        counter.last8_pattern = "SSS"
        counter.chop_mode = False
        mock_db.query.return_value.filter.return_value.first.return_value = counter
        
        result = await guard._check_momentum(
            test_signal, default_settings, user_id=1, session_key="1:EURUSD:test"
        )
        
        assert result.decision == GuardDecision.EXECUTE
        assert counter.opposite_momentum == 3  # Should increment

    @pytest.mark.asyncio
    async def test_warn_threshold_triggers_modal(self, mock_db, default_settings, test_signal):
        """When opposite_momentum >= warn_at, should trigger warning modal"""
        default_settings.warn_at = 6
        
        guard = SignalIntelligenceGuard(mock_db)
        guard._get_momentum_settings = Mock(return_value=default_settings)
        
        # Counter at threshold
        counter = Mock(spec=SignalCounter)
        counter.current_bias = "sell"
        counter.opposite_momentum = 5  # One more will hit threshold
        counter.last8_pattern = "SSSSS"
        counter.chop_mode = False
        mock_db.query.return_value.filter.return_value.first.return_value = counter
        
        result = await guard._check_momentum(
            test_signal, default_settings, user_id=1, session_key="1:EURUSD:test"
        )
        
        assert result.decision == GuardDecision.WARN_MODAL_REQUIRED
        assert result.modal_data is not None
        assert result.modal_data["type"] == "momentum_warning"

    @pytest.mark.asyncio
    async def test_chop_detection_triggers_pause(self, mock_db, default_settings, test_signal):
        """Chop mode should trigger PAUSE_NEW_ENTRIES"""
        guard = SignalIntelligenceGuard(mock_db)
        guard._get_momentum_settings = Mock(return_value=default_settings)
        
        # Counter with choppy pattern
        counter = Mock(spec=SignalCounter)
        counter.current_bias = "buy"
        counter.opposite_momentum = 2
        counter.last8_pattern = "BSBSBSBS"  # Alternating pattern
        counter.chop_mode = True
        mock_db.query.return_value.filter.return_value.first.return_value = counter
        
        result = await guard._check_momentum(
            test_signal, default_settings, user_id=1, session_key="1:EURUSD:test"
        )
        
        assert result.decision == GuardDecision.PAUSE_NEW_ENTRIES
        assert result.annotations["chop_mode"] is True


class TestExposureGuard:
    """Test sg-004: Max Exposure Guard"""

    @pytest.mark.asyncio
    async def test_exposure_below_limit_passes(self, mock_db, default_settings, test_signal):
        """Exposure below limit should pass"""
        guard = SignalIntelligenceGuard(mock_db)
        guard._get_momentum_settings = Mock(return_value=default_settings)
        
        open_positions_summary = {
            1: {"total_margin": 3000.0, "positions_count": 2}
        }
        
        result = await guard._check_exposure(
            test_signal, default_settings, account_ids=[1], open_positions_summary=open_positions_summary
        )
        
        assert result.decision == GuardDecision.EXECUTE

    @pytest.mark.asyncio
    async def test_exposure_above_limit_pauses(self, mock_db, default_settings, test_signal):
        """Exposure above limit should pause new entries"""
        guard = SignalIntelligenceGuard(mock_db)
        guard._get_momentum_settings = Mock(return_value=default_settings)
        
        open_positions_summary = {
            1: {"total_margin": 6000.0, "positions_count": 5}  # Above 5000 limit
        }
        
        result = await guard._check_exposure(
            test_signal, default_settings, account_ids=[1], open_positions_summary=open_positions_summary
        )
        
        assert result.decision == GuardDecision.PAUSE_NEW_ENTRIES
        assert result.modal_data is not None
        assert result.modal_data["type"] == "exposure_warning"

    @pytest.mark.asyncio
    async def test_auto_pause_disabled_bypasses(self, mock_db, default_settings, test_signal):
        """If auto_pause_on_exposure is false, should bypass"""
        default_settings.auto_pause_on_exposure = False
        
        guard = SignalIntelligenceGuard(mock_db)
        guard._get_momentum_settings = Mock(return_value=default_settings)
        
        open_positions_summary = {
            1: {"total_margin": 6000.0, "positions_count": 5}
        }
        
        result = await guard._check_exposure(
            test_signal, default_settings, account_ids=[1], open_positions_summary=open_positions_summary
        )
        
        assert result.decision == GuardDecision.EXECUTE


class TestGuardIntegration:
    """Integration tests for full guard evaluation"""

    @pytest.mark.asyncio
    async def test_full_evaluation_passes(self, mock_db, default_settings, test_signal):
        """Full evaluation with all checks passing"""
        guard = SignalIntelligenceGuard(mock_db)
        guard._get_momentum_settings = Mock(return_value=default_settings)
        guard._check_staleness = AsyncMock(return_value=GuardResult(decision=GuardDecision.EXECUTE, annotations={}))
        guard._check_momentum = AsyncMock(return_value=GuardResult(decision=GuardDecision.EXECUTE, annotations={}))
        guard._check_exposure = AsyncMock(return_value=GuardResult(decision=GuardDecision.EXECUTE, annotations={}))
        
        result = await guard.evaluate(
            signal=test_signal,
            user_id=1,
            account_ids=[1],
            open_positions_summary={1: {"total_margin": 1000.0}}
        )
        
        assert result.decision == GuardDecision.EXECUTE

    @pytest.mark.asyncio
    async def test_staleness_skip_short_circuits(self, mock_db, default_settings, test_signal):
        """If staleness check fails, other checks should not run"""
        guard = SignalIntelligenceGuard(mock_db)
        guard._get_momentum_settings = Mock(return_value=default_settings)
        
        stale_result = GuardResult(
            decision=GuardDecision.SKIP,
            annotations={"discard_reason": "stale"}
        )
        guard._check_staleness = AsyncMock(return_value=stale_result)
        guard._check_momentum = AsyncMock()
        guard._check_exposure = AsyncMock()
        
        result = await guard.evaluate(
            signal=test_signal,
            user_id=1,
            account_ids=[1],
            open_positions_summary={}
        )
        
        assert result.decision == GuardDecision.SKIP
        guard._check_momentum.assert_not_called()  # Should not be called
        guard._check_exposure.assert_not_called()  # Should not be called
