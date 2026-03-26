"""
Unified Flow Feature Engine
============================

Integrates Unusual Whales + FlowAlgo + Polygon into structured flow features.

This engine:
1. Ingests UW + FlowAlgo + Polygon flow inputs
2. Normalizes them into structured numeric flow features
3. Exposes a single feature bundle per ticker/symbol
4. Feeds features into ensemble scoring, allocator, and logging

Flow is used as:
- Context and directional bias
- Confidence modifier
- Strategy weighting enhancer

Flow is NOT:
- Sole entry trigger
- Override for other controls
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

import aiohttp

logger = logging.getLogger(__name__)


class FlowSentiment(str, Enum):
    """Flow sentiment classification."""
    STRONGLY_BULLISH = "strongly_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONGLY_BEARISH = "strongly_bearish"


@dataclass
class SourceAvailability:
    """Tracks which flow sources are available."""
    unusual_whales: bool = False
    flowalgo: bool = False
    polygon: bool = False

    def any_available(self) -> bool:
        return self.unusual_whales or self.flowalgo or self.polygon

    def count_available(self) -> int:
        return sum([self.unusual_whales, self.flowalgo, self.polygon])


@dataclass
class SourceWeights:
    """Weights for each flow source based on reliability and freshness."""
    unusual_whales: float = 0.45  # Most reliable premium data
    flowalgo: float = 0.30        # Good for sweeps/blocks
    polygon: float = 0.25         # Free tier delay

    def normalize(self, availability: SourceAvailability) -> 'SourceWeights':
        """Normalize weights based on available sources."""
        total = 0.0
        if availability.unusual_whales:
            total += self.unusual_whales
        if availability.flowalgo:
            total += self.flowalgo
        if availability.polygon:
            total += self.polygon

        if total == 0:
            return SourceWeights(0, 0, 0)

        return SourceWeights(
            unusual_whales=self.unusual_whales / total if availability.unusual_whales else 0,
            flowalgo=self.flowalgo / total if availability.flowalgo else 0,
            polygon=self.polygon / total if availability.polygon else 0
        )


@dataclass
class FlowFeatureBundle:
    """
    Unified flow feature bundle for a symbol.

    This is the primary output of the flow feature engine.
    """
    # Identity
    symbol: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Core sentiment
    flow_sentiment: str = "neutral"  # FlowSentiment value
    flow_score: float = 0.0          # -1.0 to +1.0, normalized
    flow_confidence: float = 0.5     # 0.0 to 1.0

    # Premium metrics
    net_premium_millions: float = 0.0
    call_premium_millions: float = 0.0
    put_premium_millions: float = 0.0

    # Ratios
    bull_bear_ratio: float = 1.0     # > 1 = bullish, < 1 = bearish
    call_put_imbalance: float = 0.0  # -1 to +1

    # Activity metrics
    whale_count: int = 0
    sweep_count: int = 0
    block_count: int = 0
    total_trades: int = 0

    # Source tracking
    source_weights: Dict[str, float] = field(default_factory=lambda: {
        "unusual_whales": 0.0,
        "flowalgo": 0.0,
        "polygon": 0.0
    })
    source_agreement: float = 0.0    # 0-1, how well sources agree
    source_availability: Dict[str, bool] = field(default_factory=lambda: {
        "unusual_whales": False,
        "flowalgo": False,
        "polygon": False
    })

    # Individual source scores (-1 to +1)
    uw_score: float = 0.0
    flowalgo_score: float = 0.0
    polygon_score: float = 0.0

    # Notes for traceability
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API/logging."""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

    @property
    def is_actionable(self) -> bool:
        """Check if flow data is strong enough to act on."""
        return (
            self.flow_confidence >= 0.6 and
            abs(self.flow_score) >= 0.2 and
            any(self.source_availability.values())
        )


# Symbol mapping for flow lookups
SYMBOL_TO_UNDERLYING = {
    # CFD/Futures to ETF
    'US30': 'DIA', 'YM': 'DIA', 'MYM': 'DIA',
    'NAS100': 'QQQ', 'NQ': 'QQQ', 'MNQ': 'QQQ',
    'SPX500': 'SPY', 'US500': 'SPY', 'ES': 'SPY', 'MES': 'SPY',
    'XAUUSD': 'GLD', 'GC': 'GLD', 'MGC': 'GLD',
    'RTY': 'IWM', 'M2K': 'IWM',
    # Pass-through for ETFs
    'SPY': 'SPY', 'QQQ': 'QQQ', 'DIA': 'DIA', 'IWM': 'IWM', 'GLD': 'GLD',
    # Stocks
    'TSLA': 'TSLA', 'NVDA': 'NVDA', 'AAPL': 'AAPL', 'META': 'META',
}

# Strategy-specific flow weights
STRATEGY_FLOW_WEIGHTS = {
    # High influence - flow matters a lot
    'breakout': 0.35,
    'trend': 0.30,
    'flow': 0.40,
    # Medium influence
    'liquidity_reversal': 0.25,
    'pyramid': 0.20,
    # Low influence - mechanical strategies
    'mean_reversion': 0.15,
    'deterministic': 0.15,
    'quick': 0.20,
    'unified': 0.25,
    'ai': 0.30,
}


class UnifiedFlowFeatureEngine:
    """
    Unified engine that aggregates flow data from multiple sources.

    Thread-safe, async-ready, and gracefully handles missing sources.
    """

    def __init__(self):
        self._cache: Dict[str, Tuple[FlowFeatureBundle, datetime]] = {}
        self._cache_ttl = timedelta(seconds=30)
        self._flowalgo_host = os.getenv("FLOWALGO_HOST", "192.168.1.254")
        self._flowalgo_port = os.getenv("FLOWALGO_PORT", "9001")

        # Source status tracking
        self._source_status = {
            "unusual_whales": {"available": False, "last_check": None, "error": None},
            "flowalgo": {"available": False, "last_check": None, "error": None},
            "polygon": {"available": False, "last_check": None, "error": None},
        }

        # Services (lazy-loaded)
        self._uw_service = None
        self._polygon_service = None

        logger.info("UnifiedFlowFeatureEngine initialized")

    def _get_underlying(self, symbol: str) -> str:
        """Map any symbol to its options underlying."""
        return SYMBOL_TO_UNDERLYING.get(symbol.upper(), symbol.upper())

    async def _get_uw_service(self):
        """Lazy-load Unusual Whales service."""
        if self._uw_service is None:
            try:
                from app.services.unusual_whales_service import get_unusual_whales_service
                self._uw_service = await get_unusual_whales_service()
            except Exception as e:
                logger.warning(f"Failed to load UW service: {e}")
                self._uw_service = None
        return self._uw_service

    def _get_polygon_service(self):
        """Lazy-load Polygon service."""
        if self._polygon_service is None:
            try:
                from app.services.polygon_options_flow import get_polygon_flow_service
                self._polygon_service = get_polygon_flow_service()
            except Exception as e:
                logger.warning(f"Failed to load Polygon service: {e}")
                self._polygon_service = None
        return self._polygon_service

    async def get_unusual_whales_features(
        self,
        symbol: str,
        lookback_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Get flow features from Unusual Whales.

        Returns normalized features dict or empty dict on failure.
        """
        underlying = self._get_underlying(symbol)
        result = {
            "available": False,
            "score": 0.0,
            "sentiment": "neutral",
            "net_premium": 0.0,
            "call_premium": 0.0,
            "put_premium": 0.0,
            "whale_count": 0,
            "large_trades": 0,
            "error": None
        }

        try:
            uw_service = await self._get_uw_service()
            if not uw_service:
                result["error"] = "Service not available"
                return result

            flow_summary = await uw_service.get_flow_by_ticker(
                underlying,
                lookback_minutes=lookback_minutes
            )

            if flow_summary:
                result["available"] = True
                result["net_premium"] = flow_summary.net_premium / 1e6  # Convert to millions
                result["call_premium"] = flow_summary.call_premium / 1e6
                result["put_premium"] = flow_summary.put_premium / 1e6
                result["whale_count"] = flow_summary.whale_trades_count
                result["large_trades"] = flow_summary.large_trades_count

                # Normalize score to -1 to +1
                raw_score = flow_summary.sentiment_score  # -100 to +100
                result["score"] = max(-1.0, min(1.0, raw_score / 100.0))

                # Determine sentiment
                sentiment_value = getattr(flow_summary.overall_sentiment, 'value', str(flow_summary.overall_sentiment))
                result["sentiment"] = sentiment_value.lower()

                self._source_status["unusual_whales"]["available"] = True
                self._source_status["unusual_whales"]["last_check"] = datetime.now()
                self._source_status["unusual_whales"]["error"] = None

                logger.debug(f"[UW] {underlying}: score={result['score']:.2f}, "
                           f"net_premium=${result['net_premium']:.1f}M")

        except Exception as e:
            result["error"] = str(e)
            self._source_status["unusual_whales"]["error"] = str(e)
            logger.warning(f"UW features error for {underlying}: {e}")

        return result

    async def get_flowalgo_features(
        self,
        symbol: str,
        lookback_minutes: int = 15
    ) -> Dict[str, Any]:
        """
        Get flow features from FlowAlgo proxy.

        Returns normalized features dict or empty dict on failure.
        """
        underlying = self._get_underlying(symbol)
        result = {
            "available": False,
            "score": 0.0,
            "sentiment": "neutral",
            "bullish_count": 0,
            "bearish_count": 0,
            "sweep_count": 0,
            "block_count": 0,
            "total_premium": 0.0,
            "error": None
        }

        try:
            url = f"http://{self._flowalgo_host}:{self._flowalgo_port}/recent"
            params = {"ticker": underlying, "minutes": lookback_minutes}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        entries = data.get("entries", [])

                        if entries:
                            result["available"] = True

                            bullish = 0
                            bearish = 0
                            sweeps = 0
                            blocks = 0
                            total_premium = 0.0

                            for entry in entries:
                                side = entry.get("side", "").lower()
                                flow_type = entry.get("flow_type", "").lower()
                                premium = entry.get("premium", 0) or 0

                                # Weight sweeps higher
                                weight = 2 if flow_type == "sweep" else 1

                                if side == "bullish":
                                    bullish += weight
                                elif side == "bearish":
                                    bearish += weight

                                if flow_type == "sweep":
                                    sweeps += 1
                                elif flow_type == "block":
                                    blocks += 1

                                total_premium += premium

                            result["bullish_count"] = bullish
                            result["bearish_count"] = bearish
                            result["sweep_count"] = sweeps
                            result["block_count"] = blocks
                            result["total_premium"] = total_premium / 1e6  # Millions

                            # Calculate score (-1 to +1)
                            total = bullish + bearish
                            if total > 0:
                                result["score"] = (bullish - bearish) / total
                                if result["score"] > 0.3:
                                    result["sentiment"] = "bullish"
                                elif result["score"] < -0.3:
                                    result["sentiment"] = "bearish"

                            self._source_status["flowalgo"]["available"] = True
                            self._source_status["flowalgo"]["last_check"] = datetime.now()
                            self._source_status["flowalgo"]["error"] = None

                            logger.debug(f"[FlowAlgo] {underlying}: score={result['score']:.2f}, "
                                       f"bull={bullish}, bear={bearish}")

        except asyncio.TimeoutError:
            result["error"] = "Timeout"
            self._source_status["flowalgo"]["error"] = "Timeout"
        except Exception as e:
            result["error"] = str(e)
            self._source_status["flowalgo"]["error"] = str(e)
            logger.debug(f"FlowAlgo features error for {underlying}: {e}")

        return result

    async def get_polygon_flow_features(
        self,
        symbol: str,
        lookback_minutes: int = 15
    ) -> Dict[str, Any]:
        """
        Get flow features from Polygon options flow.

        Returns normalized features dict or empty dict on failure.
        """
        underlying = self._get_underlying(symbol)
        result = {
            "available": False,
            "score": 0.0,
            "sentiment": "neutral",
            "call_trades": 0,
            "put_trades": 0,
            "total_premium": 0.0,
            "aggressive_trades": 0,
            "error": None
        }

        try:
            polygon_service = self._get_polygon_service()
            if not polygon_service:
                result["error"] = "Service not available"
                return result

            trades = await polygon_service.fetch_options_trades(
                underlying,
                lookback_minutes=lookback_minutes
            )

            if trades:
                result["available"] = True

                call_count = 0
                put_count = 0
                call_premium = 0.0
                put_premium = 0.0
                aggressive = 0

                for trade in trades:
                    opt_type = getattr(trade, 'option_type', '').lower()
                    premium = getattr(trade, 'premium', 0) or 0
                    sentiment = getattr(trade, 'sentiment', '').lower()

                    if opt_type == 'call':
                        call_count += 1
                        call_premium += premium
                    elif opt_type == 'put':
                        put_count += 1
                        put_premium += premium

                    if sentiment in ['bullish', 'bearish']:
                        aggressive += 1

                result["call_trades"] = call_count
                result["put_trades"] = put_count
                result["total_premium"] = (call_premium + put_premium) / 1e6
                result["aggressive_trades"] = aggressive

                # Calculate score
                total = call_count + put_count
                if total > 0:
                    # Premium-weighted score
                    net_premium = call_premium - put_premium
                    max_premium = max(call_premium, put_premium, 1)
                    result["score"] = max(-1.0, min(1.0, net_premium / max_premium))

                    if result["score"] > 0.2:
                        result["sentiment"] = "bullish"
                    elif result["score"] < -0.2:
                        result["sentiment"] = "bearish"

                self._source_status["polygon"]["available"] = True
                self._source_status["polygon"]["last_check"] = datetime.now()
                self._source_status["polygon"]["error"] = None

                logger.debug(f"[Polygon] {underlying}: score={result['score']:.2f}, "
                           f"trades={total}")

        except Exception as e:
            result["error"] = str(e)
            self._source_status["polygon"]["error"] = str(e)
            logger.debug(f"Polygon features error for {underlying}: {e}")

        return result

    def _calculate_source_agreement(
        self,
        uw_score: float,
        fa_score: float,
        poly_score: float,
        availability: SourceAvailability
    ) -> float:
        """
        Calculate how well the sources agree.

        Returns 0-1 where 1 = perfect agreement.
        """
        scores = []
        if availability.unusual_whales:
            scores.append(uw_score)
        if availability.flowalgo:
            scores.append(fa_score)
        if availability.polygon:
            scores.append(poly_score)

        if len(scores) < 2:
            return 0.5  # Can't measure agreement with < 2 sources

        # Check if all scores have same sign (direction agreement)
        all_bullish = all(s > 0.1 for s in scores)
        all_bearish = all(s < -0.1 for s in scores)
        all_neutral = all(abs(s) <= 0.1 for s in scores)

        if all_bullish or all_bearish or all_neutral:
            # Calculate magnitude agreement
            avg_score = sum(scores) / len(scores)
            variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            # Lower variance = higher agreement
            agreement = max(0, 1 - (variance * 2))
        else:
            # Disagreement on direction
            agreement = 0.3

        return agreement

    def _determine_sentiment(self, score: float) -> str:
        """Convert numeric score to sentiment string."""
        if score >= 0.5:
            return FlowSentiment.STRONGLY_BULLISH.value
        elif score >= 0.2:
            return FlowSentiment.BULLISH.value
        elif score <= -0.5:
            return FlowSentiment.STRONGLY_BEARISH.value
        elif score <= -0.2:
            return FlowSentiment.BEARISH.value
        else:
            return FlowSentiment.NEUTRAL.value

    async def get_flow_feature_bundle(
        self,
        symbol: str,
        lookback_minutes: int = 30,
        use_cache: bool = True
    ) -> FlowFeatureBundle:
        """
        Get unified flow feature bundle for a symbol.

        This is the main entry point for flow features.
        """
        underlying = self._get_underlying(symbol)
        cache_key = f"{underlying}_{lookback_minutes}"

        # Check cache (use timezone-aware datetime)
        from zoneinfo import ZoneInfo
        EST_TZ = ZoneInfo("America/New_York")
        now = datetime.now(EST_TZ)

        if use_cache and cache_key in self._cache:
            bundle, cached_at = self._cache[cache_key]
            # Ensure cached_at is timezone-aware for comparison
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=EST_TZ)
            if now - cached_at < self._cache_ttl:
                return bundle

        # Fetch from all sources in parallel
        uw_task = self.get_unusual_whales_features(symbol, lookback_minutes)
        fa_task = self.get_flowalgo_features(symbol, min(lookback_minutes, 15))
        poly_task = self.get_polygon_flow_features(symbol, min(lookback_minutes, 15))

        uw_features, fa_features, poly_features = await asyncio.gather(
            uw_task, fa_task, poly_task,
            return_exceptions=True
        )

        # Handle exceptions
        if isinstance(uw_features, Exception):
            uw_features = {"available": False, "score": 0.0, "error": str(uw_features)}
        if isinstance(fa_features, Exception):
            fa_features = {"available": False, "score": 0.0, "error": str(fa_features)}
        if isinstance(poly_features, Exception):
            poly_features = {"available": False, "score": 0.0, "error": str(poly_features)}

        # Build availability
        availability = SourceAvailability(
            unusual_whales=uw_features.get("available", False),
            flowalgo=fa_features.get("available", False),
            polygon=poly_features.get("available", False)
        )

        # Normalize weights based on availability
        base_weights = SourceWeights()
        normalized_weights = base_weights.normalize(availability)

        # Calculate weighted score
        uw_score = uw_features.get("score", 0.0)
        fa_score = fa_features.get("score", 0.0)
        poly_score = poly_features.get("score", 0.0)

        weighted_score = (
            uw_score * normalized_weights.unusual_whales +
            fa_score * normalized_weights.flowalgo +
            poly_score * normalized_weights.polygon
        )

        # Calculate agreement
        agreement = self._calculate_source_agreement(
            uw_score, fa_score, poly_score, availability
        )

        # Calculate confidence based on:
        # - Source availability (more sources = higher)
        # - Source agreement (more agreement = higher)
        # - Signal strength (stronger signals = higher confidence)
        base_confidence = 0.3 + (availability.count_available() * 0.15)
        agreement_boost = agreement * 0.2
        strength_boost = min(0.2, abs(weighted_score) * 0.3)
        confidence = min(1.0, base_confidence + agreement_boost + strength_boost)

        # Aggregate metrics
        net_premium = (
            uw_features.get("net_premium", 0.0) +
            (fa_features.get("total_premium", 0.0) * (1 if fa_score > 0 else -1))
        )
        call_premium = uw_features.get("call_premium", 0.0)
        put_premium = uw_features.get("put_premium", 0.0)

        # Bull/bear ratio
        if put_premium > 0:
            bull_bear_ratio = call_premium / put_premium
        elif call_premium > 0:
            bull_bear_ratio = 2.0  # All calls
        else:
            bull_bear_ratio = 1.0  # Neutral

        # Call/put imbalance (-1 to +1)
        total_premium = call_premium + put_premium
        if total_premium > 0:
            call_put_imbalance = (call_premium - put_premium) / total_premium
        else:
            call_put_imbalance = 0.0

        # Build notes
        notes_parts = []
        if availability.unusual_whales:
            notes_parts.append(f"UW:{uw_features.get('sentiment', 'n/a')}")
        if availability.flowalgo:
            notes_parts.append(f"FA:{fa_features.get('sentiment', 'n/a')}")
        if availability.polygon:
            notes_parts.append(f"Poly:{poly_features.get('sentiment', 'n/a')}")

        if agreement > 0.7:
            notes_parts.append("sources aligned")
        elif agreement < 0.4 and availability.count_available() > 1:
            notes_parts.append("sources disagree")

        # Create bundle
        bundle = FlowFeatureBundle(
            symbol=underlying,
            timestamp=datetime.now(),
            flow_sentiment=self._determine_sentiment(weighted_score),
            flow_score=round(weighted_score, 3),
            flow_confidence=round(confidence, 3),
            net_premium_millions=round(net_premium, 2),
            call_premium_millions=round(call_premium, 2),
            put_premium_millions=round(put_premium, 2),
            bull_bear_ratio=round(bull_bear_ratio, 2),
            call_put_imbalance=round(call_put_imbalance, 3),
            whale_count=uw_features.get("whale_count", 0),
            sweep_count=fa_features.get("sweep_count", 0),
            block_count=fa_features.get("block_count", 0),
            total_trades=(
                uw_features.get("large_trades", 0) +
                fa_features.get("bullish_count", 0) + fa_features.get("bearish_count", 0) +
                poly_features.get("call_trades", 0) + poly_features.get("put_trades", 0)
            ),
            source_weights={
                "unusual_whales": round(normalized_weights.unusual_whales, 2),
                "flowalgo": round(normalized_weights.flowalgo, 2),
                "polygon": round(normalized_weights.polygon, 2)
            },
            source_agreement=round(agreement, 2),
            source_availability={
                "unusual_whales": availability.unusual_whales,
                "flowalgo": availability.flowalgo,
                "polygon": availability.polygon
            },
            uw_score=round(uw_score, 3),
            flowalgo_score=round(fa_score, 3),
            polygon_score=round(poly_score, 3),
            notes="; ".join(notes_parts) if notes_parts else "No flow data"
        )

        # Cache it (use timezone-aware now from earlier)
        self._cache[cache_key] = (bundle, now)

        logger.info(f"[FLOW BUNDLE] {underlying}: sentiment={bundle.flow_sentiment}, "
                   f"score={bundle.flow_score:.2f}, confidence={bundle.flow_confidence:.2f}, "
                   f"sources={availability.count_available()}/3")

        return bundle

    def get_strategy_flow_weight(self, strategy_type: str) -> float:
        """
        Get the flow weight for a specific strategy type.

        Higher weight = flow matters more for this strategy.
        """
        return STRATEGY_FLOW_WEIGHTS.get(strategy_type.lower(), 0.20)

    def calculate_flow_adjustment(
        self,
        bundle: FlowFeatureBundle,
        direction: str,  # 'long' or 'short'
        strategy_type: str = "unified"
    ) -> Tuple[float, str]:
        """
        Calculate the flow-based adjustment for a signal.

        Returns:
            (adjustment, reason): adjustment is -0.15 to +0.15
        """
        if not bundle.is_actionable:
            return 0.0, "Flow data not actionable"

        strategy_weight = self.get_strategy_flow_weight(strategy_type)

        # Base adjustment from flow score
        # Max adjustment is ±15% (0.15)
        max_adjustment = 0.15 * strategy_weight

        # Calculate alignment
        if direction == 'long':
            if bundle.flow_score > 0:
                # Bullish flow + long signal = boost
                adjustment = bundle.flow_score * bundle.flow_confidence * max_adjustment
                reason = f"Bullish flow confirms long ({bundle.flow_score:.2f})"
            else:
                # Bearish flow + long signal = penalty
                adjustment = bundle.flow_score * bundle.flow_confidence * max_adjustment
                reason = f"Bearish flow opposes long ({bundle.flow_score:.2f})"
        else:  # short
            if bundle.flow_score < 0:
                # Bearish flow + short signal = boost
                adjustment = abs(bundle.flow_score) * bundle.flow_confidence * max_adjustment
                reason = f"Bearish flow confirms short ({bundle.flow_score:.2f})"
            else:
                # Bullish flow + short signal = penalty
                adjustment = -bundle.flow_score * bundle.flow_confidence * max_adjustment
                reason = f"Bullish flow opposes short ({bundle.flow_score:.2f})"

        return round(adjustment, 4), reason

    def get_engine_status(self) -> Dict[str, Any]:
        """Get current engine status for API/monitoring."""
        return {
            "engine": "UnifiedFlowFeatureEngine",
            "version": "1.0.0",
            "sources": self._source_status,
            "cache_size": len(self._cache),
            "flowalgo_host": self._flowalgo_host,
            "flowalgo_port": self._flowalgo_port,
            "symbol_mappings": len(SYMBOL_TO_UNDERLYING),
            "strategy_weights": STRATEGY_FLOW_WEIGHTS
        }

    def clear_cache(self):
        """Clear the feature cache."""
        self._cache.clear()
        logger.info("Flow feature cache cleared")


# Singleton instance
_flow_engine: Optional[UnifiedFlowFeatureEngine] = None


def get_flow_feature_engine() -> UnifiedFlowFeatureEngine:
    """Get or create the unified flow feature engine."""
    global _flow_engine
    if _flow_engine is None:
        _flow_engine = UnifiedFlowFeatureEngine()
    return _flow_engine


async def get_flow_features(symbol: str, lookback_minutes: int = 30) -> FlowFeatureBundle:
    """Convenience function to get flow features."""
    engine = get_flow_feature_engine()
    return await engine.get_flow_feature_bundle(symbol, lookback_minutes)
