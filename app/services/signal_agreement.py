"""
Signal Agreement Layer - Phase: Quick Anchor + Regime Adaptive Enhancer
========================================================================

Combines quick engine as PRIMARY anchor with regime_adaptive as SECONDARY confirmer.

Design Principles:
- quick remains the trusted base (validated Sharpe 7.30, 73.5% win rate)
- regime_adaptive acts as confirmation/enhancement layer
- Agreement layer influences confidence, sizing, and veto decisions
- Never blindly replace quick with unproven strategies

Agreement Modes:
- advisory: regime_adaptive only adds metadata/score adjustment, never blocks
- conservative: can reduce size or block clearly contradictory signals (DEFAULT)
- strict: quick executes only when regime_adaptive agrees or is neutral
"""

import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Any, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

SIGNAL_AGREEMENT_ENABLED = os.getenv('SMARTFLOW_SIGNAL_AGREEMENT_ENABLED', 'true').lower() == 'true'
SIGNAL_AGREEMENT_MODE = os.getenv('SMARTFLOW_SIGNAL_AGREEMENT_MODE', 'conservative')

# Agreement thresholds
AGREEMENT_BOOST_MAX = float(os.getenv('SMARTFLOW_SIGNAL_AGREEMENT_MAX_BOOST', '0.15'))
AGREEMENT_PENALTY_MAX = float(os.getenv('SMARTFLOW_SIGNAL_AGREEMENT_MAX_PENALTY', '0.20'))
CONTRADICTION_SIZE_REDUCTION = float(os.getenv('SMARTFLOW_CONTRADICTION_SIZE_REDUCTION', '0.60'))
HIGH_CONFIDENCE_THRESHOLD = float(os.getenv('SMARTFLOW_HIGH_CONFIDENCE_THRESHOLD', '0.70'))
VETO_CONFIDENCE_THRESHOLD = float(os.getenv('SMARTFLOW_VETO_CONFIDENCE_THRESHOLD', '0.80'))


class AgreementMode(Enum):
    """Agreement layer operating modes."""
    ADVISORY = "advisory"           # Never blocks, only metadata
    CONSERVATIVE = "conservative"   # Can reduce size or block contradictions
    STRICT = "strict"               # Executes only on agreement


class AgreementState(Enum):
    """Possible agreement states between quick and regime_adaptive."""
    FULL_AGREEMENT = "full_agreement"
    PARTIAL_AGREEMENT = "partial_agreement"
    NEUTRAL_REGIME = "neutral_regime"
    CONTRADICTION = "contradiction"
    REGIME_VETO = "regime_veto"
    INSUFFICIENT_DATA = "insufficient_data"


class FinalDecision(Enum):
    """Final decision outcomes."""
    EXECUTE = "execute"
    REDUCE = "reduce"
    SKIP = "skip"
    BOOST = "boost"


@dataclass
class AnchorSignal:
    """Signal from the anchor (quick) engine."""
    engine: str = "quick"
    direction: Optional[str] = None  # 'long', 'short', or None
    confidence: float = 0.0
    entry_price: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegimeSignal:
    """Signal/decision from regime_adaptive layer."""
    strategy: Optional[str] = None  # e.g., 'trend_v1', 'mean_reversion_v1'
    engine: Optional[str] = None    # e.g., 'trend', 'mean_reversion'
    direction: Optional[str] = None
    confidence: float = 0.0
    regime: str = "neutral"
    regime_confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgreementResult:
    """Complete result from the signal agreement layer."""
    # Anchor (quick) details
    anchor_engine: str = "quick"
    anchor_direction: Optional[str] = None
    anchor_confidence: float = 0.0

    # Regime details
    regime_strategy: Optional[str] = None
    regime_engine: Optional[str] = None
    regime_direction: Optional[str] = None
    regime_confidence: float = 0.0
    current_regime: str = "neutral"

    # Agreement decision
    agreement_state: AgreementState = AgreementState.INSUFFICIENT_DATA
    agreement_score: float = 0.0
    final_decision: FinalDecision = FinalDecision.SKIP

    # Adjustments
    size_multiplier: float = 1.0
    confidence_adjustment: float = 0.0
    final_confidence: float = 0.0

    # Explanation
    reason: str = ""
    agreement_mode: str = "conservative"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "anchor_engine": self.anchor_engine,
            "anchor_direction": self.anchor_direction,
            "anchor_confidence": self.anchor_confidence,
            "regime_strategy": self.regime_strategy,
            "regime_engine": self.regime_engine,
            "regime_direction": self.regime_direction,
            "regime_confidence": self.regime_confidence,
            "current_regime": self.current_regime,
            "agreement_state": self.agreement_state.value,
            "agreement_score": round(self.agreement_score, 4),
            "final_decision": self.final_decision.value,
            "size_multiplier": round(self.size_multiplier, 3),
            "confidence_adjustment": round(self.confidence_adjustment, 4),
            "final_confidence": round(self.final_confidence, 4),
            "reason": self.reason,
            "agreement_mode": self.agreement_mode,
        }


class SignalAgreementLayer:
    """
    Signal Agreement Layer that combines quick (anchor) with regime_adaptive (enhancer).

    Usage:
        agreement = SignalAgreementLayer(mode='conservative')
        result = agreement.evaluate(anchor_signal, regime_signal)

        if result.final_decision == FinalDecision.EXECUTE:
            # Execute with result.size_multiplier and result.final_confidence
            ...
    """

    def __init__(self, mode: str = None):
        """
        Initialize the agreement layer.

        Args:
            mode: Operating mode ('advisory', 'conservative', 'strict')
        """
        self.mode = AgreementMode(mode or SIGNAL_AGREEMENT_MODE)
        self.enabled = SIGNAL_AGREEMENT_ENABLED

        # Thresholds
        self.boost_max = AGREEMENT_BOOST_MAX
        self.penalty_max = AGREEMENT_PENALTY_MAX
        self.contradiction_size = CONTRADICTION_SIZE_REDUCTION
        self.high_conf_threshold = HIGH_CONFIDENCE_THRESHOLD
        self.veto_conf_threshold = VETO_CONFIDENCE_THRESHOLD

        logger.info(f"SignalAgreementLayer initialized: mode={self.mode.value}, enabled={self.enabled}")

    def evaluate(
        self,
        anchor: AnchorSignal,
        regime: RegimeSignal
    ) -> AgreementResult:
        """
        Evaluate agreement between anchor (quick) and regime_adaptive signals.

        Args:
            anchor: Signal from quick engine
            regime: Signal from regime_adaptive

        Returns:
            AgreementResult with final decision and adjustments
        """
        result = AgreementResult(
            anchor_engine=anchor.engine,
            anchor_direction=anchor.direction,
            anchor_confidence=anchor.confidence,
            regime_strategy=regime.strategy,
            regime_engine=regime.engine,
            regime_direction=regime.direction,
            regime_confidence=regime.confidence,
            current_regime=regime.regime,
            agreement_mode=self.mode.value,
        )

        # If anchor has no signal, nothing to agree on
        if not anchor.direction:
            result.agreement_state = AgreementState.INSUFFICIENT_DATA
            result.final_decision = FinalDecision.SKIP
            result.reason = "No anchor signal to evaluate"
            return result

        # Determine agreement state
        agreement_state = self._determine_agreement_state(anchor, regime)
        result.agreement_state = agreement_state

        # Compute agreement score (0-1, higher = more agreement)
        result.agreement_score = self._compute_agreement_score(anchor, regime, agreement_state)

        # Decide final action based on mode and state
        final_decision, size_mult, conf_adj, reason = self._decide_final_action(
            anchor, regime, agreement_state, result.agreement_score
        )

        result.final_decision = final_decision
        result.size_multiplier = size_mult
        result.confidence_adjustment = conf_adj
        result.final_confidence = min(1.0, max(0.0, anchor.confidence + conf_adj))
        result.reason = reason

        # Log the agreement decision
        self._log_agreement(result)

        return result

    def _determine_agreement_state(
        self,
        anchor: AnchorSignal,
        regime: RegimeSignal
    ) -> AgreementState:
        """Determine the agreement state between anchor and regime signals."""

        # If regime has no direction signal
        if not regime.direction:
            return AgreementState.NEUTRAL_REGIME

        # Check if directions agree
        directions_agree = anchor.direction == regime.direction

        if directions_agree:
            # Both have same direction
            if regime.confidence >= self.high_conf_threshold:
                return AgreementState.FULL_AGREEMENT
            else:
                return AgreementState.PARTIAL_AGREEMENT
        else:
            # Directions differ (contradiction)
            if regime.confidence >= self.veto_conf_threshold:
                return AgreementState.REGIME_VETO
            elif regime.confidence >= self.high_conf_threshold:
                return AgreementState.CONTRADICTION
            else:
                # Low confidence contradiction - treat as partial agreement with anchor
                return AgreementState.PARTIAL_AGREEMENT

    def _compute_agreement_score(
        self,
        anchor: AnchorSignal,
        regime: RegimeSignal,
        state: AgreementState
    ) -> float:
        """
        Compute agreement score between 0 and 1.
        Higher scores indicate stronger agreement.
        """
        if state == AgreementState.FULL_AGREEMENT:
            # High agreement - combine confidences
            return 0.8 + 0.2 * min(anchor.confidence, regime.confidence)

        elif state == AgreementState.PARTIAL_AGREEMENT:
            # Moderate agreement
            return 0.5 + 0.3 * anchor.confidence

        elif state == AgreementState.NEUTRAL_REGIME:
            # Neutral - anchor confidence drives score
            return 0.4 + 0.4 * anchor.confidence

        elif state == AgreementState.CONTRADICTION:
            # Low agreement
            return 0.3 - 0.2 * regime.confidence

        elif state == AgreementState.REGIME_VETO:
            # Very low agreement
            return 0.1 - 0.1 * regime.confidence

        else:  # INSUFFICIENT_DATA
            return 0.0

    def _decide_final_action(
        self,
        anchor: AnchorSignal,
        regime: RegimeSignal,
        state: AgreementState,
        score: float
    ) -> Tuple[FinalDecision, float, float, str]:
        """
        Decide final action based on agreement state and mode.

        Returns:
            (final_decision, size_multiplier, confidence_adjustment, reason)
        """
        # Default values
        size_mult = 1.0
        conf_adj = 0.0

        # ===== ADVISORY MODE =====
        # Never blocks, only provides metadata
        if self.mode == AgreementMode.ADVISORY:
            if state == AgreementState.FULL_AGREEMENT:
                conf_adj = min(self.boost_max, 0.08 + 0.04 * regime.confidence)
                return (FinalDecision.BOOST, 1.15, conf_adj,
                        f"Advisory: full agreement ({anchor.direction}) with {regime.strategy}")
            elif state in [AgreementState.PARTIAL_AGREEMENT, AgreementState.NEUTRAL_REGIME]:
                return (FinalDecision.EXECUTE, 1.0, 0.0,
                        f"Advisory: proceeding with anchor ({anchor.direction})")
            else:
                # Even contradictions execute in advisory mode
                return (FinalDecision.EXECUTE, 1.0, 0.0,
                        f"Advisory: proceeding despite {state.value}")

        # ===== CONSERVATIVE MODE (DEFAULT) =====
        elif self.mode == AgreementMode.CONSERVATIVE:
            if state == AgreementState.FULL_AGREEMENT:
                # Boost confidence and size
                conf_adj = min(self.boost_max, 0.08 + 0.04 * regime.confidence)
                size_mult = min(1.25, 1.0 + 0.15 * regime.confidence)
                return (FinalDecision.BOOST, size_mult, conf_adj,
                        f"Full agreement: {anchor.direction} aligns with {regime.strategy}")

            elif state == AgreementState.PARTIAL_AGREEMENT:
                # Slight boost
                conf_adj = 0.04
                return (FinalDecision.EXECUTE, 1.05, conf_adj,
                        f"Partial agreement: {anchor.direction} with moderate regime support")

            elif state == AgreementState.NEUTRAL_REGIME:
                # Execute normally
                return (FinalDecision.EXECUTE, 1.0, 0.0,
                        f"Neutral regime: proceeding with anchor {anchor.direction}")

            elif state == AgreementState.CONTRADICTION:
                # Reduce size
                conf_adj = -min(self.penalty_max, 0.05 + 0.05 * regime.confidence)
                return (FinalDecision.REDUCE, self.contradiction_size, conf_adj,
                        f"Contradiction: {anchor.direction} vs regime {regime.direction}, reducing size")

            elif state == AgreementState.REGIME_VETO:
                # High confidence contradiction - skip
                return (FinalDecision.SKIP, 0.0, -self.penalty_max,
                        f"Regime veto: {regime.strategy} strongly favors {regime.direction} (conf={regime.confidence:.0%})")

            else:
                return (FinalDecision.SKIP, 0.0, 0.0, "Insufficient data")

        # ===== STRICT MODE =====
        else:  # STRICT
            if state == AgreementState.FULL_AGREEMENT:
                conf_adj = min(self.boost_max, 0.10 + 0.05 * regime.confidence)
                size_mult = min(1.30, 1.0 + 0.20 * regime.confidence)
                return (FinalDecision.BOOST, size_mult, conf_adj,
                        f"Strict: full agreement on {anchor.direction}")

            elif state == AgreementState.PARTIAL_AGREEMENT:
                return (FinalDecision.EXECUTE, 1.0, 0.0,
                        f"Strict: partial agreement allows execution")

            elif state == AgreementState.NEUTRAL_REGIME:
                # In strict mode, neutral regime allows execution
                return (FinalDecision.EXECUTE, 0.90, 0.0,
                        f"Strict: neutral regime, executing with reduced size")

            else:
                # Strict mode skips on any contradiction
                return (FinalDecision.SKIP, 0.0, -self.penalty_max,
                        f"Strict: regime disagreement prevents execution")

    def _log_agreement(self, result: AgreementResult) -> None:
        """Log the agreement decision."""
        state_str = result.agreement_state.value
        decision_str = result.final_decision.value

        # Build log line
        parts = [f"[AGREEMENT]"]
        parts.append(f"quick={result.anchor_direction or 'none'}")

        if result.regime_strategy:
            parts.append(f"regime={result.regime_strategy}({result.regime_direction or 'none'})")
        else:
            parts.append("regime=neutral")

        parts.append(f"state={state_str}")
        parts.append(f"final={decision_str}")

        if result.confidence_adjustment != 0:
            sign = '+' if result.confidence_adjustment > 0 else ''
            parts.append(f"boost={sign}{result.confidence_adjustment:.2f}")

        if result.size_multiplier != 1.0:
            parts.append(f"size={result.size_multiplier:.2f}x")

        log_line = " ".join(parts)

        if result.final_decision in [FinalDecision.SKIP, FinalDecision.REDUCE]:
            logger.warning(log_line)
        else:
            logger.info(log_line)

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the agreement layer."""
        return {
            "enabled": self.enabled,
            "mode": self.mode.value,
            "thresholds": {
                "boost_max": self.boost_max,
                "penalty_max": self.penalty_max,
                "contradiction_size": self.contradiction_size,
                "high_confidence": self.high_conf_threshold,
                "veto_confidence": self.veto_conf_threshold,
            }
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_default_agreement_layer: Optional[SignalAgreementLayer] = None


def get_signal_agreement_layer(mode: str = None) -> SignalAgreementLayer:
    """Get or create the default signal agreement layer instance."""
    global _default_agreement_layer

    if _default_agreement_layer is None:
        _default_agreement_layer = SignalAgreementLayer(mode=mode)

    return _default_agreement_layer


def evaluate_signal_agreement(
    anchor_direction: Optional[str],
    anchor_confidence: float,
    regime_strategy: Optional[str],
    regime_engine: Optional[str],
    regime_direction: Optional[str],
    regime_confidence: float,
    current_regime: str = "neutral",
    mode: str = None
) -> AgreementResult:
    """
    Convenience function to evaluate signal agreement.

    Args:
        anchor_direction: Direction from quick engine ('long', 'short', or None)
        anchor_confidence: Confidence of quick signal (0-1)
        regime_strategy: Strategy ID from regime_adaptive (e.g., 'trend_v1')
        regime_engine: Engine from regime_adaptive (e.g., 'trend')
        regime_direction: Direction from regime_adaptive
        regime_confidence: Confidence from regime_adaptive (0-1)
        current_regime: Current market regime
        mode: Operating mode override

    Returns:
        AgreementResult with final decision
    """
    layer = get_signal_agreement_layer(mode)

    anchor = AnchorSignal(
        engine="quick",
        direction=anchor_direction,
        confidence=anchor_confidence,
    )

    regime = RegimeSignal(
        strategy=regime_strategy,
        engine=regime_engine,
        direction=regime_direction,
        confidence=regime_confidence,
        regime=current_regime,
    )

    return layer.evaluate(anchor, regime)


def get_signal_agreement_status() -> Dict[str, Any]:
    """Get status of the signal agreement layer."""
    layer = get_signal_agreement_layer()
    return layer.get_status()
