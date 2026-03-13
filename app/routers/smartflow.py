"""
SmartFlow API Router
====================

API endpoints for SmartFlow Indicator dashboard and configuration.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
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
