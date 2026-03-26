"""
AI-Powered Trading Supervisor
==============================

Autonomous AI agent that monitors, learns, and improves the trading system.

Features:
1. FLOW VALIDATION - Ensures flow sources work during market hours
2. SIGNAL CORRECTNESS - Validates all signals before execution
3. NIGHT MODE AI - Ensures AI crypto trading works 24/7
4. LEARNING SYSTEM - Tracks mistakes and learns patterns
5. CLAUDE INTEGRATION - Uses Claude API for decision analysis

This is the brain that watches over everything.
"""

import asyncio
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import deque
from zoneinfo import ZoneInfo
import httpx

logger = logging.getLogger(__name__)
EST_TZ = ZoneInfo("America/New_York")


class MarketSession(str, Enum):
    PRE_MARKET = "pre_market"      # 4:00 AM - 9:30 AM ET
    MARKET_HOURS = "market_hours"  # 9:30 AM - 4:00 PM ET
    AFTER_HOURS = "after_hours"    # 4:00 PM - 8:00 PM ET
    OVERNIGHT = "overnight"        # 8:00 PM - 4:00 AM ET
    WEEKEND = "weekend"


class AssetClass(str, Enum):
    CRYPTO = "crypto"      # 24/7
    FUTURES = "futures"    # Nearly 24/5
    FOREX = "forex"        # 24/5
    OPTIONS = "options"    # Market hours only


@dataclass
class FlowHealthStatus:
    """Status of flow data sources."""
    unusual_whales: bool = False
    flowalgo: bool = False
    polygon: bool = False
    sources_active: int = 0
    last_check: Optional[datetime] = None
    is_market_hours: bool = False
    error: Optional[str] = None


@dataclass
class SignalValidation:
    """Comprehensive signal validation result."""
    is_valid: bool
    signal_id: str
    ticker: str
    direction: str
    regime: str
    engine: str
    confidence: float

    # Validation checks
    direction_valid: bool = True
    regime_valid: bool = True
    flow_aligned: bool = True
    engine_appropriate: bool = True
    confidence_sufficient: bool = True
    market_session_valid: bool = True

    # AI analysis
    ai_recommendation: Optional[str] = None
    ai_confidence: float = 0.0
    ai_reasoning: Optional[str] = None

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class LearningEntry:
    """Entry in the learning database."""
    timestamp: datetime
    trade_id: str
    ticker: str
    direction: str
    regime: str
    engine: str
    entry_price: float
    exit_price: Optional[float] = None
    pnl: Optional[float] = None

    # Context at time of trade
    flow_sentiment: Optional[str] = None
    flow_score: float = 0.0
    confidence: float = 0.0
    market_session: str = ""

    # Outcome analysis
    was_correct: Optional[bool] = None
    mistake_type: Optional[str] = None
    lesson_learned: Optional[str] = None

    # AI analysis
    ai_analysis: Optional[str] = None


@dataclass
class SupervisorConfig:
    """Configuration for the AI supervisor."""
    # Claude API
    claude_api_key: Optional[str] = None
    claude_model: str = "claude-sonnet-4-20250514"
    use_claude_for_decisions: bool = True

    # Flow validation
    min_flow_sources_market_hours: int = 2  # Need at least 2 sources during market
    min_flow_sources_off_hours: int = 1
    flow_check_interval_seconds: int = 60

    # Confidence thresholds
    min_confidence_day: float = 0.55
    min_confidence_night: float = 0.60  # Higher at night

    # Learning
    learning_db_path: str = ".smartflow_data/learning_db.json"
    max_learning_entries: int = 1000

    # Analysis intervals
    pattern_analysis_interval_minutes: int = 30


class AITradingSupervisor:
    """
    AI-powered supervisor that watches, learns, and improves trading.

    Uses Claude API for intelligent analysis and decision support.
    """

    def __init__(self, config: Optional[SupervisorConfig] = None):
        self.config = config or SupervisorConfig()

        # Load Claude API key from config or environment/secrets
        self._load_api_key()

        # State
        self._flow_health = FlowHealthStatus()
        self._learning_db: List[LearningEntry] = []
        self._mistake_patterns: Dict[str, int] = {}
        self._is_running = False

        # Caches
        self._last_flow_check: Optional[datetime] = None
        self._last_pattern_analysis: Optional[datetime] = None
        self._ai_insights: List[Dict] = []

        # Load learning database
        self._load_learning_db()

        logger.info(f"AITradingSupervisor initialized. Claude API: {'configured' if self._claude_key else 'NOT configured'}")

    def _load_api_key(self):
        """Load Claude API key from various sources."""
        self._claude_key = self.config.claude_api_key

        # Try Docker secret (anthropic_api_key)
        if not self._claude_key:
            for secret_path in ["/run/secrets/anthropic_api_key", "/run/secrets/claude_api_key"]:
                if os.path.exists(secret_path):
                    try:
                        with open(secret_path, "r") as f:
                            self._claude_key = f.read().strip()
                        logger.info(f"Loaded Claude API key from Docker secret: {secret_path}")
                        break
                    except Exception as e:
                        logger.error(f"Failed to read Claude API key from {secret_path}: {e}")

        # Try environment
        if not self._claude_key:
            self._claude_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
            if self._claude_key:
                logger.info("Loaded Claude API key from environment")

    # =========================================================================
    # MARKET SESSION DETECTION
    # =========================================================================

    def get_market_session(self, check_time: Optional[datetime] = None) -> MarketSession:
        """Determine the current market session."""
        if check_time is None:
            check_time = datetime.now(EST_TZ)
        elif check_time.tzinfo is None:
            check_time = check_time.replace(tzinfo=EST_TZ)

        # Weekend check
        if check_time.weekday() >= 5:
            return MarketSession.WEEKEND

        hour = check_time.hour
        minute = check_time.minute
        time_decimal = hour + minute / 60

        if 4 <= time_decimal < 9.5:
            return MarketSession.PRE_MARKET
        elif 9.5 <= time_decimal < 16:
            return MarketSession.MARKET_HOURS
        elif 16 <= time_decimal < 20:
            return MarketSession.AFTER_HOURS
        else:
            return MarketSession.OVERNIGHT

    def get_active_asset_classes(self) -> List[AssetClass]:
        """Get asset classes that should be trading now."""
        session = self.get_market_session()

        # Crypto is always active
        active = [AssetClass.CRYPTO]

        if session == MarketSession.WEEKEND:
            return active  # Only crypto on weekends

        # Futures trade nearly 24/5 (closed 5-6 PM ET daily)
        now = datetime.now(EST_TZ)
        if not (17 <= now.hour < 18):
            active.append(AssetClass.FUTURES)

        # Forex 24/5
        active.append(AssetClass.FOREX)

        # Options only during market hours
        if session == MarketSession.MARKET_HOURS:
            active.append(AssetClass.OPTIONS)

        return active

    # =========================================================================
    # FLOW VALIDATION
    # =========================================================================

    async def check_flow_health(self) -> FlowHealthStatus:
        """Check health of all flow data sources."""
        now = datetime.now(EST_TZ)
        session = self.get_market_session()
        is_market_hours = session == MarketSession.MARKET_HOURS

        status = FlowHealthStatus(
            last_check=now,
            is_market_hours=is_market_hours
        )

        try:
            # Check Unusual Whales
            from app.services.flow_feature_engine import get_flow_feature_engine
            flow_engine = get_flow_feature_engine()

            # Get flow bundle for SPY (most liquid)
            bundle = await flow_engine.get_flow_feature_bundle("SPY", use_cache=False)

            if bundle:
                status.unusual_whales = bundle.source_availability.get("unusual_whales", False)
                status.flowalgo = bundle.source_availability.get("flowalgo", False)
                status.polygon = bundle.source_availability.get("polygon", False)
                status.sources_active = sum([
                    status.unusual_whales,
                    status.flowalgo,
                    status.polygon
                ])
        except Exception as e:
            status.error = str(e)
            logger.error(f"Flow health check error: {e}")

        self._flow_health = status
        self._last_flow_check = now

        # Validate flow health
        if is_market_hours:
            if status.sources_active < self.config.min_flow_sources_market_hours:
                logger.warning(
                    f"⚠️ [SUPERVISOR] Only {status.sources_active}/3 flow sources active during market hours!"
                )
                await self._analyze_flow_issue(status)

        return status

    async def _analyze_flow_issue(self, status: FlowHealthStatus):
        """Use Claude to analyze flow issues."""
        if not self._claude_key or not self.config.use_claude_for_decisions:
            return

        prompt = f"""Analyze this trading system flow data issue:

Current Status:
- Market Hours: {status.is_market_hours}
- Unusual Whales Active: {status.unusual_whales}
- FlowAlgo Active: {status.flowalgo}
- Polygon Active: {status.polygon}
- Error: {status.error}

During market hours, we need at least 2 flow sources for reliable signals.
Only {status.sources_active} sources are active.

What could be wrong and what should we check? Be concise (2-3 sentences)."""

        analysis = await self._ask_claude(prompt)
        if analysis:
            logger.info(f"[SUPERVISOR AI] Flow issue analysis: {analysis}")
            self._ai_insights.append({
                "timestamp": datetime.now(EST_TZ).isoformat(),
                "type": "flow_issue",
                "analysis": analysis
            })

    # =========================================================================
    # SIGNAL VALIDATION
    # =========================================================================

    async def validate_signal(
        self,
        ticker: str,
        direction: str,
        regime: str,
        engine: str,
        confidence: float,
        price: float,
        flow_bundle: Optional[Any] = None,
        metadata: Optional[Dict] = None
    ) -> SignalValidation:
        """
        Comprehensive signal validation with AI analysis.

        This is the main entry point for signal validation.
        """
        signal_id = f"{ticker}_{direction}_{datetime.now(EST_TZ).strftime('%H%M%S')}"
        session = self.get_market_session()

        validation = SignalValidation(
            is_valid=True,
            signal_id=signal_id,
            ticker=ticker,
            direction=direction,
            regime=regime,
            engine=engine,
            confidence=confidence,
            market_session_valid=True
        )

        # Check 1: Direction matches regime
        if not self._validate_direction_regime(direction, regime):
            validation.direction_valid = False
            validation.is_valid = False
            validation.errors.append(
                f"Direction {direction} invalid for regime {regime}"
            )

        # Check 2: Engine is appropriate for regime
        if not self._validate_engine_regime(engine, regime):
            validation.engine_appropriate = False
            validation.warnings.append(
                f"Engine {engine} may not be optimal for {regime}"
            )

        # Check 3: Confidence threshold based on session
        min_conf = self.config.min_confidence_night if session in [
            MarketSession.OVERNIGHT, MarketSession.AFTER_HOURS
        ] else self.config.min_confidence_day

        if confidence < min_conf:
            validation.confidence_sufficient = False
            validation.warnings.append(
                f"Confidence {confidence:.1%} below threshold {min_conf:.1%}"
            )

        # Check 4: Flow alignment (if available)
        if flow_bundle:
            flow_sentiment = getattr(flow_bundle, 'flow_sentiment', 'neutral')
            flow_score = getattr(flow_bundle, 'flow_score', 0.0)

            if direction == 'long' and flow_score < -0.3:
                validation.flow_aligned = False
                validation.warnings.append(
                    f"LONG signal but flow is bearish ({flow_score:.2f})"
                )
            elif direction == 'short' and flow_score > 0.3:
                validation.flow_aligned = False
                validation.warnings.append(
                    f"SHORT signal but flow is bullish ({flow_score:.2f})"
                )

        # Check 5: Market session validity for asset class
        asset_class = self._get_asset_class(ticker)
        active_classes = self.get_active_asset_classes()

        if asset_class not in active_classes:
            validation.market_session_valid = False
            validation.is_valid = False
            validation.errors.append(
                f"{ticker} ({asset_class.value}) not trading during {session.value}"
            )

        # AI Analysis (if enabled and we have warnings/errors)
        if self._claude_key and self.config.use_claude_for_decisions:
            if validation.errors or len(validation.warnings) >= 2:
                ai_result = await self._get_ai_signal_analysis(validation, flow_bundle)
                if ai_result:
                    validation.ai_recommendation = ai_result.get("recommendation")
                    validation.ai_confidence = ai_result.get("confidence", 0.0)
                    validation.ai_reasoning = ai_result.get("reasoning")

        return validation

    def _validate_direction_regime(self, direction: str, regime: str) -> bool:
        """Validate direction is appropriate for regime."""
        direction = direction.lower()
        regime = regime.lower()

        if regime in ['trending_up', 'breakout']:
            return direction == 'long'
        elif regime == 'trending_down':
            return direction == 'short'
        elif regime == 'ranging':
            return direction in ['long', 'short']
        return True

    def _validate_engine_regime(self, engine: str, regime: str) -> bool:
        """Validate engine is appropriate for regime."""
        engine = engine.lower()
        regime = regime.lower()

        optimal_engines = {
            'trending_up': ['trend', 'breakout', 'flow'],
            'trending_down': ['trend', 'flow'],
            'breakout': ['breakout', 'trend'],
            'ranging': ['mean_reversion', 'liquidity_reversal'],
        }

        if regime in optimal_engines:
            return engine in optimal_engines[regime] or engine in ['unified', 'quick', 'deterministic']
        return True

    def _get_asset_class(self, ticker: str) -> AssetClass:
        """Determine asset class from ticker."""
        ticker = ticker.upper()

        crypto_tickers = ['BTCUSD', 'ETHUSD', 'BTC', 'ETH', 'SOLUSD', 'SOL']
        futures_tickers = ['MES', 'MNQ', 'MYM', 'ES', 'NQ', 'YM', 'RTY', 'M2K', 'GC', 'MGC']
        forex_tickers = ['USDJPY', 'GBPJPY', 'EURUSD', 'GBPUSD']
        index_cfd = ['US30', 'NAS100', 'SPX500', 'US500']

        if ticker in crypto_tickers:
            return AssetClass.CRYPTO
        elif ticker in futures_tickers:
            return AssetClass.FUTURES
        elif ticker in forex_tickers:
            return AssetClass.FOREX
        elif ticker in index_cfd:
            return AssetClass.FUTURES  # Treat as futures
        else:
            return AssetClass.OPTIONS  # Default to most restrictive

    async def _get_ai_signal_analysis(
        self,
        validation: SignalValidation,
        flow_bundle: Optional[Any]
    ) -> Optional[Dict]:
        """Get AI analysis for a signal."""
        flow_info = ""
        if flow_bundle:
            flow_info = f"""
Flow Data:
- Sentiment: {getattr(flow_bundle, 'flow_sentiment', 'unknown')}
- Score: {getattr(flow_bundle, 'flow_score', 0):.2f}
- Confidence: {getattr(flow_bundle, 'flow_confidence', 0):.2f}
"""

        prompt = f"""Analyze this trading signal:

Signal:
- Ticker: {validation.ticker}
- Direction: {validation.direction}
- Regime: {validation.regime}
- Engine: {validation.engine}
- Confidence: {validation.confidence:.1%}

{flow_info}

Validation Issues:
- Errors: {validation.errors}
- Warnings: {validation.warnings}

Based on this, should we:
1. EXECUTE - Take the trade
2. REDUCE - Take with smaller size
3. SKIP - Don't take this trade

Respond in JSON format:
{{"recommendation": "EXECUTE|REDUCE|SKIP", "confidence": 0.0-1.0, "reasoning": "brief reason"}}"""

        response = await self._ask_claude(prompt)
        if response:
            try:
                # Extract JSON from response
                import re
                json_match = re.search(r'\{[^}]+\}', response)
                if json_match:
                    return json.loads(json_match.group())
            except:
                pass
        return None

    # =========================================================================
    # LEARNING SYSTEM
    # =========================================================================

    def record_trade(
        self,
        trade_id: str,
        ticker: str,
        direction: str,
        regime: str,
        engine: str,
        entry_price: float,
        confidence: float,
        flow_sentiment: Optional[str] = None,
        flow_score: float = 0.0
    ):
        """Record a trade for learning."""
        entry = LearningEntry(
            timestamp=datetime.now(EST_TZ),
            trade_id=trade_id,
            ticker=ticker,
            direction=direction,
            regime=regime,
            engine=engine,
            entry_price=entry_price,
            confidence=confidence,
            flow_sentiment=flow_sentiment,
            flow_score=flow_score,
            market_session=self.get_market_session().value
        )

        self._learning_db.append(entry)

        # Trim if too large
        if len(self._learning_db) > self.config.max_learning_entries:
            self._learning_db = self._learning_db[-self.config.max_learning_entries:]

        self._save_learning_db()

    def record_trade_outcome(
        self,
        trade_id: str,
        exit_price: float,
        pnl: float
    ):
        """Record outcome of a trade for learning."""
        for entry in self._learning_db:
            if entry.trade_id == trade_id:
                entry.exit_price = exit_price
                entry.pnl = pnl
                entry.was_correct = pnl >= 0

                # Analyze mistake if loss
                if pnl < 0:
                    asyncio.create_task(self._analyze_mistake(entry))

                self._save_learning_db()
                break

    async def _analyze_mistake(self, entry: LearningEntry):
        """Analyze a losing trade to learn from it."""
        # Categorize mistake
        mistake_type = self._categorize_mistake(entry)
        entry.mistake_type = mistake_type

        # Track pattern
        self._mistake_patterns[mistake_type] = self._mistake_patterns.get(mistake_type, 0) + 1

        # AI analysis
        if self._claude_key and self.config.use_claude_for_decisions:
            analysis = await self._get_ai_mistake_analysis(entry)
            if analysis:
                entry.ai_analysis = analysis
                entry.lesson_learned = analysis

        logger.info(f"[LEARNING] Mistake analyzed: {mistake_type} on {entry.ticker}")

    def _categorize_mistake(self, entry: LearningEntry) -> str:
        """Categorize what type of mistake was made."""
        # Direction vs regime mismatch
        if entry.regime == 'trending_down' and entry.direction == 'long':
            return "wrong_direction_trending_down"
        if entry.regime in ['trending_up', 'breakout'] and entry.direction == 'short':
            return "wrong_direction_trending_up"

        # Flow disagreement
        if entry.flow_score:
            if entry.direction == 'long' and entry.flow_score < -0.3:
                return "ignored_bearish_flow"
            if entry.direction == 'short' and entry.flow_score > 0.3:
                return "ignored_bullish_flow"

        # Low confidence trade
        if entry.confidence < 0.55:
            return "low_confidence_trade"

        # Session mismatch
        if entry.market_session == "overnight" and self._get_asset_class(entry.ticker) == AssetClass.OPTIONS:
            return "wrong_session"

        return "market_moved_against"

    async def _get_ai_mistake_analysis(self, entry: LearningEntry) -> Optional[str]:
        """Get AI analysis of a mistake."""
        prompt = f"""Analyze this losing trade to help us learn:

Trade:
- Ticker: {entry.ticker}
- Direction: {entry.direction}
- Regime: {entry.regime}
- Engine: {entry.engine}
- Entry: ${entry.entry_price:.2f}
- Exit: ${entry.exit_price:.2f if entry.exit_price else 0}
- PnL: ${entry.pnl:.2f if entry.pnl else 0}
- Confidence: {entry.confidence:.1%}
- Flow Sentiment: {entry.flow_sentiment}
- Flow Score: {entry.flow_score:.2f}
- Session: {entry.market_session}
- Mistake Type: {entry.mistake_type}

What's the key lesson? Be concise (1-2 sentences)."""

        return await self._ask_claude(prompt)

    async def get_pattern_insights(self) -> Dict[str, Any]:
        """Get insights from learned patterns."""
        # Basic stats
        total_trades = len(self._learning_db)
        wins = sum(1 for e in self._learning_db if e.was_correct == True)
        losses = sum(1 for e in self._learning_db if e.was_correct == False)

        insights = {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": wins / max(1, wins + losses),
            "mistake_patterns": dict(self._mistake_patterns),
            "top_mistakes": sorted(
                self._mistake_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }

        # AI pattern analysis
        if self._claude_key and total_trades >= 10:
            now = datetime.now(EST_TZ)
            if (not self._last_pattern_analysis or
                (now - self._last_pattern_analysis).total_seconds() >
                self.config.pattern_analysis_interval_minutes * 60):

                ai_insights = await self._get_ai_pattern_analysis()
                if ai_insights:
                    insights["ai_analysis"] = ai_insights
                self._last_pattern_analysis = now

        return insights

    async def _get_ai_pattern_analysis(self) -> Optional[str]:
        """Get AI analysis of trading patterns."""
        # Prepare summary
        recent = self._learning_db[-50:]  # Last 50 trades

        by_regime = {}
        by_engine = {}
        by_session = {}

        for entry in recent:
            # By regime
            if entry.regime not in by_regime:
                by_regime[entry.regime] = {"wins": 0, "losses": 0}
            if entry.was_correct:
                by_regime[entry.regime]["wins"] += 1
            elif entry.was_correct == False:
                by_regime[entry.regime]["losses"] += 1

            # By engine
            if entry.engine not in by_engine:
                by_engine[entry.engine] = {"wins": 0, "losses": 0}
            if entry.was_correct:
                by_engine[entry.engine]["wins"] += 1
            elif entry.was_correct == False:
                by_engine[entry.engine]["losses"] += 1

            # By session
            if entry.market_session not in by_session:
                by_session[entry.market_session] = {"wins": 0, "losses": 0}
            if entry.was_correct:
                by_session[entry.market_session]["wins"] += 1
            elif entry.was_correct == False:
                by_session[entry.market_session]["losses"] += 1

        prompt = f"""Analyze these trading patterns and give improvement recommendations:

Performance by Regime:
{json.dumps(by_regime, indent=2)}

Performance by Engine:
{json.dumps(by_engine, indent=2)}

Performance by Session:
{json.dumps(by_session, indent=2)}

Common Mistakes:
{json.dumps(dict(self._mistake_patterns), indent=2)}

Give 3 specific, actionable recommendations to improve. Be concise."""

        return await self._ask_claude(prompt)

    # =========================================================================
    # CLAUDE API INTEGRATION
    # =========================================================================

    async def _ask_claude(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        """Send a prompt to Claude API."""
        if not self._claude_key:
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self._claude_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": self.config.claude_model,
                        "max_tokens": max_tokens,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ]
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("content"):
                        return data["content"][0]["text"]
                else:
                    logger.error(f"Claude API error: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Claude API request error: {e}")

        return None

    # =========================================================================
    # PERSISTENCE
    # =========================================================================

    def _load_learning_db(self):
        """Load learning database from disk."""
        try:
            path = self.config.learning_db_path
            os.makedirs(os.path.dirname(path), exist_ok=True)

            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
                    self._learning_db = [
                        LearningEntry(
                            timestamp=datetime.fromisoformat(e['timestamp']),
                            **{k: v for k, v in e.items() if k != 'timestamp'}
                        )
                        for e in data.get('entries', [])
                    ]
                    self._mistake_patterns = data.get('mistake_patterns', {})
                logger.info(f"Loaded {len(self._learning_db)} learning entries")
        except Exception as e:
            logger.warning(f"Could not load learning DB: {e}")

    def _save_learning_db(self):
        """Save learning database to disk."""
        try:
            path = self.config.learning_db_path
            os.makedirs(os.path.dirname(path), exist_ok=True)

            with open(path, 'w') as f:
                json.dump({
                    'entries': [
                        {
                            **asdict(e),
                            'timestamp': e.timestamp.isoformat()
                        }
                        for e in self._learning_db
                    ],
                    'mistake_patterns': self._mistake_patterns
                }, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Could not save learning DB: {e}")

    # =========================================================================
    # STATUS
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get supervisor status."""
        return {
            "claude_configured": bool(self._claude_key),
            "market_session": self.get_market_session().value,
            "active_asset_classes": [a.value for a in self.get_active_asset_classes()],
            "flow_health": asdict(self._flow_health) if self._flow_health.last_check else None,
            "learning_entries": len(self._learning_db),
            "mistake_patterns": dict(self._mistake_patterns),
            "recent_ai_insights": self._ai_insights[-5:],
            "config": {
                "use_claude": self.config.use_claude_for_decisions,
                "min_flow_sources_market": self.config.min_flow_sources_market_hours,
                "min_confidence_day": self.config.min_confidence_day,
                "min_confidence_night": self.config.min_confidence_night
            }
        }


# Singleton
_supervisor: Optional[AITradingSupervisor] = None


def get_ai_supervisor() -> AITradingSupervisor:
    """Get or create the AI trading supervisor."""
    global _supervisor
    if _supervisor is None:
        _supervisor = AITradingSupervisor()
    return _supervisor
