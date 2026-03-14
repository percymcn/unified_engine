"""
AI Strategy Suite Service
==========================

Institutional-grade AI analysis engine that provides 10 analysis frameworks:
1. Goldman Sachs Stock Screener - Stock screening with P/E, growth, moats
2. Morgan Stanley DCF Valuation - Discounted cash flow analysis
3. Bridgewater Risk Analysis - Portfolio risk assessment
4. JPMorgan Earnings Breakdown - Earnings analysis & predictions
5. BlackRock Portfolio Construction - Asset allocation strategy
6. Citadel Technical Analysis - Technical indicators & signals
7. Harvard Dividend Strategy - Dividend income portfolio
8. Bain Competitive Advantage - Competitive moat analysis
9. Renaissance Technologies Patterns - Statistical edge & patterns
10. McKinsey Macro Impact - Macro economic analysis

Each analysis returns structured data that enhances SmartFlow signal quality.
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor

import anthropic
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from app.db.database import Base, SessionLocal

# Import market data service for live data
try:
    from app.services.market_data_service import market_data_service
    MARKET_DATA_AVAILABLE = True
except ImportError:
    market_data_service = None
    MARKET_DATA_AVAILABLE = False

logger = logging.getLogger(__name__)

# Thread pool for parallel API calls
_analysis_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ai_strategy")


class AnalysisType(str, Enum):
    """Available analysis types"""
    STOCK_SCREENER = "stock_screener"           # Goldman Sachs
    DCF_VALUATION = "dcf_valuation"             # Morgan Stanley
    RISK_ANALYSIS = "risk_analysis"             # Bridgewater
    EARNINGS_BREAKDOWN = "earnings_breakdown"   # JPMorgan
    PORTFOLIO_CONSTRUCTION = "portfolio"        # BlackRock
    TECHNICAL_ANALYSIS = "technical"            # Citadel
    DIVIDEND_STRATEGY = "dividend"              # Harvard
    COMPETITIVE_ADVANTAGE = "competitive"       # Bain
    PATTERN_FINDER = "patterns"                 # Renaissance Tech
    MACRO_IMPACT = "macro"                      # McKinsey


@dataclass
class AnalysisResult:
    """Result from an AI analysis"""
    analysis_type: str
    ticker: str
    timestamp: datetime

    # Core result
    recommendation: str  # strong_buy, buy, neutral, sell, strong_sell
    confidence: float    # 0-100%
    summary: str         # Brief summary

    # Analysis-specific data
    data: Dict[str, Any]

    # Metadata
    cache_key: str = ""
    from_cache: bool = False
    processing_time_ms: int = 0


class AIStrategyAnalysisCache(Base):
    """Cache AI analysis results to reduce API costs"""
    __tablename__ = "ai_strategy_cache"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(64), unique=True, nullable=False, index=True)
    analysis_type = Column(String(50), nullable=False)
    ticker = Column(String(20), nullable=False, index=True)

    # Result
    recommendation = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    summary = Column(Text, nullable=True)
    data = Column(JSON, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    hit_count = Column(Integer, default=0)


class AIStrategySuite:
    """
    AI-powered institutional analysis suite.

    Uses Claude API to generate professional-grade analyses
    for stocks, ETFs, and futures.
    """

    def __init__(self):
        # Try Docker secret file first, then environment variable
        self.api_key = None
        secret_path = "/run/secrets/anthropic_api_key"
        if os.path.exists(secret_path):
            try:
                with open(secret_path, "r") as f:
                    self.api_key = f.read().strip()
                logger.info("AI Strategy Suite: Loaded API key from Docker secret")
            except Exception as e:
                logger.error(f"Failed to read API key from secret file: {e}")

        if not self.api_key:
            self.api_key = os.getenv("ANTHROPIC_API_KEY")

        self.client = None
        # Use Haiku for cost efficiency (12x cheaper than Sonnet)
        # Haiku: $0.25 input / $1.25 output per 1M tokens
        # Sonnet: $3 input / $15 output per 1M tokens
        self.model = "claude-3-haiku-20240307"  # Cost-optimized for routine scans
        self.model_sonnet = "claude-3-5-sonnet-20241022"  # For critical deep analysis only
        self.max_tokens = 4096

        # Cache settings (reduce API costs)
        # Extended cache TTL to reduce API costs (4x longer)
        self.cache_ttl = {
            AnalysisType.TECHNICAL_ANALYSIS: timedelta(hours=1),  # Was 15min, now 1h
            AnalysisType.PATTERN_FINDER: timedelta(hours=2),  # Was 30min, now 2h
            AnalysisType.MACRO_IMPACT: timedelta(hours=8),  # Was 4h, now 8h - macro is slow-moving
            AnalysisType.DCF_VALUATION: timedelta(hours=24),  # Very long - fundamentals
            AnalysisType.EARNINGS_BREAKDOWN: timedelta(hours=12),
            AnalysisType.COMPETITIVE_ADVANTAGE: timedelta(hours=24),
            AnalysisType.DIVIDEND_STRATEGY: timedelta(hours=24),
            AnalysisType.RISK_ANALYSIS: timedelta(hours=2),
            AnalysisType.PORTFOLIO_CONSTRUCTION: timedelta(hours=6),
            AnalysisType.STOCK_SCREENER: timedelta(hours=4),
        }

        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info("AI Strategy Suite initialized with Anthropic API")
        else:
            logger.warning("AI Strategy Suite: No ANTHROPIC_API_KEY found")

        # Check market data availability
        self.market_data_available = MARKET_DATA_AVAILABLE and market_data_service is not None
        if self.market_data_available:
            logger.info("AI Strategy Suite: Live market data integration enabled")

    async def _enrich_context_with_market_data(self, ticker: str, context: Dict = None) -> Dict:
        """
        Enrich analysis context with HYBRID live market data from ProjectX + Polygon.
        This gives Claude real-time prices from ProjectX futures + historical patterns from Polygon.
        """
        enriched = context.copy() if context else {}

        if not self.market_data_available:
            enriched['market_data_note'] = 'Live market data not available'
            return enriched

        try:
            # Try hybrid data first (ProjectX real-time + Polygon historical)
            hybrid_data = await market_data_service.get_hybrid_data(ticker)
            if hybrid_data:
                enriched['live_market_data'] = {
                    'ticker': hybrid_data.symbol,
                    'source': f"{hybrid_data.realtime_source} (RT) + {hybrid_data.historical_source} (Hist)",
                    'price': {
                        'current': hybrid_data.current_price,
                        'bid': hybrid_data.bid,
                        'ask': hybrid_data.ask,
                        'spread': hybrid_data.spread,
                    },
                    'indicators': {
                        'ema_9': hybrid_data.ema_9,
                        'ema_20': hybrid_data.ema_20,
                        'rsi_14': hybrid_data.rsi,
                    },
                    'fibonacci': {
                        'swing_high': hybrid_data.fib_levels.swing_high if hybrid_data.fib_levels else None,
                        'swing_low': hybrid_data.fib_levels.swing_low if hybrid_data.fib_levels else None,
                        'level_0_618': hybrid_data.fib_levels.level_0_618 if hybrid_data.fib_levels else None,
                        'level_0_5': hybrid_data.fib_levels.level_0_5 if hybrid_data.fib_levels else None,
                        'trend': hybrid_data.fib_levels.trend if hybrid_data.fib_levels else None,
                    } if hybrid_data.fib_levels else None,
                    'bars_count': len(hybrid_data.bars),
                    'timestamp': hybrid_data.timestamp.isoformat(),
                }
                logger.info(f"✅ Hybrid data: {ticker} @ ${hybrid_data.current_price:.2f} (RT:{hybrid_data.realtime_source}, Hist:{len(hybrid_data.bars)} bars)")
                return enriched

            # Fallback to Polygon-only data
            live_data = market_data_service.get_ai_context(ticker)
            if live_data and 'error' not in live_data:
                enriched['live_market_data'] = live_data
                logger.debug(f"Enriched {ticker} context with Polygon data (fallback)")
            else:
                enriched['market_data_note'] = live_data.get('error', 'No data available')
        except Exception as e:
            logger.warning(f"Failed to enrich context with market data: {e}")
            enriched['market_data_note'] = f'Market data error: {str(e)}'

        return enriched

    def _generate_cache_key(self, analysis_type: str, ticker: str, context: Dict = None) -> str:
        """Generate cache key for analysis"""
        key_data = f"{analysis_type}:{ticker}:{json.dumps(context or {}, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _check_cache(self, cache_key: str) -> Optional[AnalysisResult]:
        """Check if analysis is cached"""
        try:
            db = SessionLocal()
            try:
                cached = db.query(AIStrategyAnalysisCache).filter(
                    AIStrategyAnalysisCache.cache_key == cache_key,
                    AIStrategyAnalysisCache.expires_at > datetime.utcnow()
                ).first()

                if cached:
                    # Update hit count
                    cached.hit_count += 1
                    db.commit()

                    return AnalysisResult(
                        analysis_type=cached.analysis_type,
                        ticker=cached.ticker,
                        timestamp=cached.created_at,
                        recommendation=cached.recommendation,
                        confidence=cached.confidence,
                        summary=cached.summary or "",
                        data=cached.data,
                        cache_key=cache_key,
                        from_cache=True
                    )
                return None
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
            return None

    def _save_to_cache(self, result: AnalysisResult, ttl: timedelta):
        """Save analysis result to cache"""
        try:
            db = SessionLocal()
            try:
                # Remove old cache entry if exists
                db.query(AIStrategyAnalysisCache).filter(
                    AIStrategyAnalysisCache.cache_key == result.cache_key
                ).delete()

                cache_entry = AIStrategyAnalysisCache(
                    cache_key=result.cache_key,
                    analysis_type=result.analysis_type,
                    ticker=result.ticker,
                    recommendation=result.recommendation,
                    confidence=result.confidence,
                    summary=result.summary,
                    data=result.data,
                    expires_at=datetime.utcnow() + ttl
                )

                db.add(cache_entry)
                db.commit()
                logger.debug(f"Cached analysis: {result.analysis_type} for {result.ticker}")
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Failed to cache analysis: {e}")

    def _parse_recommendation(self, text: str) -> Tuple[str, float]:
        """Parse recommendation and confidence from AI response"""
        text_lower = text.lower()

        # Extract recommendation
        if "strong buy" in text_lower or "strongly buy" in text_lower:
            rec = "strong_buy"
            base_conf = 85
        elif "strong sell" in text_lower or "strongly sell" in text_lower:
            rec = "strong_sell"
            base_conf = 85
        elif "buy" in text_lower and "sell" not in text_lower:
            rec = "buy"
            base_conf = 70
        elif "sell" in text_lower and "buy" not in text_lower:
            rec = "sell"
            base_conf = 70
        else:
            rec = "neutral"
            base_conf = 50

        # Try to extract explicit confidence
        import re
        conf_match = re.search(r'(\d{1,3})%?\s*confidence', text_lower)
        if conf_match:
            base_conf = min(100, max(0, int(conf_match.group(1))))

        return rec, base_conf

    async def _call_claude(self, system_prompt: str, user_prompt: str) -> str:
        """Make Claude API call"""
        if not self.client:
            raise ValueError("Anthropic client not initialized")

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                _analysis_executor,
                lambda: self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                )
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise

    # ==========================================
    # ANALYSIS FRAMEWORKS
    # ==========================================

    async def analyze_technical(self, ticker: str, context: Dict = None) -> AnalysisResult:
        """
        Citadel-Grade Technical Analysis System

        Analyzes:
        - Trend direction (daily/weekly/monthly)
        - Support/resistance levels
        - Moving averages (50/100/200-day)
        - RSI, MACD, Bollinger Bands
        - Volume trends
        - Chart patterns
        - Fibonacci retracements
        - Entry/exit levels

        Uses LIVE market data from Polygon when available.
        """
        start_time = datetime.now()
        analysis_type = AnalysisType.TECHNICAL_ANALYSIS

        # Enrich context with live market data
        enriched_context = await self._enrich_context_with_market_data(ticker, context)

        cache_key = self._generate_cache_key(analysis_type, ticker, context)

        # Check cache
        cached = self._check_cache(cache_key)
        if cached:
            return cached

        system_prompt = """You are a senior quantitative trader at Citadel who combines
technical analysis with statistical models to time entries and exits.

Analyze the given stock/ETF and provide a technical analysis report card.
Format your response as JSON with these fields:
{
    "recommendation": "strong_buy|buy|neutral|sell|strong_sell",
    "confidence": 0-100,
    "summary": "1-2 sentence summary",
    "trend": {"daily": "up|down|sideways", "weekly": "...", "monthly": "..."},
    "support_levels": [price1, price2, price3],
    "resistance_levels": [price1, price2, price3],
    "moving_averages": {"ma50": price, "ma100": price, "ma200": price, "ema9": price, "ema20": price},
    "indicators": {"rsi": value, "macd": "bullish|bearish", "bollinger": "upper|middle|lower"},
    "volume_trend": "increasing|decreasing|stable",
    "chart_pattern": "pattern name or none",
    "fibonacci_levels": {"0.236": price, "0.382": price, "0.5": price, "0.618": price},
    "entry_price": optimal_entry,
    "stop_loss": stop_loss_price,
    "profit_target": target_price,
    "risk_reward_ratio": ratio
}"""

        # Build context with live data if available
        live_data_section = ""
        if enriched_context.get('live_market_data'):
            live_data = enriched_context['live_market_data']
            live_data_section = f"""
LIVE MARKET DATA (from Polygon):
{json.dumps(live_data, indent=2)}

Use this real-time data for accurate analysis. The EMA, RSI, and Fibonacci levels are calculated from actual bars.
"""
            # Add multi-timeframe analysis if available
            if live_data.get('multi_timeframe'):
                mtf = live_data['multi_timeframe']
                live_data_section += f"""
MULTI-TIMEFRAME ANALYSIS (Day Trading Focus):
- Overall Bias: {mtf.get('overall_bias', 'unknown')}
- Bullish Alignment: {mtf.get('bullish_alignment', 0)}%
- Bearish Alignment: {mtf.get('bearish_alignment', 0)}%
- Confluences: {', '.join(mtf.get('confluences', [])) or 'None detected'}

Timeframe Breakdown:
{json.dumps(mtf.get('timeframes', {}), indent=2)}

IMPORTANT: Use this multi-timeframe analysis for day trading decisions.
- 5m timeframe is PRIMARY for entry timing
- 15m and 30m confirm intraday momentum
- 1h and 4h provide structure context
- Trade WITH the overall bias alignment
"""

        user_prompt = f"""Analyze {ticker} technically for day trading.
{live_data_section}
Additional context:
{json.dumps(context or {"note": "Use your knowledge of recent market conditions"}, indent=2)}

Consider ALL timeframes (5m, 15m, 30m, 1h, 4h) for your analysis.
Provide the technical analysis as specified JSON format."""

        try:
            response = await self._call_claude(system_prompt, user_prompt)

            # Parse JSON from response
            try:
                # Try to extract JSON from response
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    data = json.loads(response[json_start:json_end])
                else:
                    data = {"raw_response": response}
            except json.JSONDecodeError:
                data = {"raw_response": response}

            rec = data.get("recommendation", "neutral")
            conf = data.get("confidence", 50)
            summary = data.get("summary", "Technical analysis completed")

            result = AnalysisResult(
                analysis_type=analysis_type,
                ticker=ticker,
                timestamp=datetime.now(),
                recommendation=rec,
                confidence=float(conf),
                summary=summary,
                data=data,
                cache_key=cache_key,
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )

            # Cache result
            self._save_to_cache(result, self.cache_ttl[analysis_type])

            return result

        except Exception as e:
            logger.error(f"Technical analysis failed for {ticker}: {e}")
            return AnalysisResult(
                analysis_type=analysis_type,
                ticker=ticker,
                timestamp=datetime.now(),
                recommendation="neutral",
                confidence=0,
                summary=f"Analysis failed: {str(e)}",
                data={"error": str(e)},
                cache_key=cache_key
            )

    async def analyze_dcf_valuation(self, ticker: str, context: Dict = None) -> AnalysisResult:
        """
        Morgan Stanley-Style DCF Valuation Deep Dive

        Analyzes:
        - 5-year revenue projections
        - Operating margins
        - Free cash flow
        - WACC estimate
        - Terminal value
        - Fair value vs current price
        """
        start_time = datetime.now()
        analysis_type = AnalysisType.DCF_VALUATION
        cache_key = self._generate_cache_key(analysis_type, ticker, context)

        cached = self._check_cache(cache_key)
        if cached:
            return cached

        system_prompt = """You are a VP-level investment banker at Morgan Stanley who
builds valuation models for Fortune 500 M&A deals.

Provide a DCF valuation analysis. Format as JSON:
{
    "recommendation": "strong_buy|buy|neutral|sell|strong_sell",
    "confidence": 0-100,
    "summary": "1-2 sentence valuation summary",
    "fair_value": estimated_price,
    "current_price": current_price,
    "upside_downside_pct": percentage,
    "verdict": "undervalued|fairly_valued|overvalued",
    "revenue_projections": {"year1": val, "year2": val, "year3": val, "year4": val, "year5": val},
    "operating_margin": {"current": pct, "projected": pct},
    "wacc": percentage,
    "terminal_growth": percentage,
    "dcf_value": value,
    "sensitivity_table": {"low_wacc": value, "mid_wacc": value, "high_wacc": value},
    "key_assumptions": ["assumption1", "assumption2"]
}"""

        user_prompt = f"""Provide DCF valuation for {ticker}.

Context: {json.dumps(context or {}, indent=2)}

Return analysis as JSON."""

        try:
            response = await self._call_claude(system_prompt, user_prompt)

            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                data = json.loads(response[json_start:json_end]) if json_start >= 0 else {"raw": response}
            except:
                data = {"raw_response": response}

            result = AnalysisResult(
                analysis_type=analysis_type,
                ticker=ticker,
                timestamp=datetime.now(),
                recommendation=data.get("recommendation", "neutral"),
                confidence=float(data.get("confidence", 50)),
                summary=data.get("summary", "DCF analysis completed"),
                data=data,
                cache_key=cache_key,
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )

            self._save_to_cache(result, self.cache_ttl[analysis_type])
            return result

        except Exception as e:
            logger.error(f"DCF analysis failed for {ticker}: {e}")
            return AnalysisResult(
                analysis_type=analysis_type, ticker=ticker, timestamp=datetime.now(),
                recommendation="neutral", confidence=0, summary=f"Error: {e}",
                data={"error": str(e)}, cache_key=cache_key
            )

    async def analyze_risk(self, ticker: str, portfolio: List[Dict] = None, context: Dict = None) -> AnalysisResult:
        """
        Bridgewater-Inspired Risk Analysis Framework

        Analyzes:
        - Correlation analysis
        - Sector concentration
        - Geographic/currency risk
        - Interest rate sensitivity
        - Recession stress test
        - Liquidity risk
        - Tail risk scenarios
        """
        start_time = datetime.now()
        analysis_type = AnalysisType.RISK_ANALYSIS
        cache_key = self._generate_cache_key(analysis_type, ticker, {"portfolio": portfolio, **(context or {})})

        cached = self._check_cache(cache_key)
        if cached:
            return cached

        system_prompt = """You are a senior risk analyst at Bridgewater Associates
trained by Ray Dalio's principles of radical transparency.

Provide risk assessment. Format as JSON:
{
    "recommendation": "reduce_risk|maintain|increase_exposure",
    "confidence": 0-100,
    "summary": "Risk assessment summary",
    "overall_risk_score": 1-10,
    "correlation_risk": {"score": 1-10, "note": "..."},
    "sector_concentration": {"score": 1-10, "sectors": {...}},
    "interest_rate_sensitivity": {"score": 1-10, "impact": "..."},
    "recession_stress_test": {"drawdown_estimate": pct, "recovery_time": "..."},
    "liquidity_risk": {"score": 1-10, "note": "..."},
    "tail_risks": [{"scenario": "...", "probability": pct, "impact": pct}],
    "hedging_recommendations": ["rec1", "rec2"],
    "position_sizing": {"recommended_pct": pct, "max_pct": pct}
}"""

        portfolio_str = json.dumps(portfolio or [], indent=2)
        user_prompt = f"""Analyze risk for {ticker}.

Current portfolio holdings:
{portfolio_str}

Context: {json.dumps(context or {}, indent=2)}

Return risk analysis as JSON."""

        try:
            response = await self._call_claude(system_prompt, user_prompt)

            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                data = json.loads(response[json_start:json_end]) if json_start >= 0 else {"raw": response}
            except:
                data = {"raw_response": response}

            result = AnalysisResult(
                analysis_type=analysis_type,
                ticker=ticker,
                timestamp=datetime.now(),
                recommendation=data.get("recommendation", "maintain"),
                confidence=float(data.get("confidence", 50)),
                summary=data.get("summary", "Risk analysis completed"),
                data=data,
                cache_key=cache_key,
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )

            self._save_to_cache(result, self.cache_ttl[analysis_type])
            return result

        except Exception as e:
            logger.error(f"Risk analysis failed for {ticker}: {e}")
            return AnalysisResult(
                analysis_type=analysis_type, ticker=ticker, timestamp=datetime.now(),
                recommendation="maintain", confidence=0, summary=f"Error: {e}",
                data={"error": str(e)}, cache_key=cache_key
            )

    async def analyze_earnings(self, ticker: str, context: Dict = None) -> AnalysisResult:
        """
        JPMorgan-Level Earnings Breakdown

        Analyzes:
        - Last 4 quarters vs estimates
        - Revenue/EPS consensus
        - Key metrics Wall Street watches
        - Segment breakdown
        - Management guidance
        - Options implied move
        - Bull/bear scenarios
        """
        start_time = datetime.now()
        analysis_type = AnalysisType.EARNINGS_BREAKDOWN
        cache_key = self._generate_cache_key(analysis_type, ticker, context)

        cached = self._check_cache(cache_key)
        if cached:
            return cached

        system_prompt = """You are a senior equity research analyst at JPMorgan Chase
who writes earnings previews for institutional investors.

Provide earnings analysis. Format as JSON:
{
    "recommendation": "buy_before|sell_before|wait",
    "confidence": 0-100,
    "summary": "Earnings outlook summary",
    "last_4_quarters": [{"quarter": "Q1", "eps_actual": val, "eps_est": val, "beat": bool}],
    "next_quarter_estimate": {"revenue": val, "eps": val},
    "key_metrics": ["metric1", "metric2"],
    "segment_breakdown": {"segment1": pct, "segment2": pct},
    "management_guidance": "summary",
    "implied_move": percentage,
    "historical_post_earnings_move": percentage,
    "bull_case": {"scenario": "...", "price_target": val},
    "bear_case": {"scenario": "...", "price_target": val},
    "earnings_date": "date or estimated"
}"""

        user_prompt = f"""Analyze earnings outlook for {ticker}.

Context: {json.dumps(context or {}, indent=2)}

Return earnings analysis as JSON."""

        try:
            response = await self._call_claude(system_prompt, user_prompt)

            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                data = json.loads(response[json_start:json_end]) if json_start >= 0 else {"raw": response}
            except:
                data = {"raw_response": response}

            result = AnalysisResult(
                analysis_type=analysis_type,
                ticker=ticker,
                timestamp=datetime.now(),
                recommendation=data.get("recommendation", "wait"),
                confidence=float(data.get("confidence", 50)),
                summary=data.get("summary", "Earnings analysis completed"),
                data=data,
                cache_key=cache_key,
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )

            self._save_to_cache(result, self.cache_ttl[analysis_type])
            return result

        except Exception as e:
            logger.error(f"Earnings analysis failed for {ticker}: {e}")
            return AnalysisResult(
                analysis_type=analysis_type, ticker=ticker, timestamp=datetime.now(),
                recommendation="wait", confidence=0, summary=f"Error: {e}",
                data={"error": str(e)}, cache_key=cache_key
            )

    async def analyze_patterns(self, ticker: str, context: Dict = None) -> AnalysisResult:
        """
        Renaissance Technologies Pattern Finder

        Analyzes:
        - Seasonal patterns
        - Day-of-week patterns
        - Fed/CPI event correlations
        - Insider buying/selling
        - Institutional ownership trends
        - Short interest / squeeze potential
        - Unusual options activity
        - Post-earnings patterns
        """
        start_time = datetime.now()
        analysis_type = AnalysisType.PATTERN_FINDER
        cache_key = self._generate_cache_key(analysis_type, ticker, context)

        cached = self._check_cache(cache_key)
        if cached:
            return cached

        system_prompt = """You are a quantitative researcher at Renaissance Technologies
using data-driven methods to find statistical edges.

Find hidden patterns. Format as JSON:
{
    "recommendation": "strong_buy|buy|neutral|sell|strong_sell",
    "confidence": 0-100,
    "summary": "Pattern analysis summary",
    "statistical_edge": "description of quantifiable advantage",
    "seasonal_pattern": {"best_months": [...], "worst_months": [...], "effect_size": pct},
    "day_of_week": {"best_days": [...], "worst_days": [...], "significance": pct},
    "event_correlations": [{"event": "Fed meeting", "typical_move": pct}],
    "insider_activity": {"net_buying": bool, "notable_transactions": [...]},
    "institutional_ownership": {"change_3m": pct, "direction": "buying|selling"},
    "short_interest": {"pct_float": pct, "days_to_cover": days, "squeeze_potential": "low|medium|high"},
    "unusual_options": {"detected": bool, "sentiment": "bullish|bearish|mixed"},
    "post_earnings_pattern": {"avg_move": pct, "direction_accuracy": pct}
}"""

        user_prompt = f"""Find statistical patterns for {ticker}.

Context: {json.dumps(context or {}, indent=2)}

Return pattern analysis as JSON."""

        try:
            response = await self._call_claude(system_prompt, user_prompt)

            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                data = json.loads(response[json_start:json_end]) if json_start >= 0 else {"raw": response}
            except:
                data = {"raw_response": response}

            result = AnalysisResult(
                analysis_type=analysis_type,
                ticker=ticker,
                timestamp=datetime.now(),
                recommendation=data.get("recommendation", "neutral"),
                confidence=float(data.get("confidence", 50)),
                summary=data.get("summary", "Pattern analysis completed"),
                data=data,
                cache_key=cache_key,
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )

            self._save_to_cache(result, self.cache_ttl[analysis_type])
            return result

        except Exception as e:
            logger.error(f"Pattern analysis failed for {ticker}: {e}")
            return AnalysisResult(
                analysis_type=analysis_type, ticker=ticker, timestamp=datetime.now(),
                recommendation="neutral", confidence=0, summary=f"Error: {e}",
                data={"error": str(e)}, cache_key=cache_key
            )

    async def analyze_macro(self, ticker: str, context: Dict = None) -> AnalysisResult:
        """
        McKinsey-Level Macro Impact Assessment

        Analyzes:
        - Interest rate impact
        - Inflation effects
        - GDP forecast
        - USD strength impact
        - Fed policy outlook
        - Global risk factors
        - Sector rotation
        """
        start_time = datetime.now()
        analysis_type = AnalysisType.MACRO_IMPACT
        cache_key = self._generate_cache_key(analysis_type, ticker, context)

        cached = self._check_cache(cache_key)
        if cached:
            return cached

        system_prompt = """You are a senior partner at McKinsey's Global Institute
advising sovereign wealth funds on macroeconomic trends.

Provide macro impact analysis. Format as JSON:
{
    "recommendation": "overweight|neutral|underweight",
    "confidence": 0-100,
    "summary": "Macro impact summary",
    "interest_rate_impact": {"direction": "positive|negative|neutral", "magnitude": "high|medium|low"},
    "inflation_impact": {"sectors_benefit": [...], "sectors_hurt": [...]},
    "gdp_outlook": {"forecast": pct, "impact_on_earnings": pct},
    "usd_strength": {"outlook": "strong|weak|stable", "impact": "..."},
    "fed_policy": {"next_move": "hike|cut|hold", "timeline": "...", "probability": pct},
    "global_risks": [{"risk": "...", "probability": pct, "impact": "high|medium|low"}],
    "sector_rotation": {"favored": [...], "avoid": [...]},
    "portfolio_adjustments": ["adjustment1", "adjustment2"],
    "timeline": "when these factors will most likely impact markets"
}"""

        user_prompt = f"""Analyze macro impact on {ticker}.

Context: {json.dumps(context or {}, indent=2)}

Return macro analysis as JSON."""

        try:
            response = await self._call_claude(system_prompt, user_prompt)

            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                data = json.loads(response[json_start:json_end]) if json_start >= 0 else {"raw": response}
            except:
                data = {"raw_response": response}

            result = AnalysisResult(
                analysis_type=analysis_type,
                ticker=ticker,
                timestamp=datetime.now(),
                recommendation=data.get("recommendation", "neutral"),
                confidence=float(data.get("confidence", 50)),
                summary=data.get("summary", "Macro analysis completed"),
                data=data,
                cache_key=cache_key,
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )

            self._save_to_cache(result, self.cache_ttl[analysis_type])
            return result

        except Exception as e:
            logger.error(f"Macro analysis failed for {ticker}: {e}")
            return AnalysisResult(
                analysis_type=analysis_type, ticker=ticker, timestamp=datetime.now(),
                recommendation="neutral", confidence=0, summary=f"Error: {e}",
                data={"error": str(e)}, cache_key=cache_key
            )

    async def analyze_competitive(self, ticker: str, context: Dict = None) -> AnalysisResult:
        """
        Bain-Style Competitive Advantage Analysis

        Analyzes:
        - Top competitors
        - Revenue/margin comparison
        - Competitive moat
        - Market share trends
        - Management quality
        - Innovation/R&D
        - SWOT analysis
        """
        start_time = datetime.now()
        analysis_type = AnalysisType.COMPETITIVE_ADVANTAGE
        cache_key = self._generate_cache_key(analysis_type, ticker, context)

        cached = self._check_cache(cache_key)
        if cached:
            return cached

        system_prompt = """You are a senior partner at Bain & Company conducting
competitive strategy analysis for a major investment fund.

Provide competitive analysis. Format as JSON:
{
    "recommendation": "strong_buy|buy|neutral|sell|strong_sell",
    "confidence": 0-100,
    "summary": "Competitive position summary",
    "moat_rating": "wide|narrow|none",
    "moat_sources": ["source1", "source2"],
    "competitors": [{"name": "...", "market_cap": val, "margin": pct}],
    "market_share": {"current": pct, "trend": "growing|stable|declining"},
    "management_quality": {"score": 1-10, "capital_allocation": "excellent|good|poor"},
    "innovation_score": 1-10,
    "threats": [{"threat": "...", "severity": "high|medium|low"}],
    "swot": {"strengths": [...], "weaknesses": [...], "opportunities": [...], "threats": [...]},
    "best_stock_in_sector": {"ticker": "...", "rationale": "..."},
    "catalysts_12m": ["catalyst1", "catalyst2"]
}"""

        user_prompt = f"""Analyze competitive position of {ticker}.

Context: {json.dumps(context or {}, indent=2)}

Return competitive analysis as JSON."""

        try:
            response = await self._call_claude(system_prompt, user_prompt)

            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                data = json.loads(response[json_start:json_end]) if json_start >= 0 else {"raw": response}
            except:
                data = {"raw_response": response}

            result = AnalysisResult(
                analysis_type=analysis_type,
                ticker=ticker,
                timestamp=datetime.now(),
                recommendation=data.get("recommendation", "neutral"),
                confidence=float(data.get("confidence", 50)),
                summary=data.get("summary", "Competitive analysis completed"),
                data=data,
                cache_key=cache_key,
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )

            self._save_to_cache(result, self.cache_ttl[analysis_type])
            return result

        except Exception as e:
            logger.error(f"Competitive analysis failed for {ticker}: {e}")
            return AnalysisResult(
                analysis_type=analysis_type, ticker=ticker, timestamp=datetime.now(),
                recommendation="neutral", confidence=0, summary=f"Error: {e}",
                data={"error": str(e)}, cache_key=cache_key
            )

    # ==========================================
    # COMPOSITE ANALYSIS
    # ==========================================

    async def run_full_analysis(
        self,
        ticker: str,
        analyses: List[AnalysisType] = None,
        context: Dict = None
    ) -> Dict[str, AnalysisResult]:
        """
        Run multiple analyses in parallel and return combined results.

        Args:
            ticker: Stock/ETF symbol
            analyses: List of analysis types to run (default: all)
            context: Additional context (price, volume, etc.)

        Returns:
            Dict mapping analysis type to result
        """
        if analyses is None:
            # Default to key analyses for trading signals
            analyses = [
                AnalysisType.TECHNICAL_ANALYSIS,
                AnalysisType.PATTERN_FINDER,
                AnalysisType.MACRO_IMPACT,
            ]

        # Map analysis types to methods
        analysis_methods = {
            AnalysisType.TECHNICAL_ANALYSIS: self.analyze_technical,
            AnalysisType.DCF_VALUATION: self.analyze_dcf_valuation,
            AnalysisType.RISK_ANALYSIS: self.analyze_risk,
            AnalysisType.EARNINGS_BREAKDOWN: self.analyze_earnings,
            AnalysisType.PATTERN_FINDER: self.analyze_patterns,
            AnalysisType.MACRO_IMPACT: self.analyze_macro,
            AnalysisType.COMPETITIVE_ADVANTAGE: self.analyze_competitive,
        }

        # Run analyses in parallel
        tasks = []
        for analysis_type in analyses:
            if analysis_type in analysis_methods:
                tasks.append(
                    (analysis_type, analysis_methods[analysis_type](ticker, context))
                )

        results = {}
        for analysis_type, task in tasks:
            try:
                result = await task
                results[analysis_type.value] = result
            except Exception as e:
                logger.error(f"Analysis {analysis_type} failed: {e}")
                results[analysis_type.value] = AnalysisResult(
                    analysis_type=analysis_type,
                    ticker=ticker,
                    timestamp=datetime.now(),
                    recommendation="neutral",
                    confidence=0,
                    summary=f"Error: {e}",
                    data={"error": str(e)},
                    cache_key=""
                )

        return results

    def compute_composite_score(self, results: Dict[str, AnalysisResult]) -> Dict[str, Any]:
        """
        Compute composite conviction score from multiple analyses.

        Returns:
            {
                "composite_recommendation": "strong_buy|buy|neutral|sell|strong_sell",
                "composite_confidence": 0-100,
                "individual_scores": {...},
                "agreement_level": "high|medium|low",
                "signal_strength": 0-100
            }
        """
        if not results:
            return {
                "composite_recommendation": "neutral",
                "composite_confidence": 0,
                "individual_scores": {},
                "agreement_level": "low",
                "signal_strength": 0
            }

        # Convert recommendations to numeric scores
        rec_scores = {
            "strong_buy": 2, "buy": 1, "overweight": 1,
            "neutral": 0, "maintain": 0, "wait": 0,
            "sell": -1, "underweight": -1,
            "strong_sell": -2, "reduce_risk": -1
        }

        scores = []
        confidences = []
        individual_scores = {}

        for analysis_type, result in results.items():
            rec = result.recommendation.lower()
            score = rec_scores.get(rec, 0)
            scores.append(score)
            confidences.append(result.confidence)
            individual_scores[analysis_type] = {
                "recommendation": result.recommendation,
                "confidence": result.confidence,
                "score": score
            }

        # Calculate composite
        avg_score = sum(scores) / len(scores) if scores else 0
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        # Agreement level
        if len(set(s > 0 for s in scores if s != 0)) <= 1:
            agreement = "high"
        elif abs(avg_score) >= 0.5:
            agreement = "medium"
        else:
            agreement = "low"

        # Map back to recommendation
        if avg_score >= 1.5:
            composite_rec = "strong_buy"
        elif avg_score >= 0.5:
            composite_rec = "buy"
        elif avg_score <= -1.5:
            composite_rec = "strong_sell"
        elif avg_score <= -0.5:
            composite_rec = "sell"
        else:
            composite_rec = "neutral"

        # Signal strength (0-100)
        signal_strength = min(100, abs(avg_score) * 50 * (avg_confidence / 100))

        return {
            "composite_recommendation": composite_rec,
            "composite_confidence": avg_confidence,
            "individual_scores": individual_scores,
            "agreement_level": agreement,
            "signal_strength": signal_strength,
            "avg_score": avg_score
        }


# Global instance
ai_strategy_suite = AIStrategySuite()
