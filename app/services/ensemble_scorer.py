"""
Ensemble Meta-Model Scorer
==========================

Combines signals from multiple modes into a single probability score:
- Deterministic (MTF indicators)
- Quick Mode (5m momentum)
- Flow Mode (options flow sentiment)
- Regime Detection

Starts with weighted voting, upgradeable to:
- Logistic Regression (sklearn)
- LightGBM/XGBoost (for stronger signal combination)
- Simple RL agent

Only fires webhook if ensemble prob > 68% AND regime allows.

This is the "intelligent brain" that turns independent generators
into one coordinated system - the quant edge.
"""

import logging
import numpy as np
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import sklearn for advanced scoring
try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    LogisticRegression = None
    StandardScaler = None

# Try to import LightGBM for even stronger scoring
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    lgb = None


class SignalSource(Enum):
    """Signal sources for ensemble"""
    DETERMINISTIC = "deterministic"
    QUICK_MODE = "quick_5m"
    FLOW = "flow"
    AI_ONLY = "ai_only"


@dataclass
class SignalInput:
    """Standardized signal input for ensemble"""
    source: SignalSource
    ticker: str
    action: str  # 'buy', 'sell', 'none'
    confidence: float  # 0-100
    timestamp: datetime

    # Optional details
    risk_reward: float = 0.0
    aligned_tfs: int = 0
    volume_ratio: float = 1.0
    flow_score: float = 0.0

    # Regime context
    market_regime: str = 'neutral'

    # Raw data for feature engineering
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnsembleScore:
    """Ensemble scoring result"""
    ticker: str
    action: str  # 'buy', 'sell', 'none'
    probability: float  # 0-100, final combined probability
    position_size_mult: float  # Position size multiplier (0.5-1.5)

    # Contributing signals
    signals_count: int = 0
    signals_agreeing: int = 0
    signals_disagreeing: int = 0

    # Individual contributions
    contributions: Dict[str, float] = field(default_factory=dict)

    # Decision
    should_trade: bool = False
    rejection_reason: str = ''

    # Metadata
    ensemble_method: str = 'weighted_voting'
    calculated_at: datetime = field(default_factory=datetime.now)

    # Debug
    feature_vector: List[float] = field(default_factory=list)
    weights_used: Dict[str, float] = field(default_factory=dict)


@dataclass
class EnsembleConfig:
    """Configuration for ensemble scoring"""
    # Minimum probability to trade
    min_probability: float = 68.0

    # Weight per source (sums to ~1.0 for interpretability)
    weights: Dict[str, float] = field(default_factory=lambda: {
        SignalSource.DETERMINISTIC.value: 0.40,  # Highest weight - most reliable
        SignalSource.QUICK_MODE.value: 0.25,     # Good for momentum
        SignalSource.FLOW.value: 0.20,           # Flow as confirmation
        SignalSource.AI_ONLY.value: 0.15,        # Lower weight - more variable
    })

    # Regime-based weight adjustments
    regime_weight_mods: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        'trending': {
            SignalSource.DETERMINISTIC.value: 1.2,  # Boost deterministic in trends
            SignalSource.QUICK_MODE.value: 1.1,
            SignalSource.FLOW.value: 0.9,
        },
        'ranging': {
            SignalSource.DETERMINISTIC.value: 0.9,
            SignalSource.QUICK_MODE.value: 1.3,  # Quick scalps work in ranges
            SignalSource.FLOW.value: 1.0,
        },
        'high_vol': {
            SignalSource.DETERMINISTIC.value: 1.3,  # Trust MTF more in volatility
            SignalSource.QUICK_MODE.value: 0.7,    # Quick mode risky
            SignalSource.FLOW.value: 0.8,
        },
        'low_vol': {
            SignalSource.DETERMINISTIC.value: 1.0,
            SignalSource.QUICK_MODE.value: 1.0,
            SignalSource.FLOW.value: 1.2,  # Flow breakouts in compression
        },
    })

    # Agreement bonuses
    all_agree_bonus: float = 10.0  # +10% if all signals agree
    majority_agree_bonus: float = 5.0  # +5% if majority agree

    # Disagreement penalties
    conflict_penalty: float = 15.0  # -15% if signals conflict

    # Position sizing parameters
    max_size_mult: float = 1.5
    min_size_mult: float = 0.25
    confidence_size_scaling: bool = True


class EnsembleScorer:
    """
    Combines multiple signal sources into unified trading decision.

    Methods:
    1. Weighted Voting (default) - Simple, interpretable, fast
    2. Logistic Regression - Learns optimal weights from history
    3. LightGBM - Non-linear combinations for complex patterns
    """

    def __init__(self, config: Optional[EnsembleConfig] = None):
        self.config = config or EnsembleConfig()

        # Model for ML-based scoring (loaded if available)
        self.ml_model = None
        self.scaler = None
        self.model_type = 'weighted_voting'

        # Feature names for ML model
        self.feature_names = [
            'det_confidence', 'det_rr', 'det_aligned_tfs',
            'quick_confidence', 'quick_volume_ratio',
            'flow_score', 'flow_premium_ratio',
            'regime_trending', 'regime_ranging', 'regime_high_vol', 'regime_low_vol',
            'signal_agreement',
        ]

        # Performance tracking
        self.decision_history: List[Dict] = []
        self.max_history = 1000

        logger.info(f"EnsembleScorer initialized: method={self.model_type}, "
                   f"min_prob={self.config.min_probability}%")

    def _normalize_confidence(self, confidence: float) -> float:
        """Normalize confidence to 0-1 range."""
        return max(0.0, min(1.0, confidence / 100.0))

    def _build_feature_vector(
        self,
        signals: List[SignalInput],
        regime: str
    ) -> np.ndarray:
        """
        Build feature vector for ML model.

        Returns array of features suitable for sklearn/lightgbm.
        """
        features = []

        # Initialize with zeros
        det_conf, det_rr, det_tfs = 0.0, 0.0, 0.0
        quick_conf, quick_vol = 0.0, 0.0
        flow_score, flow_prem = 0.0, 0.0

        for sig in signals:
            if sig.source == SignalSource.DETERMINISTIC:
                det_conf = self._normalize_confidence(sig.confidence)
                det_rr = min(sig.risk_reward / 5.0, 1.0)  # Normalize R:R to 0-1
                det_tfs = sig.aligned_tfs / 5.0

            elif sig.source == SignalSource.QUICK_MODE:
                quick_conf = self._normalize_confidence(sig.confidence)
                quick_vol = min(sig.volume_ratio / 3.0, 1.0)

            elif sig.source == SignalSource.FLOW:
                flow_score = (sig.flow_score + 10) / 20  # Normalize -10 to +10 -> 0-1
                flow_prem = min(sig.raw_data.get('premium_ratio', 1.0), 1.0)

        # Regime one-hot encoding
        regime_trending = 1.0 if regime == 'trending' else 0.0
        regime_ranging = 1.0 if regime == 'ranging' else 0.0
        regime_high_vol = 1.0 if regime == 'high_vol' else 0.0
        regime_low_vol = 1.0 if regime == 'low_vol' else 0.0

        # Signal agreement (how many agree)
        actions = [s.action for s in signals if s.action != 'none']
        if actions:
            most_common = max(set(actions), key=actions.count)
            agreement = actions.count(most_common) / len(actions)
        else:
            agreement = 0.0

        features = [
            det_conf, det_rr, det_tfs,
            quick_conf, quick_vol,
            flow_score, flow_prem,
            regime_trending, regime_ranging, regime_high_vol, regime_low_vol,
            agreement,
        ]

        return np.array(features).reshape(1, -1)

    def score_signals(
        self,
        signals: List[SignalInput],
        regime: str = 'neutral'
    ) -> EnsembleScore:
        """
        Score multiple signals and produce ensemble decision.

        Args:
            signals: List of SignalInput from different sources
            regime: Current market regime

        Returns:
            EnsembleScore with final probability and decision
        """
        if not signals:
            return EnsembleScore(
                ticker="UNKNOWN",
                action='none',
                probability=0.0,
                position_size_mult=0.0,
                should_trade=False,
                rejection_reason="No signals provided"
            )

        ticker = signals[0].ticker

        # Determine primary action (what most signals suggest)
        buy_signals = [s for s in signals if s.action == 'buy']
        sell_signals = [s for s in signals if s.action == 'sell']
        none_signals = [s for s in signals if s.action == 'none']

        if len(buy_signals) >= len(sell_signals) and len(buy_signals) > 0:
            primary_action = 'buy'
            agreeing = buy_signals
            disagreeing = sell_signals
        elif len(sell_signals) > 0:
            primary_action = 'sell'
            agreeing = sell_signals
            disagreeing = buy_signals
        else:
            return EnsembleScore(
                ticker=ticker,
                action='none',
                probability=0.0,
                position_size_mult=0.0,
                should_trade=False,
                rejection_reason="All signals neutral"
            )

        # Use appropriate scoring method
        if self.model_type == 'weighted_voting':
            result = self._score_weighted_voting(
                signals, primary_action, agreeing, disagreeing, regime
            )
        elif self.model_type == 'logistic' and self.ml_model is not None:
            result = self._score_logistic(signals, primary_action, regime)
        else:
            result = self._score_weighted_voting(
                signals, primary_action, agreeing, disagreeing, regime
            )

        result.ticker = ticker
        result.action = primary_action
        result.signals_count = len(signals)
        result.signals_agreeing = len(agreeing)
        result.signals_disagreeing = len(disagreeing)

        # Calculate position size
        result.position_size_mult = self._calculate_position_size(
            result.probability, regime, len(agreeing), len(disagreeing)
        )

        # Final decision
        if result.probability >= self.config.min_probability:
            if result.signals_disagreeing > result.signals_agreeing:
                result.should_trade = False
                result.rejection_reason = f"Signal conflict: {result.signals_disagreeing} disagree"
            else:
                result.should_trade = True
        else:
            result.should_trade = False
            result.rejection_reason = f"Probability {result.probability:.1f}% < {self.config.min_probability}%"

        # Log decision
        logger.info(
            f"🎲 Ensemble {ticker}: {primary_action.upper()} prob={result.probability:.1f}% "
            f"({result.signals_agreeing}/{result.signals_count} agree) "
            f"size={result.position_size_mult:.2f}x "
            f"regime={regime} → {'✅ TRADE' if result.should_trade else '❌ SKIP'}"
        )

        return result

    def _score_weighted_voting(
        self,
        signals: List[SignalInput],
        primary_action: str,
        agreeing: List[SignalInput],
        disagreeing: List[SignalInput],
        regime: str
    ) -> EnsembleScore:
        """
        Weighted voting ensemble method.

        Each signal contributes its confidence * weight.
        Bonuses/penalties for agreement/disagreement.
        """
        result = EnsembleScore(
            ticker="",
            action=primary_action,
            probability=0.0,
            position_size_mult=1.0,
            ensemble_method='weighted_voting'
        )

        # Get regime weight modifiers
        regime_mods = self.config.regime_weight_mods.get(regime, {})

        total_weight = 0.0
        weighted_score = 0.0

        for signal in signals:
            source_name = signal.source.value
            base_weight = self.config.weights.get(source_name, 0.1)
            regime_mod = regime_mods.get(source_name, 1.0)
            final_weight = base_weight * regime_mod

            if signal.action == primary_action:
                contribution = self._normalize_confidence(signal.confidence) * final_weight
            elif signal.action == 'none':
                contribution = 0.0  # Neutral doesn't contribute
            else:
                # Opposing signal - negative contribution
                contribution = -self._normalize_confidence(signal.confidence) * final_weight * 0.5

            weighted_score += contribution
            total_weight += final_weight

            result.contributions[source_name] = contribution
            result.weights_used[source_name] = final_weight

        # Normalize to percentage
        if total_weight > 0:
            base_probability = (weighted_score / total_weight) * 100
        else:
            base_probability = 0.0

        # Apply bonuses/penalties
        bonus = 0.0

        # All agree bonus
        if len(agreeing) == len(signals) and len(signals) >= 2:
            bonus += self.config.all_agree_bonus

        # Majority agree bonus
        elif len(agreeing) > len(disagreeing) and len(agreeing) >= 2:
            bonus += self.config.majority_agree_bonus

        # Conflict penalty
        if len(disagreeing) > 0 and len(agreeing) > 0:
            conflict_ratio = len(disagreeing) / (len(agreeing) + len(disagreeing))
            bonus -= self.config.conflict_penalty * conflict_ratio

        result.probability = max(0, min(100, base_probability + bonus))
        return result

    def _score_logistic(
        self,
        signals: List[SignalInput],
        primary_action: str,
        regime: str
    ) -> EnsembleScore:
        """
        Logistic regression ensemble method.

        Uses trained model to predict win probability.
        """
        result = EnsembleScore(
            ticker="",
            action=primary_action,
            probability=0.0,
            position_size_mult=1.0,
            ensemble_method='logistic_regression'
        )

        try:
            features = self._build_feature_vector(signals, regime)
            result.feature_vector = features[0].tolist()

            if self.scaler is not None:
                features = self.scaler.transform(features)

            # Predict probability
            proba = self.ml_model.predict_proba(features)[0]

            # Assuming binary classification: index 1 = positive class (trade)
            result.probability = float(proba[1]) * 100

        except Exception as e:
            logger.warning(f"Logistic scoring failed: {e}, falling back to weighted voting")
            agreeing = [s for s in signals if s.action == primary_action]
            disagreeing = [s for s in signals if s.action not in [primary_action, 'none']]
            return self._score_weighted_voting(signals, primary_action, agreeing, disagreeing, regime)

        return result

    def _calculate_position_size(
        self,
        probability: float,
        regime: str,
        agreeing_count: int,
        disagreeing_count: int
    ) -> float:
        """
        Calculate position size multiplier based on conviction.

        Uses simplified Kelly-like approach.
        """
        # Base multiplier from probability
        if self.config.confidence_size_scaling:
            # Scale from 0.5 to 1.5 based on probability
            # 50% prob -> 0.5x, 75% -> 1.0x, 100% -> 1.5x
            base_mult = 0.5 + (probability / 100) * 1.0
        else:
            base_mult = 1.0

        # Agreement bonus
        if agreeing_count > disagreeing_count:
            agreement_mult = 1.0 + (agreeing_count - disagreeing_count) * 0.1
        else:
            agreement_mult = 0.8

        # Regime adjustment
        regime_mult = {
            'trending': 1.1,
            'ranging': 0.9,
            'high_vol': 0.7,  # Smaller in high volatility
            'low_vol': 1.0,
            'neutral': 1.0
        }.get(regime, 1.0)

        final_mult = base_mult * agreement_mult * regime_mult
        return max(self.config.min_size_mult, min(self.config.max_size_mult, final_mult))

    def train_logistic_model(self, historical_data: List[Dict]) -> bool:
        """
        Train logistic regression model from historical trade data.

        Args:
            historical_data: List of dicts with features and outcome (win/loss)

        Returns:
            True if training successful
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("sklearn not available for logistic training")
            return False

        if len(historical_data) < 50:
            logger.warning(f"Insufficient data for training: {len(historical_data)} trades (need 50+)")
            return False

        try:
            # Extract features and labels
            X = np.array([d['features'] for d in historical_data])
            y = np.array([1 if d['outcome'] == 'win' else 0 for d in historical_data])

            # Scale features
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)

            # Train model
            self.ml_model = LogisticRegression(max_iter=1000, random_state=42)
            self.ml_model.fit(X_scaled, y)

            self.model_type = 'logistic'

            # Log coefficients
            logger.info(f"Logistic model trained on {len(historical_data)} trades")
            for name, coef in zip(self.feature_names, self.ml_model.coef_[0]):
                logger.debug(f"  {name}: {coef:.4f}")

            return True

        except Exception as e:
            logger.error(f"Logistic training failed: {e}")
            return False

    def save_model(self, path: str) -> bool:
        """Save trained model to disk."""
        if not SKLEARN_AVAILABLE or self.ml_model is None:
            return False

        try:
            joblib.dump({
                'model': self.ml_model,
                'scaler': self.scaler,
                'feature_names': self.feature_names,
            }, path)
            logger.info(f"Ensemble model saved to {path}")
            return True
        except Exception as e:
            logger.error(f"Model save failed: {e}")
            return False

    def load_model(self, path: str) -> bool:
        """Load trained model from disk."""
        if not SKLEARN_AVAILABLE:
            return False

        try:
            data = joblib.load(path)
            self.ml_model = data['model']
            self.scaler = data['scaler']
            self.feature_names = data['feature_names']
            self.model_type = 'logistic'
            logger.info(f"Ensemble model loaded from {path}")
            return True
        except Exception as e:
            logger.error(f"Model load failed: {e}")
            return False


# Global instance
_ensemble_scorer: Optional[EnsembleScorer] = None


def get_ensemble_scorer() -> EnsembleScorer:
    """Get or create global ensemble scorer instance."""
    global _ensemble_scorer
    if _ensemble_scorer is None:
        _ensemble_scorer = EnsembleScorer()
    return _ensemble_scorer
