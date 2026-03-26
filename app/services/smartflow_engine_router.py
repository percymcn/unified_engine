"""
SmartFlow Adaptive Engine Router - Phase 3
===========================================

Honest, regime-aware engine selection using only fully-routed engines.

Routing Modes:
- MANUAL: User selects engine explicitly
- AUTO_BY_REGIME: Router selects based on market regime

SLIM MAP MODE (env: SMARTFLOW_SLIM_MAP=true):
When enabled, restricts routing to only truly backtest-validated engines:
- quick (Sharpe 7.30, 73.5% win rate - VALIDATED)
- unified (129% return, Sharpe 5.61 - VALIDATED)

Specialized engines (breakout, trend, mean_reversion, liquidity_reversal)
are excluded from slim map until true specialized backtest paths exist.

Auto-Eligible Engines (fully routed only):
- unified
- deterministic
- quick

Manual-Only Engines (fallback-backed):
- ai
- flow

Routing Logic (First Version - Rule-Based):
- ranging/mean-reverting → deterministic (strict alignment)
- fast momentum/intraday → quick (5m momentum)
- mixed/unclear/default → unified (balanced)

Later versions may use comparison results to override rules.
"""

import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

# Phase 8A: Strategy Registry Integration
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# =============================================================================
# SLIM MAP MODE - Honest Interim Runtime Configuration
# =============================================================================
# When SMARTFLOW_SLIM_MAP=true, only truly backtest-validated engines are used
SLIM_MAP_ENABLED = os.getenv('SMARTFLOW_SLIM_MAP', 'true').lower() == 'true'

# Engines with TRUE backtest paths (validated, not unified fallback)
SLIM_MAP_ENGINES = ['quick', 'unified']

# Specialized engines - Phase 5C: Now have TRUE backtest paths
# They were previously falling back to unified_strategy, but are now fully routed
SPECIALIZED_ENGINES_TRUE_PATHS = ['breakout', 'trend', 'mean_reversion', 'liquidity_reversal']

# Legacy alias for backwards compatibility
SPECIALIZED_ENGINES_PENDING = []  # Empty - all now have TRUE paths as of Phase 5C

# Deterministic is validated but weak - can be optionally restricted
DETERMINISTIC_RESTRICTED = os.getenv('SMARTFLOW_DETERMINISTIC_RESTRICTED', 'true').lower() == 'true'

# =============================================================================
# ENGINE STATUS LABELS (Phase 5C - Honest Labeling)
# =============================================================================
# These labels reflect the TRUE state of each engine's backtest capability
ENGINE_STATUS = {
    'quick': {
        'label': 'VALIDATED',
        'backtest_path': 'TRUE',
        'performance': 'Strong (Sharpe 7.30, 73.5% win rate in prior testing)',
        'routing': 'SLIM_MAP_ELIGIBLE',
        'notes': 'True 5m momentum quick mode with volume confirmation'
    },
    'unified': {
        'label': 'VALIDATED',
        'backtest_path': 'TRUE',
        'performance': 'Strong (129% return, Sharpe 5.61 in prior testing)',
        'routing': 'SLIM_MAP_ELIGIBLE',
        'notes': 'Default unified strategy with regime detection'
    },
    'deterministic': {
        'label': 'VALIDATED_WEAK',
        'backtest_path': 'TRUE',
        'performance': 'Weak (-1% return, 30.8% win rate)',
        'routing': 'RESTRICTED' if DETERMINISTIC_RESTRICTED else 'AVAILABLE',
        'notes': 'True MTF deterministic but underperforming - restricted by default'
    },
    'breakout': {
        'label': 'TRUE_PATH_AVAILABLE',
        'backtest_path': 'TRUE',  # Phase 5C: Now TRUE
        'performance': 'Needs validation (sparse signals, strict criteria)',
        'routing': 'EXCLUDED_FROM_SLIM_MAP',
        'notes': 'True compression + structural breakout engine (Phase 5C)'
    },
    'trend': {
        'label': 'TRUE_PATH_AVAILABLE',
        'backtest_path': 'TRUE',  # Phase 5C: Now TRUE
        'performance': 'Needs validation (sparse signals in ranging markets)',
        'routing': 'EXCLUDED_FROM_SLIM_MAP',
        'notes': 'True EMA pullback trend engine (Phase 5C)'
    },
    'mean_reversion': {
        'label': 'TRUE_PATH_AVAILABLE',
        'backtest_path': 'TRUE',  # Phase 5C: Now TRUE
        'performance': 'Needs validation (sparse signals)',
        'routing': 'EXCLUDED_FROM_SLIM_MAP',
        'notes': 'True Bollinger Band + RSI mean reversion engine (Phase 5C)'
    },
    'liquidity_reversal': {
        'label': 'TRUE_PATH_AVAILABLE',
        'backtest_path': 'TRUE',  # Phase 5C: Now TRUE
        'performance': 'Needs validation (counter-trend, higher risk)',
        'routing': 'EXCLUDED_FROM_SLIM_MAP',
        'notes': 'True stop-hunt reversal engine (Phase 5C)'
    },
    'ai': {
        'label': 'PROXY_BACKTEST',
        'backtest_path': 'PROXY',
        'performance': 'AI-proxy (not true Claude analysis)',
        'routing': 'MANUAL_ONLY',
        'notes': 'Uses MTF analysis + AI thresholds for backtest'
    },
    'flow': {
        'label': 'VALIDATED',
        'backtest_path': 'TRUE',
        'performance': 'True historical Polygon flow replay',
        'routing': 'MANUAL_ONLY',
        'notes': 'Uses real options flow data from Polygon'
    }
}


def get_engine_status(engine_type: str) -> Dict[str, str]:
    """Get status information for an engine."""
    return ENGINE_STATUS.get(engine_type, {
        'label': 'UNKNOWN',
        'backtest_path': 'UNKNOWN',
        'performance': 'Unknown',
        'routing': 'UNKNOWN',
        'notes': 'Engine not found in status registry'
    })


def get_slim_map_eligible_engines() -> List[str]:
    """
    Get list of engines eligible for routing in slim map mode.

    Returns:
        List of engine names that can be used in slim map mode
    """
    engines = SLIM_MAP_ENGINES.copy()

    # Optionally include deterministic if not restricted
    if not DETERMINISTIC_RESTRICTED:
        engines.append('deterministic')

    return engines


def is_engine_slim_map_eligible(engine: str) -> bool:
    """Check if an engine is eligible for slim map routing."""
    return engine in get_slim_map_eligible_engines()


def filter_engines_for_slim_map(engines: List[str]) -> List[str]:
    """
    Filter a list of engines to only include slim map eligible ones.

    Maintains original ordering, just removes ineligible engines.
    """
    if not SLIM_MAP_ENABLED:
        return engines

    eligible = get_slim_map_eligible_engines()
    return [e for e in engines if e in eligible]


class RoutingMode(str, Enum):
    """Router operating modes."""
    MANUAL = "manual"  # User selects engine
    AUTO_BY_REGIME = "auto_by_regime"  # Router selects based on regime


class DecisionSource(str, Enum):
    """Source of routing decision."""
    MANUAL_OVERRIDE = "manual_override"  # User forced specific engine
    COMPARISON_RESULTS = "comparison_results"  # Based on backtest comparison data (statistically sufficient)
    LOW_CONFIDENCE_DATA = "low_confidence_data"  # Based on comparison data (insufficient samples)
    FALLBACK_RULE = "fallback_rule"  # Rule-based (no comparison data)
    DEFAULT = "default"  # No regime detected, using default


# Auto-eligible engines (fully-routed engines)
AUTO_ELIGIBLE_ENGINES = [
    'unified',
    'deterministic',
    'quick',
    # Phase 14: 4 Core Strategy Engines
    'breakout',
    'trend',
    'mean_reversion',
    'liquidity_reversal'
]

# Manual-only engines (fallback-backed, not auto-preferred)
MANUAL_ONLY_ENGINES = ['ai', 'flow']

# All available engines
ALL_ENGINES = AUTO_ELIGIBLE_ENGINES + MANUAL_ONLY_ENGINES

# Phase 4.5: Statistical confidence thresholds
MINIMUM_REGIME_SAMPLES = 20  # Minimum comparisons needed for statistical confidence
CONFIDENCE_DENOMINATOR = 50  # Sample size for 100% confidence


@dataclass
class EngineRanking:
    """Ranking of engines for a specific regime."""
    regime: str
    ranked_engines: List[str]  # Ordered by preference (best first)
    source: DecisionSource
    confidence: float  # 0-1, how confident we are in this ranking
    notes: str = ""

    # Phase 4.5: Statistical metadata
    sample_size: int = 0  # Number of comparisons used for this ranking

    # If source is comparison_results, include metrics
    comparison_metrics: Optional[Dict[str, Any]] = None


@dataclass
class RouterDecision:
    """A routing decision with full traceability."""
    # Core decision
    routing_mode: RoutingMode
    current_regime: str
    selected_engine: str

    # Rankings
    eligible_engines: List[str]  # Which engines could be chosen
    ranking: List[str]  # Ordered preference for this regime

    # Traceability
    decision_source: DecisionSource
    decision_reason: str
    fallback_used: bool  # True if using rule instead of data

    # Phase 8A: Strategy-level selection (with defaults after non-default fields)
    selected_strategy_id: str = ""  # Specific strategy chosen (e.g., "deterministic_v1.7")
    strategy_status: str = ""  # Status of selected strategy (built_in, approved_for_router, active)
    parent_strategy: Optional[str] = None  # Parent strategy if variant, None if built-in

    # Phase 4.5: Statistical confidence
    sample_size: int = 0  # Number of comparisons used for this decision
    statistical_confidence: float = 0.0  # 0-1 based on sample size

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    manual_override: Optional[str] = None  # If user forced a choice

    # Optional: regime confidence
    regime_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for API responses."""
        result = asdict(self)
        result['routing_mode'] = self.routing_mode.value
        result['decision_source'] = self.decision_source.value
        result['timestamp'] = self.timestamp.isoformat()
        return result


class SmartFlowEngineRouter:
    """
    Adaptive engine router - Phase 3.

    Selects the best engine for current market conditions using:
    1. Comparison results by regime (when available)
    2. Current regime detection
    3. Transparent fallback rules

    Only auto-prefers fully-routed engines (unified, deterministic, quick).
    AI and Flow remain manual-only until truly routed.
    """

    def __init__(self, db: Optional[Session] = None):
        self.routing_mode = RoutingMode.MANUAL
        self.manual_override_engine: Optional[str] = None

        # Phase 8A: Database session for strategy registry queries
        self._db = db

        # Comparison results cache (regime → engine rankings)
        # This would be populated from actual backtest comparison data
        self._comparison_rankings: Dict[str, EngineRanking] = {}

        # Fallback routing rules (used when no comparison data)
        self._fallback_rules = self._initialize_fallback_rules()

        # Phase 4: Load comparison data from store
        self._load_comparison_rankings_from_store()

        # Log initialization with slim map status
        if SLIM_MAP_ENABLED:
            slim_engines = get_slim_map_eligible_engines()
            logger.info(
                f"SmartFlowEngineRouter initialized: mode={self.routing_mode.value} "
                f"[SLIM MAP ACTIVE - validated engines: {slim_engines}]"
            )
            logger.info(
                f"[SLIM MAP] Excluded from production: {SPECIALIZED_ENGINES_PENDING} "
                f"(pending true backtest implementation)"
            )
            if DETERMINISTIC_RESTRICTED:
                logger.info("[SLIM MAP] Deterministic engine: RESTRICTED (weak performance)")
        else:
            logger.info(f"SmartFlowEngineRouter initialized: mode={self.routing_mode.value}")

    def _initialize_fallback_rules(self) -> Dict[str, EngineRanking]:
        """
        Initialize rule-based fallback routing.

        These are transparent defaults used when we don't have
        comparison data for a regime.

        Phase 14: Updated with 4 new strategy engines.
        """
        return {
            'ranging': EngineRanking(
                regime='ranging',
                ranked_engines=['mean_reversion', 'liquidity_reversal', 'deterministic', 'unified'],
                source=DecisionSource.FALLBACK_RULE,
                confidence=0.7,
                notes='Ranging: Mean reversion preferred for range-bound markets, liquidity reversal for false breakouts'
            ),
            'mean_reverting': EngineRanking(
                regime='mean_reverting',
                ranked_engines=['mean_reversion', 'deterministic', 'unified'],
                source=DecisionSource.FALLBACK_RULE,
                confidence=0.75,
                notes='Mean-reverting: Mean reversion engine optimal for extremes returning to fair value'
            ),
            'trending_up': EngineRanking(
                regime='trending_up',
                ranked_engines=['trend', 'quick', 'unified'],
                source=DecisionSource.FALLBACK_RULE,
                confidence=0.75,
                notes='Trending up: Trend engine preferred for pullback entries in sustained uptrends'
            ),
            'trending_down': EngineRanking(
                regime='trending_down',
                ranked_engines=['trend', 'quick', 'unified'],
                source=DecisionSource.FALLBACK_RULE,
                confidence=0.75,
                notes='Trending down: Trend engine preferred for pullback entries in sustained downtrends'
            ),
            'vol_expansion': EngineRanking(
                regime='vol_expansion',
                ranked_engines=['breakout', 'quick', 'unified'],
                source=DecisionSource.FALLBACK_RULE,
                confidence=0.8,
                notes='Volatility expansion: Breakout engine optimal for compression → expansion moves'
            ),
            'vol_contraction': EngineRanking(
                regime='vol_contraction',
                ranked_engines=['breakout', 'deterministic', 'unified'],
                source=DecisionSource.FALLBACK_RULE,
                confidence=0.7,
                notes='Volatility contraction: Breakout engine preparing for compression breakout'
            ),
            'chaotic': EngineRanking(
                regime='chaotic',
                ranked_engines=['liquidity_reversal', 'unified', 'deterministic'],
                source=DecisionSource.FALLBACK_RULE,
                confidence=0.6,
                notes='Chaotic: Liquidity reversal for stop hunts in choppy conditions, unified as fallback'
            ),
            'neutral': EngineRanking(
                regime='neutral',
                ranked_engines=['unified', 'trend', 'mean_reversion'],
                source=DecisionSource.FALLBACK_RULE,
                confidence=0.5,
                notes='Neutral: Unified preferred as balanced default, trend and mean reversion as alternatives'
            ),
        }

    def set_routing_mode(self, mode: RoutingMode) -> None:
        """Set the router operating mode."""
        old_mode = self.routing_mode
        self.routing_mode = mode
        logger.info(f"Router mode changed: {old_mode.value} → {mode.value}")

    def set_manual_override(self, engine: Optional[str]) -> None:
        """
        Set manual engine override.

        Args:
            engine: Engine to force, or None to clear override
        """
        if engine and engine not in ALL_ENGINES:
            raise ValueError(f"Invalid engine: {engine}. Must be one of {ALL_ENGINES}")

        old_override = self.manual_override_engine
        self.manual_override_engine = engine

        if engine:
            logger.info(f"Manual override set: {engine}")
        else:
            logger.info(f"Manual override cleared (was: {old_override})")

    def get_engine_rankings_for_regime(
        self,
        regime: str,
        use_comparison_data: bool = True
    ) -> EngineRanking:
        """
        Get ranked engines for a specific regime.

        Priority:
        1. Comparison results (if available and use_comparison_data=True)
        2. Fallback rules

        Args:
            regime: Market regime name
            use_comparison_data: Whether to use comparison results

        Returns:
            EngineRanking with source clearly labeled
        """
        # Check comparison results first
        if use_comparison_data and regime in self._comparison_rankings:
            ranking = self._comparison_rankings[regime]
            logger.debug(f"Using comparison results for regime '{regime}'")
            return ranking

        # Fall back to rules
        if regime in self._fallback_rules:
            ranking = self._fallback_rules[regime]
            logger.debug(f"Using fallback rule for regime '{regime}'")
            return ranking

        # Default: neutral regime
        logger.warning(f"Unknown regime '{regime}', using neutral fallback")
        return self._fallback_rules['neutral']

    def _select_best_strategy_for_engine(
        self,
        engine_type: str
    ) -> Tuple[str, str, Optional[str]]:
        """
        Phase 8A: Select best strategy_id for a given engine type.

        Queries strategy registry for eligible strategies and selects
        the best one based on performance metrics.

        Args:
            engine_type: Engine type (unified, deterministic, quick, etc.)

        Returns:
            (strategy_id, strategy_status, parent_strategy)
        """
        # Fallback if no DB session
        if not self._db:
            # Default to built-in strategy
            strategy_id = f"{engine_type}_v1"
            logger.debug(f"No DB session - defaulting to built-in: {strategy_id}")
            return (strategy_id, "built_in", None)

        try:
            # Import here to avoid circular dependencies
            from app.services.strategy_registry import StrategyRegistry

            registry = StrategyRegistry(self._db)
            eligible_strategies = registry.get_router_eligible_strategies()

            # Filter by engine type
            type_strategies = [s for s in eligible_strategies if s.strategy_type == engine_type]

            if not type_strategies:
                # No eligible strategies for this type - use built-in
                strategy_id = f"{engine_type}_v1"
                logger.warning(f"No eligible strategies for type '{engine_type}' - defaulting to built-in: {strategy_id}")
                return (strategy_id, "built_in", None)

            # Select best by sharpe_ratio (or most recent if no sharpe)
            best_strategy = max(
                type_strategies,
                key=lambda s: (s.sharpe_ratio or 0.0, s.created_at or datetime.min)
            )

            logger.info(
                f"Selected strategy: {best_strategy.strategy_id} "
                f"(type={engine_type}, status={best_strategy.status}, "
                f"sharpe={best_strategy.sharpe_ratio or 0.0:.2f}, "
                f"is_variant={best_strategy.parent_strategy_id is not None})"
            )

            return (
                best_strategy.strategy_id,
                best_strategy.status,
                best_strategy.parent_strategy_id
            )

        except Exception as e:
            # Safety fallback on any error
            strategy_id = f"{engine_type}_v1"
            logger.error(f"Error selecting strategy for '{engine_type}': {e}. Falling back to {strategy_id}")
            return (strategy_id, "built_in", None)

    def select_best_engine_for_regime(
        self,
        regime: str,
        regime_confidence: float = 0.0
    ) -> Tuple[str, EngineRanking]:
        """
        Select the best engine for a given regime.

        Args:
            regime: Current market regime
            regime_confidence: Confidence in regime detection (0-1)

        Returns:
            (selected_engine, ranking_info)
        """
        ranking = self.get_engine_rankings_for_regime(regime)

        # Get ranked engines, filtered through slim map if enabled
        available_engines = filter_engines_for_slim_map(ranking.ranked_engines)

        # Select top-ranked engine from available engines
        if available_engines:
            selected = available_engines[0]

            # Log if slim map filtered out higher-ranked engines
            if SLIM_MAP_ENABLED and ranking.ranked_engines and ranking.ranked_engines[0] != selected:
                original_top = ranking.ranked_engines[0]
                logger.info(
                    f"[SLIM MAP] Filtered '{original_top}' → '{selected}' for regime '{regime}' "
                    f"('{original_top}' not in validated engines)"
                )
        else:
            # Safeguard: default to unified (always in slim map)
            selected = 'unified'
            if SLIM_MAP_ENABLED:
                logger.warning(
                    f"[SLIM MAP] No validated engines in ranking for regime '{regime}', "
                    f"defaulting to unified"
                )
            else:
                logger.warning(f"No ranking available for regime '{regime}', defaulting to unified")

        return selected, ranking

    def route_signal_request(
        self,
        regime: str,
        regime_confidence: float = 0.0
    ) -> RouterDecision:
        """
        Make a routing decision for a signal request.

        This is the main entry point for signal routing.

        Args:
            regime: Current market regime
            regime_confidence: Confidence in regime detection (0-1)

        Returns:
            RouterDecision with full traceability
        """
        # Check for manual override first
        if self.manual_override_engine:
            # Phase 8A: Select best strategy for overridden engine
            strategy_id, strategy_status, parent_strategy = self._select_best_strategy_for_engine(
                self.manual_override_engine
            )

            return RouterDecision(
                routing_mode=RoutingMode.MANUAL,
                current_regime=regime,
                selected_engine=self.manual_override_engine,
                selected_strategy_id=strategy_id,
                strategy_status=strategy_status,
                parent_strategy=parent_strategy,
                eligible_engines=ALL_ENGINES,
                ranking=[self.manual_override_engine],
                decision_source=DecisionSource.MANUAL_OVERRIDE,
                decision_reason=f"Manual override to {self.manual_override_engine}",
                fallback_used=False,
                manual_override=self.manual_override_engine,
                regime_confidence=regime_confidence
            )

        # Manual mode: no auto-selection (would need user to specify)
        if self.routing_mode == RoutingMode.MANUAL:
            # In manual mode, default to unified if no override
            # Phase 8A: Select best strategy for unified
            strategy_id, strategy_status, parent_strategy = self._select_best_strategy_for_engine('unified')

            return RouterDecision(
                routing_mode=RoutingMode.MANUAL,
                current_regime=regime,
                selected_engine='unified',
                selected_strategy_id=strategy_id,
                strategy_status=strategy_status,
                parent_strategy=parent_strategy,
                eligible_engines=ALL_ENGINES,
                ranking=['unified'],
                decision_source=DecisionSource.DEFAULT,
                decision_reason="Manual mode with no override - using unified default",
                fallback_used=False,
                regime_confidence=regime_confidence
            )

        # Auto mode: select based on regime
        selected_engine, ranking = self.select_best_engine_for_regime(regime, regime_confidence)

        # Phase 8A: Select best strategy for selected engine
        strategy_id, strategy_status, parent_strategy = self._select_best_strategy_for_engine(
            selected_engine
        )

        # Determine eligible engines based on slim map mode
        if SLIM_MAP_ENABLED:
            current_eligible = get_slim_map_eligible_engines()
        else:
            current_eligible = AUTO_ELIGIBLE_ENGINES

        # Filter ranking to show only available engines
        filtered_ranking = filter_engines_for_slim_map(ranking.ranked_engines)

        # Phase 4.5: Include statistical confidence
        decision = RouterDecision(
            routing_mode=self.routing_mode,
            current_regime=regime,
            selected_engine=selected_engine,
            selected_strategy_id=strategy_id,
            strategy_status=strategy_status,
            parent_strategy=parent_strategy,
            eligible_engines=current_eligible,
            ranking=filtered_ranking,  # Use filtered ranking
            decision_source=ranking.source,
            decision_reason=ranking.notes,
            fallback_used=(ranking.source == DecisionSource.FALLBACK_RULE),
            sample_size=ranking.sample_size,  # Phase 4.5
            statistical_confidence=ranking.confidence,  # Phase 4.5
            regime_confidence=regime_confidence
        )

        # Include slim map status in log
        slim_map_tag = "[SLIM MAP] " if SLIM_MAP_ENABLED else ""
        logger.info(
            f"{slim_map_tag}Router decision: {regime} → {selected_engine} / {strategy_id} "
            f"(source: {ranking.source.value}, samples: {ranking.sample_size}, "
            f"confidence: {ranking.confidence:.2f}, mode: {self.routing_mode.value}, "
            f"status: {strategy_status})"
        )

        return decision

    def explain_engine_selection(self, decision: RouterDecision) -> str:
        """
        Generate human-readable explanation of routing decision.

        Args:
            decision: RouterDecision to explain

        Returns:
            Explanation string
        """
        if decision.manual_override:
            return f"Manual override: Using {decision.selected_engine} (user-selected)"

        if decision.routing_mode == RoutingMode.MANUAL:
            return f"Manual mode: Using {decision.selected_engine} (default)"

        # Auto mode explanation
        source_label = {
            DecisionSource.COMPARISON_RESULTS: "based on statistically sufficient backtest data",
            DecisionSource.LOW_CONFIDENCE_DATA: "based on limited backtest data (low confidence)",
            DecisionSource.FALLBACK_RULE: "based on regime-based routing rules",
            DecisionSource.DEFAULT: "using default"
        }.get(decision.decision_source, "unknown source")

        # Phase 4.5: Include confidence in explanation
        confidence_note = ""
        if decision.statistical_confidence > 0:
            confidence_note = f" [Confidence: {decision.statistical_confidence*100:.0f}%, {decision.sample_size} samples]"

        return (
            f"Auto-selected {decision.selected_engine} for '{decision.current_regime}' regime "
            f"({source_label}){confidence_note}. {decision.decision_reason}"
        )

    def get_router_status(self) -> Dict[str, Any]:
        """
        Get current router status.

        Phase 4.5: Now includes statistical confidence information.

        Returns:
            Status dictionary with routing configuration
        """
        # Phase 4.5: Categorize regimes by data confidence
        high_confidence_regimes = []
        low_confidence_regimes = []
        fallback_only_regimes = []

        for regime, ranking in self._comparison_rankings.items():
            if ranking.source == DecisionSource.COMPARISON_RESULTS:
                high_confidence_regimes.append(regime)
            elif ranking.source == DecisionSource.LOW_CONFIDENCE_DATA:
                low_confidence_regimes.append(regime)

        # Regimes with only fallback rules (no comparison data)
        all_regimes = set(self._fallback_rules.keys())
        regimes_with_data = set(self._comparison_rankings.keys())
        fallback_only_regimes = list(all_regimes - regimes_with_data)

        return {
            'routing_mode': self.routing_mode.value,
            'manual_override_engine': self.manual_override_engine,
            'auto_eligible_engines': AUTO_ELIGIBLE_ENGINES,
            'manual_only_engines': MANUAL_ONLY_ENGINES,
            'all_engines': ALL_ENGINES,
            # Slim Map Configuration
            'slim_map_enabled': SLIM_MAP_ENABLED,
            'slim_map_engines': get_slim_map_eligible_engines() if SLIM_MAP_ENABLED else [],
            'specialized_engines_true_paths': SPECIALIZED_ENGINES_TRUE_PATHS,
            'specialized_engines_pending': SPECIALIZED_ENGINES_PENDING,  # Legacy (now empty)
            'deterministic_restricted': DETERMINISTIC_RESTRICTED,
            # Phase 5C: Engine status labels
            'engine_status': {engine: get_engine_status(engine) for engine in ALL_ENGINES},
            # Phase 4.5: Statistical confidence fields
            'confidence_threshold': MINIMUM_REGIME_SAMPLES,
            'high_confidence_regimes': high_confidence_regimes,  # >= threshold
            'low_confidence_regimes': low_confidence_regimes,  # < threshold
            'fallback_only_regimes': fallback_only_regimes,  # no data
            # Legacy fields
            'comparison_rankings_available': list(self._comparison_rankings.keys()),
            'fallback_rules_available': list(self._fallback_rules.keys()),
            'timestamp': datetime.now().isoformat()
        }

    def get_regime_mapping(self) -> Dict[str, Any]:
        """
        Get regime-to-engine mapping.

        Shows which engine is preferred for each regime,
        and whether that preference comes from data or rules.

        Phase 4.5: Now includes sample_size and statistical confidence.

        Returns:
            Mapping dictionary
        """
        mapping = {}

        # Get all known regimes (from fallback rules)
        all_regimes = set(self._fallback_rules.keys())
        all_regimes.update(self._comparison_rankings.keys())

        for regime in sorted(all_regimes):
            ranking = self.get_engine_rankings_for_regime(regime)

            mapping[regime] = {
                'preferred_engine': ranking.ranked_engines[0] if ranking.ranked_engines else 'unified',
                'ranking': ranking.ranked_engines,
                'source': ranking.source.value,
                'confidence': ranking.confidence,
                'sample_size': ranking.sample_size,  # Phase 4.5
                'notes': ranking.notes,
                # Phase 4.5: is_data_backed true for both high and low confidence data
                'is_data_backed': ranking.source in [DecisionSource.COMPARISON_RESULTS, DecisionSource.LOW_CONFIDENCE_DATA]
            }

        return mapping

    def _load_comparison_rankings_from_store(self) -> None:
        """
        Load comparison rankings from persistent store (Phase 4).

        This populates _comparison_rankings with actual backtest data,
        allowing data-driven routing decisions.
        """
        try:
            from app.services.backtesting.comparison_store import get_comparison_store

            store = get_comparison_store()
            regime_rankings = store.get_all_regime_rankings()

            loaded_count = 0
            for regime, data in regime_rankings.items():
                ranking = self._convert_store_data_to_ranking(regime, data)
                if ranking:
                    self._comparison_rankings[regime] = ranking
                    loaded_count += 1

            if loaded_count > 0:
                logger.info(f"Loaded comparison data for {loaded_count} regimes from store")
            else:
                logger.info("No comparison data available - using fallback rules only")

        except Exception as e:
            logger.warning(f"Failed to load comparison rankings: {e}")
            logger.info("Router will use fallback rules only")

    def _convert_store_data_to_ranking(
        self,
        regime: str,
        store_data: Dict[str, Any]
    ) -> Optional[EngineRanking]:
        """
        Convert comparison store data to EngineRanking.

        Phase 4.5: Now evaluates statistical confidence based on sample size.

        Args:
            regime: Market regime name
            store_data: Data from comparison store

        Returns:
            EngineRanking or None if data is invalid
        """
        ranked_engines = store_data.get('ranked_engines', [])
        engine_stats = store_data.get('engine_stats', {})  # Phase 4.5: aggregated stats
        sample_count = store_data.get('sample_count', 0)
        last_updated = store_data.get('last_updated')

        if not ranked_engines:
            return None

        # Filter to only auto-eligible engines
        ranked_engines = [e for e in ranked_engines if e in AUTO_ELIGIBLE_ENGINES]

        if not ranked_engines:
            logger.warning(f"No auto-eligible engines in ranking for '{regime}'")
            return None

        # Phase 4.5: Calculate statistical confidence
        statistical_confidence = min(1.0, sample_count / CONFIDENCE_DENOMINATOR)

        # Phase 4.5: Determine decision source based on sample size
        if sample_count >= MINIMUM_REGIME_SAMPLES:
            source = DecisionSource.COMPARISON_RESULTS
            source_label = "statistically sufficient data"
        elif sample_count > 0:
            source = DecisionSource.LOW_CONFIDENCE_DATA
            source_label = "insufficient samples for confidence"
        else:
            # Shouldn't happen (we have ranked_engines but no samples)
            return None

        # Build notes from aggregated statistics
        if ranked_engines and engine_stats:
            top_engine = ranked_engines[0]
            top_stats = engine_stats.get(top_engine, {})
            avg_win_rate = top_stats.get('avg_win_rate', 0) * 100
            avg_pnl = top_stats.get('avg_pnl', 0)
            engine_samples = top_stats.get('samples', sample_count)

            notes = (
                f"Based on {sample_count} comparison(s) - {source_label}: "
                f"{top_engine} leads (avg WR: {avg_win_rate:.1f}%, avg P&L: ${avg_pnl:.2f}, "
                f"{engine_samples} samples). "
                f"Confidence: {statistical_confidence*100:.0f}%. "
                f"Last updated: {last_updated or 'unknown'}"
            )
        else:
            notes = f"Based on {sample_count} comparison(s) - {source_label}"

        return EngineRanking(
            regime=regime,
            ranked_engines=ranked_engines,
            source=source,  # Phase 4.5: comparison_results or low_confidence_data
            confidence=statistical_confidence,  # Phase 4.5: 0-1 based on sample size
            notes=notes,
            sample_size=sample_count,  # Phase 4.5: track sample size
            comparison_metrics=engine_stats  # Phase 4.5: use aggregated stats
        )

    def refresh_comparison_rankings(self) -> int:
        """
        Refresh comparison rankings from store.

        This should be called after new comparisons are run to update
        the router with latest data.

        Returns:
            Number of regimes updated with comparison data
        """
        logger.info("Refreshing comparison rankings from store...")
        old_count = len(self._comparison_rankings)

        self._comparison_rankings.clear()
        self._load_comparison_rankings_from_store()

        new_count = len(self._comparison_rankings)
        logger.info(f"Refresh complete: {new_count} regimes now have comparison data")

        return new_count

    def update_comparison_rankings(
        self,
        comparison_results: Dict[str, Any]
    ) -> None:
        """
        Update router with new comparison results (deprecated).

        This method is deprecated in favor of automatic loading from
        the comparison store. The store is automatically updated when
        comparisons complete, and the router loads from it.

        Use refresh_comparison_rankings() instead to reload from store.

        Args:
            comparison_results: Results from engine comparison (unused)
        """
        logger.warning(
            "update_comparison_rankings() is deprecated. "
            "Use refresh_comparison_rankings() instead."
        )
        self.refresh_comparison_rankings()


# Global instance
_router_instance: Optional[SmartFlowEngineRouter] = None


def get_router(db: Optional[Session] = None) -> SmartFlowEngineRouter:
    """
    Get or create global router instance.

    Phase 8A: Accepts optional db session for strategy registry queries.
    """
    global _router_instance
    if _router_instance is None:
        _router_instance = SmartFlowEngineRouter(db)
    elif db and not _router_instance._db:
        # Update db if router exists but has no db session
        _router_instance._db = db
    return _router_instance
