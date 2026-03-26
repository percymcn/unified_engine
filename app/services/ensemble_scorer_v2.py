"""
Elite Ensemble Meta-Model v2 - 2026 Best Practices
===================================================

LightGBM/XGBoost classifier with rich feature engineering:
- Regime probability vector from RegimeDetectorV2
- Bollinger Band metrics (%B, width, squeeze)
- Volume z-score and flow premium delta
- Cross-ticker correlation (NQ-MES rolling 30-min)
- Lagged performance (meta-strategy style)
- Calibrated probability + Expected Value estimation

Training: Walk-forward on 60-90 days journal data (nightly)
Output: Only trade if prob > 0.65 AND EV > 0

Pi5 optimized: ~50-100ms inference with pre-loaded model
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import json
import os

logger = logging.getLogger(__name__)

# Try to import LightGBM (primary choice)
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    lgb = None
    logger.warning("LightGBM not available - install with: pip install lightgbm")

# Try to import XGBoost (fallback)
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    xgb = None

# Try to import CatBoost (for categorical regimes)
try:
    import catboost as cb
    CATBOOST_AVAILABLE = True
except ImportError:
    CATBOOST_AVAILABLE = False
    cb = None

# Try sklearn for calibration and preprocessing
try:
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import TimeSeriesSplit
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    StandardScaler = None


class SignalSourceV2(Enum):
    """Extended signal sources for ensemble v2"""
    DETERMINISTIC = "deterministic"
    QUICK_MODE = "quick_5m"
    FLOW = "flow"
    AI_ONLY = "ai_only"
    REGIME = "regime"  # Regime detector itself can signal
    LEVELS = "levels"  # Key levels (PDH/PDL/Fib) confluence


@dataclass
class SignalInputV2:
    """Enhanced signal input with rich features"""
    source: SignalSourceV2
    ticker: str
    action: str  # 'buy', 'sell', 'none'
    confidence: float  # 0-100
    timestamp: datetime

    # Indicator features
    risk_reward: float = 0.0
    aligned_tfs: int = 0
    volume_ratio: float = 1.0
    volume_zscore: float = 0.0

    # Bollinger Band features
    bb_percent: float = 0.5  # %B (0-1)
    bb_width: float = 0.0
    bb_squeeze: bool = False

    # Flow features
    flow_score: float = 0.0
    flow_premium: float = 0.0
    flow_premium_delta: float = 0.0  # Change from previous

    # Regime features (from RegimeDetectorV2)
    regime_probs: Dict[str, float] = field(default_factory=dict)
    primary_regime: str = 'neutral'
    regime_confidence: float = 0.0

    # Cross-asset correlation
    correlation_nq_mes: float = 0.0
    correlation_spy_qqq: float = 0.0

    # Meta-strategy features (lagged performance)
    last_5_trades_win_rate: float = 0.5
    last_10_trades_pnl: float = 0.0
    streak: int = 0  # Positive = winning streak, negative = losing
    time_since_last_trade_mins: float = 60.0

    # Market context
    is_market_open: bool = True
    minutes_since_open: int = 0
    day_of_week: int = 0  # 0=Monday

    # Key levels confluence (PDH/PDL/Fib)
    levels_confluence: float = 0.0   # 0-100 confluence score
    nearest_level: str = ''          # Name of nearest level
    level_distance_pct: float = 0.0  # Distance to nearest level as %
    levels_nearby: int = 0           # Count of levels within 0.5%

    # News sentiment
    news_sentiment: float = 0.0      # -1 to +1 sentiment score
    news_boost: float = 0.0          # Probability boost from news

    # Microstructure features
    order_imbalance: float = 0.0     # -1 (ask heavy) to +1 (bid heavy)
    vpin_toxicity: float = 0.0       # Volume-weighted probability of informed trading

    # Crypto funding rate
    funding_rate: float = 0.0        # Current funding rate (for crypto)
    funding_bias: str = 'neutral'    # 'long_crowded', 'short_crowded', 'neutral'

    # VWAP features (NEW)
    vwap_distance_pct: float = 0.0   # Distance from VWAP as %
    vwap_bias: float = 0.0           # VWAP bias score (-1 to +1)
    vwap_confluence: float = 0.0     # 1.0 if within threshold, 0.0 otherwise
    vwap_boost: float = 0.0          # Probability boost from VWAP

    # Raw data for debugging
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnsembleScoreV2:
    """Enhanced ensemble scoring result"""
    ticker: str
    action: str

    # Primary outputs
    probability: float  # Calibrated probability (0-1)
    expected_value: float  # Expected value of trade
    position_size_pct: float  # Position size as % of capital

    # Decision
    should_trade: bool = False
    rejection_reason: str = ''

    # Signal analysis
    signals_count: int = 0
    signals_agreeing: int = 0
    signals_disagreeing: int = 0

    # Feature importance (top 5)
    top_features: Dict[str, float] = field(default_factory=dict)

    # Confidence intervals
    prob_lower: float = 0.0
    prob_upper: float = 0.0

    # Model info
    model_type: str = 'lightgbm'
    model_version: str = '2.0'
    calculated_at: datetime = field(default_factory=datetime.now)

    # Walk-forward metrics
    model_accuracy_30d: float = 0.0
    model_sharpe_30d: float = 0.0

    # Debug
    feature_vector: List[float] = field(default_factory=list)
    feature_names: List[str] = field(default_factory=list)


@dataclass
class EnsembleConfigV2:
    """Enhanced configuration for ensemble v2"""
    # Trading thresholds
    min_probability: float = 0.62  # Base: > 62% confident (updated from 0.65)
    min_expected_value: float = 0.0  # Must have positive EV

    # Regime-specific probability overrides (NEW)
    uptrend_min_probability: float = 0.66    # Stricter for trending_up: > 66%
    uptrend_flow_require: str = 'HIGH'       # Require HIGH/EXTREME flow for uptrend
    uptrend_imbalance_min: float = 0.45      # Min imbalance for uptrend longs

    # Levels confluence boost (NEW)
    # If levels_confluence >= 70 AND flow >= HIGH AND imbalance > 0.4 → add boost
    levels_confluence_boost: float = 0.22  # +22% probability boost
    levels_confluence_min: float = 70.0    # Minimum confluence for boost
    levels_flow_min: str = 'HIGH'          # Minimum flow conviction for boost
    levels_imbalance_min: float = 0.4      # Minimum imbalance for boost

    # News sentiment boost (ENHANCED)
    news_sentiment_min_boost: float = 0.08   # Min +8% from news (when sentiment > 0.5)
    news_sentiment_max_boost: float = 0.12   # Max +12% from news
    news_sentiment_threshold: float = 0.5    # Min sentiment score for boost
    news_sentiment_flow_require: str = 'MEDIUM'  # Min flow for news boost

    # VWAP confluence boost (NEW)
    vwap_confluence_boost: float = 0.12     # +12% probability boost
    vwap_distance_threshold: float = 0.5    # Max distance for confluence (%)
    vwap_tight_distance: float = 0.3        # Tight distance for extra boost
    vwap_tight_boost: float = 0.15          # +15% boost when tight
    vwap_mean_reversion_boost: float = 0.18 # +18% for mean-reversion near VWAP

    # Position sizing (Kelly-based)
    kelly_fraction: float = 0.25  # Use 25% of optimal Kelly
    max_position_pct: float = 5.0  # Max 5% per position
    min_position_pct: float = 0.5

    # Model selection
    model_type: str = 'lightgbm'  # 'lightgbm', 'xgboost', 'catboost'

    # Training parameters
    walk_forward_days: int = 60  # Train on 60 days
    validation_days: int = 7  # Validate on 7 days
    retrain_frequency_hours: int = 24  # Retrain daily

    # LightGBM parameters (Pi5 optimized)
    lgb_params: Dict[str, Any] = field(default_factory=lambda: {
        'objective': 'binary',
        'metric': 'auc',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'max_depth': 5,  # Shallow for speed
        'learning_rate': 0.05,
        'n_estimators': 100,
        'min_child_samples': 20,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'reg_alpha': 0.1,
        'reg_lambda': 0.1,
        'random_state': 42,
        'n_jobs': 4,  # Pi5 has 4 cores
        'verbose': -1,
    })

    # XGBoost parameters (fallback)
    xgb_params: Dict[str, Any] = field(default_factory=lambda: {
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'max_depth': 5,
        'learning_rate': 0.05,
        'n_estimators': 100,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'reg_alpha': 0.1,
        'reg_lambda': 0.1,
        'random_state': 42,
        'n_jobs': 4,
    })

    # Feature configuration
    use_regime_probs: bool = True
    use_bb_features: bool = True
    use_flow_features: bool = True
    use_correlation_features: bool = True
    use_meta_features: bool = True  # Lagged performance
    use_time_features: bool = True

    # Paths
    model_path: str = '/home/pharma5/unified_engine/models/ensemble_v2.pkl'
    training_log_path: str = '/home/pharma5/unified_engine/logs/ensemble_training.log'


class EnsembleScorerV2:
    """
    Elite ensemble meta-model with LightGBM/XGBoost.

    Features:
    - Rich feature engineering from all signal sources
    - Walk-forward training on journal data
    - Calibrated probabilities with confidence intervals
    - Expected Value estimation for decision-making
    - Meta-strategy overlay (lagged performance features)
    """

    # Complete feature list
    FEATURE_NAMES = [
        # Signal confidence features
        'det_confidence', 'det_rr', 'det_aligned_tfs',
        'quick_confidence', 'quick_volume_ratio', 'quick_volume_zscore',
        'flow_score', 'flow_premium_log', 'flow_premium_delta',

        # Bollinger Band features
        'bb_percent', 'bb_width', 'bb_squeeze',

        # Key levels confluence (NEW)
        'levels_confluence', 'level_distance', 'levels_nearby',

        # Microstructure features (NEW)
        'order_imbalance', 'vpin_toxicity',

        # News sentiment (NEW)
        'news_sentiment', 'news_boost',

        # Crypto funding (NEW)
        'funding_rate', 'funding_crowded_long', 'funding_crowded_short',

        # VWAP features (NEW)
        'vwap_distance_pct', 'vwap_bias', 'vwap_confluence',

        # Regime probability vector (6 features)
        'regime_prob_trending_up', 'regime_prob_trending_down',
        'regime_prob_mean_reverting', 'regime_prob_vol_expansion',
        'regime_prob_vol_contraction', 'regime_prob_chaotic',
        'regime_confidence',

        # Cross-asset correlation
        'corr_nq_mes', 'corr_spy_qqq',

        # Meta-strategy (lagged performance)
        'last_5_win_rate', 'last_10_pnl', 'streak',
        'time_since_last_trade',

        # Time features
        'is_market_open', 'minutes_since_open',
        'day_monday', 'day_tuesday', 'day_wednesday',
        'day_thursday', 'day_friday',

        # Signal agreement
        'signal_agreement', 'signal_count',
    ]

    def __init__(self, config: Optional[EnsembleConfigV2] = None):
        self.config = config or EnsembleConfigV2()

        # Model components
        self.model = None
        self.calibrator = None
        self.scaler = None
        self.model_type = self.config.model_type

        # Training state
        self.last_trained: Optional[datetime] = None
        self.training_history: List[Dict] = []

        # Performance tracking
        self.recent_predictions: deque = deque(maxlen=100)
        self.recent_outcomes: deque = deque(maxlen=100)

        # Cross-asset correlation tracking
        self.returns_history: Dict[str, deque] = {
            'NQ': deque(maxlen=100),
            'MES': deque(maxlen=100),
            'SPY': deque(maxlen=100),
            'QQQ': deque(maxlen=100),
        }

        # Feature importance cache
        self.feature_importance: Dict[str, float] = {}

        # Try to load existing model
        self._load_model()

        logger.info(
            f"EnsembleScorerV2 initialized: model={self.model_type}, "
            f"min_prob={self.config.min_probability}, min_ev={self.config.min_expected_value}, "
            f"LGBM={LIGHTGBM_AVAILABLE}, XGB={XGBOOST_AVAILABLE}"
        )

    def _load_model(self) -> bool:
        """Load pre-trained model if available."""
        if not os.path.exists(self.config.model_path):
            logger.info("No pre-trained ensemble model found, will use weighted voting fallback")
            return False

        try:
            if SKLEARN_AVAILABLE:
                data = joblib.load(self.config.model_path)
                self.model = data.get('model')
                self.calibrator = data.get('calibrator')
                self.scaler = data.get('scaler')
                self.last_trained = data.get('trained_at')
                self.feature_importance = data.get('feature_importance', {})
                self.model_type = data.get('model_type', 'lightgbm')

                logger.info(f"Loaded ensemble model from {self.config.model_path}")
                return True
        except Exception as e:
            logger.warning(f"Failed to load ensemble model: {e}")

        return False

    def _build_feature_vector(
        self,
        signals: List[SignalInputV2],
        primary_action: str
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Build rich feature vector from signals.

        Returns (features, feature_names)
        """
        features = {}

        # Initialize all features to defaults
        features['det_confidence'] = 0.0
        features['det_rr'] = 0.0
        features['det_aligned_tfs'] = 0.0
        features['quick_confidence'] = 0.0
        features['quick_volume_ratio'] = 1.0
        features['quick_volume_zscore'] = 0.0
        features['flow_score'] = 0.0
        features['flow_premium_log'] = 0.0
        features['flow_premium_delta'] = 0.0
        features['bb_percent'] = 0.5
        features['bb_width'] = 0.0
        features['bb_squeeze'] = 0.0

        # Key levels confluence (NEW)
        features['levels_confluence'] = 0.0
        features['level_distance'] = 1.0  # 1.0 = far from levels
        features['levels_nearby'] = 0.0

        # Microstructure features (NEW)
        features['order_imbalance'] = 0.0
        features['vpin_toxicity'] = 0.0

        # News sentiment (NEW)
        features['news_sentiment'] = 0.0
        features['news_boost'] = 0.0

        # Crypto funding (NEW)
        features['funding_rate'] = 0.0
        features['funding_crowded_long'] = 0.0
        features['funding_crowded_short'] = 0.0

        # VWAP features (NEW)
        features['vwap_distance_pct'] = 0.0
        features['vwap_bias'] = 0.0
        features['vwap_confluence'] = 0.0

        # Regime probabilities
        features['regime_prob_trending_up'] = 0.0
        features['regime_prob_trending_down'] = 0.0
        features['regime_prob_mean_reverting'] = 0.0
        features['regime_prob_vol_expansion'] = 0.0
        features['regime_prob_vol_contraction'] = 0.0
        features['regime_prob_chaotic'] = 0.167  # Default uniform
        features['regime_confidence'] = 50.0

        # Correlation
        features['corr_nq_mes'] = 0.0
        features['corr_spy_qqq'] = 0.0

        # Meta-strategy
        features['last_5_win_rate'] = 0.5
        features['last_10_pnl'] = 0.0
        features['streak'] = 0
        features['time_since_last_trade'] = 60.0

        # Time features
        features['is_market_open'] = 1.0
        features['minutes_since_open'] = 0
        features['day_monday'] = 0.0
        features['day_tuesday'] = 0.0
        features['day_wednesday'] = 0.0
        features['day_thursday'] = 0.0
        features['day_friday'] = 0.0

        # Process each signal
        for sig in signals:
            # Determine if signal agrees with primary action
            agrees = sig.action == primary_action
            sign = 1.0 if agrees else -0.5  # Penalty for disagreement

            if sig.source == SignalSourceV2.DETERMINISTIC:
                features['det_confidence'] = self._normalize(sig.confidence, 0, 100) * sign
                features['det_rr'] = min(sig.risk_reward / 5.0, 1.0)  # Cap at 5:1
                features['det_aligned_tfs'] = sig.aligned_tfs / 5.0
                features['bb_percent'] = sig.bb_percent
                features['bb_width'] = min(sig.bb_width / 0.1, 1.0)  # Normalize width
                features['bb_squeeze'] = 1.0 if sig.bb_squeeze else 0.0

            elif sig.source == SignalSourceV2.QUICK_MODE:
                features['quick_confidence'] = self._normalize(sig.confidence, 0, 100) * sign
                features['quick_volume_ratio'] = min(sig.volume_ratio / 3.0, 1.0)
                features['quick_volume_zscore'] = np.clip(sig.volume_zscore / 3.0, -1, 1)

            elif sig.source == SignalSourceV2.FLOW:
                features['flow_score'] = np.clip(sig.flow_score / 10.0, -1, 1)
                features['flow_premium_log'] = np.log1p(sig.flow_premium) / 15.0  # Log scale
                features['flow_premium_delta'] = np.clip(sig.flow_premium_delta / 100000, -1, 1)

            # Use regime probs from any signal that has them
            if sig.regime_probs:
                features['regime_prob_trending_up'] = sig.regime_probs.get('trending_up', 0)
                features['regime_prob_trending_down'] = sig.regime_probs.get('trending_down', 0)
                features['regime_prob_mean_reverting'] = sig.regime_probs.get('mean_reverting', 0)
                features['regime_prob_vol_expansion'] = sig.regime_probs.get('vol_expansion', 0)
                features['regime_prob_vol_contraction'] = sig.regime_probs.get('vol_contraction', 0)
                features['regime_prob_chaotic'] = sig.regime_probs.get('chaotic', 0)
                features['regime_confidence'] = self._normalize(sig.regime_confidence, 0, 100)

            # Correlation features
            if sig.correlation_nq_mes != 0:
                features['corr_nq_mes'] = sig.correlation_nq_mes
            if sig.correlation_spy_qqq != 0:
                features['corr_spy_qqq'] = sig.correlation_spy_qqq

            # Key levels confluence (NEW)
            if sig.levels_confluence > 0:
                features['levels_confluence'] = sig.levels_confluence / 100.0  # Normalize to 0-1
                features['level_distance'] = 1.0 - min(sig.level_distance_pct / 2.0, 1.0)  # Invert: closer = higher
                features['levels_nearby'] = min(sig.levels_nearby / 5.0, 1.0)

            # Microstructure features (NEW)
            if sig.order_imbalance != 0:
                features['order_imbalance'] = sig.order_imbalance
            if sig.vpin_toxicity != 0:
                features['vpin_toxicity'] = sig.vpin_toxicity

            # News sentiment (NEW)
            if sig.news_sentiment != 0:
                features['news_sentiment'] = sig.news_sentiment
                features['news_boost'] = sig.news_boost

            # Crypto funding (NEW)
            if sig.funding_rate != 0:
                features['funding_rate'] = np.clip(sig.funding_rate / 0.1, -1, 1)  # Normalize
                features['funding_crowded_long'] = 1.0 if sig.funding_bias == 'long_crowded' else 0.0
                features['funding_crowded_short'] = 1.0 if sig.funding_bias == 'short_crowded' else 0.0

            # VWAP features (NEW)
            if sig.vwap_distance_pct != 0 or sig.vwap_bias != 0:
                features['vwap_distance_pct'] = np.clip(sig.vwap_distance_pct / 2.0, -1, 1)  # Normalize
                features['vwap_bias'] = sig.vwap_bias  # Already -1 to +1
                features['vwap_confluence'] = sig.vwap_confluence  # 0 or 1

            # Meta-strategy features (use from any signal)
            if sig.last_5_trades_win_rate != 0.5:
                features['last_5_win_rate'] = sig.last_5_trades_win_rate
            if sig.last_10_trades_pnl != 0:
                features['last_10_pnl'] = np.clip(sig.last_10_trades_pnl / 1000, -1, 1)
            if sig.streak != 0:
                features['streak'] = np.clip(sig.streak / 5, -1, 1)
            features['time_since_last_trade'] = min(sig.time_since_last_trade_mins / 480, 1.0)

            # Time features
            features['is_market_open'] = 1.0 if sig.is_market_open else 0.0
            features['minutes_since_open'] = min(sig.minutes_since_open / 390, 1.0)  # 390 min trading day

            # Day of week one-hot
            if sig.day_of_week == 0:
                features['day_monday'] = 1.0
            elif sig.day_of_week == 1:
                features['day_tuesday'] = 1.0
            elif sig.day_of_week == 2:
                features['day_wednesday'] = 1.0
            elif sig.day_of_week == 3:
                features['day_thursday'] = 1.0
            elif sig.day_of_week == 4:
                features['day_friday'] = 1.0

        # Signal agreement feature
        actions = [s.action for s in signals if s.action != 'none']
        if actions:
            most_common = max(set(actions), key=actions.count)
            features['signal_agreement'] = actions.count(most_common) / len(actions)
        else:
            features['signal_agreement'] = 0.0

        features['signal_count'] = min(len(signals) / 4.0, 1.0)

        # Build ordered feature vector
        feature_names = self.FEATURE_NAMES
        feature_vector = [features.get(name, 0.0) for name in feature_names]

        return np.array(feature_vector).reshape(1, -1), feature_names

    def _normalize(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize value to 0-1 range."""
        if max_val == min_val:
            return 0.5
        return np.clip((value - min_val) / (max_val - min_val), 0, 1)

    def score_signals(
        self,
        signals: List[SignalInputV2],
        avg_win_rate: float = 0.55,
        avg_rr: float = 2.0
    ) -> EnsembleScoreV2:
        """
        Score signals using trained ML model or fallback.

        Args:
            signals: List of SignalInputV2 from different sources
            avg_win_rate: Historical win rate for EV calculation
            avg_rr: Historical risk/reward for EV calculation

        Returns:
            EnsembleScoreV2 with probability, EV, and decision
        """
        if not signals:
            return EnsembleScoreV2(
                ticker="UNKNOWN",
                action='none',
                probability=0.0,
                expected_value=0.0,
                position_size_pct=0.0,
                should_trade=False,
                rejection_reason="No signals provided"
            )

        ticker = signals[0].ticker

        # Determine primary action
        buy_signals = [s for s in signals if s.action == 'buy']
        sell_signals = [s for s in signals if s.action == 'sell']

        if len(buy_signals) >= len(sell_signals) and len(buy_signals) > 0:
            primary_action = 'buy'
            agreeing = buy_signals
            disagreeing = sell_signals
        elif len(sell_signals) > 0:
            primary_action = 'sell'
            agreeing = sell_signals
            disagreeing = buy_signals
        else:
            return EnsembleScoreV2(
                ticker=ticker,
                action='none',
                probability=0.0,
                expected_value=0.0,
                position_size_pct=0.0,
                should_trade=False,
                rejection_reason="All signals neutral"
            )

        # Build feature vector
        features, feature_names = self._build_feature_vector(signals, primary_action)

        # Score using ML model or fallback
        if self.model is not None:
            result = self._score_ml_model(features, feature_names, primary_action, ticker)
        else:
            result = self._score_weighted_voting(signals, primary_action, agreeing, disagreeing)

        result.ticker = ticker
        result.action = primary_action
        result.signals_count = len(signals)
        result.signals_agreeing = len(agreeing)
        result.signals_disagreeing = len(disagreeing)
        result.feature_vector = features[0].tolist()
        result.feature_names = feature_names

        # ========================================
        # LEVELS CONFLUENCE BOOST (NEW)
        # ========================================
        # If levels_confluence >= 70 AND flow >= HIGH AND imbalance > 0.4 → add boost
        levels_boost = 0.0
        flow_conviction = 'NONE'
        order_imbalance = 0.0

        for sig in signals:
            if sig.levels_confluence > 0:
                # Check levels confluence condition
                if sig.levels_confluence >= self.config.levels_confluence_min:
                    # Extract flow conviction from flow signals
                    if sig.source == SignalSourceV2.FLOW:
                        if sig.confidence >= 70:
                            flow_conviction = 'EXTREME'
                        elif sig.confidence >= 50:
                            flow_conviction = 'HIGH'
                        elif sig.confidence >= 30:
                            flow_conviction = 'MEDIUM'

                    # Get order imbalance
                    if sig.order_imbalance != 0:
                        order_imbalance = sig.order_imbalance

        # Check if all conditions met for levels boost
        flow_levels = ['HIGH', 'EXTREME']
        if self.config.levels_flow_min == 'MEDIUM':
            flow_levels.append('MEDIUM')

        if (flow_conviction in flow_levels and
            abs(order_imbalance) >= self.config.levels_imbalance_min):
            # Find max levels confluence from signals
            max_confluence = max((s.levels_confluence for s in signals if s.levels_confluence > 0), default=0)
            if max_confluence >= self.config.levels_confluence_min:
                levels_boost = self.config.levels_confluence_boost
                logger.info(f"📍 Levels boost applied: +{levels_boost:.0%} "
                           f"(confluence={max_confluence:.0f}, flow={flow_conviction}, imbal={order_imbalance:.2f})")

        # Add levels boost to probability
        result.probability = min(1.0, result.probability + levels_boost)

        # ========================================
        # NEWS SENTIMENT BOOST (ENHANCED)
        # ========================================
        # If sentiment > 0.5 and flow >= MEDIUM → +0.08 to +0.12 boost
        news_boost = 0.0
        has_flow_for_news = flow_conviction in ['MEDIUM', 'HIGH', 'EXTREME']

        for sig in signals:
            if sig.news_sentiment != 0 and abs(sig.news_sentiment) >= self.config.news_sentiment_threshold:
                # Only apply if direction matches AND flow is sufficient
                direction_matches = (
                    (primary_action == 'buy' and sig.news_sentiment > 0) or
                    (primary_action == 'sell' and sig.news_sentiment < 0)
                )

                if direction_matches and has_flow_for_news:
                    # Scale boost between min and max based on sentiment strength
                    sentiment_strength = min(abs(sig.news_sentiment), 1.0)
                    scaled_boost = self.config.news_sentiment_min_boost + \
                        (self.config.news_sentiment_max_boost - self.config.news_sentiment_min_boost) * \
                        (sentiment_strength - self.config.news_sentiment_threshold) / (1.0 - self.config.news_sentiment_threshold)
                    news_boost = max(news_boost, scaled_boost)
                    logger.info(f"📰 News sentiment boost: +{news_boost:.0%} "
                               f"(sentiment={sig.news_sentiment:.2f}, flow={flow_conviction})")
                elif not direction_matches and abs(sig.news_sentiment) > 0.7:
                    # Strong opposing sentiment - penalty
                    news_boost = min(news_boost, -0.05)

        result.probability = max(0, min(1.0, result.probability + news_boost))

        # ========================================
        # VWAP CONFLUENCE BOOST (NEW)
        # ========================================
        # If price near VWAP and direction aligns → add boost
        vwap_boost = 0.0
        for sig in signals:
            if sig.vwap_boost > 0 and sig.vwap_confluence > 0:
                # Check if VWAP bias direction aligns with trade direction
                if (primary_action == 'buy' and sig.vwap_bias >= 0) or \
                   (primary_action == 'sell' and sig.vwap_bias <= 0):
                    # Determine boost level based on distance
                    abs_distance = abs(sig.vwap_distance_pct)
                    if abs_distance <= self.config.vwap_tight_distance:
                        # Tight distance - extra boost
                        vwap_boost = max(vwap_boost, self.config.vwap_tight_boost)
                    else:
                        vwap_boost = max(vwap_boost, self.config.vwap_confluence_boost)

                    # Extra boost for mean-reversion regime near VWAP
                    regime = sig.primary_regime
                    if regime in ['mean_reverting', 'vol_contraction', 'choppy']:
                        if abs_distance <= self.config.vwap_tight_distance:
                            vwap_boost = max(vwap_boost, self.config.vwap_mean_reversion_boost)

        if vwap_boost > 0:
            logger.info(f"📊 VWAP boost applied: +{vwap_boost:.0%}")
            result.probability = min(1.0, result.probability + vwap_boost)

        # Calculate Expected Value
        # EV = (win_prob * avg_win) - (loss_prob * avg_loss)
        # Assuming avg_rr = avg_win / avg_loss
        avg_loss = 1.0  # Normalized
        avg_win = avg_loss * avg_rr

        result.expected_value = (result.probability * avg_win) - ((1 - result.probability) * avg_loss)

        # Calculate position size using simplified Kelly
        # Kelly % = (win_prob * payoff - loss_prob) / payoff
        if avg_rr > 0:
            kelly_pct = ((result.probability * avg_rr) - (1 - result.probability)) / avg_rr
            kelly_pct = max(0, kelly_pct)  # No negative positions
            result.position_size_pct = kelly_pct * self.config.kelly_fraction * 100  # Convert to %
            result.position_size_pct = max(
                self.config.min_position_pct,
                min(self.config.max_position_pct, result.position_size_pct)
            )
        else:
            result.position_size_pct = self.config.min_position_pct

        # ========================================
        # REGIME-SPECIFIC PROBABILITY THRESHOLD (NEW)
        # ========================================
        # Get primary regime from signals
        primary_regime = 'neutral'
        for sig in signals:
            if sig.primary_regime:
                primary_regime = sig.primary_regime.lower().replace('-', '_')
                break

        # Determine effective min_probability based on regime
        effective_min_prob = self.config.min_probability
        if primary_regime == 'trending_up' and primary_action == 'buy':
            # Stricter threshold for longs in uptrend
            effective_min_prob = self.config.uptrend_min_probability

            # Also check flow and imbalance requirements
            has_high_flow = False
            has_min_imbalance = False
            for sig in signals:
                if sig.source == SignalSourceV2.FLOW:
                    if sig.confidence >= 50:  # HIGH = 50+
                        has_high_flow = True
                if sig.order_imbalance >= self.config.uptrend_imbalance_min:
                    has_min_imbalance = True

            if not has_high_flow:
                result.should_trade = False
                result.rejection_reason = f"Uptrend long requires {self.config.uptrend_flow_require}+ flow"
                logger.info(
                    f"🎲 EnsembleV2 {ticker}: {primary_action.upper()} REJECTED - "
                    f"Uptrend requires {self.config.uptrend_flow_require}+ flow"
                )
                return result

            if not has_min_imbalance:
                result.should_trade = False
                result.rejection_reason = f"Uptrend long requires imbalance >= {self.config.uptrend_imbalance_min}"
                logger.info(
                    f"🎲 EnsembleV2 {ticker}: {primary_action.upper()} REJECTED - "
                    f"Uptrend requires imbalance >= {self.config.uptrend_imbalance_min}"
                )
                return result

        # Final decision with effective threshold
        if result.probability >= effective_min_prob:
            if result.expected_value >= self.config.min_expected_value:
                if result.signals_disagreeing > result.signals_agreeing:
                    result.should_trade = False
                    result.rejection_reason = f"Signal conflict: {result.signals_disagreeing} disagree"
                else:
                    result.should_trade = True
            else:
                result.should_trade = False
                result.rejection_reason = f"Negative EV: {result.expected_value:.3f}"
        else:
            result.should_trade = False
            threshold_label = f"{effective_min_prob:.0%}"
            if primary_regime == 'trending_up':
                threshold_label += " (uptrend override)"
            result.rejection_reason = f"Low probability: {result.probability:.1%} < {threshold_label}"

        # Log decision
        regime_note = f" [regime={primary_regime}]" if primary_regime != 'neutral' else ""
        logger.info(
            f"🎲 EnsembleV2 {ticker}: {primary_action.upper()} "
            f"prob={result.probability:.1%} EV={result.expected_value:.3f} "
            f"size={result.position_size_pct:.1f}% "
            f"({result.signals_agreeing}/{result.signals_count} agree){regime_note} "
            f"→ {'TRADE' if result.should_trade else 'SKIP'}"
        )

        return result

    def _score_ml_model(
        self,
        features: np.ndarray,
        feature_names: List[str],
        primary_action: str,
        ticker: str
    ) -> EnsembleScoreV2:
        """Score using trained ML model."""
        result = EnsembleScoreV2(
            ticker=ticker,
            action=primary_action,
            probability=0.0,
            expected_value=0.0,
            position_size_pct=0.0,
            model_type=self.model_type
        )

        try:
            # Scale features if scaler available
            if self.scaler is not None:
                features_scaled = self.scaler.transform(features)
            else:
                features_scaled = features

            # Get probability prediction
            if self.calibrator is not None:
                # Use calibrated probabilities
                proba = self.calibrator.predict_proba(features_scaled)[0]
            else:
                # Use raw model probabilities
                proba = self.model.predict_proba(features_scaled)[0]

            # Binary classification: index 1 = positive (trade is good)
            result.probability = float(proba[1])

            # Confidence interval (approximate using probability)
            # More extreme probabilities = narrower intervals
            uncertainty = 0.1 * (1 - abs(result.probability - 0.5) * 2)
            result.prob_lower = max(0, result.probability - uncertainty)
            result.prob_upper = min(1, result.probability + uncertainty)

            # Top features by importance
            if self.feature_importance:
                sorted_importance = sorted(
                    self.feature_importance.items(),
                    key=lambda x: abs(x[1]),
                    reverse=True
                )[:5]
                result.top_features = dict(sorted_importance)

        except Exception as e:
            logger.warning(f"ML scoring failed: {e}, falling back to weighted voting")
            # Fallback will be handled by caller
            result.probability = 0.0

        return result

    def _score_weighted_voting(
        self,
        signals: List[SignalInputV2],
        primary_action: str,
        agreeing: List[SignalInputV2],
        disagreeing: List[SignalInputV2]
    ) -> EnsembleScoreV2:
        """
        Fallback weighted voting when no ML model available.
        """
        result = EnsembleScoreV2(
            ticker="",
            action=primary_action,
            probability=0.0,
            expected_value=0.0,
            position_size_pct=0.0,
            model_type='weighted_voting'
        )

        # Source weights (without ML)
        weights = {
            SignalSourceV2.DETERMINISTIC.value: 0.40,
            SignalSourceV2.QUICK_MODE.value: 0.25,
            SignalSourceV2.FLOW.value: 0.20,
            SignalSourceV2.AI_ONLY.value: 0.10,
            SignalSourceV2.REGIME.value: 0.05,
        }

        total_weight = 0.0
        weighted_score = 0.0

        for signal in signals:
            source_name = signal.source.value
            weight = weights.get(source_name, 0.1)

            if signal.action == primary_action:
                contribution = (signal.confidence / 100.0) * weight
            elif signal.action == 'none':
                contribution = 0.0
            else:
                contribution = -(signal.confidence / 100.0) * weight * 0.5

            weighted_score += contribution
            total_weight += weight

        # Normalize to probability
        if total_weight > 0:
            base_prob = weighted_score / total_weight
        else:
            base_prob = 0.0

        # Agreement bonus/penalty
        if len(agreeing) == len(signals) and len(signals) >= 2:
            base_prob += 0.10  # +10% for full agreement
        elif len(disagreeing) > len(agreeing):
            base_prob -= 0.15  # -15% for majority disagreement

        result.probability = max(0, min(1, base_prob))

        # Simple confidence interval
        result.prob_lower = max(0, result.probability - 0.15)
        result.prob_upper = min(1, result.probability + 0.15)

        return result

    def train_model(
        self,
        training_data: List[Dict],
        model_type: Optional[str] = None
    ) -> bool:
        """
        Train ML model on historical journal data.

        Args:
            training_data: List of dicts with:
                - 'features': feature vector
                - 'outcome': 1 for win, 0 for loss
                - 'timestamp': datetime of trade
            model_type: 'lightgbm', 'xgboost', or 'catboost'

        Returns:
            True if training successful
        """
        if len(training_data) < 50:
            logger.warning(f"Insufficient training data: {len(training_data)} (need 50+)")
            return False

        model_type = model_type or self.config.model_type

        # Sort by timestamp for walk-forward
        training_data = sorted(training_data, key=lambda x: x.get('timestamp', datetime.min))

        # Extract features and labels
        X = np.array([d['features'] for d in training_data])
        y = np.array([d['outcome'] for d in training_data])

        logger.info(f"Training EnsembleV2 on {len(training_data)} trades, model={model_type}")

        try:
            # Scale features
            if SKLEARN_AVAILABLE:
                self.scaler = StandardScaler()
                X_scaled = self.scaler.fit_transform(X)
            else:
                X_scaled = X

            # Walk-forward split (most recent for validation)
            split_idx = int(len(X) * 0.85)
            X_train, X_val = X_scaled[:split_idx], X_scaled[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]

            # Train model
            if model_type == 'lightgbm' and LIGHTGBM_AVAILABLE:
                self.model = lgb.LGBMClassifier(**self.config.lgb_params)
                self.model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    callbacks=[lgb.early_stopping(20, verbose=False)]
                )
                self.feature_importance = dict(zip(
                    self.FEATURE_NAMES,
                    self.model.feature_importances_
                ))

            elif model_type == 'xgboost' and XGBOOST_AVAILABLE:
                self.model = xgb.XGBClassifier(**self.config.xgb_params)
                self.model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    verbose=False
                )
                self.feature_importance = dict(zip(
                    self.FEATURE_NAMES,
                    self.model.feature_importances_
                ))

            elif model_type == 'catboost' and CATBOOST_AVAILABLE:
                self.model = cb.CatBoostClassifier(
                    iterations=100,
                    depth=5,
                    learning_rate=0.05,
                    verbose=False
                )
                self.model.fit(X_train, y_train, eval_set=(X_val, y_val))
                self.feature_importance = dict(zip(
                    self.FEATURE_NAMES,
                    self.model.feature_importances_
                ))
            else:
                logger.warning(f"Model type {model_type} not available")
                return False

            # Calibrate probabilities (isotonic for better calibration)
            if SKLEARN_AVAILABLE and len(X_val) > 20:
                self.calibrator = CalibratedClassifierCV(
                    self.model, method='isotonic', cv='prefit'
                )
                self.calibrator.fit(X_val, y_val)

            self.model_type = model_type
            self.last_trained = datetime.now()

            # Calculate validation metrics
            val_preds = self.model.predict_proba(X_val)[:, 1]
            val_accuracy = np.mean((val_preds > 0.5) == y_val)

            logger.info(
                f"EnsembleV2 trained: accuracy={val_accuracy:.1%}, "
                f"features={len(self.FEATURE_NAMES)}"
            )

            # Log top features
            sorted_importance = sorted(
                self.feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            logger.info("Top features: " + ", ".join(
                f"{name}={imp:.3f}" for name, imp in sorted_importance
            ))

            # Save model
            self._save_model()

            return True

        except Exception as e:
            logger.error(f"Training failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _save_model(self) -> bool:
        """Save trained model to disk."""
        if not SKLEARN_AVAILABLE or self.model is None:
            return False

        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(self.config.model_path), exist_ok=True)

            joblib.dump({
                'model': self.model,
                'calibrator': self.calibrator,
                'scaler': self.scaler,
                'trained_at': self.last_trained,
                'feature_importance': self.feature_importance,
                'feature_names': self.FEATURE_NAMES,
                'model_type': self.model_type,
            }, self.config.model_path)

            logger.info(f"Saved ensemble model to {self.config.model_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False

    def record_outcome(
        self,
        prediction: EnsembleScoreV2,
        actual_outcome: int  # 1 = win, 0 = loss
    ):
        """Record prediction outcome for calibration tracking."""
        self.recent_predictions.append(prediction.probability)
        self.recent_outcomes.append(actual_outcome)

        # Calculate recent calibration
        if len(self.recent_predictions) >= 20:
            preds = np.array(list(self.recent_predictions))
            outcomes = np.array(list(self.recent_outcomes))

            # Brier score (lower = better calibration)
            brier = np.mean((preds - outcomes) ** 2)

            # Log if poorly calibrated
            if brier > 0.25:
                logger.warning(f"Model calibration degraded: Brier={brier:.3f}")

    def update_correlation(
        self,
        ticker: str,
        returns: float
    ):
        """Update cross-asset correlation tracking."""
        if ticker in self.returns_history:
            self.returns_history[ticker].append(returns)

    def get_correlation(self, ticker1: str, ticker2: str) -> float:
        """Calculate rolling correlation between two assets."""
        if ticker1 not in self.returns_history or ticker2 not in self.returns_history:
            return 0.0

        ret1 = list(self.returns_history[ticker1])
        ret2 = list(self.returns_history[ticker2])

        min_len = min(len(ret1), len(ret2))
        if min_len < 20:
            return 0.0

        return float(np.corrcoef(ret1[-min_len:], ret2[-min_len:])[0, 1])

    def get_status(self) -> Dict:
        """Get ensemble status for monitoring."""
        return {
            'model_type': self.model_type,
            'model_loaded': self.model is not None,
            'last_trained': self.last_trained.isoformat() if self.last_trained else None,
            'recent_predictions': len(self.recent_predictions),
            'top_features': dict(list(
                sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
            )) if self.feature_importance else {},
            'config': {
                'min_probability': self.config.min_probability,
                'min_expected_value': self.config.min_expected_value,
                'kelly_fraction': self.config.kelly_fraction,
            }
        }


# Global instance
_ensemble_scorer_v2: Optional[EnsembleScorerV2] = None


def get_ensemble_scorer_v2() -> EnsembleScorerV2:
    """Get or create global ensemble scorer v2 instance."""
    global _ensemble_scorer_v2
    if _ensemble_scorer_v2 is None:
        _ensemble_scorer_v2 = EnsembleScorerV2()
    return _ensemble_scorer_v2
