"""
Adaptive Learning & Drift Detection - 2026 Best Practices
==========================================================

Live validation and auto-adaptation loop:
- Online learning for ensemble (incremental LightGBM updates)
- Concept drift detection (ADWIN + Page-Hinkley)
- A/B testing with shadow mode (parallel thresholds)
- Automatic retraining triggers
- Strategy decay tracking

Pi5 optimized: Incremental updates ~10-50ms
"""

import logging
import numpy as np
from typing import Dict, Optional, List, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from enum import Enum
import json
import os

logger = logging.getLogger(__name__)

# Try to import LightGBM for incremental learning
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    lgb = None


class DriftStatus(Enum):
    """Concept drift status"""
    STABLE = "stable"
    WARNING = "warning"
    DRIFT_DETECTED = "drift_detected"
    RETRAINING = "retraining"


@dataclass
class DriftMetrics:
    """Metrics from drift detection"""
    status: DriftStatus = DriftStatus.STABLE
    timestamp: datetime = field(default_factory=datetime.now)

    # ADWIN metrics
    adwin_mean_old: float = 0.0
    adwin_mean_new: float = 0.0
    adwin_window_size: int = 0
    adwin_cut_point: Optional[int] = None

    # Page-Hinkley metrics
    ph_cumsum: float = 0.0
    ph_min_cumsum: float = 0.0
    ph_threshold_exceeded: bool = False

    # Residual statistics
    residual_mean: float = 0.0
    residual_std: float = 0.0
    residual_zscore: float = 0.0

    # Confidence
    drift_confidence: float = 0.0  # 0-1


@dataclass
class ShadowModeResult:
    """Result from shadow mode A/B testing"""
    config_a_name: str
    config_b_name: str
    timestamp: datetime = field(default_factory=datetime.now)

    # A/B metrics
    trades_a: int = 0
    trades_b: int = 0
    wins_a: int = 0
    wins_b: int = 0
    pnl_a: float = 0.0
    pnl_b: float = 0.0

    # Derived
    win_rate_a: float = 0.0
    win_rate_b: float = 0.0
    sharpe_a: float = 0.0
    sharpe_b: float = 0.0

    # Winner
    winner: str = ''
    confidence: float = 0.0


@dataclass
class StrategyDecay:
    """Strategy performance decay tracking"""
    ticker: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Rolling Sharpe
    sharpe_30d: float = 0.0
    sharpe_90d: float = 0.0
    sharpe_lifetime: float = 0.0

    # Decay metrics
    sharpe_decay_30d: float = 0.0  # Current vs 30d ago
    sharpe_decay_90d: float = 0.0

    # Win rate decay
    win_rate_30d: float = 0.0
    win_rate_decay: float = 0.0

    # Action
    should_reduce_size: bool = False
    recommended_size_mult: float = 1.0


@dataclass
class AdaptiveLearningConfig:
    """Configuration for adaptive learning"""
    # ADWIN parameters
    adwin_delta: float = 0.002  # Confidence parameter (lower = more sensitive)
    adwin_min_window: int = 30

    # Page-Hinkley parameters
    ph_lambda: float = 0.5  # Minimum detection threshold
    ph_alpha: float = 0.005  # Tolerable change magnitude

    # Retraining triggers
    drift_retrain_threshold: float = 0.7  # Confidence to trigger retrain
    max_retrain_frequency_hours: int = 24
    min_samples_for_retrain: int = 100

    # Shadow mode
    shadow_mode_enabled: bool = True
    shadow_warmup_trades: int = 20
    shadow_significance_threshold: float = 0.7

    # Decay tracking
    decay_check_interval_hours: int = 24
    decay_threshold_sharpe: float = 0.5  # Reduce size if Sharpe drops below
    decay_reduction_factor: float = 0.5  # Reduce to this fraction

    # Online learning
    online_learning_enabled: bool = True
    batch_size_for_update: int = 10
    learning_rate_decay: float = 0.99


class ADWINDetector:
    """
    ADWIN (Adaptive Windowing) drift detector.

    Maintains a variable-length window of recent values,
    automatically shrinking when distribution changes.
    """

    def __init__(self, delta: float = 0.002, min_window: int = 30):
        self.delta = delta
        self.min_window = min_window
        self.window: deque = deque()
        self.total: float = 0.0
        self.variance: float = 0.0
        self.width: int = 0

    def update(self, value: float) -> Tuple[bool, Optional[DriftMetrics]]:
        """
        Add value and check for drift.

        Returns: (drift_detected, metrics)
        """
        self.window.append(value)
        self.total += value
        self.width += 1

        if self.width < self.min_window * 2:
            return False, None

        # Check for drift using statistical test
        drift_detected = False
        cut_point = None
        old_mean = 0.0
        new_mean = 0.0

        # Try different cut points
        for i in range(self.min_window, len(self.window) - self.min_window):
            n1 = i
            n2 = len(self.window) - i

            sum1 = sum(list(self.window)[:i])
            sum2 = sum(list(self.window)[i:])

            mean1 = sum1 / n1
            mean2 = sum2 / n2

            # Hoeffding bound
            epsilon = self._compute_epsilon(n1, n2)

            if abs(mean1 - mean2) > epsilon:
                drift_detected = True
                cut_point = i
                old_mean = mean1
                new_mean = mean2
                break

        if drift_detected:
            # Shrink window
            for _ in range(cut_point):
                removed = self.window.popleft()
                self.total -= removed
                self.width -= 1

            metrics = DriftMetrics(
                status=DriftStatus.DRIFT_DETECTED,
                adwin_mean_old=old_mean,
                adwin_mean_new=new_mean,
                adwin_window_size=self.width,
                adwin_cut_point=cut_point,
                drift_confidence=0.8
            )
            return True, metrics

        return False, None

    def _compute_epsilon(self, n1: int, n2: int) -> float:
        """Compute Hoeffding bound."""
        m = 1.0 / (1.0 / n1 + 1.0 / n2)
        delta_prime = np.log(2.0 / self.delta)
        epsilon = np.sqrt(0.5 * (1.0 / m) * delta_prime)
        return epsilon

    @property
    def mean(self) -> float:
        """Current mean of window."""
        return self.total / self.width if self.width > 0 else 0.0


class PageHinkleyDetector:
    """
    Page-Hinkley drift detector.

    Detects changes in the mean of a Gaussian signal.
    Good for detecting gradual drift.
    """

    def __init__(self, lambda_param: float = 0.5, alpha: float = 0.005):
        self.lambda_param = lambda_param  # Threshold
        self.alpha = alpha  # Tolerable change
        self.cumsum: float = 0.0
        self.min_cumsum: float = float('inf')
        self.n: int = 0
        self.sum: float = 0.0

    def update(self, value: float) -> Tuple[bool, Optional[DriftMetrics]]:
        """
        Add value and check for drift.

        Returns: (drift_detected, metrics)
        """
        self.n += 1
        self.sum += value
        mean = self.sum / self.n

        # Update cumulative sum
        self.cumsum += value - mean - self.alpha
        self.min_cumsum = min(self.min_cumsum, self.cumsum)

        # Check for drift
        ph_value = self.cumsum - self.min_cumsum

        if ph_value > self.lambda_param:
            metrics = DriftMetrics(
                status=DriftStatus.DRIFT_DETECTED,
                ph_cumsum=self.cumsum,
                ph_min_cumsum=self.min_cumsum,
                ph_threshold_exceeded=True,
                drift_confidence=min(1.0, ph_value / (self.lambda_param * 2))
            )
            return True, metrics

        return False, None

    def reset(self):
        """Reset detector after drift detection."""
        self.cumsum = 0.0
        self.min_cumsum = float('inf')
        self.n = 0
        self.sum = 0.0


class AdaptiveLearningManager:
    """
    Manages adaptive learning and drift detection.

    Features:
    - Online incremental learning for LightGBM
    - Dual drift detection (ADWIN + Page-Hinkley)
    - Shadow mode A/B testing
    - Strategy decay tracking
    - Automatic retraining triggers
    """

    def __init__(self, config: Optional[AdaptiveLearningConfig] = None):
        self.config = config or AdaptiveLearningConfig()

        # Drift detectors per ticker/strategy
        self.adwin_detectors: Dict[str, ADWINDetector] = {}
        self.ph_detectors: Dict[str, PageHinkleyDetector] = {}

        # Drift status
        self.drift_status: Dict[str, DriftStatus] = {}
        self.last_drift_time: Dict[str, datetime] = {}
        self.last_retrain_time: Optional[datetime] = None

        # Online learning buffer
        self.learning_buffer: List[Dict] = []
        self.online_model = None

        # Shadow mode tracking
        self.shadow_trades_a: List[Dict] = []
        self.shadow_trades_b: List[Dict] = []
        self.shadow_config_a: Dict[str, Any] = {}
        self.shadow_config_b: Dict[str, Any] = {}

        # Strategy decay tracking
        self.performance_history: Dict[str, deque] = {}
        self.sharpe_history: Dict[str, deque] = {}
        self.max_history = 500

        # Callbacks
        self.on_drift_detected: Optional[Callable] = None
        self.on_retrain_needed: Optional[Callable] = None

        logger.info(
            f"AdaptiveLearningManager initialized: "
            f"ADWIN_delta={self.config.adwin_delta}, "
            f"PH_lambda={self.config.ph_lambda}, "
            f"shadow_mode={'enabled' if self.config.shadow_mode_enabled else 'disabled'}"
        )

    # ========================================
    # DRIFT DETECTION
    # ========================================

    def check_drift(
        self,
        key: str,
        residual: float
    ) -> DriftMetrics:
        """
        Check for concept drift using prediction residuals.

        Args:
            key: Strategy/model identifier
            residual: Prediction error (predicted - actual)

        Returns:
            DriftMetrics with current status
        """
        # Initialize detectors if needed
        if key not in self.adwin_detectors:
            self.adwin_detectors[key] = ADWINDetector(
                delta=self.config.adwin_delta,
                min_window=self.config.adwin_min_window
            )
        if key not in self.ph_detectors:
            self.ph_detectors[key] = PageHinkleyDetector(
                lambda_param=self.config.ph_lambda,
                alpha=self.config.ph_alpha
            )

        # Run both detectors
        adwin_drift, adwin_metrics = self.adwin_detectors[key].update(residual)
        ph_drift, ph_metrics = self.ph_detectors[key].update(residual)

        # Combine results
        if adwin_drift or ph_drift:
            self.drift_status[key] = DriftStatus.DRIFT_DETECTED
            self.last_drift_time[key] = datetime.now()

            # Combine metrics
            metrics = adwin_metrics or ph_metrics or DriftMetrics()
            metrics.status = DriftStatus.DRIFT_DETECTED

            if adwin_metrics and ph_metrics:
                metrics.drift_confidence = max(
                    adwin_metrics.drift_confidence,
                    ph_metrics.drift_confidence
                )

            # Log and callback
            logger.warning(
                f"🚨 Drift detected for {key}: "
                f"ADWIN={adwin_drift}, PH={ph_drift}, "
                f"confidence={metrics.drift_confidence:.2f}"
            )

            if self.on_drift_detected:
                self.on_drift_detected(key, metrics)

            # Check if retraining needed
            if metrics.drift_confidence >= self.config.drift_retrain_threshold:
                self._trigger_retrain(key)

            return metrics

        # No drift
        self.drift_status[key] = DriftStatus.STABLE
        return DriftMetrics(status=DriftStatus.STABLE)

    def _trigger_retrain(self, key: str):
        """Trigger model retraining if conditions met."""
        # Check frequency limit
        if self.last_retrain_time:
            hours_since = (datetime.now() - self.last_retrain_time).total_seconds() / 3600
            if hours_since < self.config.max_retrain_frequency_hours:
                logger.info(f"Retrain skipped: only {hours_since:.1f}h since last retrain")
                return

        # Check buffer size
        if len(self.learning_buffer) < self.config.min_samples_for_retrain:
            logger.info(
                f"Retrain skipped: only {len(self.learning_buffer)} samples "
                f"(need {self.config.min_samples_for_retrain})"
            )
            return

        logger.info(f"🔄 Triggering retrain for {key}")
        self.drift_status[key] = DriftStatus.RETRAINING

        if self.on_retrain_needed:
            self.on_retrain_needed(key, self.learning_buffer.copy())

        # Reset detector
        self.ph_detectors[key].reset()
        self.last_retrain_time = datetime.now()

    # ========================================
    # ONLINE LEARNING
    # ========================================

    def add_sample(
        self,
        features: np.ndarray,
        label: int,  # 1 = win, 0 = loss
        metadata: Optional[Dict] = None
    ):
        """
        Add sample to learning buffer for incremental updates.

        Args:
            features: Feature vector
            label: Outcome label
            metadata: Optional metadata (ticker, timestamp, etc.)
        """
        sample = {
            'features': features.tolist() if isinstance(features, np.ndarray) else features,
            'label': label,
            'timestamp': datetime.now(),
            'metadata': metadata or {}
        }

        self.learning_buffer.append(sample)

        # Trigger incremental update if batch full
        if len(self.learning_buffer) >= self.config.batch_size_for_update:
            self._incremental_update()

    def _incremental_update(self) -> bool:
        """
        Perform incremental update on model.

        LightGBM supports incremental training via continue_train.
        """
        if not self.config.online_learning_enabled:
            return False

        if not LIGHTGBM_AVAILABLE:
            logger.warning("LightGBM not available for online learning")
            return False

        if self.online_model is None:
            logger.debug("No model loaded for online learning")
            return False

        try:
            # Extract batch
            batch = self.learning_buffer[-self.config.batch_size_for_update:]

            X = np.array([s['features'] for s in batch])
            y = np.array([s['label'] for s in batch])

            # Create dataset
            train_data = lgb.Dataset(X, label=y)

            # Incremental update (continue training)
            self.online_model = lgb.train(
                params={
                    'objective': 'binary',
                    'metric': 'auc',
                    'boosting_type': 'gbdt',
                    'num_leaves': 31,
                    'learning_rate': 0.01 * self.config.learning_rate_decay,  # Lower LR for updates
                    'n_estimators': 5,  # Few iterations
                    'verbose': -1,
                },
                train_set=train_data,
                init_model=self.online_model,
                num_boost_round=5
            )

            logger.debug(f"Incremental update completed with {len(batch)} samples")
            return True

        except Exception as e:
            logger.error(f"Incremental update failed: {e}")
            return False

    def set_online_model(self, model):
        """Set the model for online learning."""
        self.online_model = model

    # ========================================
    # SHADOW MODE A/B TESTING
    # ========================================

    def setup_shadow_mode(
        self,
        config_a: Dict[str, Any],
        config_b: Dict[str, Any],
        name_a: str = "current",
        name_b: str = "candidate"
    ):
        """
        Setup shadow mode for A/B testing.

        Args:
            config_a: Configuration A (e.g., threshold=0.65)
            config_b: Configuration B (e.g., threshold=0.70)
            name_a: Name for config A
            name_b: Name for config B
        """
        self.shadow_config_a = {'name': name_a, **config_a}
        self.shadow_config_b = {'name': name_b, **config_b}
        self.shadow_trades_a = []
        self.shadow_trades_b = []

        logger.info(f"Shadow mode setup: {name_a} vs {name_b}")

    def record_shadow_trade(
        self,
        config: str,  # 'a' or 'b'
        would_trade: bool,
        outcome: Optional[int] = None,  # 1 = win, 0 = loss, None = pending
        pnl: float = 0.0
    ):
        """Record trade decision/outcome for shadow testing."""
        trade = {
            'timestamp': datetime.now(),
            'would_trade': would_trade,
            'outcome': outcome,
            'pnl': pnl
        }

        if config == 'a':
            self.shadow_trades_a.append(trade)
        else:
            self.shadow_trades_b.append(trade)

    def evaluate_shadow_mode(self) -> Optional[ShadowModeResult]:
        """
        Evaluate A/B test results.

        Returns winner with confidence.
        """
        if not self.config.shadow_mode_enabled:
            return None

        # Filter completed trades
        completed_a = [t for t in self.shadow_trades_a if t['outcome'] is not None]
        completed_b = [t for t in self.shadow_trades_b if t['outcome'] is not None]

        if len(completed_a) < self.config.shadow_warmup_trades or \
           len(completed_b) < self.config.shadow_warmup_trades:
            return None

        result = ShadowModeResult(
            config_a_name=self.shadow_config_a.get('name', 'A'),
            config_b_name=self.shadow_config_b.get('name', 'B')
        )

        # Calculate metrics
        result.trades_a = len(completed_a)
        result.trades_b = len(completed_b)

        result.wins_a = sum(1 for t in completed_a if t['outcome'] == 1)
        result.wins_b = sum(1 for t in completed_b if t['outcome'] == 1)

        result.pnl_a = sum(t['pnl'] for t in completed_a)
        result.pnl_b = sum(t['pnl'] for t in completed_b)

        result.win_rate_a = result.wins_a / result.trades_a if result.trades_a > 0 else 0
        result.win_rate_b = result.wins_b / result.trades_b if result.trades_b > 0 else 0

        # Calculate Sharpe approximation
        pnls_a = [t['pnl'] for t in completed_a]
        pnls_b = [t['pnl'] for t in completed_b]

        if len(pnls_a) > 1:
            result.sharpe_a = np.mean(pnls_a) / np.std(pnls_a) if np.std(pnls_a) > 0 else 0
        if len(pnls_b) > 1:
            result.sharpe_b = np.mean(pnls_b) / np.std(pnls_b) if np.std(pnls_b) > 0 else 0

        # Determine winner (prioritize Sharpe)
        if result.sharpe_a > result.sharpe_b:
            result.winner = result.config_a_name
            sharpe_diff = result.sharpe_a - result.sharpe_b
        else:
            result.winner = result.config_b_name
            sharpe_diff = result.sharpe_b - result.sharpe_a

        # Confidence based on sample size and difference
        min_trades = min(result.trades_a, result.trades_b)
        sample_confidence = min(1.0, min_trades / 50)
        diff_confidence = min(1.0, sharpe_diff / 0.5)

        result.confidence = sample_confidence * diff_confidence

        logger.info(
            f"📊 Shadow mode: {result.config_a_name} Sharpe={result.sharpe_a:.2f} vs "
            f"{result.config_b_name} Sharpe={result.sharpe_b:.2f} → "
            f"Winner: {result.winner} (conf={result.confidence:.2f})"
        )

        return result

    # ========================================
    # STRATEGY DECAY TRACKING
    # ========================================

    def record_performance(
        self,
        key: str,
        pnl: float,
        is_win: bool
    ):
        """Record trade performance for decay tracking."""
        if key not in self.performance_history:
            self.performance_history[key] = deque(maxlen=self.max_history)
            self.sharpe_history[key] = deque(maxlen=self.max_history)

        self.performance_history[key].append({
            'timestamp': datetime.now(),
            'pnl': pnl,
            'is_win': is_win
        })

    def calculate_decay(self, key: str) -> StrategyDecay:
        """
        Calculate strategy performance decay.

        Returns recommendations for size adjustment.
        """
        decay = StrategyDecay(ticker=key)

        if key not in self.performance_history:
            return decay

        history = list(self.performance_history[key])
        if len(history) < 30:
            return decay

        now = datetime.now()

        # Split by time periods
        trades_30d = [t for t in history
                      if (now - t['timestamp']).days <= 30]
        trades_90d = [t for t in history
                      if (now - t['timestamp']).days <= 90]

        # Calculate Sharpe for periods
        if len(trades_30d) > 10:
            pnls_30d = [t['pnl'] for t in trades_30d]
            decay.sharpe_30d = (
                np.mean(pnls_30d) / np.std(pnls_30d) * np.sqrt(252)
                if np.std(pnls_30d) > 0 else 0
            )
            decay.win_rate_30d = sum(1 for t in trades_30d if t['is_win']) / len(trades_30d)

        if len(trades_90d) > 30:
            pnls_90d = [t['pnl'] for t in trades_90d]
            decay.sharpe_90d = (
                np.mean(pnls_90d) / np.std(pnls_90d) * np.sqrt(252)
                if np.std(pnls_90d) > 0 else 0
            )

        # Calculate decay (comparing recent to older performance)
        if decay.sharpe_90d > 0:
            decay.sharpe_decay_90d = (decay.sharpe_90d - decay.sharpe_30d) / decay.sharpe_90d

        # Check if size reduction needed
        if decay.sharpe_30d < self.config.decay_threshold_sharpe:
            decay.should_reduce_size = True
            decay.recommended_size_mult = self.config.decay_reduction_factor

            logger.warning(
                f"📉 Strategy decay {key}: Sharpe_30d={decay.sharpe_30d:.2f} < "
                f"threshold={self.config.decay_threshold_sharpe} → "
                f"reduce size to {decay.recommended_size_mult:.0%}"
            )

        return decay

    # ========================================
    # STATUS
    # ========================================

    def get_status(self) -> Dict[str, Any]:
        """Get adaptive learning status."""
        return {
            'drift_status': {k: v.value for k, v in self.drift_status.items()},
            'learning_buffer_size': len(self.learning_buffer),
            'online_model_loaded': self.online_model is not None,
            'shadow_mode': {
                'enabled': self.config.shadow_mode_enabled,
                'trades_a': len(self.shadow_trades_a),
                'trades_b': len(self.shadow_trades_b),
                'config_a': self.shadow_config_a.get('name', ''),
                'config_b': self.shadow_config_b.get('name', ''),
            },
            'last_retrain': self.last_retrain_time.isoformat() if self.last_retrain_time else None,
            'performance_trackers': list(self.performance_history.keys()),
        }


# Global instance
_adaptive_manager: Optional[AdaptiveLearningManager] = None


def get_adaptive_manager() -> AdaptiveLearningManager:
    """Get or create global adaptive learning manager."""
    global _adaptive_manager
    if _adaptive_manager is None:
        _adaptive_manager = AdaptiveLearningManager()
    return _adaptive_manager
