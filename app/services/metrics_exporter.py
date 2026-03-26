"""
Prometheus Metrics Exporter - Observability
============================================

Live monitoring metrics for Grafana dashboard:
- Regime probabilities
- Ensemble calibration
- Drawdown tracking
- Signal conviction
- Feature importance
- Strategy decay alerts

Exposes /metrics endpoint for Prometheus scraping.

Pi5 optimized: Lightweight counters/gauges
"""

import logging
import time
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import prometheus_client
try:
    from prometheus_client import Counter, Gauge, Histogram, Summary, Info
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from prometheus_client import CollectorRegistry, multiprocess, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not available - install with: pip install prometheus-client")


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Monitoring alert"""
    name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    ticker: Optional[str] = None
    value: Optional[float] = None
    threshold: Optional[float] = None
    resolved: bool = False


@dataclass
class MetricsConfig:
    """Configuration for metrics exporter"""
    # Enable/disable
    enabled: bool = True

    # Metric namespace
    namespace: str = "smartflow"

    # Alert thresholds
    drawdown_warning_pct: float = 5.0
    drawdown_critical_pct: float = 10.0
    calibration_drift_threshold: float = 0.15
    feature_importance_drop_threshold: float = 0.5
    sharpe_decay_threshold: float = 0.5

    # Alert cooldown (don't spam same alert)
    alert_cooldown_minutes: int = 30

    # History retention
    max_alert_history: int = 1000


class SmartFlowMetrics:
    """
    Prometheus metrics exporter for SmartFlow.

    Creates and manages Prometheus metrics for:
    - Trading signals and outcomes
    - Regime detection
    - Ensemble model performance
    - Risk metrics
    - Feature importance tracking
    """

    def __init__(self, config: Optional[MetricsConfig] = None):
        self.config = config or MetricsConfig()

        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus metrics disabled - library not available")
            self.enabled = False
            return

        self.enabled = self.config.enabled
        self.namespace = self.config.namespace

        # Initialize metrics
        self._init_trading_metrics()
        self._init_regime_metrics()
        self._init_ensemble_metrics()
        self._init_risk_metrics()
        self._init_feature_metrics()
        self._init_system_metrics()

        # Alert tracking
        self.alerts: deque = deque(maxlen=self.config.max_alert_history)
        self.last_alert_time: Dict[str, datetime] = {}

        logger.info(f"SmartFlowMetrics initialized: namespace={self.namespace}")

    def _init_trading_metrics(self):
        """Initialize trading-related metrics."""
        # Signal counters
        self.signals_total = Counter(
            f'{self.namespace}_signals_total',
            'Total signals generated',
            ['ticker', 'action', 'source']
        )

        self.trades_total = Counter(
            f'{self.namespace}_trades_total',
            'Total trades executed',
            ['ticker', 'action', 'outcome']
        )

        # Current signal metrics
        self.signal_confidence = Gauge(
            f'{self.namespace}_signal_confidence',
            'Current signal confidence',
            ['ticker']
        )

        self.signal_conviction = Gauge(
            f'{self.namespace}_signal_conviction',
            'Current signal conviction (flow)',
            ['ticker']
        )

        # P&L metrics
        self.pnl_total = Gauge(
            f'{self.namespace}_pnl_total',
            'Total P&L',
            ['ticker']
        )

        self.pnl_daily = Gauge(
            f'{self.namespace}_pnl_daily',
            'Daily P&L',
            []
        )

        # Win rate
        self.win_rate = Gauge(
            f'{self.namespace}_win_rate',
            'Rolling win rate',
            ['ticker', 'window']
        )

    def _init_regime_metrics(self):
        """Initialize regime detection metrics."""
        # Regime probabilities
        self.regime_probability = Gauge(
            f'{self.namespace}_regime_probability',
            'Regime probability',
            ['ticker', 'regime']
        )

        # Primary regime
        self.primary_regime = Gauge(
            f'{self.namespace}_primary_regime',
            'Primary regime (encoded)',
            ['ticker']
        )

        # Regime features
        self.regime_adx = Gauge(
            f'{self.namespace}_regime_adx',
            'ADX value',
            ['ticker']
        )

        self.regime_hurst = Gauge(
            f'{self.namespace}_regime_hurst',
            'Hurst exponent',
            ['ticker']
        )

        self.regime_vol_zscore = Gauge(
            f'{self.namespace}_regime_vol_zscore',
            'Volatility z-score',
            ['ticker']
        )

    def _init_ensemble_metrics(self):
        """Initialize ensemble model metrics."""
        # Prediction probability
        self.ensemble_probability = Gauge(
            f'{self.namespace}_ensemble_probability',
            'Ensemble prediction probability',
            ['ticker']
        )

        # Expected value
        self.ensemble_ev = Gauge(
            f'{self.namespace}_ensemble_expected_value',
            'Ensemble expected value',
            ['ticker']
        )

        # Calibration
        self.ensemble_calibration_error = Gauge(
            f'{self.namespace}_ensemble_calibration_error',
            'Ensemble calibration error (Brier)',
            []
        )

        # Signal agreement
        self.signal_agreement = Gauge(
            f'{self.namespace}_signal_agreement',
            'Signal source agreement ratio',
            ['ticker']
        )

        # Model metrics
        self.model_accuracy = Gauge(
            f'{self.namespace}_model_accuracy',
            'Rolling model accuracy',
            ['window']
        )

        self.model_sharpe = Gauge(
            f'{self.namespace}_model_sharpe',
            'Rolling Sharpe ratio',
            ['window']
        )

    def _init_risk_metrics(self):
        """Initialize risk management metrics."""
        # Drawdown
        self.drawdown_current = Gauge(
            f'{self.namespace}_drawdown_current',
            'Current drawdown percentage',
            []
        )

        self.drawdown_max = Gauge(
            f'{self.namespace}_drawdown_max',
            'Maximum drawdown percentage',
            []
        )

        # Position metrics
        self.positions_active = Gauge(
            f'{self.namespace}_positions_active',
            'Number of active positions',
            []
        )

        self.exposure_total = Gauge(
            f'{self.namespace}_exposure_total',
            'Total exposure percentage',
            []
        )

        self.exposure_sector = Gauge(
            f'{self.namespace}_exposure_sector',
            'Sector exposure percentage',
            ['sector']
        )

        # CVaR
        self.cvar_95 = Gauge(
            f'{self.namespace}_cvar_95',
            'CVaR 95%',
            ['ticker']
        )

        # Kelly fraction
        self.kelly_fraction = Gauge(
            f'{self.namespace}_kelly_fraction',
            'Current Kelly fraction',
            []
        )

        # Meta-strategy state
        self.trading_state = Gauge(
            f'{self.namespace}_trading_state',
            'Trading state (0=normal, 1=reduced, 2=paused)',
            []
        )

        self.consecutive_losses = Gauge(
            f'{self.namespace}_consecutive_losses',
            'Consecutive losses count',
            []
        )

    def _init_feature_metrics(self):
        """Initialize feature importance metrics."""
        self.feature_importance = Gauge(
            f'{self.namespace}_feature_importance',
            'Feature importance score',
            ['feature']
        )

        self.feature_importance_change = Gauge(
            f'{self.namespace}_feature_importance_change',
            'Feature importance change from baseline',
            ['feature']
        )

    def _init_system_metrics(self):
        """Initialize system metrics."""
        # Drift detection
        self.drift_detected = Gauge(
            f'{self.namespace}_drift_detected',
            'Concept drift detected (0/1)',
            ['strategy']
        )

        self.drift_confidence = Gauge(
            f'{self.namespace}_drift_confidence',
            'Drift detection confidence',
            ['strategy']
        )

        # Processing times
        self.processing_time = Histogram(
            f'{self.namespace}_processing_seconds',
            'Processing time in seconds',
            ['operation'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
        )

        # Data freshness
        self.data_age_seconds = Gauge(
            f'{self.namespace}_data_age_seconds',
            'Data age in seconds',
            ['source']
        )

        # Alert counter
        self.alerts_total = Counter(
            f'{self.namespace}_alerts_total',
            'Total alerts generated',
            ['severity', 'type']
        )

    # ========================================
    # UPDATE METHODS
    # ========================================

    def record_signal(
        self,
        ticker: str,
        action: str,
        source: str,
        confidence: float,
        conviction: float = 0.0
    ):
        """Record a trading signal."""
        if not self.enabled:
            return

        self.signals_total.labels(
            ticker=ticker,
            action=action,
            source=source
        ).inc()

        self.signal_confidence.labels(ticker=ticker).set(confidence)

        if conviction > 0:
            self.signal_conviction.labels(ticker=ticker).set(conviction)

    def record_trade(
        self,
        ticker: str,
        action: str,
        outcome: str,  # 'win', 'loss', 'scratch'
        pnl: float
    ):
        """Record a completed trade."""
        if not self.enabled:
            return

        self.trades_total.labels(
            ticker=ticker,
            action=action,
            outcome=outcome
        ).inc()

        # Update P&L
        current_pnl = self.pnl_total.labels(ticker=ticker)._value.get() or 0
        self.pnl_total.labels(ticker=ticker).set(current_pnl + pnl)

    def update_regime(
        self,
        ticker: str,
        regime_probs: Dict[str, float],
        adx: float,
        hurst: float,
        vol_zscore: float
    ):
        """Update regime detection metrics."""
        if not self.enabled:
            return

        for regime, prob in regime_probs.items():
            self.regime_probability.labels(
                ticker=ticker,
                regime=regime
            ).set(prob)

        # Primary regime (highest prob)
        primary = max(regime_probs, key=regime_probs.get)
        regime_map = {
            'trending_up': 1, 'trending_down': 2,
            'mean_reverting': 3, 'vol_expansion': 4,
            'vol_contraction': 5, 'chaotic': 6
        }
        self.primary_regime.labels(ticker=ticker).set(regime_map.get(primary, 0))

        self.regime_adx.labels(ticker=ticker).set(adx)
        self.regime_hurst.labels(ticker=ticker).set(hurst)
        self.regime_vol_zscore.labels(ticker=ticker).set(vol_zscore)

    def update_ensemble(
        self,
        ticker: str,
        probability: float,
        expected_value: float,
        signal_agreement: float
    ):
        """Update ensemble model metrics."""
        if not self.enabled:
            return

        self.ensemble_probability.labels(ticker=ticker).set(probability)
        self.ensemble_ev.labels(ticker=ticker).set(expected_value)
        self.signal_agreement.labels(ticker=ticker).set(signal_agreement)

    def update_calibration(self, brier_score: float):
        """Update calibration error metric."""
        if not self.enabled:
            return

        self.ensemble_calibration_error.set(brier_score)

        # Check for drift alert
        if brier_score > self.config.calibration_drift_threshold:
            self._create_alert(
                "calibration_drift",
                AlertSeverity.WARNING,
                f"Ensemble calibration degraded: Brier={brier_score:.3f}",
                value=brier_score,
                threshold=self.config.calibration_drift_threshold
            )

    def update_risk(
        self,
        drawdown_current: float,
        drawdown_max: float,
        positions_active: int,
        exposure_total: float,
        sector_exposure: Dict[str, float],
        kelly_fraction: float,
        trading_state: int,  # 0=normal, 1=reduced, 2=paused
        consecutive_losses: int
    ):
        """Update risk metrics."""
        if not self.enabled:
            return

        self.drawdown_current.set(drawdown_current)
        self.drawdown_max.set(drawdown_max)
        self.positions_active.set(positions_active)
        self.exposure_total.set(exposure_total)
        self.kelly_fraction.set(kelly_fraction)
        self.trading_state.set(trading_state)
        self.consecutive_losses.set(consecutive_losses)

        for sector, exposure in sector_exposure.items():
            self.exposure_sector.labels(sector=sector).set(exposure)

        # Check drawdown alerts
        if drawdown_current > self.config.drawdown_critical_pct:
            self._create_alert(
                "drawdown_critical",
                AlertSeverity.CRITICAL,
                f"Critical drawdown: {drawdown_current:.1f}%",
                value=drawdown_current,
                threshold=self.config.drawdown_critical_pct
            )
        elif drawdown_current > self.config.drawdown_warning_pct:
            self._create_alert(
                "drawdown_warning",
                AlertSeverity.WARNING,
                f"Drawdown warning: {drawdown_current:.1f}%",
                value=drawdown_current,
                threshold=self.config.drawdown_warning_pct
            )

    def update_feature_importance(
        self,
        importances: Dict[str, float],
        baseline: Optional[Dict[str, float]] = None
    ):
        """Update feature importance metrics."""
        if not self.enabled:
            return

        for feature, importance in importances.items():
            self.feature_importance.labels(feature=feature).set(importance)

            if baseline and feature in baseline:
                change = (importance - baseline[feature]) / baseline[feature]
                self.feature_importance_change.labels(feature=feature).set(change)

                # Alert if importance dropped significantly
                if change < -self.config.feature_importance_drop_threshold:
                    self._create_alert(
                        "feature_importance_drop",
                        AlertSeverity.WARNING,
                        f"Feature '{feature}' importance dropped {abs(change)*100:.0f}%",
                        value=change,
                        threshold=-self.config.feature_importance_drop_threshold
                    )

    def update_drift(
        self,
        strategy: str,
        drift_detected: bool,
        confidence: float
    ):
        """Update drift detection metrics."""
        if not self.enabled:
            return

        self.drift_detected.labels(strategy=strategy).set(1 if drift_detected else 0)
        self.drift_confidence.labels(strategy=strategy).set(confidence)

        if drift_detected:
            self._create_alert(
                "concept_drift",
                AlertSeverity.WARNING,
                f"Concept drift detected for {strategy} (conf={confidence:.2f})",
                value=confidence
            )

    def update_model_performance(
        self,
        accuracy_30d: float,
        accuracy_90d: float,
        sharpe_30d: float,
        sharpe_90d: float
    ):
        """Update model performance metrics."""
        if not self.enabled:
            return

        self.model_accuracy.labels(window='30d').set(accuracy_30d)
        self.model_accuracy.labels(window='90d').set(accuracy_90d)
        self.model_sharpe.labels(window='30d').set(sharpe_30d)
        self.model_sharpe.labels(window='90d').set(sharpe_90d)

        # Alert on Sharpe decay
        if sharpe_30d < self.config.sharpe_decay_threshold:
            self._create_alert(
                "sharpe_decay",
                AlertSeverity.WARNING,
                f"Sharpe ratio decay: 30d={sharpe_30d:.2f}",
                value=sharpe_30d,
                threshold=self.config.sharpe_decay_threshold
            )

    def record_processing_time(self, operation: str, duration: float):
        """Record operation processing time."""
        if not self.enabled:
            return

        self.processing_time.labels(operation=operation).observe(duration)

    def update_data_freshness(self, source: str, age_seconds: float):
        """Update data freshness metric."""
        if not self.enabled:
            return

        self.data_age_seconds.labels(source=source).set(age_seconds)

    # ========================================
    # ALERTS
    # ========================================

    def _create_alert(
        self,
        alert_type: str,
        severity: AlertSeverity,
        message: str,
        ticker: Optional[str] = None,
        value: Optional[float] = None,
        threshold: Optional[float] = None
    ):
        """Create and record an alert."""
        # Check cooldown
        alert_key = f"{alert_type}:{ticker or 'global'}"
        if alert_key in self.last_alert_time:
            elapsed = (datetime.now() - self.last_alert_time[alert_key]).total_seconds() / 60
            if elapsed < self.config.alert_cooldown_minutes:
                return

        alert = Alert(
            name=alert_type,
            severity=severity,
            message=message,
            ticker=ticker,
            value=value,
            threshold=threshold
        )

        self.alerts.append(alert)
        self.last_alert_time[alert_key] = datetime.now()

        # Increment counter
        if self.enabled:
            self.alerts_total.labels(
                severity=severity.value,
                type=alert_type
            ).inc()

        # Log
        log_fn = logger.warning if severity == AlertSeverity.WARNING else logger.error
        if severity == AlertSeverity.CRITICAL:
            log_fn = logger.error
        log_fn(f"🚨 Alert [{severity.value}]: {message}")

    def get_active_alerts(self) -> List[Alert]:
        """Get unresolved alerts."""
        return [a for a in self.alerts if not a.resolved]

    def resolve_alert(self, alert_name: str, ticker: Optional[str] = None):
        """Mark alert as resolved."""
        for alert in self.alerts:
            if alert.name == alert_name and alert.ticker == ticker:
                alert.resolved = True

    # ========================================
    # EXPORT
    # ========================================

    def get_metrics(self) -> bytes:
        """Get Prometheus metrics in text format."""
        if not PROMETHEUS_AVAILABLE:
            return b"# Prometheus client not available\n"

        return generate_latest(REGISTRY)

    def get_content_type(self) -> str:
        """Get content type for metrics endpoint."""
        if not PROMETHEUS_AVAILABLE:
            return "text/plain"
        return CONTENT_TYPE_LATEST

    def get_status(self) -> Dict[str, Any]:
        """Get metrics exporter status."""
        return {
            'enabled': self.enabled,
            'prometheus_available': PROMETHEUS_AVAILABLE,
            'active_alerts': len(self.get_active_alerts()),
            'total_alerts': len(self.alerts),
            'namespace': self.config.namespace,
        }


# Global instance
_metrics: Optional[SmartFlowMetrics] = None


def get_metrics() -> SmartFlowMetrics:
    """Get or create global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = SmartFlowMetrics()
    return _metrics
