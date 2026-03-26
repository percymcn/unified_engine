"""
Forward Test Models
===================

Dedicated table for forward test trades with full decision snapshots.
Enables complete audit trail and explains WHY each signal fired.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, Index
from sqlalchemy.sql import func
from datetime import datetime

from app.db.database import Base


class ForwardTestTrade(Base):
    """
    Complete forward test trade record with full decision snapshot.

    Each row captures the entire decision context at entry time,
    making it possible to explain why the signal fired.
    """
    __tablename__ = "forward_test_trades"
    __table_args__ = (
        Index('ix_ftt_session', 'session_id'),
        Index('ix_ftt_symbol', 'symbol'),
        Index('ix_ftt_entry_time', 'entry_time'),
        Index('ix_ftt_status', 'status'),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, index=True)

    # ========================================
    # CORRELATION FIELDS (for clean filtering/joins)
    # ========================================
    trade_id = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "BTCUSD_170425449898"
    session_id = Column(String(100), nullable=False, index=True)  # e.g., "FT_20260314_170424"
    signal_id = Column(String(100), nullable=True)  # Links to SmartFlowSignalLog if applicable
    correlation_id = Column(String(100), nullable=True)  # For grouping related trades/pyramids

    # ========================================
    # TRADE BASICS
    # ========================================
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # 'buy' or 'sell'
    direction = Column(String(10), nullable=False)  # 'long' or 'short'

    # Entry
    entry_time = Column(DateTime(timezone=True), nullable=False, default=func.now())
    entry_price = Column(Float, nullable=False)

    # Exit (null if still open)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    exit_price = Column(Float, nullable=True)
    exit_reason = Column(String(50), nullable=True)  # 'stop_loss', 'take_profit', 'manual', 'signal'

    # Risk Levels
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    trailing_stop = Column(Float, nullable=True)

    # P&L
    pnl = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)
    status = Column(String(20), default='open')  # 'open', 'closed', 'cancelled'

    # Position
    size = Column(Float, default=1.0)
    is_pyramid = Column(Boolean, default=False)
    pyramid_level = Column(Integer, default=0)
    parent_trade_id = Column(String(100), nullable=True)

    # ========================================
    # DECISION SNAPSHOT (explains WHY signal fired)
    # ========================================

    # Regime Detection
    regime = Column(String(50), nullable=True)  # 'trending_up', 'trending_down', 'ranging', 'volatile', 'breakout'
    regime_confidence = Column(Float, nullable=True)

    # Technical Indicators at Entry
    adx = Column(Float, nullable=True)  # ADX(14) value
    hurst = Column(Float, nullable=True)  # Hurst exponent (mean-reversion vs momentum)
    atr = Column(Float, nullable=True)  # ATR for volatility
    atr_pct = Column(Float, nullable=True)  # ATR as % of price
    rsi = Column(Float, nullable=True)  # RSI(14)

    # Price Action
    price_change_24h = Column(Float, nullable=True)  # 24h % change
    volume_ratio = Column(Float, nullable=True)  # Volume vs average
    compression_flag = Column(Boolean, default=False)  # Low volatility compression
    breakout_flag = Column(Boolean, default=False)  # Breakout detected

    # Ensemble Scoring
    probability = Column(Float, nullable=True)  # Ensemble probability (0-1)
    signal_strength = Column(Float, nullable=True)  # Signal strength (0-100)
    confidence_score = Column(Float, nullable=True)  # Combined confidence

    # Strategy Selection
    strategy_mode = Column(String(50), nullable=True)  # 'TRENDING', 'RANGING', 'VOLATILE', 'BREAKOUT'
    stop_pct_used = Column(Float, nullable=True)  # Actual stop % used (1%, 2%, etc.)
    target_pct_used = Column(Float, nullable=True)  # Actual target % used
    size_multiplier = Column(Float, default=1.0)  # Position size multiplier

    # Engine Source Tracking (Phase 0.5)
    engine_type = Column(String(50), nullable=True)  # 'flow', 'ai_enhancement', 'ai_only', 'deterministic', 'quick'

    # Threshold Checks
    min_prob_threshold = Column(Float, nullable=True)  # Threshold that was required
    min_strength_threshold = Column(Float, nullable=True)
    threshold_passed = Column(Boolean, default=True)  # Did it pass all thresholds?

    # ========================================
    # RAW SNAPSHOT (for debugging)
    # ========================================
    raw_snapshot = Column(JSON, nullable=True)  # Full JSON dump of all decision data

    # ========================================
    # METADATA
    # ========================================
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ForwardTestSession(Base):
    """
    Forward test session metadata.
    Groups trades by session for analytics.

    Phase 7: Extended with strategy linkage and forward-test gate tracking.
    """
    __tablename__ = "forward_test_sessions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)

    # Phase 7: Strategy Linkage (nullable for backward compatibility)
    strategy_id = Column(String, nullable=True, index=True)  # Links to smartflow_strategies.strategy_id

    # Session Config
    tickers = Column(JSON, nullable=False)  # List of tickers traded
    strategy_mode = Column(String(50), default='DYNAMIC')  # 'DYNAMIC', 'FIXED'
    initial_capital = Column(Float, default=25000.0)

    # Time
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    # Performance Summary
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_pnl = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)  # Phase 7: Added for gate criteria

    # Phase 7: Forward-Test Gate Decision
    gate_status = Column(String(20), nullable=True)  # 'in_progress', 'passed', 'failed', None
    gate_evaluated_at = Column(DateTime(timezone=True), nullable=True)
    gate_evaluated_by = Column(String, nullable=True)
    gate_decision_reason = Column(Text, nullable=True)
    gate_criteria_results = Column(JSON, nullable=True)  # Detailed gate evaluation results

    # Config Snapshot
    config_snapshot = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
