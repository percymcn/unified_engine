"""
Feature Importance Tracker - 2026 Best Practices
=================================================

Tracks model feature importance over time to detect:
- Feature saturation (importance declining)
- Alpha decay in key features (BB, flow, regime)
- Model drift via importance shifts
- Feature interaction changes

Supports:
- LightGBM / XGBoost importance extraction
- Baseline comparison with alerting
- Rolling importance trends
- Nightly batch updates

Pi5 optimized: Lightweight numpy operations
"""

import logging
import numpy as np
from typing import Dict, Optional, List, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from enum import Enum
import json

logger = logging.getLogger(__name__)

# Try importing model libraries
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False


class ImportanceType(Enum):
    """Feature importance calculation methods"""
    GAIN = "gain"  # Total gain from splits
    SPLIT = "split"  # Number of splits
    PERMUTATION = "permutation"  # Permutation importance


class AlertType(Enum):
    """Feature importance alert types"""
    SATURATION = "saturation"  # Feature importance declining
    RANK_CHANGE = "rank_change"  # Important feature dropped in ranking
    CORRELATION_SHIFT = "correlation_shift"  # Feature correlation changed
    NEW_DOMINANT = "new_dominant"  # New feature became dominant


@dataclass
class FeatureImportanceSnapshot:
    """Snapshot of feature importance at a point in time"""
    timestamp: datetime
    importances: Dict[str, float]  # feature -> importance
    importance_type: ImportanceType
    model_type: str  # 'lightgbm', 'xgboost', etc.

    # Rankings
    top_features: List[str] = field(default_factory=list)

    # Model metadata
    n_features: int = 0
    model_version: str = ""


@dataclass
class FeatureAlert:
    """Alert for feature importance change"""
    timestamp: datetime
    alert_type: AlertType
    feature: str
    message: str

    # Values
    current_value: float = 0.0
    baseline_value: float = 0.0
    change_pct: float = 0.0

    # Severity
    severity: str = "warning"  # 'info', 'warning', 'critical'


@dataclass
class FeatureTrend:
    """Trend analysis for a single feature"""
    feature: str

    # Current stats
    current_importance: float = 0.0
    baseline_importance: float = 0.0
    change_from_baseline_pct: float = 0.0

    # Trend
    slope: float = 0.0  # Importance slope over time
    trend_direction: str = "stable"  # 'increasing', 'decreasing', 'stable'
    is_saturating: bool = False

    # Historical
    importance_history: List[float] = field(default_factory=list)
    rank_history: List[int] = field(default_factory=list)

    # Alerts
    recent_alerts: List[FeatureAlert] = field(default_factory=list)


@dataclass
class FeatureImportanceConfig:
    """Configuration for feature importance tracking"""
    # Core features to monitor closely
    critical_features: List[str] = field(default_factory=lambda: [
        'bb_position', 'bb_squeeze', 'bb_width',  # Bollinger
        'flow_conviction', 'flow_delta', 'call_put_ratio',  # Flow
        'regime_prob', 'adx', 'hurst',  # Regime
        'rsi', 'macd_hist', 'atr_pct',  # TA
        'microstructure_imbalance', 'cumulative_delta',  # Microstructure
    ])

    # Alert thresholds
    saturation_threshold: float = 0.3  # 30% decline = saturation
    rank_change_threshold: int = 5  # Alert if rank drops by this much
    new_dominant_threshold: float = 0.2  # Feature gaining 20%+ importance

    # Trend detection
    trend_window: int = 30  # Days for trend calculation
    slope_threshold: float = 0.01  # Min slope for trend detection

    # History
    max_history: int = 365  # Days of history to keep

    # Baseline
    baseline_window: int = 90  # Days for baseline calculation


class FeatureImportanceTracker:
    """
    Tracks feature importance over time with alerting.

    Features:
    - Extract importance from LightGBM/XGBoost models
    - Track importance trends over time
    - Detect saturation (declining predictive power)
    - Alert on critical feature importance drops
    - Nightly batch analysis
    """

    def __init__(self, config: Optional[FeatureImportanceConfig] = None):
        self.config = config or FeatureImportanceConfig()

        # Importance history per feature
        self.feature_trends: Dict[str, FeatureTrend] = {}

        # Snapshots over time
        self.snapshots: deque = deque(maxlen=self.config.max_history)

        # Baseline importance (running average)
        self.baseline: Dict[str, float] = {}

        # Alerts
        self.alerts: deque = deque(maxlen=1000)

        # Last analysis time
        self.last_analysis: Optional[datetime] = None

        logger.info(
            f"FeatureImportanceTracker initialized: "
            f"critical_features={len(self.config.critical_features)}"
        )

    # ========================================
    # IMPORTANCE EXTRACTION
    # ========================================

    def extract_lightgbm_importance(
        self,
        model,
        importance_type: ImportanceType = ImportanceType.GAIN
    ) -> Dict[str, float]:
        """
        Extract feature importance from LightGBM model.

        Args:
            model: LightGBM Booster or sklearn wrapper
            importance_type: Type of importance to extract

        Returns:
            Dict of feature -> importance
        """
        if not LIGHTGBM_AVAILABLE:
            logger.warning("LightGBM not available")
            return {}

        try:
            # Get importance type string
            imp_type = importance_type.value

            # Handle different model types
            if hasattr(model, 'feature_importance'):
                # LightGBM Booster
                importance = model.feature_importance(importance_type=imp_type)
                features = model.feature_name()
            elif hasattr(model, 'feature_importances_'):
                # sklearn wrapper
                importance = model.feature_importances_
                if hasattr(model, 'feature_name_'):
                    features = model.feature_name_
                else:
                    features = [f'f{i}' for i in range(len(importance))]
            else:
                logger.warning("Unknown LightGBM model type")
                return {}

            # Normalize
            total = sum(importance)
            if total > 0:
                importance = importance / total

            return dict(zip(features, importance))

        except Exception as e:
            logger.error(f"Error extracting LightGBM importance: {e}")
            return {}

    def extract_xgboost_importance(
        self,
        model,
        importance_type: ImportanceType = ImportanceType.GAIN
    ) -> Dict[str, float]:
        """
        Extract feature importance from XGBoost model.

        Args:
            model: XGBoost Booster or sklearn wrapper
            importance_type: Type of importance to extract

        Returns:
            Dict of feature -> importance
        """
        if not XGBOOST_AVAILABLE:
            logger.warning("XGBoost not available")
            return {}

        try:
            # Map importance type
            imp_map = {
                ImportanceType.GAIN: 'gain',
                ImportanceType.SPLIT: 'weight',
                ImportanceType.PERMUTATION: 'cover',
            }
            imp_type = imp_map.get(importance_type, 'gain')

            if hasattr(model, 'get_score'):
                # XGBoost Booster
                importance = model.get_score(importance_type=imp_type)
            elif hasattr(model, 'feature_importances_'):
                # sklearn wrapper
                importance_arr = model.feature_importances_
                if hasattr(model, 'get_booster'):
                    features = model.get_booster().feature_names
                    if features is None:
                        features = [f'f{i}' for i in range(len(importance_arr))]
                else:
                    features = [f'f{i}' for i in range(len(importance_arr))]
                importance = dict(zip(features, importance_arr))
            else:
                logger.warning("Unknown XGBoost model type")
                return {}

            # Normalize
            total = sum(importance.values())
            if total > 0:
                importance = {k: v/total for k, v in importance.items()}

            return importance

        except Exception as e:
            logger.error(f"Error extracting XGBoost importance: {e}")
            return {}

    def extract_importance(
        self,
        model,
        model_type: str = 'auto',
        importance_type: ImportanceType = ImportanceType.GAIN
    ) -> Dict[str, float]:
        """
        Auto-detect model type and extract importance.

        Args:
            model: Model object
            model_type: 'lightgbm', 'xgboost', or 'auto'
            importance_type: Type of importance

        Returns:
            Dict of feature -> importance
        """
        if model_type == 'auto':
            # Try to detect model type
            model_class = type(model).__name__.lower()
            if 'lgb' in model_class or 'lightgbm' in model_class:
                model_type = 'lightgbm'
            elif 'xgb' in model_class or 'xgboost' in model_class:
                model_type = 'xgboost'
            else:
                logger.warning(f"Could not detect model type: {model_class}")
                return {}

        if model_type == 'lightgbm':
            return self.extract_lightgbm_importance(model, importance_type)
        elif model_type == 'xgboost':
            return self.extract_xgboost_importance(model, importance_type)
        else:
            logger.warning(f"Unsupported model type: {model_type}")
            return {}

    # ========================================
    # TRACKING & ANALYSIS
    # ========================================

    def record_snapshot(
        self,
        importances: Dict[str, float],
        model_type: str = 'unknown',
        model_version: str = '',
        importance_type: ImportanceType = ImportanceType.GAIN
    ) -> FeatureImportanceSnapshot:
        """
        Record a feature importance snapshot.

        Args:
            importances: Dict of feature -> importance
            model_type: Type of model
            model_version: Version identifier
            importance_type: How importance was calculated

        Returns:
            FeatureImportanceSnapshot
        """
        # Create snapshot
        snapshot = FeatureImportanceSnapshot(
            timestamp=datetime.now(),
            importances=importances.copy(),
            importance_type=importance_type,
            model_type=model_type,
            n_features=len(importances),
            model_version=model_version
        )

        # Calculate top features
        sorted_features = sorted(
            importances.items(),
            key=lambda x: x[1],
            reverse=True
        )
        snapshot.top_features = [f[0] for f in sorted_features[:10]]

        # Store snapshot
        self.snapshots.append(snapshot)

        # Update feature trends
        for rank, (feature, importance) in enumerate(sorted_features):
            self._update_feature_trend(feature, importance, rank)

        # Update baseline
        self._update_baseline(importances)

        # Check for alerts
        self._check_alerts(importances)

        self.last_analysis = datetime.now()

        logger.debug(
            f"Recorded importance snapshot: {len(importances)} features, "
            f"top={snapshot.top_features[:3]}"
        )

        return snapshot

    def _update_feature_trend(
        self,
        feature: str,
        importance: float,
        rank: int
    ):
        """Update trend tracking for a feature."""
        if feature not in self.feature_trends:
            self.feature_trends[feature] = FeatureTrend(feature=feature)

        trend = self.feature_trends[feature]
        trend.current_importance = importance
        trend.importance_history.append(importance)
        trend.rank_history.append(rank)

        # Trim history
        max_hist = self.config.max_history
        if len(trend.importance_history) > max_hist:
            trend.importance_history = trend.importance_history[-max_hist:]
            trend.rank_history = trend.rank_history[-max_hist:]

        # Calculate trend
        if len(trend.importance_history) >= self.config.trend_window:
            recent = trend.importance_history[-self.config.trend_window:]
            x = np.arange(len(recent))

            # Simple linear regression for slope
            if len(recent) > 1:
                slope = np.polyfit(x, recent, 1)[0]
                trend.slope = slope

                if slope > self.config.slope_threshold:
                    trend.trend_direction = 'increasing'
                elif slope < -self.config.slope_threshold:
                    trend.trend_direction = 'decreasing'
                else:
                    trend.trend_direction = 'stable'

        # Update change from baseline
        if feature in self.baseline and self.baseline[feature] > 0:
            trend.baseline_importance = self.baseline[feature]
            trend.change_from_baseline_pct = (
                (importance - self.baseline[feature]) / self.baseline[feature]
            ) * 100

            # Check for saturation
            trend.is_saturating = (
                trend.change_from_baseline_pct < -self.config.saturation_threshold * 100
            )

    def _update_baseline(self, importances: Dict[str, float]):
        """Update rolling baseline importance."""
        # Get recent snapshots for baseline
        baseline_window = self.config.baseline_window
        recent_snapshots = [
            s for s in self.snapshots
            if (datetime.now() - s.timestamp).days <= baseline_window
        ]

        if len(recent_snapshots) < 7:
            # Not enough data, use current as baseline
            for feature, imp in importances.items():
                if feature not in self.baseline:
                    self.baseline[feature] = imp
            return

        # Calculate average importance per feature
        feature_values: Dict[str, List[float]] = {}
        for snapshot in recent_snapshots:
            for feature, imp in snapshot.importances.items():
                if feature not in feature_values:
                    feature_values[feature] = []
                feature_values[feature].append(imp)

        for feature, values in feature_values.items():
            self.baseline[feature] = np.mean(values)

    def _check_alerts(self, importances: Dict[str, float]):
        """Check for importance alerts."""
        for feature, importance in importances.items():
            trend = self.feature_trends.get(feature)
            if not trend:
                continue

            # Check saturation for critical features
            if feature in self.config.critical_features:
                if trend.is_saturating:
                    self._create_alert(
                        AlertType.SATURATION,
                        feature,
                        f"Critical feature '{feature}' is saturating "
                        f"({trend.change_from_baseline_pct:.1f}% from baseline)",
                        importance,
                        trend.baseline_importance,
                        trend.change_from_baseline_pct,
                        severity='critical'
                    )

            # Check rank changes
            if len(trend.rank_history) >= 2:
                rank_change = trend.rank_history[-2] - trend.rank_history[-1]
                if rank_change >= self.config.rank_change_threshold:
                    if feature in self.config.critical_features:
                        self._create_alert(
                            AlertType.RANK_CHANGE,
                            feature,
                            f"Feature '{feature}' dropped {rank_change} ranks "
                            f"({trend.rank_history[-2]} → {trend.rank_history[-1]})",
                            importance,
                            trend.baseline_importance,
                            rank_change,
                            severity='warning'
                        )

            # Check for new dominant features
            if feature not in self.config.critical_features:
                if (
                    trend.change_from_baseline_pct >
                    self.config.new_dominant_threshold * 100
                ):
                    # Feature gaining importance rapidly
                    if importance > 0.1:  # At least 10% importance
                        self._create_alert(
                            AlertType.NEW_DOMINANT,
                            feature,
                            f"Non-critical feature '{feature}' becoming dominant "
                            f"(+{trend.change_from_baseline_pct:.1f}%, now {importance*100:.1f}%)",
                            importance,
                            trend.baseline_importance,
                            trend.change_from_baseline_pct,
                            severity='info'
                        )

    def _create_alert(
        self,
        alert_type: AlertType,
        feature: str,
        message: str,
        current_value: float,
        baseline_value: float,
        change_pct: float,
        severity: str = 'warning'
    ):
        """Create a feature alert."""
        alert = FeatureAlert(
            timestamp=datetime.now(),
            alert_type=alert_type,
            feature=feature,
            message=message,
            current_value=current_value,
            baseline_value=baseline_value,
            change_pct=change_pct,
            severity=severity
        )

        self.alerts.append(alert)

        # Add to feature trend
        if feature in self.feature_trends:
            self.feature_trends[feature].recent_alerts.append(alert)
            # Keep only recent alerts
            self.feature_trends[feature].recent_alerts = \
                self.feature_trends[feature].recent_alerts[-10:]

        # Log
        log_fn = logger.info if severity == 'info' else (
            logger.warning if severity == 'warning' else logger.error
        )
        log_fn(f"Feature alert [{severity}]: {message}")

    # ========================================
    # BATCH ANALYSIS
    # ========================================

    def run_nightly_analysis(
        self,
        model,
        model_type: str = 'auto'
    ) -> Dict[str, Any]:
        """
        Run nightly feature importance analysis.

        Call this daily after model retraining.

        Returns:
            Dict with analysis results
        """
        logger.info("Running nightly feature importance analysis...")

        results = {
            'timestamp': datetime.now().isoformat(),
            'alerts': [],
            'critical_features_status': {},
            'top_changes': [],
            'saturation_warnings': [],
        }

        # Extract importance
        importances = self.extract_importance(model, model_type)

        if not importances:
            results['error'] = 'Could not extract importance'
            return results

        # Record snapshot
        snapshot = self.record_snapshot(
            importances,
            model_type=model_type,
            model_version=datetime.now().strftime('%Y%m%d')
        )

        # Analyze critical features
        for feature in self.config.critical_features:
            if feature in self.feature_trends:
                trend = self.feature_trends[feature]
                results['critical_features_status'][feature] = {
                    'importance': trend.current_importance,
                    'baseline': trend.baseline_importance,
                    'change_pct': trend.change_from_baseline_pct,
                    'trend': trend.trend_direction,
                    'is_saturating': trend.is_saturating,
                    'rank': trend.rank_history[-1] if trend.rank_history else None,
                }

        # Get top changes
        changes = []
        for feature, trend in self.feature_trends.items():
            if abs(trend.change_from_baseline_pct) > 10:  # >10% change
                changes.append({
                    'feature': feature,
                    'change_pct': trend.change_from_baseline_pct,
                    'direction': 'up' if trend.change_from_baseline_pct > 0 else 'down',
                })

        results['top_changes'] = sorted(
            changes,
            key=lambda x: abs(x['change_pct']),
            reverse=True
        )[:10]

        # Saturation warnings
        for feature, trend in self.feature_trends.items():
            if trend.is_saturating:
                results['saturation_warnings'].append({
                    'feature': feature,
                    'decline_pct': abs(trend.change_from_baseline_pct),
                    'is_critical': feature in self.config.critical_features,
                })

        # Recent alerts
        recent_cutoff = datetime.now() - timedelta(hours=24)
        results['alerts'] = [
            {
                'type': a.alert_type.value,
                'feature': a.feature,
                'message': a.message,
                'severity': a.severity,
            }
            for a in self.alerts
            if a.timestamp > recent_cutoff
        ]

        logger.info(
            f"Nightly analysis complete: "
            f"{len(results['saturation_warnings'])} saturations, "
            f"{len(results['alerts'])} alerts"
        )

        return results

    def get_feature_report(self, feature: str) -> Optional[Dict[str, Any]]:
        """Get detailed report for a single feature."""
        if feature not in self.feature_trends:
            return None

        trend = self.feature_trends[feature]

        return {
            'feature': feature,
            'is_critical': feature in self.config.critical_features,
            'current_importance': trend.current_importance,
            'baseline_importance': trend.baseline_importance,
            'change_from_baseline_pct': trend.change_from_baseline_pct,
            'trend_direction': trend.trend_direction,
            'slope': trend.slope,
            'is_saturating': trend.is_saturating,
            'current_rank': trend.rank_history[-1] if trend.rank_history else None,
            'importance_history_7d': trend.importance_history[-7:],
            'recent_alerts': [
                {
                    'type': a.alert_type.value,
                    'message': a.message,
                    'timestamp': a.timestamp.isoformat(),
                }
                for a in trend.recent_alerts[-5:]
            ],
        }

    def get_saturation_report(self) -> List[Dict[str, Any]]:
        """Get report of all saturating features."""
        saturating = []

        for feature, trend in self.feature_trends.items():
            if trend.is_saturating:
                saturating.append({
                    'feature': feature,
                    'is_critical': feature in self.config.critical_features,
                    'importance': trend.current_importance,
                    'baseline': trend.baseline_importance,
                    'decline_pct': abs(trend.change_from_baseline_pct),
                    'trend_slope': trend.slope,
                })

        # Sort by criticality then decline
        saturating.sort(
            key=lambda x: (not x['is_critical'], -x['decline_pct'])
        )

        return saturating

    # ========================================
    # METRICS INTEGRATION
    # ========================================

    def get_prometheus_metrics(self) -> Dict[str, float]:
        """
        Get metrics for Prometheus exporter.

        Returns:
            Dict suitable for update_feature_importance()
        """
        importances = {}
        for feature, trend in self.feature_trends.items():
            importances[feature] = trend.current_importance
        return importances

    def get_baseline_for_prometheus(self) -> Dict[str, float]:
        """Get baseline for Prometheus comparison."""
        return self.baseline.copy()

    # ========================================
    # STATUS
    # ========================================

    def get_status(self) -> Dict[str, Any]:
        """Get tracker status."""
        return {
            'features_tracked': len(self.feature_trends),
            'critical_features': len(self.config.critical_features),
            'snapshots_stored': len(self.snapshots),
            'alerts_total': len(self.alerts),
            'last_analysis': self.last_analysis.isoformat() if self.last_analysis else None,
            'saturating_features': sum(
                1 for t in self.feature_trends.values() if t.is_saturating
            ),
            'baseline_features': len(self.baseline),
        }

    def export_to_json(self, filepath: str):
        """Export importance history to JSON for analysis."""
        data = {
            'exported_at': datetime.now().isoformat(),
            'config': {
                'critical_features': self.config.critical_features,
                'saturation_threshold': self.config.saturation_threshold,
            },
            'baseline': self.baseline,
            'feature_trends': {
                feature: {
                    'current_importance': trend.current_importance,
                    'baseline_importance': trend.baseline_importance,
                    'change_pct': trend.change_from_baseline_pct,
                    'trend_direction': trend.trend_direction,
                    'is_saturating': trend.is_saturating,
                    'importance_history': trend.importance_history[-30:],
                    'rank_history': trend.rank_history[-30:],
                }
                for feature, trend in self.feature_trends.items()
            },
            'recent_alerts': [
                {
                    'type': a.alert_type.value,
                    'feature': a.feature,
                    'message': a.message,
                    'severity': a.severity,
                    'timestamp': a.timestamp.isoformat(),
                }
                for a in list(self.alerts)[-100:]
            ],
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported importance data to {filepath}")


# Global instance
_importance_tracker: Optional[FeatureImportanceTracker] = None


def get_importance_tracker() -> FeatureImportanceTracker:
    """Get or create global importance tracker."""
    global _importance_tracker
    if _importance_tracker is None:
        _importance_tracker = FeatureImportanceTracker()
    return _importance_tracker
