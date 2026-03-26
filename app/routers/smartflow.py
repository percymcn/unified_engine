"""
SmartFlow API Router
====================

API endpoints for SmartFlow Indicator dashboard and configuration.
"""

import logging
import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.models.smartflow_models import SmartFlowConfig, SmartFlowSignalLog, SmartFlowScoreHistory
from app.models.models import User
from app.services.smartflow_service import smartflow_service
from app.routers.auth import get_current_user

logger = logging.getLogger(__name__)

# SmartFlow tier requirements
SMARTFLOW_ALLOWED_TIERS = {"tier_3", "tier_4", "pro", "enterprise"}


def require_smartflow_tier(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that ensures user has Pro or Enterprise tier for SmartFlow access.
    Raises 402 (Payment Required) if user doesn't have access.
    """
    tier = (current_user.subscription_tier or "free").lower()

    # Check subscription status
    if current_user.subscription_status not in ["active", "trialing", "canceling"]:
        tier = "free"

    if tier not in SMARTFLOW_ALLOWED_TIERS:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "smartflow_tier_required",
                "message": "SmartFlow AI Signals requires Pro or Enterprise tier. Upgrade to unlock this feature.",
                "current_tier": tier,
                "required_tiers": ["Pro", "Enterprise"],
                "upgrade_url": "/pricing"
            }
        )

    return current_user

router = APIRouter(tags=["SmartFlow"])


# ============================================================================
# Request/Response Models
# ============================================================================

class SmartFlowConfigRequest(BaseModel):
    """Request to update SmartFlow configuration"""
    enabled: bool
    webhook_urls: List[str] = Field(default_factory=list)
    buy_threshold: Optional[float] = 4.0
    sell_threshold: Optional[float] = -4.0
    close_threshold: Optional[float] = 1.0
    score_window_minutes: Optional[int] = 5
    update_interval_seconds: Optional[int] = 45
    # Enhanced toggles
    enable_vix_inverse: Optional[bool] = False
    enable_golden_sweeps: Optional[bool] = False
    enable_leveraged_etfs: Optional[bool] = False
    vix_golden_threshold: Optional[float] = 100000.0
    min_premium: Optional[float] = 50000.0
    # Confirmation filter toggles
    enable_price_confirmation: Optional[bool] = False
    enable_rsi_filter: Optional[bool] = False
    enable_volume_filter: Optional[bool] = False
    enable_time_filter: Optional[bool] = False
    enable_fib_confluence: Optional[bool] = False
    min_confidence_score: Optional[float] = 70.0
    # AI Strategy Suite integration
    enable_ai_enhancement: Optional[bool] = False
    ai_analysis_types: Optional[List[str]] = ['technical', 'patterns']
    block_on_ai_disagree: Optional[bool] = True  # HARD BLOCK when AI says opposite direction
    check_market_trend: Optional[bool] = True  # Block when actual price trend conflicts
    # AI-Only Mode (24/7 trading)
    enable_ai_only_mode: Optional[bool] = False
    ai_only_scan_interval: Optional[int] = 300
    ai_only_confidence_threshold: Optional[float] = 70.0
    ai_only_instruments: Optional[List[str]] = ['MES', 'NQ', 'RTY', 'USDJPY', 'BTCUSD']
    # Deterministic Indicator Engine (Phase 0.5)
    enable_deterministic_mode: Optional[bool] = True
    deterministic_min_confidence: Optional[float] = 75.0
    deterministic_min_aligned_tfs: Optional[int] = 4
    deterministic_min_rr: Optional[float] = 2.0
    deterministic_rr_preset: Optional[str] = 'balanced'
    # Quick Mode / Scalping Engine (Phase 0.5)
    enable_quick_mode: Optional[bool] = True
    quick_scan_interval: Optional[int] = 60
    quick_min_confidence: Optional[float] = 60.0
    quick_min_rr: Optional[float] = 1.5
    quick_require_15m_confirmation: Optional[bool] = True
    # Confirmation filter parameters
    rsi_overbought: Optional[float] = 70.0
    rsi_oversold: Optional[float] = 30.0
    volume_spike_multiplier: Optional[float] = 1.5
    time_filter_start_hour: Optional[int] = 9
    time_filter_start_minute: Optional[int] = 30
    time_filter_end_hour: Optional[int] = 15
    time_filter_end_minute: Optional[int] = 0


class SmartFlowConfigResponse(BaseModel):
    """SmartFlow configuration response"""
    id: int
    user_id: int
    enabled: bool
    webhook_urls: List[str]
    buy_threshold: float
    sell_threshold: float
    close_threshold: float
    score_window_minutes: int
    update_interval_seconds: int
    # Enhanced toggles
    enable_vix_inverse: bool
    enable_golden_sweeps: bool
    enable_leveraged_etfs: bool
    vix_golden_threshold: float
    min_premium: float
    # Confirmation filter toggles
    enable_price_confirmation: bool
    enable_rsi_filter: bool
    enable_volume_filter: bool
    enable_time_filter: bool
    enable_fib_confluence: bool
    min_confidence_score: float
    # AI Strategy Suite integration
    enable_ai_enhancement: bool = False
    ai_analysis_types: List[str] = ['technical', 'patterns']
    block_on_ai_disagree: bool = True
    check_market_trend: bool = True
    # AI-Only Mode (24/7 trading)
    enable_ai_only_mode: bool = False
    ai_only_scan_interval: int = 300
    ai_only_confidence_threshold: float = 70.0
    ai_only_instruments: List[str] = ['MES', 'NQ', 'RTY', 'USDJPY', 'BTCUSD']
    # Deterministic Indicator Engine (Phase 0.5)
    enable_deterministic_mode: bool = True
    deterministic_min_confidence: float = 75.0
    deterministic_min_aligned_tfs: int = 4
    deterministic_min_rr: float = 2.0
    deterministic_rr_preset: str = 'balanced'
    # Quick Mode / Scalping Engine (Phase 0.5)
    enable_quick_mode: bool = True
    quick_scan_interval: int = 60
    quick_min_confidence: float = 60.0
    quick_min_rr: float = 1.5
    quick_require_15m_confirmation: bool = True
    # Confirmation filter parameters
    rsi_overbought: float
    rsi_oversold: float
    volume_spike_multiplier: float
    time_filter_start_hour: int
    time_filter_start_minute: int
    time_filter_end_hour: int
    time_filter_end_minute: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SmartFlowStatusResponse(BaseModel):
    """Current SmartFlow status"""
    enabled: bool
    latest_scores: dict
    last_signals: dict
    recent_signals: list
    webhook_count: int
    update_interval: int
    # Deterministic Mode
    enable_deterministic_mode: Optional[bool] = None
    deterministic_available: Optional[bool] = None
    deterministic_min_confidence: Optional[float] = None
    deterministic_min_rr: Optional[float] = None
    deterministic_min_aligned_tfs: Optional[int] = None
    deterministic_instruments: Optional[list] = None
    deterministic_scan_interval: Optional[int] = None
    deterministic_rr_preset: Optional[str] = None
    deterministic_rr_presets: Optional[dict] = None
    # Quick Mode
    enable_quick_mode: Optional[bool] = None
    quick_scan_interval: Optional[int] = None
    quick_min_confidence: Optional[float] = None
    quick_require_15m_confirmation: Optional[bool] = None
    quick_min_rr: Optional[float] = None
    quick_instruments: Optional[list] = None
    # Strategy Stats
    strategy_stats: Optional[dict] = None
    # MTF Analysis
    mtf_analysis: Optional[dict] = None
    # Flow toggles
    use_flow_confirmation: Optional[bool] = None
    use_polygon_options_flow: Optional[bool] = None
    use_flowalgo_flow: Optional[bool] = None
    # Other
    vix_bias: Optional[str] = None
    enable_ai_enhancement: Optional[bool] = None
    ai_available: Optional[bool] = None
    enable_trade_journal: Optional[bool] = None
    trade_journal_available: Optional[bool] = None
    latency_target_ms: Optional[int] = None
    latency_stats: Optional[dict] = None

    class Config:
        extra = 'allow'  # Allow extra fields not defined in model


class SignalLogResponse(BaseModel):
    """Signal log entry"""
    id: int
    ticker: str
    action: str
    score: float
    price: Optional[float]
    bullish_flows: int
    bearish_flows: int
    total_premium: float
    engine_type: Optional[str] = None  # Phase 0.5: Engine source tracking
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Configuration Endpoints
# ============================================================================

@router.get("/config", response_model=SmartFlowConfigResponse)
async def get_smartflow_config(
    current_user: User = Depends(require_smartflow_tier),
    db: Session = Depends(get_db)
):
    """
    Get SmartFlow configuration for current user
    """
    config = db.query(SmartFlowConfig).filter(SmartFlowConfig.user_id == current_user.id).first()

    if not config:
        # Create default config
        config = SmartFlowConfig(
            user_id=current_user.id,
            enabled=False,
            webhook_urls=[],
            buy_threshold=4.0,
            sell_threshold=-4.0,
            close_threshold=1.0,
            score_window_minutes=5,
            update_interval_seconds=45,
            # Enhanced toggles
            enable_vix_inverse=False,
            enable_golden_sweeps=False,
            enable_leveraged_etfs=False,
            vix_golden_threshold=100000.0,
            min_premium=50000.0,
            # Confirmation filter toggles
            enable_price_confirmation=False,
            enable_rsi_filter=False,
            enable_volume_filter=False,
            enable_time_filter=False,
            enable_fib_confluence=False,
            min_confidence_score=70.0,
            # Confirmation filter parameters
            rsi_overbought=70.0,
            rsi_oversold=30.0,
            volume_spike_multiplier=1.5,
            time_filter_start_hour=9,
            time_filter_start_minute=30,
            time_filter_end_hour=15,
            time_filter_end_minute=0
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    return config


@router.put("/config", response_model=SmartFlowConfigResponse)
async def update_smartflow_config(
    request: SmartFlowConfigRequest,
    current_user: User = Depends(require_smartflow_tier),
    db: Session = Depends(get_db)
):
    """
    Update SmartFlow configuration

    When enabled, SmartFlow will start generating signals from FlowAlgo data.
    """
    config = db.query(SmartFlowConfig).filter(SmartFlowConfig.user_id == current_user.id).first()

    if not config:
        # Create new config
        config = SmartFlowConfig(user_id=current_user.id)
        db.add(config)

    # Update configuration
    config.enabled = request.enabled
    config.webhook_urls = request.webhook_urls
    config.buy_threshold = request.buy_threshold
    config.sell_threshold = request.sell_threshold
    config.close_threshold = request.close_threshold
    config.score_window_minutes = request.score_window_minutes
    config.update_interval_seconds = request.update_interval_seconds
    # Enhanced toggles
    config.enable_vix_inverse = request.enable_vix_inverse
    config.enable_golden_sweeps = request.enable_golden_sweeps
    config.enable_leveraged_etfs = request.enable_leveraged_etfs
    config.vix_golden_threshold = request.vix_golden_threshold
    config.min_premium = request.min_premium
    # Confirmation filter toggles
    config.enable_price_confirmation = request.enable_price_confirmation
    config.enable_rsi_filter = request.enable_rsi_filter
    config.enable_volume_filter = request.enable_volume_filter
    config.enable_time_filter = request.enable_time_filter
    config.enable_fib_confluence = request.enable_fib_confluence
    config.min_confidence_score = request.min_confidence_score
    # AI Strategy Suite settings
    config.enable_ai_enhancement = request.enable_ai_enhancement
    config.ai_analysis_types = request.ai_analysis_types
    config.block_on_ai_disagree = request.block_on_ai_disagree
    config.check_market_trend = request.check_market_trend
    config.enable_ai_only_mode = request.enable_ai_only_mode
    config.ai_only_scan_interval = request.ai_only_scan_interval
    config.ai_only_confidence_threshold = request.ai_only_confidence_threshold
    config.ai_only_instruments = request.ai_only_instruments
    # Deterministic Indicator Engine (Phase 0.5)
    config.enable_deterministic_mode = request.enable_deterministic_mode
    config.deterministic_min_confidence = request.deterministic_min_confidence
    config.deterministic_min_aligned_tfs = request.deterministic_min_aligned_tfs
    config.deterministic_min_rr = request.deterministic_min_rr
    config.deterministic_rr_preset = request.deterministic_rr_preset
    # Quick Mode / Scalping Engine (Phase 0.5)
    config.enable_quick_mode = request.enable_quick_mode
    config.quick_scan_interval = request.quick_scan_interval
    config.quick_min_confidence = request.quick_min_confidence
    config.quick_min_rr = request.quick_min_rr
    config.quick_require_15m_confirmation = request.quick_require_15m_confirmation
    # Confirmation filter parameters
    config.rsi_overbought = request.rsi_overbought
    config.rsi_oversold = request.rsi_oversold
    config.volume_spike_multiplier = request.volume_spike_multiplier
    config.time_filter_start_hour = request.time_filter_start_hour
    config.time_filter_start_minute = request.time_filter_start_minute
    config.time_filter_end_hour = request.time_filter_end_hour
    config.time_filter_end_minute = request.time_filter_end_minute
    config.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(config)

    # Update service configuration
    if request.enabled:
        smartflow_service.enable(request.webhook_urls)
        smartflow_service.score_threshold_buy = request.buy_threshold
        smartflow_service.score_threshold_sell = request.sell_threshold
        smartflow_service.close_threshold = request.close_threshold
        smartflow_service.score_window_minutes = request.score_window_minutes
        smartflow_service.update_interval_seconds = request.update_interval_seconds
        # Update enhanced toggles
        smartflow_service.enable_vix_inverse = request.enable_vix_inverse
        smartflow_service.enable_golden_sweeps = request.enable_golden_sweeps
        smartflow_service.enable_leveraged_etfs = request.enable_leveraged_etfs
        smartflow_service.vix_golden_threshold = request.vix_golden_threshold
        smartflow_service.min_premium = request.min_premium
        # Update confirmation filter toggles
        smartflow_service.enable_price_confirmation = request.enable_price_confirmation
        smartflow_service.enable_rsi_filter = request.enable_rsi_filter
        smartflow_service.enable_volume_filter = request.enable_volume_filter
        smartflow_service.enable_time_filter = request.enable_time_filter
        smartflow_service.enable_fib_confluence = request.enable_fib_confluence
        smartflow_service.min_confidence_score = request.min_confidence_score
        # Update AI Strategy Suite settings
        smartflow_service.enable_ai_enhancement = request.enable_ai_enhancement
        smartflow_service.ai_analysis_types = request.ai_analysis_types
        smartflow_service.block_on_ai_disagree = request.block_on_ai_disagree
        smartflow_service.check_market_trend = request.check_market_trend
        smartflow_service.enable_ai_only_mode = request.enable_ai_only_mode
        smartflow_service.ai_only_scan_interval = request.ai_only_scan_interval
        smartflow_service.ai_only_confidence_threshold = request.ai_only_confidence_threshold
        smartflow_service.ai_only_instruments = request.ai_only_instruments
        # Update confirmation filter parameters
        smartflow_service.rsi_overbought = request.rsi_overbought
        smartflow_service.rsi_oversold = request.rsi_oversold
        smartflow_service.volume_spike_multiplier = request.volume_spike_multiplier
        smartflow_service.time_filter_start_hour = request.time_filter_start_hour
        smartflow_service.time_filter_start_minute = request.time_filter_start_minute
        smartflow_service.time_filter_end_hour = request.time_filter_end_hour
        smartflow_service.time_filter_end_minute = request.time_filter_end_minute
    else:
        smartflow_service.disable()

    logger.info(f"SmartFlow config updated for user {current_user.id}: enabled={request.enabled}")

    return config


@router.patch("/config")
async def patch_smartflow_config(
    updates: Dict[str, Any] = Body(...),
    current_user: User = Depends(require_smartflow_tier),
    db: Session = Depends(get_db)
):
    """
    Partially update SmartFlow configuration.

    Accepts a JSON object with only the fields to update.
    Used by the UI for real-time toggle switches and sliders.
    """
    config = db.query(SmartFlowConfig).filter(SmartFlowConfig.user_id == current_user.id).first()

    if not config:
        raise HTTPException(status_code=404, detail="SmartFlow config not found")

    # Map of allowed fields and their service attribute names
    allowed_fields = {
        # Deterministic mode settings
        'enable_deterministic_mode': 'enable_deterministic_mode',
        'deterministic_min_confidence': 'deterministic_min_confidence',
        'deterministic_min_aligned_tfs': 'deterministic_min_aligned_tfs',
        'deterministic_rr_preset': 'deterministic_rr_preset',
        # Quick mode settings
        'enable_quick_mode': 'enable_quick_mode',
        'quick_scan_interval': 'quick_scan_interval',
        'quick_min_confidence': 'quick_min_confidence',
        'quick_require_15m_confirmation': 'quick_require_15m_confirmation',
        'quick_min_rr': 'quick_min_rr',
        # Flow confirmation
        'use_flow_confirmation': 'use_flow_confirmation',
        'use_polygon_options_flow': 'use_polygon_options_flow',
        'use_flowalgo_flow': 'use_flowalgo_flow',
        # Basic toggles
        'enabled': 'enabled',
        'enable_ai_enhancement': 'enable_ai_enhancement',
        'enable_ai_only_mode': 'enable_ai_only_mode',
    }

    updated_fields = []

    for field, service_attr in allowed_fields.items():
        if field in updates:
            value = updates[field]
            updated_fields.append(f"{field}={value}")

            # Update the service directly (runtime config)
            if hasattr(smartflow_service, service_attr):
                setattr(smartflow_service, service_attr, value)
                logger.debug(f"Updated smartflow_service.{service_attr} = {value}")

    # Special handling for enabled toggle
    if 'enabled' in updates:
        if updates['enabled']:
            smartflow_service.enable(config.webhook_urls or [])
        else:
            smartflow_service.disable()

    config.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"SmartFlow PATCH config for user {current_user.id}: {', '.join(updated_fields)}")

    # Return the current state of relevant fields for UI sync
    return {
        "status": "ok",
        "updated": updated_fields,
        "message": f"Updated {len(updated_fields)} field(s)",
        "current_state": {
            "enable_quick_mode": smartflow_service.enable_quick_mode,
            "enable_deterministic_mode": smartflow_service.enable_deterministic_mode,
        }
    }


# ============================================================================
# Status and Monitoring Endpoints
# ============================================================================

@router.get("/status", response_model=SmartFlowStatusResponse)
async def get_smartflow_status(
    current_user: User = Depends(require_smartflow_tier)
):
    """
    Get current SmartFlow status

    Returns:
    - enabled: Whether SmartFlow is active
    - latest_scores: Current sentiment scores for SPY/QQQ/GLD
    - last_signals: Most recent signal per ticker
    - recent_signals: Last 20 signals generated
    - webhook_count: Number of configured webhooks
    """
    status = smartflow_service.get_status()
    return status


@router.get("/signals", response_model=List[SignalLogResponse])
async def get_signal_history(
    limit: int = 50,
    ticker: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get SmartFlow signal history

    Query parameters:
    - limit: Maximum number of signals to return (default 50)
    - ticker: Filter by ticker (MES, NQ, GC)
    """
    config = db.query(SmartFlowConfig).filter(SmartFlowConfig.user_id == current_user.id).first()

    if not config:
        return []

    query = db.query(SmartFlowSignalLog).filter(SmartFlowSignalLog.config_id == config.id)

    if ticker:
        query = query.filter(SmartFlowSignalLog.ticker == ticker.upper())

    signals = query.order_by(SmartFlowSignalLog.created_at.desc()).limit(limit).all()

    return signals


@router.get("/scores/history")
async def get_score_history(
    ticker: str,
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get sentiment score history for charting

    Query parameters:
    - ticker: SPY, QQQ, or GLD
    - hours: How many hours of history (default 24)
    """
    ticker = ticker.upper()
    if ticker not in ['SPY', 'QQQ', 'GLD']:
        raise HTTPException(status_code=400, detail="Ticker must be SPY, QQQ, or GLD")

    cutoff = datetime.utcnow() - timedelta(hours=hours)

    scores = db.query(SmartFlowScoreHistory).filter(
        SmartFlowScoreHistory.ticker == ticker,
        SmartFlowScoreHistory.timestamp >= cutoff
    ).order_by(SmartFlowScoreHistory.timestamp.asc()).all()

    return [{
        'timestamp': score.timestamp.isoformat(),
        'score': score.score,
        'bullish_flows': score.bullish_flows,
        'bearish_flows': score.bearish_flows,
        'total_premium': score.total_premium
    } for score in scores]


# ============================================================================
# Testing Endpoint
# ============================================================================

@router.post("/test-signal")
async def test_smartflow_signal(
    ticker: str,
    action: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Test SmartFlow signal posting (for debugging)

    Sends a test signal to configured webhooks without actually checking flow data.
    """
    config = db.query(SmartFlowConfig).filter(SmartFlowConfig.user_id == current_user.id).first()

    if not config or not config.enabled:
        raise HTTPException(status_code=400, detail="SmartFlow not enabled")

    if not config.webhook_urls:
        raise HTTPException(status_code=400, detail="No webhook URLs configured")

    if action not in ['buy', 'sell', 'close']:
        raise HTTPException(status_code=400, detail="Action must be buy, sell, or close")

    # Create test signal
    from app.services.smartflow_service import SmartFlowSignal

    test_signal = SmartFlowSignal(
        ticker=ticker.upper(),
        action=action,
        score=10.0 if action == 'buy' else -10.0 if action == 'sell' else 0.0,
        price=None
    )

    # Post to webhooks
    await smartflow_service.post_signal_to_webhooks(test_signal)

    logger.info(f"Test signal sent: {ticker} {action}")

    return {
        'status': 'success',
        'message': f'Test {action} signal sent for {ticker}',
        'webhooks_posted': len(config.webhook_urls)
    }


# ============================================================================
# ML LEARNING ENDPOINTS
# ============================================================================

class SignalOutcomeRequest(BaseModel):
    """Request to record a signal outcome for ML learning"""
    signal_log_id: int
    trade_executed: bool
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    time_in_trade: Optional[int] = None
    max_favorable: Optional[float] = None
    max_adverse: Optional[float] = None


class MLDashboardResponse(BaseModel):
    """ML performance dashboard data"""
    model_state: Optional[dict]
    daily_metrics: List[dict]
    top_patterns: List[dict]
    recent_correlations: List[dict]
    is_learning: bool


@router.post("/ml/record-outcome")
async def record_signal_outcome(
    request: SignalOutcomeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Record the outcome of a SmartFlow signal for ML learning.

    This is the feedback loop that enables self-improvement:
    - Call this endpoint after a trade closes
    - Provide entry/exit prices and P&L
    - ML will learn from the outcome to improve future signals
    """
    from app.services.smartflow_ml_service import SmartFlowMLService

    ml_service = SmartFlowMLService(db)
    result = await ml_service.record_signal_outcome(
        signal_log_id=request.signal_log_id,
        trade_executed=request.trade_executed,
        entry_price=request.entry_price,
        exit_price=request.exit_price,
        pnl=request.pnl,
        time_in_trade=request.time_in_trade,
        max_favorable=request.max_favorable,
        max_adverse=request.max_adverse
    )

    return result


@router.get("/ml/dashboard")
async def get_ml_dashboard(
    ticker: str = "SPY",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get ML performance dashboard data.

    Returns:
    - Model state (thresholds, win rates, best hours)
    - Daily performance metrics
    - Top performing patterns
    - Recent correlation signals
    - Learning status
    """
    from app.services.smartflow_ml_service import SmartFlowMLService

    ml_service = SmartFlowMLService(db)
    dashboard = await ml_service.get_ml_dashboard(ticker.upper())

    return dashboard


@router.get("/ml/adaptive-thresholds")
async def get_adaptive_thresholds(
    ticker: str = "SPY",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get ML-optimized FSS thresholds for a ticker.

    Returns adaptive buy/sell thresholds learned from historical outcomes.
    If not enough data, returns defaults.
    """
    from app.services.smartflow_ml_service import SmartFlowMLService

    ml_service = SmartFlowMLService(db)
    thresholds = await ml_service.get_adaptive_thresholds(ticker.upper())

    return thresholds


@router.post("/ml/optimize-thresholds")
async def optimize_thresholds(
    ticker: str = "SPY",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Run threshold optimization for a ticker.

    Analyzes historical outcomes to find optimal FSS thresholds
    that maximize expectancy.
    """
    from app.services.smartflow_ml_service import SmartFlowMLService

    ml_service = SmartFlowMLService(db)
    result = await ml_service.optimize_thresholds(ticker.upper())

    return result


@router.get("/ml/time-optimization")
async def get_time_optimization(
    ticker: str = "SPY",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get time-of-day optimization data.

    Returns:
    - Hourly win rates
    - Best trading hours
    - Hours to avoid
    - Daily win rates
    - Best trading days
    """
    from app.services.smartflow_ml_service import SmartFlowMLService

    ml_service = SmartFlowMLService(db)
    time_data = await ml_service.get_time_optimization(ticker.upper())

    return time_data


@router.post("/ml/calculate-time-optimization")
async def calculate_time_optimization(
    ticker: str = "SPY",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate and update time-of-day optimization.

    Analyzes historical outcomes to find best trading hours/days.
    """
    from app.services.smartflow_ml_service import SmartFlowMLService

    ml_service = SmartFlowMLService(db)
    result = await ml_service.calculate_time_optimization(ticker.upper())

    return result


@router.get("/ml/signal-confidence")
async def get_signal_confidence(
    ticker: str,
    fss_score: float,
    action: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate ML-enhanced confidence score for a potential signal.

    Parameters:
    - ticker: The ticker symbol
    - fss_score: Current FSS score
    - action: buy or sell

    Returns confidence score (0-100) with factors that contributed.
    """
    from app.services.smartflow_ml_service import SmartFlowMLService

    current_hour = datetime.utcnow().hour
    current_day = datetime.utcnow().weekday()

    ml_service = SmartFlowMLService(db)
    confidence = await ml_service.calculate_signal_confidence(
        ticker=ticker.upper(),
        fss_score=fss_score,
        action=action.lower(),
        current_hour=current_hour,
        current_day=current_day
    )

    return confidence


@router.post("/ml/detect-correlation")
async def detect_correlation_signal(
    ticker_scores: dict,
    min_tickers: int = 2,
    threshold: float = 3.0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Detect cross-ticker correlation signals.

    Parameters:
    - ticker_scores: Dict of ticker -> FSS score (e.g., {"SPY": 4.5, "QQQ": 5.2})
    - min_tickers: Minimum aligned tickers for signal
    - threshold: FSS threshold for alignment

    Returns correlation signal if detected, or null.
    """
    from app.services.smartflow_ml_service import SmartFlowMLService

    ml_service = SmartFlowMLService(db)
    signal = await ml_service.detect_correlation_signal(
        ticker_scores=ticker_scores,
        min_tickers=min_tickers,
        threshold=threshold
    )

    return signal or {"detected": False}


@router.post("/ml/update-market-regime")
async def update_market_regime(
    ticker: str,
    regime: str,
    confidence: float,
    strength: float,
    vix_level: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update detected market regime for a ticker.

    Parameters:
    - ticker: Ticker symbol
    - regime: trending_up, trending_down, ranging, volatile, squeeze
    - confidence: 0-1 confidence in classification
    - strength: 0-1 strength of the regime
    - vix_level: Current VIX level (optional)
    """
    from app.services.smartflow_ml_service import SmartFlowMLService

    ml_service = SmartFlowMLService(db)
    result = await ml_service.update_market_regime(
        ticker=ticker.upper(),
        regime=regime.lower(),
        confidence=confidence,
        strength=strength,
        vix_level=vix_level
    )

    return result


class MLOptimizationRequest(BaseModel):
    tickers: Optional[List[str]] = None


@router.post("/ml/run-optimization")
async def run_full_optimization(
    request: Optional[MLOptimizationRequest] = None,
    current_user: User = Depends(require_smartflow_tier),
    db: Session = Depends(get_db)
):
    """
    Run full ML optimization for all tracked tickers.

    This should be called periodically (e.g., daily) to:
    - Optimize FSS thresholds
    - Update time-of-day analysis
    - Recalculate pattern performance
    """
    from app.services.smartflow_ml_service import SmartFlowMLService

    ml_service = SmartFlowMLService(db)
    tickers = request.tickers if request else None
    result = await ml_service.run_full_optimization(
        tickers=[t.upper() for t in tickers] if tickers else None
    )

    return result


# ============================================================================
# AI ANALYSIS HISTORY ENDPOINTS
# ============================================================================

@router.get("/ai/analysis")
async def get_ai_analysis_history(
    ticker: Optional[str] = None,
    analysis_type: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI analysis history from cache.

    Query parameters:
    - ticker: Filter by ticker symbol (optional)
    - analysis_type: Filter by analysis type (technical, patterns, sentiment)
    - limit: Maximum results to return (default 50)

    Returns list of AI analyses with recommendations, confidence, and summaries.
    """
    from sqlalchemy import text

    try:
        # Build query based on filters
        query = """
            SELECT id, ticker, analysis_type, recommendation, confidence,
                   summary, data, created_at, hit_count
            FROM ai_strategy_cache
            WHERE 1=1
        """
        params = {"limit": limit}

        if ticker:
            query += " AND ticker ILIKE :ticker"
            params["ticker"] = f"%{ticker}%"

        if analysis_type:
            query += " AND analysis_type = :analysis_type"
            params["analysis_type"] = analysis_type

        query += " ORDER BY created_at DESC LIMIT :limit"

        result = db.execute(text(query), params)
        rows = result.fetchall()

        analyses = []
        for row in rows:
            analyses.append({
                "id": row[0],
                "ticker": row[1],
                "analysis_type": row[2],
                "recommendation": row[3],
                "confidence": row[4],
                "summary": row[5],
                "data": row[6],
                "created_at": row[7].isoformat() if row[7] else None,
                "hit_count": row[8]
            })

        return {
            "analyses": analyses,
            "total": len(analyses)
        }

    except Exception as e:
        logger.error(f"Error fetching AI analysis history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch AI analysis history: {str(e)}"
        )


@router.get("/ai/analysis/stats")
async def get_ai_analysis_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI analysis statistics.
    """
    from sqlalchemy import text

    try:
        # Get counts by recommendation
        rec_query = text("""
            SELECT recommendation, COUNT(*) as count
            FROM ai_strategy_cache
            GROUP BY recommendation
            ORDER BY count DESC
        """)
        rec_result = db.execute(rec_query)
        recommendations = {row[0]: row[1] for row in rec_result.fetchall()}

        # Get counts by ticker
        ticker_query = text("""
            SELECT ticker, COUNT(*) as count
            FROM ai_strategy_cache
            GROUP BY ticker
            ORDER BY count DESC
            LIMIT 10
        """)
        ticker_result = db.execute(ticker_query)
        top_tickers = {row[0]: row[1] for row in ticker_result.fetchall()}

        # Get average confidence by recommendation
        conf_query = text("""
            SELECT recommendation, AVG(confidence) as avg_conf
            FROM ai_strategy_cache
            GROUP BY recommendation
        """)
        conf_result = db.execute(conf_query)
        avg_confidence = {row[0]: round(row[1], 1) for row in conf_result.fetchall()}

        # Get total count
        total_query = text("SELECT COUNT(*) FROM ai_strategy_cache")
        total = db.execute(total_query).scalar()

        return {
            "total_analyses": total,
            "by_recommendation": recommendations,
            "top_tickers": top_tickers,
            "avg_confidence_by_recommendation": avg_confidence
        }

    except Exception as e:
        logger.error(f"Error fetching AI analysis stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch AI analysis stats: {str(e)}"
        )


@router.get("/ai-context")
async def get_ai_market_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-powered market context analysis.

    This endpoint provides real-time AI analysis of market conditions
    without affecting trading decisions (deterministic mode uses pure indicators).

    Returns:
    - Market regime (trending/ranging/volatile)
    - Key support/resistance levels
    - Sentiment summary across instruments
    - Recent signal performance context
    """
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    from sqlalchemy import text

    try:
        EST = ZoneInfo('America/New_York')
        now = datetime.now(EST)

        # Get recent signals from signal_journal
        recent_signals_query = """
            SELECT ticker, direction, confidence, aligned_tfs, signal_accepted,
                   entry_price, created_at
            FROM signal_journal
            WHERE created_at > :cutoff
            ORDER BY created_at DESC
            LIMIT 20
        """
        cutoff = now - timedelta(hours=4)
        result = db.execute(text(recent_signals_query), {"cutoff": cutoff})
        recent_signals = result.fetchall()

        # Get recent trade outcomes
        trade_outcomes_query = """
            SELECT symbol, side, net_pnl, status, entry_time
            FROM trade_journal
            WHERE entry_time > :cutoff
            ORDER BY entry_time DESC
            LIMIT 10
        """
        trade_result = db.execute(text(trade_outcomes_query), {"cutoff": cutoff})
        recent_trades = trade_result.fetchall()

        # Build context analysis
        total_signals = len(recent_signals)
        accepted_signals = sum(1 for s in recent_signals if s[4])  # signal_accepted
        bullish_signals = sum(1 for s in recent_signals if s[1] == 'buy')
        bearish_signals = sum(1 for s in recent_signals if s[1] == 'sell')

        # Calculate win rate from recent trades
        closed_trades = [t for t in recent_trades if t[2] is not None]  # has pnl
        wins = sum(1 for t in closed_trades if t[2] > 0)
        win_rate = (wins / len(closed_trades) * 100) if closed_trades else 0

        # Generate AI context summary
        market_bias = "NEUTRAL"
        if bullish_signals > bearish_signals * 1.5:
            market_bias = "BULLISH"
        elif bearish_signals > bullish_signals * 1.5:
            market_bias = "BEARISH"

        context_lines = [
            f"=== AI MARKET CONTEXT ({now.strftime('%I:%M %p EST')}) ===",
            "",
            f"MARKET BIAS: {market_bias}",
            f"  - Bullish signals: {bullish_signals}",
            f"  - Bearish signals: {bearish_signals}",
            "",
            f"SIGNAL QUALITY (last 4h):",
            f"  - Total signals: {total_signals}",
            f"  - Accepted: {accepted_signals} ({accepted_signals/total_signals*100:.0f}%)" if total_signals > 0 else "  - No signals yet",
            "",
            f"RECENT PERFORMANCE:",
            f"  - Trades: {len(recent_trades)}",
            f"  - Win rate: {win_rate:.0f}%",
        ]

        # Add instrument-specific context
        instrument_signals = {}
        for s in recent_signals:
            ticker = s[0]
            if ticker not in instrument_signals:
                instrument_signals[ticker] = {'bull': 0, 'bear': 0}
            if s[1] == 'buy':
                instrument_signals[ticker]['bull'] += 1
            else:
                instrument_signals[ticker]['bear'] += 1

        if instrument_signals:
            context_lines.append("")
            context_lines.append("INSTRUMENT SENTIMENT:")
            for ticker, counts in instrument_signals.items():
                bias = "BULL" if counts['bull'] > counts['bear'] else "BEAR" if counts['bear'] > counts['bull'] else "NEUTRAL"
                context_lines.append(f"  - {ticker}: {bias} (B:{counts['bull']} S:{counts['bear']})")

        context_lines.append("")
        context_lines.append("NOTE: Trading decisions are DETERMINISTIC (indicators only).")
        context_lines.append("This AI context is for informational purposes only.")

        return {
            "analysis": "\n".join(context_lines),
            "market_bias": market_bias,
            "total_signals": total_signals,
            "accepted_signals": accepted_signals,
            "win_rate": win_rate,
            "timestamp": now.isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating AI context: {e}")
        return {
            "analysis": f"Error generating context: {str(e)}",
            "market_bias": "UNKNOWN",
            "total_signals": 0,
            "timestamp": datetime.now().isoformat()
        }


@router.get("/trade-decisions")
async def get_trade_decision_history(
    ticker: Optional[str] = None,
    limit: int = 50,
    include_closed: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get trade decision history with full AI analysis context.

    Shows each trade taken with:
    - Signal details (FSS score, flow counts)
    - AI analysis that influenced the decision
    - Confidence scores and reasoning
    - Trade outcome (if closed)

    Query parameters:
    - ticker: Filter by ticker symbol
    - limit: Maximum results (default 50)
    - include_closed: Include trades with PnL data
    """
    from sqlalchemy import text

    try:
        query = """
            SELECT
                el.id as execution_id,
                el.symbol,
                el.action as trade_action,
                el.entry_price,
                el.exit_price,
                el.pnl,
                el.pnl_pct,
                el.status,
                el.close_reason,
                el.created_at as trade_time,
                el.closed_at,
                el.broker,
                sl.id as signal_id,
                sl.ticker as signal_ticker,
                sl.action as signal_action,
                sl.score as fss_score,
                sl.confidence,
                sl.reason,
                sl.bullish_flows,
                sl.bearish_flows,
                sl.total_premium,
                sl.created_at as signal_time,
                so.is_winner,
                so.market_regime,
                so.hour_of_day,
                so.day_of_week
            FROM execution_logs el
            LEFT JOIN smartflow_signal_logs sl ON el.smartflow_signal_log_id = sl.id
            LEFT JOIN smartflow_signal_outcomes so ON so.signal_log_id = sl.id
            WHERE el.status = 'success'
              AND el.action IN ('BUY', 'SELL')
        """
        params = {"limit": limit}

        if ticker:
            query += " AND (el.symbol ILIKE :ticker OR sl.ticker ILIKE :ticker)"
            params["ticker"] = f"%{ticker}%"

        if not include_closed:
            query += " AND el.pnl IS NULL"

        query += " ORDER BY el.created_at DESC LIMIT :limit"

        result = db.execute(text(query), params)
        rows = result.fetchall()

        decisions = []
        for row in rows:
            # Parse the reason field to extract AI analysis details
            reason = row[17] or ""
            ai_mode = "hybrid"
            ai_recommendation = None
            ai_confidence_boost = 0

            if "AI-Only:" in reason:
                ai_mode = "ai_only"
                # Parse AI-Only format: "AI-Only: bullish via SYMBOL (X buy / Y sell, Z% conf)"
                if "bullish" in reason.lower():
                    ai_recommendation = "buy"
                elif "bearish" in reason.lower():
                    ai_recommendation = "sell"
                else:
                    ai_recommendation = "neutral"
            elif "AI " in reason:
                # Parse hybrid format: "... | AI sell (+25%)"
                if "AI buy" in reason or "AI bullish" in reason:
                    ai_recommendation = "buy"
                elif "AI sell" in reason or "AI bearish" in reason:
                    ai_recommendation = "sell"
                else:
                    ai_recommendation = "neutral"
                # Extract confidence boost
                import re
                boost_match = re.search(r'\(([+-]?\d+)%\)', reason.split("AI")[-1])
                if boost_match:
                    ai_confidence_boost = int(boost_match.group(1))

            # Determine outcome - prefer signal outcome, fallback to execution PnL
            pnl = row[5]
            is_winner_from_outcome = row[22]
            is_winner_from_pnl = pnl > 0 if pnl is not None else None
            final_is_winner = is_winner_from_outcome if is_winner_from_outcome is not None else is_winner_from_pnl

            # Determine trade status: open, winner, loser
            trade_status = "open"
            if pnl is not None or row[4] is not None:  # has pnl or exit_price
                trade_status = "winner" if final_is_winner else "loser"
            elif row[10]:  # has closed_at
                trade_status = "closed"

            decisions.append({
                "execution_id": row[0],
                "symbol": row[1],
                "trade_action": row[2],
                "entry_price": row[3],
                "exit_price": row[4],
                "pnl": row[5],
                "pnl_pct": row[6],
                "status": row[7],
                "trade_status": trade_status,  # New field: open/winner/loser
                "close_reason": row[8],
                "trade_time": row[9].isoformat() if row[9] else None,
                "closed_at": row[10].isoformat() if row[10] else None,
                "broker": row[11],
                "signal": {
                    "id": row[12],
                    "ticker": row[13],
                    "action": row[14],
                    "fss_score": row[15],
                    "confidence": row[16],
                    "reason": row[17],
                    "bullish_flows": row[18],
                    "bearish_flows": row[19],
                    "total_premium": row[20],
                    "time": row[21].isoformat() if row[21] else None
                } if row[12] else None,
                "outcome": {
                    "is_winner": final_is_winner,
                    "market_regime": row[23],
                    "hour_of_day": row[24],
                    "day_of_week": row[25]
                } if final_is_winner is not None else None,
                "ai_context": {
                    "mode": ai_mode,
                    "recommendation": ai_recommendation,
                    "confidence_boost": ai_confidence_boost
                },
                "ai_analysis": None  # Will be populated below
            })

        # Enrich decisions with AI analysis data from cache
        # This provides the full reasoning behind AI decisions
        if decisions:
            unique_tickers = set()
            for d in decisions:
                if d["signal"] and d["signal"]["ticker"]:
                    ticker = d["signal"]["ticker"]
                    unique_tickers.add(ticker)
                    # Also add mapped versions for cross-market lookup
                    ticker_mappings = {
                        "MES": ["MES", "SPY", "ES"],
                        "NQ": ["NQ", "QQQ", "MNQ"],
                        "RTY": ["RTY", "IWM", "M2K"],
                        "GLD": ["GLD", "C:XAUUSD", "MGC"],
                        "BTCUSD": ["X:BTCUSD", "BTCUSD"],
                        "ETHUSD": ["X:ETHUSD", "ETHUSD"],
                    }
                    for base, variants in ticker_mappings.items():
                        if ticker in variants or ticker == base:
                            unique_tickers.update(variants)

            if unique_tickers:
                ai_query = text("""
                    SELECT DISTINCT ON (ticker)
                        ticker,
                        recommendation,
                        confidence,
                        summary,
                        data,
                        created_at
                    FROM ai_strategy_cache
                    WHERE ticker = ANY(:tickers)
                    ORDER BY ticker, created_at DESC
                """)
                ai_result = db.execute(ai_query, {"tickers": list(unique_tickers)})
                ai_cache = {}
                for ai_row in ai_result.fetchall():
                    ai_cache[ai_row[0]] = {
                        "recommendation": ai_row[1],
                        "confidence": ai_row[2],
                        "summary": ai_row[3],
                        "data": ai_row[4] if ai_row[4] else {},
                        "analyzed_at": ai_row[5].isoformat() if ai_row[5] else None
                    }

                # Map AI analysis to decisions
                for d in decisions:
                    if d["signal"] and d["signal"]["ticker"]:
                        ticker = d["signal"]["ticker"]
                        # Try exact match first
                        if ticker in ai_cache:
                            d["ai_analysis"] = ai_cache[ticker]
                        else:
                            # Try mapped variants
                            for ai_ticker, ai_data in ai_cache.items():
                                if ticker in ai_ticker or ai_ticker in ticker:
                                    d["ai_analysis"] = ai_data
                                    break

        return {
            "decisions": decisions,
            "total": len(decisions)
        }

    except Exception as e:
        logger.error(f"Error fetching trade decisions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch trade decisions: {str(e)}"
        )


@router.get("/trade-decisions/stats")
async def get_trade_decision_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get trade decision statistics.
    """
    from sqlalchemy import text

    try:
        # Get AI mode breakdown - use so.is_winner as primary source, fallback to el.pnl
        mode_query = text("""
            SELECT
                CASE
                    WHEN sl.reason LIKE '%AI-Only:%' THEN 'ai_only'
                    WHEN sl.reason LIKE '%AI %' THEN 'hybrid'
                    ELSE 'flow_only'
                END as mode,
                COUNT(*) as count,
                SUM(CASE
                    WHEN so.is_winner = true OR (so.is_winner IS NULL AND el.pnl > 0) THEN 1
                    ELSE 0
                END) as winners,
                SUM(CASE
                    WHEN so.is_winner = false OR (so.is_winner IS NULL AND el.pnl < 0) THEN 1
                    ELSE 0
                END) as losers,
                SUM(CASE WHEN so.is_winner IS NULL AND (el.pnl IS NULL OR el.pnl = 0) THEN 1 ELSE 0 END) as open_trades
            FROM execution_logs el
            JOIN smartflow_signal_logs sl ON el.smartflow_signal_log_id = sl.id
            LEFT JOIN smartflow_signal_outcomes so ON so.signal_log_id = sl.id
            WHERE el.status = 'success' AND el.action IN ('BUY', 'SELL')
            GROUP BY mode
        """)
        mode_result = db.execute(mode_query)
        modes = {}
        for row in mode_result.fetchall():
            winners = row[2] or 0
            losers = row[3] or 0
            open_trades = row[4] or 0
            closed_total = winners + losers
            win_rate = round(winners / closed_total * 100, 1) if closed_total > 0 else 0
            modes[row[0]] = {
                "count": row[1],
                "winners": winners,
                "losers": losers,
                "open_trades": open_trades,
                "win_rate": win_rate
            }

        # Get ticker breakdown - use so.is_winner as primary source, fallback to el.pnl
        ticker_query = text("""
            SELECT
                sl.ticker,
                COUNT(*) as trades,
                SUM(CASE WHEN so.is_winner = true OR (so.is_winner IS NULL AND el.pnl > 0) THEN 1 ELSE 0 END) as winners,
                SUM(CASE WHEN so.is_winner = false OR (so.is_winner IS NULL AND el.pnl < 0) THEN 1 ELSE 0 END) as losers,
                SUM(COALESCE(so.pnl, el.pnl, 0)) as total_pnl
            FROM execution_logs el
            JOIN smartflow_signal_logs sl ON el.smartflow_signal_log_id = sl.id
            LEFT JOIN smartflow_signal_outcomes so ON so.signal_log_id = sl.id
            WHERE el.status = 'success' AND el.action IN ('BUY', 'SELL')
            GROUP BY sl.ticker
            ORDER BY trades DESC
            LIMIT 10
        """)
        ticker_result = db.execute(ticker_query)
        tickers = {}
        for row in ticker_result.fetchall():
            winners = row[2] or 0
            losers = row[3] or 0
            closed_total = winners + losers
            tickers[row[0]] = {
                "trades": row[1],
                "winners": winners,
                "losers": losers,
                "total_pnl": round(row[4] or 0, 2),
                "win_rate": round(winners / closed_total * 100, 1) if closed_total > 0 else 0
            }

        # Get recent performance - use so.is_winner as primary source, fallback to el.pnl
        recent_query = text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN so.is_winner = true OR (so.is_winner IS NULL AND el.pnl > 0) THEN 1 ELSE 0 END) as winners,
                SUM(CASE WHEN so.is_winner = false OR (so.is_winner IS NULL AND el.pnl < 0) THEN 1 ELSE 0 END) as losers,
                SUM(COALESCE(so.pnl, el.pnl, 0)) as total_pnl,
                SUM(CASE WHEN so.is_winner IS NULL AND (el.pnl IS NULL OR el.pnl = 0) THEN 1 ELSE 0 END) as open_trades
            FROM execution_logs el
            JOIN smartflow_signal_logs sl ON el.smartflow_signal_log_id = sl.id
            LEFT JOIN smartflow_signal_outcomes so ON so.signal_log_id = sl.id
            WHERE el.status = 'success'
              AND el.action IN ('BUY', 'SELL')
              AND el.created_at > NOW() - INTERVAL '7 days'
        """)
        recent = db.execute(recent_query).fetchone()

        winners = recent[1] or 0
        losers = recent[2] or 0
        closed_total = winners + losers

        return {
            "by_mode": modes,
            "by_ticker": tickers,
            "last_7_days": {
                "total_trades": recent[0] or 0,
                "winners": winners,
                "losers": losers,
                "open_trades": recent[4] or 0,
                "win_rate": round(winners / closed_total * 100, 1) if closed_total > 0 else 0,
                "total_pnl": round(recent[3] or 0, 2)
            }
        }

    except Exception as e:
        logger.error(f"Error fetching trade decision stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch stats: {str(e)}"
        )


@router.get("/deterministic/performance")
async def get_deterministic_performance(
    days: int = 30,
    symbol: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get deterministic strategy performance metrics from trade_journal.

    Returns comprehensive stats for forward testing validation:
    - Win rate, profit factor, expectancy
    - By symbol breakdown
    - By direction (long/short)
    - Recent trend analysis

    Target metrics:
    - Win Rate: >52%
    - Profit Factor: >1.5
    - Expectancy: >0
    """
    from sqlalchemy import text

    try:
        # Build symbol filter
        symbol_filter = "AND symbol = :symbol" if symbol else ""
        params = {"days": days}
        if symbol:
            params["symbol"] = symbol

        # Overall performance
        overall_query = text(f"""
            WITH metrics AS (
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as winners,
                    SUM(CASE WHEN net_pnl < 0 THEN 1 ELSE 0 END) as losers,
                    SUM(net_pnl) as total_pnl,
                    SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END) as gross_profit,
                    ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)) as gross_loss,
                    AVG(CASE WHEN net_pnl > 0 THEN net_pnl END) as avg_win,
                    AVG(CASE WHEN net_pnl < 0 THEN net_pnl END) as avg_loss,
                    MAX(net_pnl) as largest_win,
                    MIN(net_pnl) as largest_loss
                FROM trade_journal
                WHERE net_pnl IS NOT NULL
                  AND entry_time > NOW() - INTERVAL '{days} days'
                  {symbol_filter}
            )
            SELECT
                total_trades,
                winners,
                losers,
                ROUND(100.0 * winners / NULLIF(total_trades, 0), 2) as win_rate,
                ROUND(total_pnl::numeric, 2) as total_pnl,
                ROUND((gross_profit / NULLIF(gross_loss, 0))::numeric, 2) as profit_factor,
                ROUND(avg_win::numeric, 2) as avg_win,
                ROUND(avg_loss::numeric, 2) as avg_loss,
                ROUND((total_pnl / NULLIF(total_trades, 0))::numeric, 2) as expectancy,
                ROUND(largest_win::numeric, 2) as largest_win,
                ROUND(largest_loss::numeric, 2) as largest_loss
            FROM metrics
        """)
        overall = db.execute(overall_query, params).fetchone()

        # By symbol
        symbol_query = text(f"""
            SELECT
                symbol,
                COUNT(*) as trades,
                SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as wins,
                ROUND(100.0 * SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) as win_rate,
                ROUND(SUM(net_pnl)::numeric, 2) as total_pnl,
                ROUND((SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END) /
                    NULLIF(ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)), 0))::numeric, 2) as pf
            FROM trade_journal
            WHERE net_pnl IS NOT NULL
              AND entry_time > NOW() - INTERVAL '{days} days'
            GROUP BY symbol
            ORDER BY total_pnl DESC
            LIMIT 15
        """)
        symbols_result = db.execute(symbol_query).fetchall()
        by_symbol = {row[0]: {
            "trades": row[1], "wins": row[2], "win_rate": row[3],
            "total_pnl": row[4], "profit_factor": row[5]
        } for row in symbols_result}

        # By direction
        direction_query = text(f"""
            SELECT
                side,
                COUNT(*) as trades,
                SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as wins,
                ROUND(100.0 * SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) as win_rate,
                ROUND(SUM(net_pnl)::numeric, 2) as total_pnl,
                ROUND((SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END) /
                    NULLIF(ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)), 0))::numeric, 2) as pf
            FROM trade_journal
            WHERE net_pnl IS NOT NULL
              AND entry_time > NOW() - INTERVAL '{days} days'
              {symbol_filter}
            GROUP BY side
        """)
        direction_result = db.execute(direction_query, params).fetchall()
        by_direction = {row[0]: {
            "trades": row[1], "wins": row[2], "win_rate": row[3],
            "total_pnl": row[4], "profit_factor": row[5]
        } for row in direction_result}

        # Daily PnL trend (last 7 days)
        daily_query = text(f"""
            SELECT
                DATE(entry_time) as trade_date,
                COUNT(*) as trades,
                SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as wins,
                ROUND(SUM(net_pnl)::numeric, 2) as pnl
            FROM trade_journal
            WHERE net_pnl IS NOT NULL
              AND entry_time > NOW() - INTERVAL '7 days'
              {symbol_filter}
            GROUP BY DATE(entry_time)
            ORDER BY trade_date DESC
            LIMIT 7
        """)
        daily_result = db.execute(daily_query, params).fetchall()
        daily_pnl = [{
            "date": row[0].isoformat() if row[0] else None,
            "trades": row[1], "wins": row[2], "pnl": row[3]
        } for row in daily_result]

        # Health check against targets
        win_rate = overall[3] or 0 if overall else 0
        profit_factor = overall[5] or 0 if overall else 0
        expectancy = overall[8] or 0 if overall else 0

        health = {
            "win_rate": {"value": win_rate, "target": 52, "pass": win_rate >= 52},
            "profit_factor": {"value": profit_factor, "target": 1.5, "pass": profit_factor >= 1.5},
            "expectancy": {"value": expectancy, "target": 0, "pass": expectancy > 0}
        }

        return {
            "period_days": days,
            "overall": {
                "total_trades": overall[0] or 0 if overall else 0,
                "winners": overall[1] or 0 if overall else 0,
                "losers": overall[2] or 0 if overall else 0,
                "win_rate": win_rate,
                "total_pnl": overall[4] or 0 if overall else 0,
                "profit_factor": profit_factor,
                "avg_win": overall[6] or 0 if overall else 0,
                "avg_loss": overall[7] or 0 if overall else 0,
                "expectancy": expectancy,
                "largest_win": overall[9] or 0 if overall else 0,
                "largest_loss": overall[10] or 0 if overall else 0
            },
            "by_symbol": by_symbol,
            "by_direction": by_direction,
            "daily_pnl": daily_pnl,
            "health": health,
            "targets": {
                "win_rate": ">52%",
                "profit_factor": ">1.5",
                "expectancy": ">0"
            }
        }

    except Exception as e:
        logger.error(f"Error fetching deterministic performance: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch performance: {str(e)}"
        )


@router.get("/ai/analysis/{analysis_id}")
async def get_ai_analysis_detail(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed AI analysis by ID.
    """
    from sqlalchemy import text

    try:
        query = text("""
            SELECT id, ticker, analysis_type, recommendation, confidence,
                   summary, data, created_at, hit_count
            FROM ai_strategy_cache
            WHERE id = :id
        """)

        result = db.execute(query, {"id": analysis_id})
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Analysis not found")

        return {
            "id": row[0],
            "ticker": row[1],
            "analysis_type": row[2],
            "recommendation": row[3],
            "confidence": row[4],
            "summary": row[5],
            "data": row[6],
            "created_at": row[7].isoformat() if row[7] else None,
            "hit_count": row[8]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching AI analysis detail: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch AI analysis: {str(e)}"
        )


# ============================================================================
# ELITE DASHBOARD ENDPOINTS (SmartFlow 2026)
# ============================================================================

@router.get("/elite/overview")
async def get_elite_overview(
    days: int = 90,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get Elite Dashboard overview data including:
    - Regime detection probabilities
    - Risk metrics (CVaR, drawdown)
    - Feature importance
    - Recent performance summary
    """
    from sqlalchemy import text
    import numpy as np

    try:
        # Initialize response
        response = {
            "regime": {},
            "risk": {},
            "features": [],
            "performance": {},
            "ensemble_signals": [],
            "timestamp": datetime.utcnow().isoformat()
        }

        # Try to get regime detection data
        try:
            from app.services.regime_detector import get_regime_detector
            detector = get_regime_detector()
            probs = detector.get_regime_probabilities()
            current_regime = detector.current_regime

            response["regime"] = {
                "current": current_regime,
                "probabilities": {
                    "trending_up": probs.get("trending_up", 0.0),
                    "trending_down": probs.get("trending_down", 0.0),
                    "mean_reverting": probs.get("mean_reverting", 0.0),
                    "vol_expansion": probs.get("vol_expansion", 0.0),
                    "vol_contraction": probs.get("vol_contraction", 0.0),
                    "chaotic": probs.get("chaotic", 0.0),
                }
            }
        except Exception as e:
            logger.debug(f"Regime detector not available: {e}")
            response["regime"] = {
                "current": "unknown",
                "probabilities": {}
            }

        # Try to get risk metrics
        try:
            from app.services.advanced_risk import get_advanced_risk_manager
            risk_manager = get_advanced_risk_manager()
            status = risk_manager.get_status()

            response["risk"] = {
                "active_positions": status.get("active_positions", 0),
                "total_exposure_pct": status.get("total_exposure_pct", 0.0),
                "current_drawdown": status.get("current_drawdown_pct", 0.0),
                "max_drawdown": status.get("max_drawdown_pct", 0.0),
                "kelly_fraction": status.get("kelly_fraction", 0.0),
                "sector_exposure": status.get("sector_exposure", {}),
            }

            # Try to calculate CVaR for MES
            try:
                cvar = risk_manager.calculate_cvar("MES", 25000)
                response["risk"]["cvar_95"] = cvar.cvar_95 * 100 if cvar else 0.0
            except:
                response["risk"]["cvar_95"] = 0.0

        except Exception as e:
            logger.debug(f"Risk manager not available: {e}")
            response["risk"] = {
                "active_positions": 0,
                "total_exposure_pct": 0.0,
                "current_drawdown": 0.0,
                "max_drawdown": 0.0,
                "cvar_95": 0.0
            }

        # Try to get feature importance
        try:
            from app.services.feature_importance_tracker import get_importance_tracker
            tracker = get_importance_tracker()
            latest = tracker.get_latest_importances()

            if latest:
                response["features"] = [
                    {
                        "feature": feat,
                        "importance": imp,
                        "change": 0.0,  # Would need historical data
                        "is_critical": imp > 0.10
                    }
                    for feat, imp in sorted(latest.items(), key=lambda x: -x[1])[:8]
                ]
        except Exception as e:
            logger.debug(f"Feature tracker not available: {e}")
            response["features"] = []

        # Get performance from trade_journal
        try:
            perf_query = text("""
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as winners,
                    SUM(CASE WHEN net_pnl < 0 THEN 1 ELSE 0 END) as losers,
                    SUM(net_pnl) as total_pnl,
                    SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END) as gross_profit,
                    ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)) as gross_loss,
                    AVG(net_pnl) as avg_trade,
                    STDDEV(net_pnl) as std_pnl
                FROM trade_journal
                WHERE net_pnl IS NOT NULL
                  AND entry_time > NOW() - (INTERVAL '1 day' * :days)
            """)
            result = db.execute(perf_query, {"days": days})
            row = result.fetchone()

            if row and row[0] > 0:
                win_rate = (row[1] or 0) / row[0] * 100 if row[0] > 0 else 0
                profit_factor = (row[4] or 0) / row[5] if row[5] and row[5] > 0 else 0
                avg_trade = row[6] or 0
                std_pnl = row[7] or 1

                # Estimate Sharpe (annualized)
                sharpe = (avg_trade / std_pnl) * np.sqrt(252) if std_pnl > 0 else 0

                response["performance"] = {
                    "total_trades": row[0] or 0,
                    "win_rate": round(win_rate, 1),
                    "profit_factor": round(profit_factor, 2),
                    "total_pnl": round(row[3] or 0, 2),
                    "sharpe_ratio": round(sharpe, 2),
                    "expectancy": round(avg_trade, 2),
                    "max_drawdown": response["risk"].get("max_drawdown", 0.0)
                }
            else:
                response["performance"] = {
                    "total_trades": 0,
                    "win_rate": 0.0,
                    "profit_factor": 0.0,
                    "total_pnl": 0.0,
                    "sharpe_ratio": 0.0,
                    "expectancy": 0.0,
                    "max_drawdown": 0.0
                }
        except Exception as e:
            logger.debug(f"Could not fetch performance: {e}")
            response["performance"] = {}

        return response

    except Exception as e:
        logger.error(f"Error fetching elite overview: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch elite overview: {str(e)}"
        )


@router.get("/elite/equity-curve")
async def get_elite_equity_curve(
    days: int = 90,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get equity curve data for charting.
    """
    from sqlalchemy import text

    try:
        query = text("""
            WITH daily_pnl AS (
                SELECT
                    DATE(entry_time) as trade_date,
                    SUM(net_pnl) as daily_pnl
                FROM trade_journal
                WHERE net_pnl IS NOT NULL
                  AND entry_time > NOW() - (INTERVAL '1 day' * :days)
                GROUP BY DATE(entry_time)
                ORDER BY trade_date
            ),
            cumulative AS (
                SELECT
                    trade_date,
                    daily_pnl,
                    SUM(daily_pnl) OVER (ORDER BY trade_date) as cumulative_pnl
                FROM daily_pnl
            )
            SELECT
                trade_date,
                daily_pnl,
                cumulative_pnl,
                25000 + cumulative_pnl as equity
            FROM cumulative
            ORDER BY trade_date
        """)

        result = db.execute(query, {"days": days})
        rows = result.fetchall()

        equity_curve = []
        drawdown_history = []
        peak = 25000

        for row in rows:
            equity = float(row[3]) if row[3] else 25000

            # Track drawdown
            if equity > peak:
                peak = equity
            dd = ((peak - equity) / peak) * 100 if peak > 0 else 0

            equity_curve.append({
                "date": row[0].isoformat() if row[0] else None,
                "equity": round(equity, 2),
                "daily_pnl": round(float(row[1]) if row[1] else 0, 2)
            })

            drawdown_history.append({
                "date": row[0].isoformat() if row[0] else None,
                "drawdown": round(dd, 2)
            })

        return {
            "equity_curve": equity_curve,
            "drawdown_history": drawdown_history,
            "starting_capital": 25000
        }

    except Exception as e:
        logger.error(f"Error fetching equity curve: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch equity curve: {str(e)}"
        )


@router.get("/elite/regime-performance")
async def get_elite_regime_performance(
    days: int = 90,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get performance breakdown by market regime.
    """
    from sqlalchemy import text

    try:
        # Try to get regime data - simplified since signal_journal_id may not exist
        query = text("""
            SELECT
                'unknown' as regime,
                COUNT(*) as trades,
                SUM(CASE WHEN tj.net_pnl > 0 THEN 1 ELSE 0 END) as winners,
                ROUND(SUM(tj.net_pnl)::numeric, 2) as total_pnl
            FROM trade_journal tj
            WHERE tj.net_pnl IS NOT NULL
              AND tj.entry_time > NOW() - (INTERVAL '1 day' * :days)
            GROUP BY 'unknown'
            ORDER BY total_pnl DESC
        """)

        result = db.execute(query, {"days": days})
        rows = result.fetchall()

        regimes = []
        for row in rows:
            win_rate = (row[2] / row[1] * 100) if row[1] > 0 else 0
            regimes.append({
                "regime": row[0],
                "trades": row[1],
                "win_rate": round(win_rate, 1),
                "total_pnl": float(row[3]) if row[3] else 0
            })

        return {"regime_performance": regimes}

    except Exception as e:
        logger.error(f"Error fetching regime performance: {e}")
        return {"regime_performance": []}


@router.get("/elite/recent-trades")
async def get_elite_recent_trades(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get recent trades for the Elite Dashboard trades table.
    """
    from sqlalchemy import text

    try:
        query = text("""
            SELECT
                tj.id,
                tj.entry_time,
                tj.symbol,
                tj.side,
                tj.entry_price,
                tj.exit_price,
                tj.net_pnl,
                'unknown' as regime
            FROM trade_journal tj
            WHERE tj.net_pnl IS NOT NULL
            ORDER BY tj.entry_time DESC
            LIMIT :limit
        """)

        result = db.execute(query, {"limit": limit})
        rows = result.fetchall()

        trades = []
        for row in rows:
            pnl = float(row[6]) if row[6] else 0
            trades.append({
                "id": str(row[0]),
                "timestamp": row[1].strftime("%Y-%m-%d %H:%M") if row[1] else "",
                "ticker": row[2],
                "direction": "long" if row[3] == "BUY" else "short",
                "entry_price": float(row[4]) if row[4] else 0,
                "exit_price": float(row[5]) if row[5] else 0,
                "pnl": round(pnl, 2),
                "regime": row[7],
                "is_winner": pnl > 0
            })

        return {"trades": trades}

    except Exception as e:
        logger.error(f"Error fetching recent trades: {e}")
        return {"trades": []}


@router.post("/elite/run-backtest")
async def run_elite_backtest(
    ticker: str = "MES",
    days: int = 90,
    initial_capital: float = 25000,
    current_user: User = Depends(require_smartflow_tier),
    db: Session = Depends(get_db)
):
    """
    Run a backtest using the SmartFlow Elite Backtest Engine.

    Parameters:
    - ticker: Instrument to backtest (MES, MNQ, etc.)
    - days: Number of days of historical data
    - initial_capital: Starting capital

    Returns comprehensive backtest metrics.
    """
    try:
        from app.services.smartflow_backtest import SmartFlowBacktester

        # Create backtester
        bt = SmartFlowBacktester(initial_capital=initial_capital)

        # Run backtest
        results = await bt.run_backtest(ticker=ticker, days=days)

        if results:
            return {
                "status": "success",
                "ticker": ticker,
                "days": days,
                "metrics": asdict(results.metrics) if hasattr(results, 'metrics') else {},
                "trade_count": len(results.trades) if hasattr(results, 'trades') else 0,
                "message": f"Backtest completed for {ticker} over {days} days"
            }
        else:
            return {
                "status": "error",
                "message": "Backtest did not return results - check data availability"
            }

    except ImportError as e:
        logger.error(f"Backtest engine import error: {e}")
        return {
            "status": "error",
            "message": f"Backtest engine not available: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run backtest: {str(e)}"
        )


@router.get("/elite/backtest-results")
async def get_backtest_results(
    current_user: User = Depends(get_current_user)
):
    """
    Get latest backtest results from file cache.
    """
    try:
        # Use /app in container, or current directory for local dev
        results_file = "/app/backtest_results.json" if os.path.exists("/app") else "backtest_results.json"
        if os.path.exists(results_file):
            with open(results_file, 'r') as f:
                return json.load(f)
        else:
            return {
                "status": "no_results",
                "message": "No backtest results found. Run a backtest first."
            }
    except Exception as e:
        logger.error(f"Error loading backtest results: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================================
# Forward Test Trades API (Full Audit Trail with Decision Snapshots)
# ============================================================================

@router.get("/forward-test/trades")
async def get_forward_test_trades(
    limit: int = 50,
    ticker: Optional[str] = None,
    session_id: Optional[str] = None,
    include_open: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get forward test trades with full audit trail and decision snapshots.

    Returns trades from forward_test_trades table with complete decision context:
    - Entry/exit details with precise timing
    - Regime detection at entry (ADX, Hurst, ATR)
    - Strategy selection (why this stop%/target%)
    - Signal thresholds that passed/failed
    - Full raw snapshot for debugging

    Query parameters:
    - limit: Maximum trades to return (default 50)
    - ticker: Filter by symbol (e.g., BTCUSD)
    - session_id: Filter by session (e.g., FT_20260314_170424)
    - include_open: Include open trades (default true)
    """
    from sqlalchemy import text

    try:
        # Query from forward_test_trades table (new schema with full snapshots)
        query = """
            SELECT
                id, trade_id, session_id, signal_id, correlation_id,
                symbol, side, direction, entry_time, entry_price,
                exit_time, exit_price, exit_reason,
                stop_loss, take_profit, trailing_stop,
                pnl, pnl_pct, status, size,
                is_pyramid, pyramid_level, parent_trade_id,
                regime, regime_confidence,
                adx, hurst, atr, atr_pct, rsi,
                price_change_24h, volume_ratio, compression_flag, breakout_flag,
                probability, signal_strength, confidence_score,
                strategy_mode, stop_pct_used, target_pct_used, size_multiplier,
                min_prob_threshold, min_strength_threshold, threshold_passed,
                engine_type,
                raw_snapshot, created_at, updated_at
            FROM forward_test_trades
            WHERE 1=1
        """
        params = {"limit": limit}

        if ticker:
            query += " AND symbol = :ticker"
            params["ticker"] = ticker.upper()

        if session_id:
            query += " AND session_id = :session_id"
            params["session_id"] = session_id

        if not include_open:
            query += " AND status = 'closed'"

        query += " ORDER BY entry_time DESC LIMIT :limit"

        result = db.execute(text(query), params)
        rows = result.fetchall()

        trades = []
        for row in rows:
            trades.append({
                # Correlation fields
                "id": row[0],
                "trade_id": row[1],
                "session_id": row[2],
                "signal_id": row[3],
                "correlation_id": row[4],

                # Trade basics
                "symbol": row[5],
                "side": row[6],
                "direction": row[7],
                "entry_time": row[8].isoformat() if row[8] else None,
                "entry_price": float(row[9]) if row[9] else 0,
                "exit_time": row[10].isoformat() if row[10] else None,
                "exit_price": float(row[11]) if row[11] else None,
                "exit_reason": row[12],

                # Risk levels
                "stop_loss": float(row[13]) if row[13] else None,
                "take_profit": float(row[14]) if row[14] else None,
                "trailing_stop": float(row[15]) if row[15] else None,

                # P&L
                "pnl": float(row[16]) if row[16] else None,
                "pnl_pct": float(row[17]) if row[17] else None,
                "status": row[18],
                "size": float(row[19]) if row[19] else 1.0,

                # Pyramid info
                "is_pyramid": row[20],
                "pyramid_level": row[21],
                "parent_trade_id": row[22],

                # Decision snapshot - Regime
                "regime": row[23],
                "regime_confidence": float(row[24]) if row[24] else None,

                # Decision snapshot - Indicators
                "indicators": {
                    "adx": float(row[25]) if row[25] else None,
                    "hurst": float(row[26]) if row[26] else None,
                    "atr": float(row[27]) if row[27] else None,
                    "atr_pct": float(row[28]) if row[28] else None,
                    "rsi": float(row[29]) if row[29] else None,
                    "price_change_24h": float(row[30]) if row[30] else None,
                    "volume_ratio": float(row[31]) if row[31] else None,
                    "compression_flag": row[32],
                    "breakout_flag": row[33],
                },

                # Decision snapshot - Scoring
                "scoring": {
                    "probability": float(row[34]) if row[34] else None,
                    "signal_strength": float(row[35]) if row[35] else None,
                    "confidence_score": float(row[36]) if row[36] else None,
                },

                # Decision snapshot - Strategy selection
                "strategy": {
                    "mode": row[37],
                    "stop_pct_used": float(row[38]) if row[38] else None,
                    "target_pct_used": float(row[39]) if row[39] else None,
                    "size_multiplier": float(row[40]) if row[40] else 1.0,
                },

                # Decision snapshot - Thresholds
                "thresholds": {
                    "min_prob": float(row[41]) if row[41] else None,
                    "min_strength": float(row[42]) if row[42] else None,
                    "passed": row[43],
                },

                # Engine Source (Phase 0.5)
                "engine_type": row[44],

                # Raw debug snapshot
                "raw_snapshot": row[45],

                # Metadata
                "created_at": row[46].isoformat() if row[46] else None,
                "updated_at": row[47].isoformat() if row[47] else None,

                "is_forward_test": True,
            })

        # Calculate summary stats
        closed_trades = [t for t in trades if t["pnl"] is not None]
        wins = sum(1 for t in closed_trades if t["pnl"] and t["pnl"] > 0)
        losses = sum(1 for t in closed_trades if t["pnl"] and t["pnl"] < 0)
        total_pnl = sum(t["pnl"] for t in closed_trades if t["pnl"])

        # Regime breakdown
        regime_stats = {}
        for t in closed_trades:
            regime = t.get("regime") or "unknown"
            if regime not in regime_stats:
                regime_stats[regime] = {"trades": 0, "wins": 0, "pnl": 0}
            regime_stats[regime]["trades"] += 1
            if t["pnl"] and t["pnl"] > 0:
                regime_stats[regime]["wins"] += 1
            regime_stats[regime]["pnl"] += t["pnl"] or 0

        # Get unique sessions
        sessions = list(set(t["session_id"] for t in trades if t["session_id"]))

        return {
            "trades": trades,
            "summary": {
                "total_trades": len(trades),
                "closed_trades": len(closed_trades),
                "open_trades": len(trades) - len(closed_trades),
                "wins": wins,
                "losses": losses,
                "win_rate": round((wins / len(closed_trades) * 100), 1) if closed_trades else 0,
                "total_pnl": round(total_pnl, 2),
                "avg_pnl": round(total_pnl / len(closed_trades), 2) if closed_trades else 0,
            },
            "by_regime": regime_stats,
            "sessions": sessions,
        }

    except Exception as e:
        logger.error(f"Error fetching forward test trades: {e}")
        # Fallback to legacy query if new table doesn't exist
        return await _get_legacy_forward_test_trades(db, limit, ticker, include_open)


async def _get_legacy_forward_test_trades(db: Session, limit: int, ticker: Optional[str], include_open: bool):
    """Fallback to legacy execution_logs table if forward_test_trades doesn't exist."""
    from sqlalchemy import text

    try:
        query = """
            SELECT id, symbol, action, entry_price, exit_price, pnl, pnl_pct,
                   status, close_reason, broker, created_at, closed_at
            FROM execution_logs
            WHERE status LIKE 'FT_%'
        """
        params = {"limit": limit}

        if ticker:
            query += " AND symbol = :ticker"
            params["ticker"] = ticker.upper()

        if not include_open:
            query += " AND exit_price IS NOT NULL"

        query += " ORDER BY created_at DESC LIMIT :limit"

        result = db.execute(text(query), params)
        rows = result.fetchall()

        trades = []
        for row in rows:
            status_parts = row[7].split('_') if row[7] else []
            trade_id = '_'.join(status_parts[2:]) if len(status_parts) > 2 else row[7]

            trades.append({
                "id": row[0],
                "trade_id": trade_id,
                "symbol": row[1],
                "direction": "long" if row[2] == "buy" else "short",
                "entry_price": float(row[3]) if row[3] else 0,
                "exit_price": float(row[4]) if row[4] else None,
                "pnl": float(row[5]) if row[5] else None,
                "pnl_pct": float(row[6]) if row[6] else None,
                "exit_reason": row[8],
                "status": "closed" if row[4] else "open",
                "entry_time": row[10].isoformat() if row[10] else None,
                "exit_time": row[11].isoformat() if row[11] else None,
                "is_forward_test": True,
                "is_legacy": True,
            })

        closed_trades = [t for t in trades if t["pnl"] is not None]
        wins = sum(1 for t in closed_trades if t["pnl"] > 0)
        total_pnl = sum(t["pnl"] for t in closed_trades if t["pnl"])

        return {
            "trades": trades,
            "summary": {
                "total_trades": len(trades),
                "closed_trades": len(closed_trades),
                "open_trades": len(trades) - len(closed_trades),
                "wins": wins,
                "losses": len(closed_trades) - wins,
                "win_rate": (wins / len(closed_trades) * 100) if closed_trades else 0,
                "total_pnl": round(total_pnl, 2),
            },
            "is_legacy": True,
        }
    except Exception as e:
        logger.error(f"Error in legacy forward test query: {e}")
        return {"trades": [], "summary": {"error": str(e)}}


@router.get("/forward-test/status")
async def get_forward_test_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current forward test session status with recent signals.
    Now reads from DATABASE for live signal data (fixed stale file issue).
    """
    result = {
        "status": "active",  # SmartFlow is always running
        "recent_signals": [],
        "signal_stats": {"total_sent": 0, "total_failed": 0}
    }

    try:
        # Get user's SmartFlow config
        config = db.query(SmartFlowConfig).filter(SmartFlowConfig.user_id == current_user.id).first()

        if config:
            # Get recent signals from DATABASE (not stale file)
            from sqlalchemy import desc
            recent_signals = db.query(SmartFlowSignalLog).filter(
                SmartFlowSignalLog.config_id == config.id
            ).order_by(desc(SmartFlowSignalLog.created_at)).limit(50).all()

            # Transform to dashboard format - using actual model fields
            result["recent_signals"] = [
                {
                    "id": str(sig.id),
                    "ticker": sig.ticker,
                    "action": sig.action.upper() if sig.action else "UNKNOWN",
                    "price": float(sig.price) if sig.price else 0,
                    "score": float(sig.score) if sig.score else 0,
                    "strategy": sig.engine_type or "SmartFlow",
                    "confidence": float(sig.confidence) if sig.confidence else None,
                    "reason": sig.reason,
                    "timestamp": sig.created_at.isoformat() if sig.created_at else None,
                    "webhook_status": "sent" if sig.post_successful else "pending",
                    "source": sig.engine_type or "SmartFlow",
                    "bullish_flows": sig.bullish_flows or 0,
                    "bearish_flows": sig.bearish_flows or 0,
                    "total_premium": float(sig.total_premium) if sig.total_premium else 0,
                }
                for sig in recent_signals
            ]

            # Calculate stats using actual model fields
            total_signals = db.query(SmartFlowSignalLog).filter(
                SmartFlowSignalLog.config_id == config.id
            ).count()
            dispatched_signals = db.query(SmartFlowSignalLog).filter(
                SmartFlowSignalLog.config_id == config.id,
                SmartFlowSignalLog.post_successful == True
            ).count()

            result["signal_stats"] = {
                "total_sent": dispatched_signals,
                "total_generated": total_signals,
                "total_failed": total_signals - dispatched_signals
            }

            result["status"] = "active" if config.enabled else "paused"

        return result

    except Exception as e:
        logger.error(f"Error fetching forward test status: {e}")
        result["message"] = str(e)
        return result


# ============================================================================
# Backtesting Endpoints (Phase 1)
# ============================================================================

class BacktestRequest(BaseModel):
    """Request to run a backtest."""
    ticker: str = Field(default="MES", description="Symbol to backtest")
    days: int = Field(default=90, ge=1, le=365, description="Days of history to backtest")

    # Engine selection (Phase 2A)
    engine_type: str = Field(
        default="unified",
        description="Engine to backtest: 'unified', 'flow', 'ai', 'deterministic', 'quick'"
    )

    # Config overrides
    initial_capital: Optional[float] = Field(default=None, description="Starting capital")
    position_size_pct: Optional[float] = Field(default=None, description="Position size %")
    use_atr_stops: Optional[bool] = Field(default=None, description="Use ATR-based stops")
    atr_stop_mult: Optional[float] = Field(default=None, description="ATR stop multiplier")
    atr_target_mult: Optional[float] = Field(default=None, description="ATR target multiplier")
    use_pct_stops: Optional[bool] = Field(default=None, description="Use percentage stops")
    pct_stop: Optional[float] = Field(default=None, description="Stop loss %")
    pct_target: Optional[float] = Field(default=None, description="Take profit %")


class BacktestResponse(BaseModel):
    """Backtest results."""
    # Engine (Phase 2A)
    engine_type: str = Field(default="unified", description="Engine that was backtested")

    # Period
    start_date: str
    end_date: str
    trading_days: int

    # Returns
    total_return_pct: float
    cagr: float

    # Risk-adjusted
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float

    # Drawdown
    max_drawdown_pct: float
    avg_drawdown_pct: float

    # Trade stats
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float

    # P&L
    gross_profit: float
    gross_loss: float
    net_profit: float
    profit_factor: float
    expectancy: float

    # Trade metrics
    avg_trade: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_holding_time_hours: float

    # Costs
    total_slippage: float
    total_commission: float

    # Equity curve (last 100 points)
    equity_curve: List[Dict[str, Any]] = Field(default_factory=list)

    # Recent trades (last 20)
    trades: List[Dict[str, Any]] = Field(default_factory=list)


@router.post("/backtest/run", response_model=BacktestResponse)
async def run_backtest(
    request: BacktestRequest,
    current_user: User = Depends(require_smartflow_tier),
):
    """
    Run a backtest with specified parameters.

    This uses the SmartFlowBacktester with full regime detection,
    ensemble scoring, and advanced risk management.
    """
    try:
        from app.services.smartflow_backtest import SmartFlowBacktester, BacktestConfig

        # Create config with overrides
        config = BacktestConfig()
        if request.initial_capital is not None:
            config.initial_capital = request.initial_capital
        if request.position_size_pct is not None:
            config.position_size_pct = request.position_size_pct
        if request.use_atr_stops is not None:
            config.use_atr_stops = request.use_atr_stops
        if request.atr_stop_mult is not None:
            config.atr_stop_mult = request.atr_stop_mult
        if request.atr_target_mult is not None:
            config.atr_target_mult = request.atr_target_mult
        if request.use_pct_stops is not None:
            config.use_pct_stops = request.use_pct_stops
        if request.pct_stop is not None:
            config.pct_stop = request.pct_stop
        if request.pct_target is not None:
            config.pct_target = request.pct_target

        # Create backtester
        backtester = SmartFlowBacktester(config)

        # Run backtest
        logger.info(f"Running backtest: {request.ticker}, {request.days} days, engine={request.engine_type}")

        # NOTE: Currently all engines use the unified SmartFlow strategy
        # TODO Phase 2B: Implement engine-specific backtest routing
        # - 'flow': Use options flow signals
        # - 'ai': Use AI-only cycle logic
        # - 'deterministic': Use multi-timeframe indicators
        # - 'quick': Use 5m momentum logic
        # - 'unified': Use current ensemble strategy (default)

        metrics = await backtester.run_backtest(
            ticker=request.ticker,
            days=request.days
        )

        # Save results to file (use /app in container, or current directory for local dev)
        results_file = "/app/backtest_results.json" if os.path.exists("/app") else "backtest_results.json"
        backtester.export_results(results_file)
        logger.info(f"Backtest results saved to {results_file}")

        # Build response - convert numpy types to Python native types
        response = BacktestResponse(
            engine_type=request.engine_type,
            start_date=str(metrics.start_date),
            end_date=str(metrics.end_date),
            trading_days=int(metrics.trading_days),
            total_return_pct=float(metrics.total_return_pct),
            cagr=float(metrics.cagr),
            sharpe_ratio=float(metrics.sharpe_ratio),
            sortino_ratio=float(metrics.sortino_ratio),
            calmar_ratio=float(metrics.calmar_ratio),
            max_drawdown_pct=float(metrics.max_drawdown_pct),
            avg_drawdown_pct=float(metrics.avg_drawdown_pct),
            total_trades=int(metrics.total_trades),
            winning_trades=int(metrics.winning_trades),
            losing_trades=int(metrics.losing_trades),
            win_rate=float(metrics.win_rate),
            gross_profit=float(metrics.gross_profit),
            gross_loss=float(metrics.gross_loss),
            net_profit=float(metrics.net_profit),
            profit_factor=float(metrics.profit_factor),
            expectancy=float(metrics.expectancy),
            avg_trade=float(metrics.avg_trade),
            avg_win=float(metrics.avg_win),
            avg_loss=float(metrics.avg_loss),
            largest_win=float(metrics.largest_win),
            largest_loss=float(metrics.largest_loss),
            avg_holding_time_hours=float(metrics.avg_holding_time_hours),
            total_slippage=float(metrics.total_slippage),
            total_commission=float(metrics.total_commission),
            equity_curve=[
                {"timestamp": str(ts), "equity": float(eq)}
                for ts, eq in backtester.equity_curve[-100:]
            ],
            trades=[
                {
                    "entry_time": str(t.entry_time),
                    "exit_time": str(t.exit_time) if t.exit_time else None,
                    "ticker": t.ticker,
                    "direction": t.direction,
                    "entry_price": float(t.entry_price),
                    "exit_price": float(t.exit_price),
                    "net_pnl": float(t.net_pnl),
                    "pnl_pct": float(t.pnl_pct),
                    "regime": t.regime,
                    "is_winner": bool(t.is_winner),
                    "exit_reason": t.exit_reason,
                }
                for t in backtester.trades[-20:]
            ]
        )

        logger.info(f"Backtest complete: {metrics.total_trades} trades, {metrics.win_rate:.1f}% win rate, {metrics.sharpe_ratio:.2f} Sharpe")

        return response

    except ImportError as e:
        logger.error(f"Backtest dependencies not available: {e}")
        raise HTTPException(
            status_code=503,
            detail="Backtesting not available. Required dependencies not installed."
        )
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Backtest failed: {str(e)}"
        )


@router.get("/backtest/results", response_model=BacktestResponse)
async def get_backtest_results(
    current_user: User = Depends(require_smartflow_tier),
):
    """
    Get the most recent backtest results.

    Returns the last backtest run results from the JSON file.
    """
    try:
        # Use container path /app instead of hardcoded host path
        results_file = "/app/backtest_results.json"

        if not os.path.exists(results_file):
            raise HTTPException(
                status_code=404,
                detail="No backtest results found. Run a backtest first."
            )

        with open(results_file, 'r') as f:
            data = json.load(f)

        metrics = data.get('metrics', {})

        # Build response from saved data
        response = BacktestResponse(
            engine_type=data.get('engine_type', 'unified'),  # Phase 2A
            start_date=metrics.get('start_date', ''),
            end_date=metrics.get('end_date', ''),
            trading_days=metrics.get('trading_days', 0),
            total_return_pct=metrics.get('total_return_pct', 0.0),
            cagr=metrics.get('cagr', 0.0),
            sharpe_ratio=metrics.get('sharpe_ratio', 0.0),
            sortino_ratio=metrics.get('sortino_ratio', 0.0),
            calmar_ratio=metrics.get('calmar_ratio', 0.0),
            max_drawdown_pct=metrics.get('max_drawdown_pct', 0.0),
            avg_drawdown_pct=metrics.get('avg_drawdown_pct', 0.0),
            total_trades=metrics.get('total_trades', 0),
            winning_trades=metrics.get('winning_trades', 0),
            losing_trades=metrics.get('losing_trades', 0),
            win_rate=metrics.get('win_rate', 0.0),
            gross_profit=metrics.get('gross_profit', 0.0),
            gross_loss=metrics.get('gross_loss', 0.0),
            net_profit=metrics.get('net_profit', 0.0),
            profit_factor=metrics.get('profit_factor', 0.0),
            expectancy=metrics.get('expectancy', 0.0),
            avg_trade=metrics.get('avg_trade', 0.0),
            avg_win=metrics.get('avg_win', 0.0),
            avg_loss=metrics.get('avg_loss', 0.0),
            largest_win=metrics.get('largest_win', 0.0),
            largest_loss=metrics.get('largest_loss', 0.0),
            avg_holding_time_hours=metrics.get('avg_holding_time_hours', 0.0),
            total_slippage=metrics.get('total_slippage', 0.0),
            total_commission=metrics.get('total_commission', 0.0),
            equity_curve=data.get('equity_curve', [])[-100:],
            trades=data.get('trades', [])[-20:]
        )

        return response

    except HTTPException:
        # Re-raise HTTPExceptions (like 404) as-is
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="No backtest results found"
        )
    except Exception as e:
        logger.error(f"Error loading backtest results: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load results: {str(e)}"
        )


# ============================================================================
# Engine Comparison Endpoints (Phase 2B)
# ============================================================================

class ComparisonRequest(BaseModel):
    """Request to compare multiple engines."""
    ticker: str = Field(default="MES", description="Symbol to backtest")
    days: int = Field(default=90, ge=1, le=365, description="Days of history")
    engines: List[str] = Field(
        description="List of engines to compare",
        min_items=2,
        max_items=4
    )

    # Config overrides (same as BacktestRequest)
    initial_capital: Optional[float] = None
    position_size_pct: Optional[float] = None
    use_atr_stops: Optional[bool] = None
    atr_stop_mult: Optional[float] = None
    atr_target_mult: Optional[float] = None
    use_pct_stops: Optional[bool] = None
    pct_stop: Optional[float] = None
    pct_target: Optional[float] = None


class EngineMetadataResponse(BaseModel):
    """Execution honesty metadata for an engine."""
    requested_engine_type: str
    actual_execution_mode: str
    unified_fallback_used: bool
    routing_status: str
    notes: str = ""


class LeaderboardEntry(BaseModel):
    """Single engine's performance metrics."""
    rank: int
    engine: str
    total_return_pct: float
    net_profit: float
    sharpe_ratio: float
    win_rate: float
    max_drawdown_pct: float
    profit_factor: float
    total_trades: int
    avg_trade: float
    avg_holding_time_hours: float


class ComparisonResponse(BaseModel):
    """Results from engine comparison."""
    comparison_id: str
    timestamp: str

    # Inputs
    ticker: str
    start_date: str
    end_date: str
    initial_capital: float
    engines_compared: List[str]

    # Results
    leaderboard: List[LeaderboardEntry]
    engine_metadata: Dict[str, EngineMetadataResponse]
    regime_comparison: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    # Warnings (Phase 2B honesty)
    warnings: List[str] = Field(default_factory=list)


@router.post("/backtest/compare/run", response_model=ComparisonResponse)
async def run_engine_comparison(
    request: ComparisonRequest,
    current_user: User = Depends(require_smartflow_tier),
):
    """
    Compare multiple engines side-by-side under identical conditions.

    Phase 2B: Comparison framework with execution honesty tracking.

    IMPORTANT: Currently most engines use unified fallback strategy.
    Check the `engine_metadata` and `warnings` fields to see which
    engines have true implementation vs. fallback.
    """
    try:
        from app.services.backtesting import get_comparison_runner

        runner = get_comparison_runner()

        # Build config overrides
        config_overrides = {}
        if request.initial_capital is not None:
            config_overrides['initial_capital'] = request.initial_capital
        if request.position_size_pct is not None:
            config_overrides['position_size_pct'] = request.position_size_pct
        if request.use_atr_stops is not None:
            config_overrides['use_atr_stops'] = request.use_atr_stops
        if request.atr_stop_mult is not None:
            config_overrides['atr_stop_mult'] = request.atr_stop_mult
        if request.atr_target_mult is not None:
            config_overrides['atr_target_mult'] = request.atr_target_mult
        if request.use_pct_stops is not None:
            config_overrides['use_pct_stops'] = request.use_pct_stops
        if request.pct_stop is not None:
            config_overrides['pct_stop'] = request.pct_stop
        if request.pct_target is not None:
            config_overrides['pct_target'] = request.pct_target

        logger.info(f"Running engine comparison: {request.engines} on {request.ticker}")

        # Run comparison
        comparison = await runner.run_engine_comparison(
            ticker=request.ticker,
            days=request.days,
            engines=request.engines,
            config_overrides=config_overrides
        )

        # Build response
        response = ComparisonResponse(
            comparison_id=comparison.comparison_id,
            timestamp=comparison.timestamp.isoformat(),
            ticker=comparison.ticker,
            start_date=comparison.start_date,
            end_date=comparison.end_date,
            initial_capital=comparison.initial_capital,
            engines_compared=comparison.engines_compared,
            leaderboard=[
                LeaderboardEntry(**entry)
                for entry in comparison.leaderboard
            ],
            engine_metadata={
                engine: EngineMetadataResponse(
                    requested_engine_type=meta.requested_engine_type,
                    actual_execution_mode=meta.actual_execution_mode,
                    unified_fallback_used=meta.unified_fallback_used,
                    routing_status=meta.routing_status,
                    notes=meta.notes
                )
                for engine, meta in comparison.engine_metadata.items()
            },
            regime_comparison=comparison.regime_comparison,
            warnings=comparison.warnings
        )

        logger.info(f"Comparison complete: {len(comparison.engine_results)} engines compared")

        return response

    except Exception as e:
        logger.error(f"Engine comparison failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Comparison failed: {str(e)}"
        )


@router.get("/backtest/compare/status")
async def get_comparison_status(
    current_user: User = Depends(require_smartflow_tier),
):
    """
    Get status of comparison framework.

    Returns which engines have true implementation vs. fallback.
    """
    return {
        "framework_active": True,
        "supported_engines": ["unified", "flow", "ai", "deterministic", "quick"],
        "routing_status": {
            "unified": {
                "status": "fully_routed",
                "mode": "unified_strategy",
                "fallback": False,
                "notes": "Default unified strategy with regime detection"
            },
            "flow": {
                "status": "unified_fallback",
                "mode": "unified_fallback",
                "fallback": True,
                "notes": "Flow engine backtest not yet implemented - using unified fallback"
            },
            "ai": {
                "status": "unified_fallback",
                "mode": "unified_fallback",
                "fallback": True,
                "notes": "AI engine backtest not yet implemented - using unified fallback"
            },
            "deterministic": {
                "status": "unified_fallback",
                "mode": "unified_fallback",
                "fallback": True,
                "notes": "Deterministic engine backtest not yet implemented - using unified fallback"
            },
            "quick": {
                "status": "unified_fallback",
                "mode": "unified_fallback",
                "fallback": True,
                "notes": "Quick mode backtest not yet implemented - using unified fallback"
            }
        },
        "message": "Comparison framework active. Currently all non-unified engines use unified fallback strategy."
    }


@router.get("/backtest/compare/results/{comparison_id}")
async def get_comparison_results(
    comparison_id: str,
    current_user: User = Depends(require_smartflow_tier),
):
    """Get results from a specific comparison run."""
    try:
        from app.services.backtesting import get_comparison_runner

        runner = get_comparison_runner()
        comparison = runner.get_comparison(comparison_id)

        if not comparison:
            raise HTTPException(
                status_code=404,
                detail=f"Comparison {comparison_id} not found"
            )

        # Build response
        response = ComparisonResponse(
            comparison_id=comparison.comparison_id,
            timestamp=comparison.timestamp.isoformat(),
            ticker=comparison.ticker,
            start_date=comparison.start_date,
            end_date=comparison.end_date,
            initial_capital=comparison.initial_capital,
            engines_compared=comparison.engines_compared,
            leaderboard=[
                LeaderboardEntry(**entry)
                for entry in comparison.leaderboard
            ],
            engine_metadata={
                engine: EngineMetadataResponse(
                    requested_engine_type=meta.requested_engine_type,
                    actual_execution_mode=meta.actual_execution_mode,
                    unified_fallback_used=meta.unified_fallback_used,
                    routing_status=meta.routing_status,
                    notes=meta.notes
                )
                for engine, meta in comparison.engine_metadata.items()
            },
            regime_comparison=comparison.regime_comparison,
            warnings=comparison.warnings
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving comparison: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve comparison: {str(e)}"
        )


# ============================================================================
# PHASE 3: ADAPTIVE ENGINE ROUTER ENDPOINTS
# ============================================================================

class RouterModeRequest(BaseModel):
    """Request to change router mode."""
    mode: str = Field(..., description="Router mode: 'manual' or 'auto_by_regime'")


class RouterOverrideRequest(BaseModel):
    """Request to set manual engine override."""
    engine: Optional[str] = Field(None, description="Engine to override to, or null to clear")


class RouterStatusResponse(BaseModel):
    """Router status response."""
    routing_mode: str
    manual_override_engine: Optional[str]
    auto_eligible_engines: List[str]
    manual_only_engines: List[str]
    all_engines: List[str]
    comparison_rankings_available: List[str]
    fallback_rules_available: List[str]
    timestamp: str


class RegimeMappingResponse(BaseModel):
    """Regime-to-engine mapping response."""
    mappings: Dict[str, Any]


class RouterDecisionResponse(BaseModel):
    """Router decision response."""
    routing_mode: str
    current_regime: str
    selected_engine: str
    eligible_engines: List[str]
    ranking: List[str]
    decision_source: str
    decision_reason: str
    fallback_used: bool
    timestamp: str
    manual_override: Optional[str] = None
    regime_confidence: float = 0.0


@router.get(
    "/router/status",
    response_model=RouterStatusResponse,
    summary="Get Router Status",
    description="Get current adaptive router status and configuration"
)
async def get_router_status(
    current_user: User = Depends(require_smartflow_tier)
) -> RouterStatusResponse:
    """
    Get adaptive router status.

    Returns current routing mode, eligible engines, and available mappings.
    """
    try:
        from app.services.smartflow_engine_router import get_router

        router_instance = get_router()
        status = router_instance.get_router_status()

        return RouterStatusResponse(**status)

    except Exception as e:
        logger.error(f"Error getting router status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get router status: {str(e)}"
        )


@router.post(
    "/router/mode",
    response_model=RouterStatusResponse,
    summary="Set Router Mode",
    description="Set router operating mode (manual or auto_by_regime)"
)
async def set_router_mode(
    request: RouterModeRequest,
    current_user: User = Depends(require_smartflow_tier)
) -> RouterStatusResponse:
    """
    Set router operating mode.

    Modes:
    - manual: User selects engine explicitly
    - auto_by_regime: Router selects based on market regime
    """
    try:
        from app.services.smartflow_engine_router import get_router, RoutingMode

        router_instance = get_router()

        # Validate mode
        try:
            mode = RoutingMode(request.mode.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode: {request.mode}. Must be 'manual' or 'auto_by_regime'"
            )

        router_instance.set_routing_mode(mode)

        # Return updated status
        status = router_instance.get_router_status()
        return RouterStatusResponse(**status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting router mode: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set router mode: {str(e)}"
        )


@router.post(
    "/router/override",
    response_model=RouterStatusResponse,
    summary="Set Manual Override",
    description="Set manual engine override (or clear it)"
)
async def set_router_override(
    request: RouterOverrideRequest,
    current_user: User = Depends(require_smartflow_tier)
) -> RouterStatusResponse:
    """
    Set manual engine override.

    Pass engine name to force specific engine, or null to clear override.
    """
    try:
        from app.services.smartflow_engine_router import get_router

        router_instance = get_router()

        # Set override (None clears it)
        router_instance.set_manual_override(request.engine)

        # Return updated status
        status = router_instance.get_router_status()
        return RouterStatusResponse(**status)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error setting router override: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set router override: {str(e)}"
        )


@router.get(
    "/router/mapping",
    response_model=RegimeMappingResponse,
    summary="Get Regime Mapping",
    description="Get regime-to-engine mapping with sources"
)
async def get_regime_mapping(
    current_user: User = Depends(require_smartflow_tier)
) -> RegimeMappingResponse:
    """
    Get regime-to-engine mapping.

    Shows which engine is preferred for each regime,
    and whether that preference comes from comparison data or fallback rules.
    """
    try:
        from app.services.smartflow_engine_router import get_router

        router_instance = get_router()
        mappings = router_instance.get_regime_mapping()

        return RegimeMappingResponse(mappings=mappings)

    except Exception as e:
        logger.error(f"Error getting regime mapping: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get regime mapping: {str(e)}"
        )


@router.get(
    "/router/decision",
    response_model=RouterDecisionResponse,
    summary="Get Routing Decision",
    description="Get routing decision for current regime (test endpoint)"
)
async def get_routing_decision(
    regime: str = "neutral",
    regime_confidence: float = 0.0,
    current_user: User = Depends(require_smartflow_tier)
) -> RouterDecisionResponse:
    """
    Get routing decision for a specific regime.

    This is primarily a test endpoint to see what the router would choose
    for a given regime.
    """
    try:
        from app.services.smartflow_engine_router import get_router

        router_instance = get_router()
        decision = router_instance.route_signal_request(regime, regime_confidence)

        return RouterDecisionResponse(**decision.to_dict())

    except Exception as e:
        logger.error(f"Error getting routing decision: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get routing decision: {str(e)}"
        )


@router.post(
    "/router/refresh",
    summary="Refresh Router Rankings",
    description="Refresh router rankings from comparison store (Phase 4)"
)
async def refresh_router_rankings(
    current_user: User = Depends(require_smartflow_tier)
) -> Dict[str, Any]:
    """
    Refresh router rankings from comparison store.

    This reloads comparison data from the persistent store,
    updating the router with latest backtest results.

    Phase 4: Data-driven routing.
    """
    try:
        from app.services.smartflow_engine_router import get_router

        router_instance = get_router()
        updated_count = router_instance.refresh_comparison_rankings()

        return {
            "status": "success",
            "regimes_updated": updated_count,
            "message": f"Router refreshed with data for {updated_count} regimes"
        }

    except Exception as e:
        logger.error(f"Error refreshing router rankings: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh router rankings: {str(e)}"
        )


# ============================================================================
# Phase 9: Portfolio Allocator Endpoints
# ============================================================================

@router.get("/allocator/status")
async def get_allocator_status(db: Session = Depends(get_db)):
    """
    Get portfolio allocator status and configuration.

    Returns:
        Current allocator state, thresholds, and eligible strategy count
    """
    try:
        from app.services.strategy_allocator import StrategyAllocator

        allocator = StrategyAllocator(db)
        status = allocator.get_allocator_status()

        return {
            "status": "ok",
            **status
        }

    except Exception as e:
        logger.error(f"Error getting allocator status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get allocator status: {str(e)}"
        )


@router.get("/allocator/decision")
async def get_allocator_decision(
    strategy_ids: Optional[str] = None,
    engine_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get current allocation decision for strategies.

    Args:
        strategy_ids: Optional comma-separated list of strategy IDs to score
        engine_type: Optional engine type filter (deterministic, quick, etc.)

    Returns:
        Complete allocation decision with scores and weights
    """
    try:
        from app.services.strategy_allocator import StrategyAllocator
        from app.services.ai_feature_engine import get_ai_feature_engine

        # Parse strategy_ids if provided
        strategy_id_list = None
        if strategy_ids:
            strategy_id_list = [s.strip() for s in strategy_ids.split(',')]

        # Get AI features (optional)
        ai_features = None
        try:
            ai_engine = get_ai_feature_engine()
            ai_features = ai_engine.get_feature_dict('SPY')
        except:
            pass

        # Get allocation decision
        allocator = StrategyAllocator(db)
        decision = allocator.compute_allocation(
            strategy_ids=strategy_id_list,
            engine_type=engine_type,
            ai_features=ai_features
        )

        # Convert to response format
        return {
            "selected_strategies": [
                {
                    "strategy_id": s.strategy_id,
                    "engine_type": s.engine_type,
                    "allocation_weight": s.allocation_weight,
                    "adjusted_score": s.adjusted_score,
                    "raw_score": s.raw_score,
                    "sharpe_ratio": s.sharpe_ratio,
                    "win_rate": s.win_rate,
                    "max_drawdown": s.max_drawdown,
                    "health_status": s.health_status,
                    "health_multiplier": s.health_multiplier,
                    "ai_adjustment": s.ai_adjustment,
                    "forward_test_passed": s.forward_test_passed,
                    "notes": s.notes
                }
                for s in decision.selected_strategies
            ],
            "excluded_strategies": [
                {
                    "strategy_id": s.strategy_id,
                    "engine_type": s.engine_type,
                    "exclusion_reason": s.exclusion_reason.value if s.exclusion_reason else None,
                    "notes": s.notes
                }
                for s in decision.excluded_strategies
            ],
            "total_weight": decision.total_weight,
            "current_regime": decision.current_regime,
            "regime_confidence": decision.regime_confidence,
            "ai_features_used": decision.ai_features_used,
            "decision_source": decision.decision_source,
            "computed_at": decision.computed_at.isoformat(),
            "notes": decision.notes
        }

    except Exception as e:
        logger.error(f"Error computing allocation decision: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute allocation decision: {str(e)}"
        )


@router.get("/allocator/weights")
async def get_allocator_weights(
    strategy_ids: Optional[str] = None,
    engine_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get simplified allocation weights for strategies.

    Args:
        strategy_ids: Optional comma-separated list of strategy IDs to score
        engine_type: Optional engine type filter

    Returns:
        Dict of strategy_id -> weight mappings
    """
    try:
        from app.services.strategy_allocator import StrategyAllocator

        # Parse strategy_ids if provided
        strategy_id_list = None
        if strategy_ids:
            strategy_id_list = [s.strip() for s in strategy_ids.split(',')]

        # Get allocation decision
        allocator = StrategyAllocator(db)
        decision = allocator.compute_allocation(
            strategy_ids=strategy_id_list,
            engine_type=engine_type
        )

        # Build weights dict
        weights = {
            s.strategy_id: s.allocation_weight
            for s in decision.selected_strategies
        }

        return {
            "weights": weights,
            "total_weight": decision.total_weight,
            "selected_count": len(decision.selected_strategies),
            "excluded_count": len(decision.excluded_strategies),
            "computed_at": decision.computed_at.isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting allocation weights: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get allocation weights: {str(e)}"
        )


@router.get("/ai-features/status")
async def get_ai_features_status():
    """
    Get AI Feature Engine status.

    Returns:
        AI engine state and module availability
    """
    try:
        from app.services.ai_feature_engine import get_ai_feature_engine

        ai_engine = get_ai_feature_engine()
        status = ai_engine.get_engine_status()

        return {
            "status": "ok",
            **status
        }

    except Exception as e:
        logger.error(f"Error getting AI features status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get AI features status: {str(e)}"
        )


@router.get("/ai-features/{symbol}")
async def get_ai_features_for_symbol(
    symbol: str,
    regime: Optional[str] = None
):
    """
    Get AI features for a specific symbol.

    Args:
        symbol: Ticker symbol
        regime: Optional market regime context

    Returns:
        AI feature bundle with all computed features
    """
    try:
        from app.services.ai_feature_engine import get_ai_feature_engine

        ai_engine = get_ai_feature_engine()
        bundle = ai_engine.generate_features(symbol, regime)

        return {
            "symbol": bundle.symbol,
            "regime": bundle.regime,
            "technical_score": bundle.technical_score,
            "pattern_edge_score": bundle.pattern_edge_score,
            "macro_risk_score": bundle.macro_risk_score,
            "macro_bias_score": bundle.macro_bias_score,
            "earnings_sentiment_score": bundle.earnings_sentiment_score,
            "valuation_score": bundle.valuation_score,
            "competitive_strength_score": bundle.competitive_strength_score,
            "overall_ai_bias": bundle.overall_ai_bias,
            "confidence": bundle.confidence,
            "modules_used": bundle.modules_used,
            "computed_at": bundle.computed_at.isoformat(),
            "notes": bundle.notes
        }

    except Exception as e:
        logger.error(f"Error getting AI features for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get AI features: {str(e)}"
        )


# ==============================================================================
# UNIFIED FLOW FEATURE ENGINE ENDPOINTS
# ==============================================================================

@router.get("/flow/status")
async def get_flow_engine_status():
    """
    Get the status of the Unified Flow Feature Engine.

    Returns:
        Engine status including source availability and configuration.
    """
    try:
        from app.services.flow_feature_engine import get_flow_feature_engine

        engine = get_flow_feature_engine()
        status = engine.get_engine_status()

        return {
            "success": True,
            "engine": status["engine"],
            "version": status["version"],
            "sources": status["sources"],
            "cache_size": status["cache_size"],
            "flowalgo_host": status["flowalgo_host"],
            "strategy_weights": status["strategy_weights"]
        }

    except Exception as e:
        logger.error(f"Error getting flow engine status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get flow engine status: {str(e)}"
        )


@router.get("/flow/features/{symbol}")
async def get_flow_features_for_symbol(
    symbol: str,
    lookback_minutes: int = 30
):
    """
    Get unified flow features for a specific symbol.

    Args:
        symbol: Ticker symbol (e.g., SPY, US30, NAS100)
        lookback_minutes: How far back to look for flow data (default 30)

    Returns:
        Unified flow feature bundle with all sources normalized.
    """
    try:
        from app.services.flow_feature_engine import get_flow_feature_engine

        engine = get_flow_feature_engine()
        bundle = await engine.get_flow_feature_bundle(symbol, lookback_minutes)

        return {
            "success": True,
            "symbol": bundle.symbol,
            "timestamp": bundle.timestamp.isoformat(),
            "flow_sentiment": bundle.flow_sentiment,
            "flow_score": bundle.flow_score,
            "flow_confidence": bundle.flow_confidence,
            "net_premium_millions": bundle.net_premium_millions,
            "call_premium_millions": bundle.call_premium_millions,
            "put_premium_millions": bundle.put_premium_millions,
            "bull_bear_ratio": bundle.bull_bear_ratio,
            "call_put_imbalance": bundle.call_put_imbalance,
            "whale_count": bundle.whale_count,
            "sweep_count": bundle.sweep_count,
            "block_count": bundle.block_count,
            "total_trades": bundle.total_trades,
            "source_weights": bundle.source_weights,
            "source_agreement": bundle.source_agreement,
            "source_availability": bundle.source_availability,
            "individual_scores": {
                "unusual_whales": bundle.uw_score,
                "flowalgo": bundle.flowalgo_score,
                "polygon": bundle.polygon_score
            },
            "is_actionable": bundle.is_actionable,
            "notes": bundle.notes
        }

    except Exception as e:
        logger.error(f"Error getting flow features for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get flow features: {str(e)}"
        )


@router.get("/flow/features")
async def get_flow_features_multiple(
    symbols: str = "SPY,QQQ,DIA",
    lookback_minutes: int = 30
):
    """
    Get unified flow features for multiple symbols.

    Args:
        symbols: Comma-separated list of symbols
        lookback_minutes: How far back to look for flow data

    Returns:
        Dict of flow feature bundles keyed by symbol.
    """
    try:
        from app.services.flow_feature_engine import get_flow_feature_engine
        import asyncio

        engine = get_flow_feature_engine()
        symbol_list = [s.strip().upper() for s in symbols.split(",")]

        # Fetch all in parallel
        tasks = [
            engine.get_flow_feature_bundle(sym, lookback_minutes)
            for sym in symbol_list
        ]
        bundles = await asyncio.gather(*tasks, return_exceptions=True)

        results = {}
        for sym, bundle in zip(symbol_list, bundles):
            if isinstance(bundle, Exception):
                results[sym] = {"error": str(bundle)}
            else:
                results[sym] = {
                    "flow_sentiment": bundle.flow_sentiment,
                    "flow_score": bundle.flow_score,
                    "flow_confidence": bundle.flow_confidence,
                    "net_premium_millions": bundle.net_premium_millions,
                    "source_availability": bundle.source_availability,
                    "is_actionable": bundle.is_actionable
                }

        return {
            "success": True,
            "count": len(results),
            "features": results
        }

    except Exception as e:
        logger.error(f"Error getting multi-symbol flow features: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get flow features: {str(e)}"
        )


@router.get("/flow/sources")
async def get_flow_sources_status():
    """
    Get detailed status of all flow data sources.

    Returns:
        Status and health of each flow source (UW, FlowAlgo, Polygon).
    """
    try:
        from app.services.flow_feature_engine import get_flow_feature_engine

        engine = get_flow_feature_engine()
        status = engine.get_engine_status()

        # Test each source with SPY
        bundle = await engine.get_flow_feature_bundle("SPY", 15)

        return {
            "success": True,
            "sources": {
                "unusual_whales": {
                    "available": bundle.source_availability.get("unusual_whales", False),
                    "score": bundle.uw_score,
                    "weight": bundle.source_weights.get("unusual_whales", 0),
                    "status": status["sources"].get("unusual_whales", {})
                },
                "flowalgo": {
                    "available": bundle.source_availability.get("flowalgo", False),
                    "score": bundle.flowalgo_score,
                    "weight": bundle.source_weights.get("flowalgo", 0),
                    "status": status["sources"].get("flowalgo", {})
                },
                "polygon": {
                    "available": bundle.source_availability.get("polygon", False),
                    "score": bundle.polygon_score,
                    "weight": bundle.source_weights.get("polygon", 0),
                    "status": status["sources"].get("polygon", {})
                }
            },
            "test_symbol": "SPY",
            "combined_score": bundle.flow_score,
            "source_agreement": bundle.source_agreement
        }

    except Exception as e:
        logger.error(f"Error getting flow sources status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get flow sources: {str(e)}"
        )


@router.post("/flow/adjustment")
async def calculate_flow_adjustment(
    symbol: str = Body(...),
    direction: str = Body(...),  # 'long' or 'short'
    strategy_type: str = Body("unified")
):
    """
    Calculate the flow-based adjustment for a potential trade.

    Args:
        symbol: Ticker symbol
        direction: Trade direction ('long' or 'short')
        strategy_type: Strategy type for weighting

    Returns:
        Flow adjustment value and reasoning.
    """
    try:
        from app.services.flow_feature_engine import get_flow_feature_engine

        engine = get_flow_feature_engine()
        bundle = await engine.get_flow_feature_bundle(symbol, 30)
        adjustment, reason = engine.calculate_flow_adjustment(
            bundle, direction, strategy_type
        )

        return {
            "success": True,
            "symbol": symbol,
            "direction": direction,
            "strategy_type": strategy_type,
            "flow_adjustment": adjustment,
            "reason": reason,
            "flow_score": bundle.flow_score,
            "flow_confidence": bundle.flow_confidence,
            "strategy_weight": engine.get_strategy_flow_weight(strategy_type),
            "is_actionable": bundle.is_actionable
        }

    except Exception as e:
        logger.error(f"Error calculating flow adjustment: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate flow adjustment: {str(e)}"
        )


