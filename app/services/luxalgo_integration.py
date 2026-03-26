"""
LuxAlgo SmartFlow Integration
==============================
Processes incoming TradingView webhook alerts from 5 LuxAlgo indicators
and converts them into SmartFlow-compatible signals.

Supported LuxAlgo Indicators:
1. Smart Money Concepts (SMC)        - BOS/CHoCH structure breaks
2. Oscillator Matrix™                - Trend + reversal confluence
3. Evasive SuperTrend               - Clean directional flips
4. Price Action Concepts™ (PAC)     - Order block + CHoCH+ entries
5. Daily Polynomial Regressions     - R² trend strength + mean reversion

Webhook payload format from TradingView:
{
    "indicator": "smc" | "oscillator_matrix" | "evasive_supertrend" | "pac" | "poly_regression",
    "signal": "buy" | "sell" | "close",
    "symbol": "ES1!" | "NQ1!" | ...,
    "price": 5234.50,
    "timeframe": "5" | "15" | "60" | "D",
    "details": { ... indicator-specific data ... }
}
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class LuxAlgoIndicator(str, Enum):
    SMC = "smc"                          # Smart Money Concepts
    OSCILLATOR_MATRIX = "oscillator_matrix"  # Oscillator Matrix™
    EVASIVE_SUPERTREND = "evasive_supertrend"  # Evasive SuperTrend
    PAC = "pac"                          # Price Action Concepts™
    POLY_REGRESSION = "poly_regression"  # Daily Polynomial Regressions


@dataclass
class LuxAlgoSignal:
    """Parsed signal from a LuxAlgo TradingView alert"""
    indicator: LuxAlgoIndicator
    action: str          # 'buy', 'sell', 'close'
    symbol: str
    price: float
    timeframe: str
    confidence: float    # 0.0 - 1.0
    details: Dict[str, Any]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class LuxAlgoSignalParser:
    """
    Parses incoming TradingView webhook payloads from LuxAlgo indicators
    and computes signal confidence for SmartFlow routing.
    """

    def parse(self, payload: Dict[str, Any]) -> Optional[LuxAlgoSignal]:
        """Parse a raw TradingView webhook payload into a LuxAlgoSignal."""
        try:
            indicator = LuxAlgoIndicator(payload.get("indicator", "").lower())
            action = payload.get("signal", "").lower()
            symbol = payload.get("symbol", "")
            price = float(payload.get("price", 0))
            timeframe = str(payload.get("timeframe", "5"))
            details = payload.get("details", {})

            if action not in ("buy", "sell", "close"):
                logger.warning(f"LuxAlgo: Unknown action '{action}' — ignoring")
                return None

            confidence = self._compute_confidence(indicator, action, details)

            return LuxAlgoSignal(
                indicator=indicator,
                action=action,
                symbol=symbol,
                price=price,
                timeframe=timeframe,
                confidence=confidence,
                details=details,
            )
        except Exception as e:
            logger.error(f"LuxAlgo parse error: {e} | payload: {payload}")
            return None

    def _compute_confidence(
        self, indicator: LuxAlgoIndicator, action: str, details: Dict
    ) -> float:
        """
        Compute confidence score (0.0–1.0) based on indicator-specific data.
        """
        if indicator == LuxAlgoIndicator.SMC:
            return self._smc_confidence(action, details)
        elif indicator == LuxAlgoIndicator.OSCILLATOR_MATRIX:
            return self._oscillator_matrix_confidence(action, details)
        elif indicator == LuxAlgoIndicator.EVASIVE_SUPERTREND:
            return self._evasive_supertrend_confidence(action, details)
        elif indicator == LuxAlgoIndicator.PAC:
            return self._pac_confidence(action, details)
        elif indicator == LuxAlgoIndicator.POLY_REGRESSION:
            return self._poly_regression_confidence(action, details)
        return 0.5

    def _smc_confidence(self, action: str, details: Dict) -> float:
        """
        SMC confidence:
        - CHoCH+ (confirmed reversal) = 0.90
        - CHoCH (standard) = 0.75
        - BOS (continuation) = 0.65
        - Order block retest = +0.10 bonus
        - FVG present = +0.05 bonus
        """
        base = 0.60
        signal_type = details.get("type", "").lower()

        if "choch+" in signal_type or "choch_plus" in signal_type:
            base = 0.90
        elif "choch" in signal_type:
            base = 0.75
        elif "bos" in signal_type:
            base = 0.65

        if details.get("order_block_retest"):
            base = min(1.0, base + 0.10)
        if details.get("fvg"):
            base = min(1.0, base + 0.05)

        return round(base, 2)

    def _oscillator_matrix_confidence(self, action: str, details: Dict) -> float:
        """
        Oscillator Matrix confidence:
        - Strong signal + not overbought/oversold = 0.85
        - Normal signal = 0.70
        - Confluence components: +0.03 per aligned component (max 6)
        """
        base = 0.70
        signal_strength = details.get("strength", "normal").lower()

        if signal_strength == "strong":
            base = 0.85
        elif signal_strength == "weak":
            base = 0.55

        # Each confluent component adds weight
        confluence = int(details.get("confluence_count", 0))
        base = min(1.0, base + (confluence * 0.03))

        # Penalty if overbought/oversold against signal direction
        if action == "buy" and details.get("overbought"):
            base = max(0.3, base - 0.20)
        if action == "sell" and details.get("oversold"):
            base = max(0.3, base - 0.20)

        return round(base, 2)

    def _evasive_supertrend_confidence(self, action: str, details: Dict) -> float:
        """
        Evasive SuperTrend confidence:
        - Clean flip (first bar after direction change) = 0.80
        - Continuation (price in trend, not flip) = 0.60
        - Evasion event (band pushed away = momentum) = +0.10 bonus
        """
        base = 0.60
        is_flip = details.get("flip", False)
        is_evasion = details.get("evasion_event", False)

        if is_flip:
            base = 0.80
        if is_evasion:
            base = min(1.0, base + 0.10)

        return round(base, 2)

    def _pac_confidence(self, action: str, details: Dict) -> float:
        """
        Price Action Concepts confidence:
        - CHoCH+ at order block = 0.92 (highest quality setup)
        - CHoCH at order block = 0.80
        - Liquidity grab + reversal = 0.78
        - Standard BOS = 0.65
        """
        base = 0.65
        signal_type = details.get("type", "").lower()
        at_order_block = details.get("order_block", False)
        liquidity_grab = details.get("liquidity_grab", False)

        if "choch+" in signal_type and at_order_block:
            base = 0.92
        elif "choch" in signal_type and at_order_block:
            base = 0.80
        elif liquidity_grab:
            base = 0.78
        elif "bos" in signal_type:
            base = 0.65

        return round(base, 2)

    def _poly_regression_confidence(self, action: str, details: Dict) -> float:
        """
        Polynomial Regression confidence:
        - High R² (>0.85) + trend signal = 0.82 (ride the trend)
        - Low R² (<0.40) + mean reversion = 0.75 (fade the extension)
        - Mid R² = 0.55 (uncertain)
        """
        r_squared = float(details.get("r_squared", 0.5))
        signal_type = details.get("type", "trend").lower()  # 'trend' or 'mean_reversion'

        if signal_type == "trend" and r_squared >= 0.85:
            return 0.82
        elif signal_type == "mean_reversion" and r_squared <= 0.40:
            return 0.75
        elif r_squared >= 0.70:
            return 0.65
        else:
            return 0.50


class LuxAlgoSmartFlowBridge:
    """
    Bridge between LuxAlgo webhook signals and SmartFlow signal pipeline.
    Filters by confidence threshold, deduplicates, and injects into SmartFlow.
    """

    MIN_CONFIDENCE = 0.65  # Only pass high-confidence signals to SmartFlow

    def __init__(self):
        self.parser = LuxAlgoSignalParser()
        self._recent_signals: Dict[str, datetime] = {}  # dedup tracker

    def process_webhook(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Entry point for TradingView webhook.
        Returns a SmartFlow-compatible signal dict, or None if filtered out.
        """
        signal = self.parser.parse(payload)
        if not signal:
            return None

        # Confidence gate
        if signal.confidence < self.MIN_CONFIDENCE:
            logger.info(
                f"LuxAlgo: {signal.indicator.value} signal filtered "
                f"(confidence {signal.confidence} < {self.MIN_CONFIDENCE})"
            )
            return None

        # Deduplication: ignore same indicator+symbol+action within 60s
        dedup_key = f"{signal.indicator.value}:{signal.symbol}:{signal.action}"
        last_seen = self._recent_signals.get(dedup_key)
        if last_seen:
            delta = (signal.timestamp - last_seen).total_seconds()
            if delta < 60:
                logger.debug(f"LuxAlgo: Deduped {dedup_key} ({delta:.0f}s ago)")
                return None
        self._recent_signals[dedup_key] = signal.timestamp

        # Convert to SmartFlow signal format
        return self._to_smartflow_signal(signal)

    def _to_smartflow_signal(self, signal: LuxAlgoSignal) -> Dict[str, Any]:
        """Convert LuxAlgoSignal → SmartFlow webhook payload format."""
        # Map LuxAlgo indicators to SmartFlow engine hints
        engine_hint_map = {
            LuxAlgoIndicator.SMC: "unified",           # Structure-based → unified
            LuxAlgoIndicator.OSCILLATOR_MATRIX: "unified",  # Confluence → unified
            LuxAlgoIndicator.EVASIVE_SUPERTREND: "quick",  # Momentum flip → quick
            LuxAlgoIndicator.PAC: "unified",           # Price action → unified
            LuxAlgoIndicator.POLY_REGRESSION: "mean_reversion",  # Regression → mean_reversion
        }

        return {
            "action": signal.action,
            "symbol": signal.symbol,
            "price": signal.price,
            "source": f"luxalgo_{signal.indicator.value}",
            "confidence": signal.confidence,
            "engine_hint": engine_hint_map.get(signal.indicator, "unified"),
            "timeframe": signal.timeframe,
            "metadata": {
                "indicator": signal.indicator.value,
                "details": signal.details,
                "timestamp": signal.timestamp.isoformat(),
            }
        }


# Singleton instance
_bridge: Optional[LuxAlgoSmartFlowBridge] = None

def get_luxalgo_bridge() -> LuxAlgoSmartFlowBridge:
    global _bridge
    if _bridge is None:
        _bridge = LuxAlgoSmartFlowBridge()
    return _bridge
