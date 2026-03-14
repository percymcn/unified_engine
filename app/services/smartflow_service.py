"""
SmartFlow Indicator Service
===========================

Non-destructive enhancement to TradeFlow that generates signals from FlowAlgo data.
This service:
1. Monitors FlowAlgo flow cache (from flow_confluence_proxy.py)
2. Computes Flow Sentiment Score every 30-60s
3. Generates buy/sell/close signals based on score thresholds
4. Posts signals to user's existing webhook URLs

Scoring Logic:
- Bullish call sweep/block: +1 (>50k), +2 (>100k), +3 (>500k premium)
- Bearish put sweep/block: -1, -2, -3 (same thresholds)
- Sweeps get +0.5 bonus vs blocks
- Net score calculated over 5-minute window

Signal Thresholds:
- Score > +4: Generate 'buy' signal
- Score < -4: Generate 'sell' signal
- Score near zero after extreme: Generate 'close' signal
"""

import asyncio
import json
import logging
import time
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import requests
from sqlalchemy.orm import Session
from app.services.market_data_service import market_data_service
from app.db.database import SessionLocal
from app.models.smartflow_models import SmartFlowConfig, SmartFlowSignalLog, SmartFlowScoreHistory

# AI Strategy Suite integration (optional)
try:
    from app.services.ai_strategy_suite import ai_strategy_suite, AnalysisType
    AI_STRATEGY_AVAILABLE = True
except ImportError:
    AI_STRATEGY_AVAILABLE = False
    ai_strategy_suite = None

logger = logging.getLogger(__name__)

# Fire-and-forget thread pool for webhook posts
_webhook_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="smartflow_webhook")


def _fire_and_forget_webhook_post(api_url: str, payload: dict, webhook_key: str, signal_info: str, timeout: int = 60):
    """
    Post to webhook in background thread - fire and forget.
    Longer timeout (60s) since we're not blocking the main loop.
    """
    try:
        logger.info(f"📤 SmartFlow posting to {api_url}: {json.dumps(payload)[:200]}")
        response = requests.post(
            api_url,
            json=payload,
            timeout=timeout,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code in [200, 202]:
            logger.info(f"✅ SmartFlow webhook SUCCESS: {webhook_key[:12]}... → {signal_info}")
        else:
            logger.warning(f"⚠️ SmartFlow webhook returned {response.status_code}: {response.text[:200]}")
    except requests.exceptions.Timeout:
        logger.error(f"⏱️ SmartFlow webhook timed out after {timeout}s: {webhook_key[:12]}...")
    except Exception as e:
        logger.error(f"❌ SmartFlow webhook error: {webhook_key[:12]}... - {e}")


@dataclass
class FlowEntry:
    """Represents a single FlowAlgo flow entry"""
    timestamp: datetime
    ticker: str
    flow_type: str  # 'sweep' or 'block'
    side: str  # 'bullish' or 'bearish'
    option_type: str  # 'call' or 'put'
    premium: float
    strike: float
    expiry: str


@dataclass
class SentimentScore:
    """Flow sentiment score for a ticker"""
    ticker: str
    score: float
    bullish_flows: int
    bearish_flows: int
    total_premium: float
    timestamp: datetime


@dataclass
class SmartFlowSignal:
    """Generated SmartFlow signal"""
    ticker: str  # Mapped ticker (MES, NQ, GC) or leveraged ETF (SPXL, TQQQ, etc.)
    action: str  # 'buy', 'sell', 'close'
    score: float
    price: Optional[float]
    source: str = 'SmartFlow'
    reason: str = ''  # Signal reasoning (FSS, golden sweeps, etc.)
    lever_etf: Optional[str] = None  # Leveraged ETF if used
    confidence: float = 0.0  # Confidence score (0-100%)
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class SmartFlowService:
    """
    SmartFlow Indicator Service

    Generates trading signals from FlowAlgo options flow data.
    Runs as background task, posts signals to user's webhook URLs.
    """

    def __init__(self):
        self.enabled = False
        self.score_history: Dict[str, List[SentimentScore]] = defaultdict(list)
        self.last_signal: Dict[str, SmartFlowSignal] = {}  # Track last signal per ticker
        self.signal_log: List[SmartFlowSignal] = []  # Recent signals for dashboard
        # Use host.docker.internal or bridge IP for Docker containers, localhost for local dev
        self.flow_cache_url = os.getenv("FLOW_PROXY_URL", "http://172.17.0.1:9001/recent")
        self.webhook_urls: List[str] = []  # User's webhook URLs

        # Configuration (Symmetric thresholds for 50/50 balance)
        self.score_threshold_buy = 5.0  # Symmetric threshold for balanced signals
        self.score_threshold_sell = -5.0  # Symmetric threshold for balanced signals
        self.close_threshold = 1.0  # Close when score returns near zero after extreme
        self.score_window_minutes = 5
        self.update_interval_seconds = 45  # Compute scores every 45s

        # Enhanced toggles
        self.enable_vix_inverse = False
        self.enable_golden_sweeps = False
        self.enable_leveraged_etfs = False
        self.vix_golden_threshold = 100000.0  # VIX golden sweep threshold
        self.min_premium = 50000.0

        # Confirmation filter toggles
        self.enable_price_confirmation = False  # EMA filter
        self.enable_rsi_filter = False
        self.enable_volume_filter = False
        self.enable_time_filter = False
        self.enable_fib_confluence = False
        self.min_confidence_score = 30.0  # Only execute signals >= this %

        # Confirmation filter parameters
        self.rsi_overbought = 70.0
        self.rsi_oversold = 30.0
        self.volume_spike_multiplier = 1.5
        self.time_filter_start_hour = 10  # 10am EST
        self.time_filter_end_hour = 15    # 3pm EST
        self.fade_flow_count = 3  # Number of flows before checking for fade

        # AI Strategy Suite integration
        self.enable_ai_enhancement = False  # Toggle for AI-powered analysis
        self.ai_analysis_types = ['technical', 'patterns']  # Default fast analyses
        self.block_on_ai_disagree = True  # HARD BLOCK signals when AI recommends opposite direction
        self.check_market_trend = True  # Check actual price trend before sending signals
        self.enable_bearish_bias = False  # Solution 3: Reduce buy signals in downtrends, allow more sells

        # AI-Only Mode (24/7 trading without FlowAlgo)
        self.enable_ai_only_mode = False  # Trade using only AI analysis when no flow data
        self.ai_only_scan_interval = 900  # Scan every 15 minutes in AI-only mode (cost optimization: 66% reduction)
        self.ai_only_confidence_threshold = 70.0  # Minimum AI confidence to trade

        # DUPLICATE PREVENTION: Track recent signals to prevent spam
        self.signal_cooldown_seconds = 300  # 5 minutes between same ticker+action signals
        self.recent_signal_cache: Dict[str, datetime] = {}  # key: "ticker:action" -> last_sent_time

        self.ai_only_instruments = [
            # Futures (your most traded)
            'MES', 'NQ', 'RTY', 'MNQ', 'MYM', 'GC', 'MGC',  # Added Gold futures
            # Forex pairs
            'USDJPY', 'GBPJPY', 'EURUSD', 'GBPUSD', 'XAUUSD',  # Added Gold spot
            # Crypto
            'BTCUSD', 'ETHUSD',
            # CFD Indices
            'US30', 'US500', 'USTEC', 'NAS100'
        ]
        self.last_ai_scan_time: Dict[str, datetime] = {}  # Track last AI scan per instrument

        # Ticker mapping (inverse of proxy mapping)
        self.ticker_map = {
            'SPY': 'MES',  # SPY → MES for futures alerts
            'QQQ': 'NQ',   # QQQ → NQ/MNQ
            'GLD': 'GC',   # GLD → GC/MGC
            'IWM': 'RTY',  # IWM → RTY/M2K Russell 2000 futures
            'DIA': 'YM'    # DIA → YM/MYM Dow futures
        }

        # Leveraged ETF mapping (when enable_leveraged_etfs = True)
        self.leveraged_etf_map = {
            'SPY': {'buy': 'SPXL', 'sell': 'SPXU'},  # 3x leveraged SPY
            'QQQ': {'buy': 'TQQQ', 'sell': 'SQQQ'},  # 3x leveraged QQQ
            'IWM': {'buy': 'TNA', 'sell': 'TZA'}     # 3x leveraged IWM
        }

        # VIX tickers (inverse sentiment)
        self.vix_tickers = ['VIX', 'UVXY']

        # Correlated tickers - flows from these contribute to parent ticker sentiment
        # Key is the parent ticker, values are correlated tickers that influence it
        self.correlated_tickers = {
            'SPY': ['SPXL', 'SPXU'],  # 3x leveraged S&P
            'QQQ': ['TQQQ', 'SQQQ', 'NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'],  # Tech + leveraged
            'IWM': ['TNA', 'TZA'],    # 3x leveraged Russell
            'VIX': ['UVXY']           # Leveraged VIX
        }

        # Inverse ETFs - flows with OPPOSITE sentiment contribution
        self.inverse_etfs = ['SQQQ', 'SPXU', 'TZA']

        # Forex/Index CFD to Trading Ticker mapping for overnight trading
        # Data source ticker -> Trading ticker (uses ETF tickers that match existing symbol aliases)
        self.overnight_ticker_map = {
            # Index CFDs -> ETF tickers (symbol aliases will convert to broker format)
            'US30': 'DIA',      # Dow Jones -> DIA (aliases: MYMM6 for ProjectX, US30 for TradeLocker)
            'US500': 'SPY',     # S&P 500 -> SPY (aliases: MES for ProjectX, US500 for TradeLocker)
            'NAS100': 'QQQ',    # Nasdaq 100 -> QQQ (aliases: NQ for ProjectX, NAS100 for TradeLocker)
            'USTEC': 'QQQ',     # Also Nasdaq
            # Forex pairs -> trade directly (MT5/TradeLocker will add .pro suffix via aliases)
            'USDJPY': 'USDJPY',
            'GBPJPY': 'GBPJPY',
            'EURUSD': 'EURUSD',
            'GBPUSD': 'GBPUSD',
            'XAUUSD': 'GLD',    # Gold spot -> GLD (aliases: MGCM6 for ProjectX, XAUUSD for TradeLocker)
            # Crypto -> trade directly
            'BTCUSD': 'BTCUSD',
            'ETHUSD': 'ETHUSD',
        }

        # Polygon ticker format mapping
        # What we call it -> What Polygon needs
        self.polygon_ticker_format = {
            'US30': 'I:DJI',      # Dow Jones Industrial
            'US500': 'I:SPX',     # S&P 500 Index
            'NAS100': 'I:NDX',    # Nasdaq 100 Index
            'USTEC': 'I:NDX',
            'USDJPY': 'C:USDJPY',
            'GBPJPY': 'C:GBPJPY',
            'EURUSD': 'C:EURUSD',
            'GBPUSD': 'C:GBPUSD',
            'XAUUSD': 'C:XAUUSD',
            'BTCUSD': 'X:BTCUSD',
            'ETHUSD': 'X:ETHUSD',
        }

    def is_duplicate_signal(self, ticker: str, action: str) -> bool:
        """
        Check if this signal is a duplicate (same ticker+action within cooldown period).
        This prevents sending multiple identical signals in quick succession.

        IMPORTANT: Uses DATABASE to check for recent signals because in-memory cache
        gets cleared when service restarts (which happens frequently in Docker Swarm).

        Returns True if this is a duplicate that should be skipped.
        """
        cache_key = f"{ticker.upper()}:{action.lower()}"
        # Use EST for all time operations
        from zoneinfo import ZoneInfo
        est = ZoneInfo('America/New_York')
        now = datetime.now(est).replace(tzinfo=None)  # EST without tzinfo for comparison

        # STEP 1: Check in-memory cache first (fastest)
        # Clean up old entries (older than 2x cooldown)
        cleanup_threshold = now - timedelta(seconds=self.signal_cooldown_seconds * 2)
        self.recent_signal_cache = {
            k: v for k, v in self.recent_signal_cache.items()
            if v > cleanup_threshold
        }

        last_sent = self.recent_signal_cache.get(cache_key)
        if last_sent:
            elapsed = (now - last_sent).total_seconds()
            if elapsed < self.signal_cooldown_seconds:
                logger.info(f"⏸️ DUPLICATE (cache): {ticker} {action} sent {elapsed:.0f}s ago - SKIPPING")
                return True

        # STEP 2: Check DATABASE for recent signals (survives restarts)
        # This catches duplicates that would slip through after service restart
        try:
            from app.db.database import SessionLocal
            from app.models.smartflow_models import SmartFlowSignalLog
            db = SessionLocal()
            try:
                # DB stores UTC, so convert cutoff to UTC for query
                utc = ZoneInfo('UTC')
                now_utc = datetime.now(utc).replace(tzinfo=None)
                cutoff_utc = now_utc - timedelta(seconds=self.signal_cooldown_seconds)

                recent_signal = db.query(SmartFlowSignalLog).filter(
                    SmartFlowSignalLog.ticker == ticker.upper(),
                    SmartFlowSignalLog.action == action.lower(),
                    SmartFlowSignalLog.created_at >= cutoff_utc
                ).order_by(SmartFlowSignalLog.created_at.desc()).first()

                if recent_signal:
                    elapsed = (now_utc - recent_signal.created_at).total_seconds()
                    logger.info(f"⏸️ DUPLICATE (DB): {ticker} {action} sent {elapsed:.0f}s ago - SKIPPING")
                    return True
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"DB duplicate check failed: {e} - relying on cache only")

        # Not a duplicate - record this signal in cache
        self.recent_signal_cache[cache_key] = now
        return False

    def enable(self, webhook_urls: List[str]):
        """Enable SmartFlow with user's webhook URLs"""
        self.enabled = True
        self.webhook_urls = webhook_urls
        logger.info(f"✅ SmartFlow enabled with {len(webhook_urls)} webhook(s)")

    def disable(self):
        """Disable SmartFlow"""
        self.enabled = False
        logger.info("SmartFlow disabled")

    async def get_broker_positions(self, ticker: str) -> Dict[str, any]:
        """
        Query actual broker positions for a ticker.

        Returns:
            {
                'has_position': bool,
                'direction': 'long' | 'short' | None,
                'quantity': float,
                'entry_price': float,
                'unrealized_pnl': float
            }
        """
        try:
            # Query positions via internal API
            api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
            api_url = f"{api_base}/api/v1/positions"

            response = requests.get(api_url, timeout=5)
            if response.status_code != 200:
                logger.debug(f"Could not fetch positions: {response.status_code}")
                return {'has_position': False, 'direction': None}

            positions = response.json()

            # Map SmartFlow tickers to broker symbols
            ticker_variants = [ticker]
            # Add futures variants
            if ticker == 'MES':
                ticker_variants.extend(['MESM6', 'MESH6', 'MES1!', 'ES', 'SPY'])
            elif ticker == 'NQ':
                ticker_variants.extend(['MNQM6', 'MNQH6', 'MNQ1!', 'NQ', 'QQQ'])
            elif ticker == 'RTY':
                ticker_variants.extend(['M2KM6', 'M2KH6', 'M2K1!', 'RTY', 'IWM'])
            elif ticker == 'GC':
                ticker_variants.extend(['MGCM6', 'MGCH6', 'MGC1!', 'GC', 'GLD'])

            # Search for matching position
            for pos in positions:
                symbol = pos.get('symbol', '').upper()
                if any(variant.upper() in symbol for variant in ticker_variants):
                    qty = pos.get('quantity', 0) or pos.get('volume', 0)
                    direction = 'long' if qty > 0 else 'short' if qty < 0 else None
                    return {
                        'has_position': True,
                        'direction': direction,
                        'quantity': abs(qty),
                        'entry_price': pos.get('entry_price', 0) or pos.get('open_price', 0),
                        'unrealized_pnl': pos.get('unrealized_pnl', 0) or pos.get('profit', 0)
                    }

            return {'has_position': False, 'direction': None}

        except Exception as e:
            logger.debug(f"Position query failed: {e}")
            return {'has_position': False, 'direction': None}

    async def check_position_before_signal(self, ticker: str, signal_direction: str) -> Tuple[bool, str]:
        """
        Check actual broker position before deciding to send/skip signal.

        Returns:
            (should_send: bool, reason: str)
        """
        position = await self.get_broker_positions(ticker)

        if not position['has_position']:
            # No position - always allow signal
            return True, "no_position"

        current_direction = position['direction']

        if signal_direction == 'buy':
            if current_direction == 'long':
                return False, f"already_long (qty={position['quantity']:.2f}, pnl={position['unrealized_pnl']:.2f})"
            elif current_direction == 'short':
                # Could close short and go long, or just skip
                return True, "reversing_short_to_long"

        elif signal_direction == 'sell':
            if current_direction == 'short':
                return False, f"already_short (qty={position['quantity']:.2f}, pnl={position['unrealized_pnl']:.2f})"
            elif current_direction == 'long':
                return True, "reversing_long_to_short"

        elif signal_direction == 'close':
            if position['has_position']:
                return True, f"closing_{current_direction}_position"
            else:
                return False, "no_position_to_close"

        return True, "allowed"

    def save_signal_to_db(self, signal: 'SmartFlowSignal', sentiment: 'SentimentScore' = None,
                          webhooks_posted: List[str] = None, post_successful: bool = True,
                          post_errors: str = None) -> Optional[int]:
        """
        Save a signal to the database for ML learning.

        Returns the signal_log ID if successful, None otherwise.
        """
        try:
            db = SessionLocal()
            try:
                # Get the first enabled SmartFlow config (assumes single user for now)
                # In future, could track config_id per webhook_url
                config = db.query(SmartFlowConfig).filter(SmartFlowConfig.enabled == True).first()

                if not config:
                    logger.warning("No enabled SmartFlow config found, cannot save signal to DB")
                    return None

                # Create signal log entry
                signal_log = SmartFlowSignalLog(
                    config_id=config.id,
                    ticker=signal.ticker,
                    action=signal.action,
                    score=signal.score,
                    price=signal.price,
                    bullish_flows=sentiment.bullish_flows if sentiment else 0,
                    bearish_flows=sentiment.bearish_flows if sentiment else 0,
                    total_premium=sentiment.total_premium if sentiment else 0.0,
                    confidence=getattr(signal, 'confidence', None),  # AI confidence %
                    reason=getattr(signal, 'reason', None),  # AI reasoning
                    webhooks_posted=webhooks_posted or [],
                    post_successful=post_successful,
                    post_errors=post_errors
                )

                db.add(signal_log)
                db.commit()
                db.refresh(signal_log)

                logger.info(f"📊 Signal saved to DB: id={signal_log.id} {signal.ticker} {signal.action} score={signal.score:.1f}")
                return signal_log.id

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to save signal to DB: {e}")
            return None

    def save_score_history(self, sentiment: 'SentimentScore'):
        """
        Save sentiment score to history table for charting.
        """
        try:
            db = SessionLocal()
            try:
                score_entry = SmartFlowScoreHistory(
                    ticker=sentiment.ticker,
                    score=sentiment.score,
                    bullish_flows=sentiment.bullish_flows,
                    bearish_flows=sentiment.bearish_flows,
                    total_premium=sentiment.total_premium,
                    timestamp=sentiment.timestamp
                )

                db.add(score_entry)
                db.commit()

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to save score history: {e}")

    def record_signal_outcome(
        self,
        signal_log_id: int,
        trade_executed: bool,
        entry_price: float = None,
        exit_price: float = None,
        pnl: float = None,
        time_in_trade: int = None,
        max_favorable: float = None,
        max_adverse: float = None
    ) -> bool:
        """
        Record the outcome of a signal for ML learning.

        This is called when:
        1. A close signal is executed
        2. A stop loss is triggered
        3. Manual position close

        Returns True if outcome was saved successfully.
        """
        try:
            from app.models.smartflow_models import SmartFlowSignalOutcome, SmartFlowSignalLog

            db = SessionLocal()
            try:
                # Verify signal exists
                signal_log = db.query(SmartFlowSignalLog).filter(SmartFlowSignalLog.id == signal_log_id).first()
                if not signal_log:
                    logger.warning(f"Signal log {signal_log_id} not found for outcome recording")
                    return False

                # Check if outcome already exists
                existing = db.query(SmartFlowSignalOutcome).filter(
                    SmartFlowSignalOutcome.signal_log_id == signal_log_id
                ).first()

                if existing:
                    # Update existing outcome
                    existing.trade_executed = trade_executed
                    existing.entry_price = entry_price
                    existing.exit_price = exit_price
                    existing.pnl = pnl
                    existing.is_winner = pnl > 0 if pnl is not None else None
                    existing.pnl_percent = (pnl / entry_price * 100) if pnl and entry_price else None
                    existing.time_in_trade = time_in_trade
                    existing.max_favorable_excursion = max_favorable
                    existing.max_adverse_excursion = max_adverse
                    existing.hour_of_day = datetime.now().hour
                    existing.day_of_week = datetime.now().weekday()
                else:
                    # Create new outcome
                    outcome = SmartFlowSignalOutcome(
                        signal_log_id=signal_log_id,
                        trade_executed=trade_executed,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        pnl=pnl,
                        pnl_percent=(pnl / entry_price * 100) if pnl and entry_price else None,
                        is_winner=pnl > 0 if pnl is not None else None,
                        time_in_trade=time_in_trade,
                        max_favorable_excursion=max_favorable,
                        max_adverse_excursion=max_adverse,
                        hour_of_day=datetime.now().hour,
                        day_of_week=datetime.now().weekday()
                    )
                    db.add(outcome)

                db.commit()

                outcome_type = "WIN" if pnl and pnl > 0 else "LOSS" if pnl and pnl < 0 else "RECORDED"
                logger.info(f"📈 Signal outcome recorded: id={signal_log_id} {outcome_type} pnl={pnl:.2f}" if pnl else f"📈 Signal outcome recorded: id={signal_log_id}")

                return True

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to record signal outcome: {e}")
            return False

    def get_recent_signal_for_ticker(self, ticker: str) -> Optional[int]:
        """
        Get the most recent signal_log_id for a ticker.
        Used when a trade closes to link the outcome back to the signal.
        """
        try:
            db = SessionLocal()
            try:
                from app.models.smartflow_models import SmartFlowSignalLog

                # Map ticker variants
                ticker_variants = [ticker.upper()]
                if ticker.upper() in ['MES', 'MESM6', 'SPY']:
                    ticker_variants = ['MES', 'MESM6', 'SPY', 'ES']
                elif ticker.upper() in ['NQ', 'MNQM6', 'QQQ']:
                    ticker_variants = ['NQ', 'MNQM6', 'QQQ', 'MNQ']
                elif ticker.upper() in ['RTY', 'M2KM6', 'IWM']:
                    ticker_variants = ['RTY', 'M2KM6', 'IWM', 'M2K']

                # Get most recent signal for any variant of this ticker
                signal = db.query(SmartFlowSignalLog).filter(
                    SmartFlowSignalLog.ticker.in_(ticker_variants)
                ).order_by(SmartFlowSignalLog.created_at.desc()).first()

                return signal.id if signal else None

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to get recent signal for {ticker}: {e}")
            return None

    def get_recent_entry_signal_for_ticker(self, ticker: str) -> Optional[int]:
        """
        Get the most recent ENTRY (buy/sell) signal_log_id for a ticker.
        Used when a trade closes to link the outcome back to the entry signal.
        This excludes 'close' signals to ensure we record P&L against entries.
        """
        try:
            db = SessionLocal()
            try:
                from app.models.smartflow_models import SmartFlowSignalLog

                # Map ticker variants (same as get_recent_signal_for_ticker)
                ticker_variants = [ticker.upper()]
                if ticker.upper() in ['MES', 'MESM6', 'SPY']:
                    ticker_variants = ['MES', 'MESM6', 'SPY', 'ES']
                elif ticker.upper() in ['NQ', 'MNQM6', 'QQQ']:
                    ticker_variants = ['NQ', 'MNQM6', 'QQQ', 'MNQ']
                elif ticker.upper() in ['RTY', 'M2KM6', 'IWM']:
                    ticker_variants = ['RTY', 'M2KM6', 'IWM', 'M2K']

                # Get most recent ENTRY signal (buy or sell only, not close)
                signal = db.query(SmartFlowSignalLog).filter(
                    SmartFlowSignalLog.ticker.in_(ticker_variants),
                    SmartFlowSignalLog.action.in_(['buy', 'sell'])  # Exclude 'close'
                ).order_by(SmartFlowSignalLog.created_at.desc()).first()

                return signal.id if signal else None

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to get recent entry signal for {ticker}: {e}")
            return None

    async def fetch_flow_data(self) -> List[FlowEntry]:
        """Fetch recent flow data from FlowAlgo proxy"""
        try:
            response = requests.get(self.flow_cache_url, timeout=5)
            response.raise_for_status()
            data = response.json()

            flows = []
            for entry in data.get('entries', []):
                flows.append(FlowEntry(
                    timestamp=datetime.fromisoformat(entry['timestamp']),
                    ticker=entry['ticker'],
                    flow_type=entry['flow_type'],
                    side=entry['side'],
                    option_type=entry['type'],
                    premium=entry['premium'],
                    strike=entry['strike'],
                    expiry=entry.get('expiry', '')
                ))

            logger.debug(f"Fetched {len(flows)} flow entries from proxy")
            return flows

        except Exception as e:
            logger.error(f"Failed to fetch flow data: {e}")
            return []

    def compute_sentiment_score(self, flows: List[FlowEntry], ticker: str) -> SentimentScore:
        """
        Compute Flow Sentiment Score for a ticker with enhanced logic

        Base Scoring:
        - Bullish call: +1 (>50k), +2 (>100k), +3 (>500k) premium
        - Bearish put: -1, -2, -3 (same thresholds)

        Flow Type Weights:
        - Blocks: *0.5 (institutional hedging, lower conviction)
        - Splits: *1.5 (urgent, breaking into smaller orders)
        - Sweeps: *2 (aggressive, high conviction)

        Golden Sweeps (if enabled):
        - OTM >$1M: +3/-3 bonus
        - Weekly/same-day expiry: +4/-4 bonus (blind-follow boost)
        - Skip monthly IWM/RUT: likely hedging

        Special Cases:
        - NDX (QQQ) / RUT (IWM): Double all weights (whale priority)
        - VIX/UVXY Inverse (if enabled): Flip sentiment
          * Bullish VIX call = bearish market = -score
          * Bearish VIX put = bullish market = +score
        """
        now = datetime.now()
        window_start = now - timedelta(minutes=self.score_window_minutes)

        # Get all tickers to consider (main + correlated)
        tickers_to_check = {ticker}
        if ticker in self.correlated_tickers:
            tickers_to_check.update(self.correlated_tickers[ticker])

        # Filter flows for this ticker and correlated tickers within window
        ticker_flows = [f for f in flows if f.ticker in tickers_to_check and f.timestamp >= window_start]

        score = 0.0
        bullish_count = 0
        bearish_count = 0
        total_premium = 0.0
        is_vix_ticker = ticker in self.vix_tickers

        for flow in ticker_flows:
            total_premium += flow.premium

            # Skip below minimum premium threshold
            if flow.premium < self.min_premium:
                continue

            # Determine base score from premium
            if flow.premium >= 500000:
                base_score = 3.0
            elif flow.premium >= 100000:
                base_score = 2.0
            else:
                base_score = 1.0

            # Apply flow type weights
            if flow.flow_type == 'block':
                flow_multiplier = 0.5  # Low conviction
            elif flow.flow_type == 'split':
                flow_multiplier = 1.5  # Urgent
            elif flow.flow_type == 'sweep':
                flow_multiplier = 2.0  # Aggressive
            else:
                flow_multiplier = 1.0  # Default

            base_score *= flow_multiplier

            # Golden Sweeps (if enabled)
            if self.enable_golden_sweeps:
                # Check for OTM >$1M golden sweep
                if flow.premium >= 1000000 and flow.flow_type == 'sweep':
                    # Add massive bonus for golden sweeps
                    golden_bonus = 3.0

                    # Check expiry for blind-follow boost
                    expiry_lower = flow.expiry.lower()
                    if 'weekly' in expiry_lower or 'same-day' in expiry_lower or 'daily' in expiry_lower:
                        golden_bonus = 4.0  # Blind-follow level
                        logger.info(f"🔥 GOLDEN SWEEP: {ticker} {flow.option_type} ${flow.premium:,.0f} expiry={flow.expiry}")

                    # Skip monthly IWM/RUT (likely hedging, not directional)
                    if ticker in ['IWM', 'RUT'] and 'monthly' in expiry_lower:
                        logger.debug(f"Skipping monthly IWM/RUT golden sweep (likely hedging)")
                        continue

                    base_score += golden_bonus

            # Double weight for NDX (QQQ) and RUT (IWM) - whale priority
            if ticker in ['QQQ', 'IWM', 'RUT', 'NDX']:
                base_score *= 2.0

            # Apply direction
            is_bullish = flow.side == 'bullish' and flow.option_type == 'call'
            is_bearish = flow.side == 'bearish' and flow.option_type == 'put'

            # Inverse ETF handling: bullish SQQQ = bearish QQQ, etc.
            is_inverse_etf = flow.ticker in self.inverse_etfs
            if is_inverse_etf:
                # Flip sentiment for inverse ETFs
                is_bullish, is_bearish = is_bearish, is_bullish
                logger.debug(f"INVERSE ETF: Flipped sentiment for {flow.ticker} flow")

            if is_bullish:
                # VIX inverse logic: bullish VIX = bearish market
                if is_vix_ticker and self.enable_vix_inverse:
                    score -= base_score
                    bearish_count += 1
                    logger.debug(f"VIX INVERSE: Bullish {ticker} call → bearish market signal")
                else:
                    score += base_score
                    bullish_count += 1

            elif is_bearish:
                # VIX inverse logic: bearish VIX = bullish market
                if is_vix_ticker and self.enable_vix_inverse:
                    score += base_score
                    bullish_count += 1
                    logger.debug(f"VIX INVERSE: Bearish {ticker} put → bullish market signal")
                else:
                    score -= base_score
                    bearish_count += 1

        # VIX golden sweep threshold adjustment
        if is_vix_ticker and self.enable_vix_inverse and self.enable_golden_sweeps:
            # Check if we saw a VIX golden sweep (>100k for VIX)
            vix_golden_flows = [f for f in ticker_flows if f.premium >= self.vix_golden_threshold]
            if vix_golden_flows:
                # Adjust sell threshold to -3 for easier triggering
                logger.info(f"VIX golden sweep detected (>${self.vix_golden_threshold:,.0f}), adjusting thresholds")
                # This will be handled in should_generate_signal()

        return SentimentScore(
            ticker=ticker,
            score=score,
            bullish_flows=bullish_count,
            bearish_flows=bearish_count,
            total_premium=total_premium,
            timestamp=now
        )

    async def get_ai_enhancement(
        self,
        ticker: str,
        signal_direction: str,
        context: Dict = None
    ) -> Tuple[float, Dict[str, any]]:
        """
        Get AI Strategy Suite enhancement for a signal.

        Returns:
            (confidence_boost, ai_analysis_summary)
        """
        if not self.enable_ai_enhancement or not AI_STRATEGY_AVAILABLE or not ai_strategy_suite:
            return 0.0, {"ai_enabled": False}

        try:
            # Prepare context for AI analysis
            ai_context = context or {}
            ai_context["signal_direction"] = signal_direction

            # Run fast analyses (technical + patterns)
            analysis_types = []
            for a in self.ai_analysis_types:
                try:
                    analysis_types.append(AnalysisType(a))
                except ValueError:
                    pass

            if not analysis_types:
                analysis_types = [AnalysisType.TECHNICAL_ANALYSIS, AnalysisType.PATTERN_FINDER]

            # Run analyses
            results = await ai_strategy_suite.run_full_analysis(
                ticker,
                analysis_types,
                ai_context
            )

            if not results:
                return 0.0, {"ai_enabled": True, "error": "no_results"}

            # Compute composite score
            composite = ai_strategy_suite.compute_composite_score(results)

            # Calculate confidence boost
            base_boost = 0.0

            # High agreement = more confidence
            if composite["agreement_level"] == "high":
                base_boost = 15.0
            elif composite["agreement_level"] == "medium":
                base_boost = 8.0

            # Check if AI agrees with signal direction
            ai_rec = composite["composite_recommendation"]
            if signal_direction == "buy":
                if ai_rec in ["strong_buy", "buy"]:
                    base_boost += 10.0  # AI agrees
                elif ai_rec in ["strong_sell", "sell"]:
                    base_boost -= 20.0  # AI disagrees - penalize
            elif signal_direction == "sell":
                if ai_rec in ["strong_sell", "sell"]:
                    base_boost += 10.0
                elif ai_rec in ["strong_buy", "buy"]:
                    base_boost -= 20.0

            # Determine if we should BLOCK this signal (AI strongly disagrees)
            ai_disagrees = False
            if signal_direction == "buy" and ai_rec in ["strong_sell", "sell"]:
                ai_disagrees = True
            elif signal_direction == "sell" and ai_rec in ["strong_buy", "buy"]:
                ai_disagrees = True

            # Build summary
            ai_summary = {
                "ai_enabled": True,
                "composite_recommendation": ai_rec,
                "composite_confidence": composite["composite_confidence"],
                "agreement_level": composite["agreement_level"],
                "signal_strength": composite["signal_strength"],
                "confidence_boost": base_boost,
                "analyses_run": list(results.keys()),
                "individual_scores": composite.get("individual_scores", {}),
                "ai_disagrees": ai_disagrees  # Flag for blocking
            }

            logger.info(f"🤖 AI Enhancement for {ticker} {signal_direction}: boost={base_boost:+.1f}% rec={ai_rec} agreement={composite['agreement_level']} disagrees={ai_disagrees}")

            return base_boost, ai_summary

        except Exception as e:
            logger.warning(f"AI enhancement failed for {ticker}: {e}")
            return 0.0, {"ai_enabled": True, "error": str(e)}

    def _check_market_trend_filter(self, ticker: str, signal_direction: str) -> Tuple[bool, str]:
        """
        Check actual market trend using Polygon data.
        Returns (trend_agrees, reason)

        Uses:
        - Price vs EMA (is price above or below trend?)
        - Recent price change (is it moving in signal direction?)
        """
        if not self.check_market_trend:  # Use the toggle attribute
            return True, "trend_check_disabled"

        try:
            # Get market data from Polygon
            market_data = market_data_service.get_ai_context(ticker)

            if not market_data or 'error' in market_data:
                logger.debug(f"No market data for {ticker}, allowing signal")
                return True, "no_market_data"

            price_data = market_data.get('price', {})
            technicals = market_data.get('technicals', {})

            current_price = price_data.get('current', 0)
            change_1h = price_data.get('change_1h', 0)
            ema_trend = technicals.get('ema_trend', 'neutral')
            rsi = technicals.get('rsi_14', 50)

            # ADAPTIVE MULTI-TIMEFRAME TREND DETECTION (Day Trading Optimized)
            # Weight shorter timeframes MORE for day trading
            bearish_score = 0
            bullish_score = 0
            bearish_reasons = []
            bullish_reasons = []

            # Get all timeframe changes
            change_15m = price_data.get('change_15m', 0)
            change_30m = price_data.get('change_30m', 0)
            change_4h = price_data.get('change_4h', 0)
            change_daily = price_data.get('change_daily', 0)

            # 15-minute trend (weight=3, highest priority for day trading)
            if change_15m < -0.1:  # Down >0.1% in 15min
                bearish_score += 3
                bearish_reasons.append(f"15m: {change_15m:.2f}%")
            elif change_15m > 0.1:  # Up >0.1% in 15min
                bullish_score += 3
                bullish_reasons.append(f"15m: +{change_15m:.2f}%")

            # 30-minute trend (weight=2)
            if change_30m < -0.15:  # Down >0.15% in 30min
                bearish_score += 2
                bearish_reasons.append(f"30m: {change_30m:.2f}%")
            elif change_30m > 0.15:  # Up >0.15% in 30min
                bullish_score += 2
                bullish_reasons.append(f"30m: +{change_30m:.2f}%")

            # 1-hour trend (weight=1)
            if change_1h < -0.2:  # Down >0.2% in 1h
                bearish_score += 1
                bearish_reasons.append(f"1h: {change_1h:.2f}%")
            elif change_1h > 0.2:  # Up >0.2% in 1h
                bullish_score += 1
                bullish_reasons.append(f"1h: +{change_1h:.2f}%")

            # EMA trend (weight=1)
            if ema_trend == 'bearish':
                bearish_score += 1
                bearish_reasons.append("EMA bearish")
            elif ema_trend == 'bullish':
                bullish_score += 1
                bullish_reasons.append("EMA bullish")

            # 4-hour trend (weight=0.5, context only for day trading)
            if change_4h < -0.4:  # Down >0.4% over 4h
                bearish_score += 0.5
                bearish_reasons.append(f"4h: {change_4h:.2f}%")
            elif change_4h > 0.4:  # Up >0.4% over 4h
                bullish_score += 0.5
                bullish_reasons.append(f"4h: +{change_4h:.2f}%")

            # Daily trend (weight=0.5, context only)
            if change_daily < -0.6:  # Down >0.6% on day
                bearish_score += 0.5
                bearish_reasons.append(f"daily: {change_daily:.2f}%")
            elif change_daily > 0.6:  # Up >0.6% on day
                bullish_score += 0.5
                bullish_reasons.append(f"daily: +{change_daily:.2f}%")

            # ADAPTIVE LOGIC: Only block if there's STRONG agreement across timeframes
            # This allows catching reversals and counter-trend moves
            if signal_direction == 'buy':
                # Only block BUY if bearish score is VERY strong (6+) = all short-term agrees
                if bearish_score >= 6:
                    reason = f"STRONG BEARISH ({bearish_score:.1f}): {', '.join(bearish_reasons)}"
                    logger.warning(f"🚫 {ticker} BUY blocked - {reason}")
                    return False, reason
            elif signal_direction == 'sell':
                # Only block SELL if bullish score is VERY strong (6+) = all short-term agrees
                if bullish_score >= 6:
                    reason = f"STRONG BULLISH ({bullish_score:.1f}): {', '.join(bullish_reasons)}"
                    logger.warning(f"🚫 {ticker} SELL blocked - {reason}")
                    return False, reason

            return True, "trend_agrees"

        except Exception as e:
            logger.debug(f"Market trend check error for {ticker}: {e}")
            return True, f"trend_check_error: {e}"

    def calculate_confidence_score(
        self,
        sentiment: SentimentScore,
        ticker: str,
        signal_direction: str,
        flows: List[FlowEntry] = None
    ) -> Tuple[float, Dict[str, any]]:
        """
        Calculate confidence score (0-100%) for a signal

        Factors:
        - Base FSS strength: 30%
        - Price confirmation (EMA): 15%
        - RSI filter: 10%
        - Volume spike: 15%
        - Golden sweeps: 10%
        - Fib confluence: 20%

        Returns:
            (confidence_score, details_dict)
        """
        score = 0.0
        details = {
            'fss_strength': 0,
            'price_confirmed': False,
            'rsi_ok': False,
            'volume_spike': False,
            'golden_sweeps': 0,
            'fib_confluent': False
        }

        # 1. Base FSS strength (30 points)
        fss_abs = abs(sentiment.score)
        if fss_abs >= 8:
            score += 30
            details['fss_strength'] = 30
        elif fss_abs >= 6:
            score += 22
            details['fss_strength'] = 22
        elif fss_abs >= 4:
            score += 15
            details['fss_strength'] = 15

        # 2. Price confirmation - EMA alignment (15 points)
        if self.enable_price_confirmation:
            market_data = market_data_service.get_market_data(ticker)
            if market_data:
                current_price = market_data.get('current_price', 0)
                ema_9 = market_data.get('ema_9', 0)
                ema_20 = market_data.get('ema_20', 0)

                if signal_direction == 'buy' and current_price > ema_9 and current_price > ema_20:
                    score += 15
                    details['price_confirmed'] = True
                elif signal_direction == 'sell' and current_price < ema_9 and current_price < ema_20:
                    score += 15
                    details['price_confirmed'] = True
        else:
            # If filter disabled, give benefit of doubt
            score += 15

        # 3. RSI filter (10 points)
        if self.enable_rsi_filter:
            market_data = market_data_service.get_market_data(ticker)
            if market_data:
                rsi = market_data.get('rsi_14', 50)

                if signal_direction == 'buy' and rsi < self.rsi_overbought:
                    score += 10
                    details['rsi_ok'] = True
                elif signal_direction == 'sell' and rsi > self.rsi_oversold:
                    score += 10
                    details['rsi_ok'] = True
        else:
            score += 10

        # 4. Volume spike (15 points)
        if self.enable_volume_filter:
            market_data = market_data_service.get_market_data(ticker)
            if market_data and market_data.get('volume_spike'):
                score += 15
                details['volume_spike'] = True
        else:
            score += 15

        # 5. Golden sweeps (10 points)
        if self.enable_golden_sweeps and flows:
            golden_sweeps = [f for f in flows if f.ticker == ticker and f.premium >= 1000000 and f.flow_type == 'sweep']
            if golden_sweeps:
                score += 10
                details['golden_sweeps'] = len(golden_sweeps)

        # 6. Fibonacci confluence (20 points)
        if self.enable_fib_confluence:
            market_data = market_data_service.get_market_data(ticker)
            if market_data:
                current_price = market_data.get('current_price', 0)
                if current_price > 0:
                    is_confluent, fib_bonus = market_data_service.check_fib_confluence(ticker, current_price, signal_direction)
                    if is_confluent:
                        score += 20
                        details['fib_confluent'] = True
        else:
            # If disabled, don't penalize
            score += 10  # Partial credit

        return min(score, 100.0), details

    def check_time_filter(self) -> bool:
        """
        Check if current time is within trading window (EST timezone)

        Returns:
            True if time is OK, False if should skip
        """
        if not self.enable_time_filter:
            return True

        try:
            from zoneinfo import ZoneInfo
            EST = ZoneInfo("America/New_York")
            now = datetime.now(EST)
        except Exception:
            # Fallback to local time if zoneinfo fails
            now = datetime.now()

        current_hour = now.hour
        current_minute = now.minute

        # Convert start/end to total minutes for easier comparison
        start_minutes = self.time_filter_start_hour * 60 + getattr(self, 'time_filter_start_minute', 0)
        end_minutes = self.time_filter_end_hour * 60 + getattr(self, 'time_filter_end_minute', 0)
        current_minutes = current_hour * 60 + current_minute

        # Also check for weekends (markets closed)
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        if weekday >= 5:  # Saturday or Sunday
            logger.debug(f"Time filter: Weekend - markets closed (day={weekday})")
            return False

        # Check if within allowed window (e.g., 9:30am-3:00pm EST)
        if current_minutes < start_minutes or current_minutes >= end_minutes:
            start_time = f"{self.time_filter_start_hour}:{getattr(self, 'time_filter_start_minute', 0):02d}"
            end_time = f"{self.time_filter_end_hour}:{getattr(self, 'time_filter_end_minute', 0):02d}"
            logger.debug(f"Time filter: Outside trading window ({start_time}-{end_time} EST), current={current_hour}:{current_minute:02d}")
            return False

        return True

    async def should_generate_signal(self, sentiment: SentimentScore, ticker: str, flows: List[FlowEntry] = None) -> Optional[SmartFlowSignal]:
        """
        Determine if a signal should be generated based on sentiment score

        Rules:
        - score > +4: BUY signal (or +5 default)
        - score < -4: SELL signal (or -5 default)
        - score near 0 after extreme: CLOSE signal (fade extreme)

        Now checks ACTUAL broker positions instead of relying on in-memory state.

        Leveraged ETF mapping (if enabled):
        - BUY signal uses bullish leveraged ETF (SPXL, TQQQ, TNA)
        - SELL signal uses bearish leveraged ETF (SPXU, SQQQ, TZA)
        """
        # Determine target ticker
        if self.enable_leveraged_etfs and ticker in self.leveraged_etf_map:
            # Use leveraged ETF based on signal direction (determined below)
            base_ticker = ticker
        else:
            # Use standard futures mapping
            base_ticker = self.ticker_map.get(ticker, ticker)

        last_signal = self.last_signal.get(ticker)

        # Time filter check
        if not self.check_time_filter():
            logger.info(f"⏸️ {ticker}: Skipping signal - outside time filter window (enable_time_filter={self.enable_time_filter})")
            return None

        # Debug: Log threshold values
        logger.info(f"🔍 {ticker}: score={sentiment.score:.1f} thresholds=(buy>{self.score_threshold_buy}, sell<{self.score_threshold_sell}, close<={self.close_threshold})")

        # Prepare signal direction
        signal_direction = None
        if sentiment.score > self.score_threshold_buy:
            signal_direction = 'buy'
        elif sentiment.score < self.score_threshold_sell:
            signal_direction = 'sell'
        elif abs(sentiment.score) <= self.close_threshold:
            signal_direction = 'close'
        else:
            return None

        logger.info(f"📈 {ticker}: score={sentiment.score:.1f} -> potential {signal_direction} signal")

        # Calculate confidence score
        confidence, conf_details = self.calculate_confidence_score(sentiment, ticker, signal_direction, flows)

        # AI Strategy Suite enhancement (if enabled)
        ai_boost = 0.0
        ai_summary = {"ai_enabled": False}
        if self.enable_ai_enhancement and signal_direction in ['buy', 'sell']:
            try:
                ai_context = {
                    "fss_score": sentiment.score,
                    "bullish_flows": sentiment.bullish_flows,
                    "bearish_flows": sentiment.bearish_flows,
                    "total_premium": sentiment.total_premium
                }
                ai_boost, ai_summary = await self.get_ai_enhancement(ticker, signal_direction, ai_context)
                confidence = min(100, max(0, confidence + ai_boost))
                conf_details['ai_enhancement'] = ai_summary

                # HARD BLOCK: If AI disagrees with signal direction, block it entirely
                if self.block_on_ai_disagree and ai_summary.get('ai_disagrees', False):
                    ai_rec = ai_summary.get('composite_recommendation', 'unknown')
                    logger.warning(f"🚫 BLOCKED: {ticker} {signal_direction.upper()} - AI recommends {ai_rec} (opposite direction)")
                    logger.warning(f"   Flow says {signal_direction.upper()} but AI says {ai_rec} - signal blocked to prevent bad trade")
                    return None

            except Exception as e:
                logger.warning(f"AI enhancement error: {e}")

        # Check market trend (is price actually moving in signal direction?)
        if signal_direction in ['buy', 'sell']:
            trend_agrees, trend_reason = self._check_market_trend_filter(ticker, signal_direction)
            if not trend_agrees:
                logger.warning(f"🚫 BLOCKED: {ticker} {signal_direction.upper()} - {trend_reason}")
                return None

        # Check minimum confidence threshold
        if confidence < self.min_confidence_score:
            logger.info(f"❌ Signal rejected: {ticker} {signal_direction} confidence={confidence:.1f}% < {self.min_confidence_score}%")
            return None

        # Prepare signal reason
        reason = f"FSS={sentiment.score:.1f} (bull={sentiment.bullish_flows}, bear={sentiment.bearish_flows})"
        reason += f" | Confidence={confidence:.0f}%"

        if conf_details.get('fib_confluent'):
            reason += " | Fib confluence"
        if conf_details.get('golden_sweeps', 0) > 0:
            reason += f" | {conf_details['golden_sweeps']} golden sweep(s)"
        if conf_details.get('price_confirmed'):
            reason += " | Price✓"
        if conf_details.get('volume_spike'):
            reason += " | Vol spike"
        if ai_summary.get('ai_enabled') and ai_boost != 0:
            reason += f" | AI {ai_summary.get('composite_recommendation', 'N/A')} ({ai_boost:+.0f}%)"

        # Strong bullish signal
        if signal_direction == 'buy':
            # Check actual broker position (preferred) or fallback to in-memory
            should_send, position_reason = await self.check_position_before_signal(base_ticker, 'buy')
            if not should_send:
                # Fallback: also check in-memory state
                if last_signal and last_signal.action == 'buy':
                    logger.info(f"⏸️ {ticker}: Skipping repeat BUY ({position_reason})")
                    return None
                elif 'already_long' in position_reason:
                    logger.info(f"⏸️ {ticker}: Skipping BUY - broker shows {position_reason}")
                    return None

            # Determine target ticker for buy
            if self.enable_leveraged_etfs and ticker in self.leveraged_etf_map:
                target_ticker = self.leveraged_etf_map[ticker]['buy']  # SPXL, TQQQ, TNA
                reason += f" | Leveraged ETF"
            else:
                target_ticker = base_ticker

            logger.info(f"🟢 SmartFlow BUY signal: {ticker} → {target_ticker} score={sentiment.score:.2f} confidence={confidence:.0f}%")
            signal = SmartFlowSignal(
                ticker=target_ticker,
                action='buy',
                score=sentiment.score,
                price=None,  # Will be fetched from broker
                confidence=confidence,
                reason=reason
            )
            self.last_signal[ticker] = signal
            return signal

        # Strong bearish signal
        elif sentiment.score < self.score_threshold_sell:
            # Check actual broker position (preferred) or fallback to in-memory
            should_send, position_reason = await self.check_position_before_signal(base_ticker, 'sell')
            if not should_send:
                # Fallback: also check in-memory state
                if last_signal and last_signal.action == 'sell':
                    logger.info(f"⏸️ {ticker}: Skipping repeat SELL ({position_reason})")
                    return None
                elif 'already_short' in position_reason:
                    logger.info(f"⏸️ {ticker}: Skipping SELL - broker shows {position_reason}")
                    return None

            # Determine target ticker for sell
            if self.enable_leveraged_etfs and ticker in self.leveraged_etf_map:
                target_ticker = self.leveraged_etf_map[ticker]['sell']  # SPXU, SQQQ, TZA
                reason += f" | Leveraged ETF"
            else:
                target_ticker = base_ticker

            logger.info(f"🔴 SmartFlow SELL signal: {ticker} → {target_ticker} score={sentiment.score:.2f} confidence={confidence:.0f}%")
            signal = SmartFlowSignal(
                ticker=target_ticker,
                action='sell',
                score=sentiment.score,
                price=None,
                confidence=confidence,
                reason=reason
            )
            self.last_signal[ticker] = signal
            return signal

        # Close signal (sentiment faded back to neutral after extreme)
        elif abs(sentiment.score) <= self.close_threshold:
            if last_signal and last_signal.action in ('buy', 'sell'):
                # Check if we previously had an extreme position
                if abs(last_signal.score) > max(abs(self.score_threshold_buy), abs(self.score_threshold_sell)):
                    # Close uses the same ticker as the open signal
                    target_ticker = last_signal.ticker

                    logger.info(f"⚪ SmartFlow CLOSE signal: {ticker} → {target_ticker} score faded to {sentiment.score:.2f}")
                    signal = SmartFlowSignal(
                        ticker=target_ticker,
                        action='close',
                        score=sentiment.score,
                        price=None,
                        confidence=confidence,
                        reason=f"FSS faded to {sentiment.score:.1f}"
                    )
                    self.last_signal[ticker] = signal
                    return signal

        return None

    async def post_signal_to_webhooks(self, signal: SmartFlowSignal, sentiment: SentimentScore = None):
        """Post generated signal to user's webhook URLs and save to database

        Supports two formats:
        1. TradingView format (for routing): webhook_key string
        2. Legacy format (for custom webhooks): full http:// URL

        SAFETY CHECKS:
        1. Block 0% confidence signals
        2. Block duplicate signals within cooldown period
        """
        webhooks_posted = []
        post_errors = []
        all_successful = True
        signal_log_id = None  # Initialize for ML tracking

        # SAFETY CHECK 1: Block signals with 0% or very low confidence
        if signal.confidence is not None and signal.confidence < 10:
            logger.warning(f"🚫 BLOCKED: {signal.ticker} {signal.action} - confidence {signal.confidence}% too low (min 10%)")
            return

        # SAFETY CHECK 2: Block duplicate signals (same ticker+action within cooldown)
        if self.is_duplicate_signal(signal.ticker, signal.action):
            logger.info(f"⏸️ SKIPPED: {signal.ticker} {signal.action} - duplicate within cooldown period")
            return

        if not self.webhook_urls:
            logger.warning("No webhook URLs configured for SmartFlow")
            # Still save signal to DB even if no webhooks
            self.save_signal_to_db(signal, sentiment, [], False, "No webhooks configured")
            return

        # Pre-save signal ONCE before posting to webhooks (for ML tracking)
        if signal_log_id is None:
            signal_log_id = self.save_signal_to_db(
                signal=signal,
                sentiment=sentiment,
                webhooks_posted=[],  # Will update after all posts
                post_successful=True,
                post_errors=None
            )
            if signal_log_id:
                logger.info(f"📊 Signal pre-logged with ID {signal_log_id} for ML tracking")

        for webhook_url in self.webhook_urls:
            try:
                # Determine if this is a webhook_key (for routing) or full URL (legacy)
                is_webhook_key = not webhook_url.startswith('http')

                if is_webhook_key:
                    # === TRADINGVIEW-COMPATIBLE FORMAT FOR ROUTING ===
                    # Post to internal /execute endpoint with webhook_key in payload
                    webhook_key = webhook_url.strip()

                    payload = {
                        'webhook_key': webhook_key,
                        'action': signal.action,  # buy, sell, close
                        'symbol': signal.ticker,  # Primary field for routing
                        'ticker': signal.ticker,  # Alias for compatibility
                        'quantity': 0.01,  # Default (will be overridden by account settings)
                        'comment': f"SmartFlow: {signal.reason}",
                        'timestamp': signal.timestamp.isoformat(),
                        # SmartFlow-specific metadata
                        'score': signal.score,
                        'confidence': signal.confidence,
                        'source': 'SmartFlow',
                        'smartflow_signal_log_id': signal_log_id  # Include for ML outcome tracking
                    }

                    # Add leveraged ETF info if used
                    if signal.lever_etf:
                        payload['lever_etf'] = signal.lever_etf

                    # Post to routing endpoint (configurable via env var)
                    # Use API_BASE_URL env var or default to localhost for same-container calls
                    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
                    api_url = f"{api_base}/api/v1/webhook/execute"

                    # Fire-and-forget: submit to thread pool, don't wait for response
                    # This prevents the 10s timeout issue - broker connections can take 15-30s
                    signal_info = f"{signal.action.upper()} {signal.ticker} (FSS={signal.score:.1f}, Conf={signal.confidence:.0f}%)"
                    _webhook_executor.submit(
                        _fire_and_forget_webhook_post,
                        api_url,
                        payload.copy(),  # Copy to avoid mutation
                        webhook_key,
                        signal_info
                    )

                    # Log immediately since we're not waiting
                    logger.info(f"🚀 SmartFlow → webhook_key {webhook_key[:12]}... → {signal_info} (fire-and-forget)")
                    webhooks_posted.append(webhook_key)

                else:
                    # === LEGACY FORMAT FOR CUSTOM WEBHOOKS ===
                    # Pre-save signal to get signal_log_id for outcome tracking
                    # This happens before webhook post so we can include it in payload
                    if signal_log_id is None:
                        signal_log_id = self.save_signal_to_db(
                            signal=signal,
                            sentiment=sentiment,
                            webhooks_posted=[],  # Will update after
                            post_successful=True,
                            post_errors=None
                        )
                        if signal_log_id:
                            logger.info(f"📊 Signal pre-logged with ID {signal_log_id} for ML tracking")

                    payload = {
                        'ticker': signal.ticker,
                        'action': signal.action,
                        'price': signal.price or 0,
                        'source': 'SmartFlow',
                        'score': signal.score,
                        'confidence': signal.confidence,
                        'reason': signal.reason,
                        'timestamp': signal.timestamp.isoformat(),
                        'smartflow_signal_log_id': signal_log_id  # Include for ML outcome tracking
                    }

                    # Add leveraged ETF info if used
                    if signal.lever_etf:
                        payload['lever_etf'] = signal.lever_etf

                    # Fire-and-forget for custom webhooks too
                    signal_info = f"{signal.action.upper()} {signal.ticker} (FSS={signal.score:.1f})"
                    _webhook_executor.submit(
                        _fire_and_forget_webhook_post,
                        webhook_url,
                        payload.copy(),
                        webhook_url[:30],  # Use URL prefix as identifier
                        signal_info
                    )

                    logger.info(f"🚀 SmartFlow signal forwarded to {webhook_url[:50]}... (fire-and-forget, signal_log_id={signal_log_id})")
                    webhooks_posted.append(webhook_url[:50])

            except Exception as e:
                logger.error(f"Failed to post to webhook {webhook_url[:50]}...: {e}")
                post_errors.append(f"{webhook_url[:30]}: {str(e)[:50]}")
                all_successful = False

        # Signal already saved above (pre-save for ML tracking)
        # Just log confirmation
        if signal_log_id:
            logger.info(f"📊 SmartFlow signal {signal_log_id}: {signal.ticker} {signal.action} score={signal.score:.1f}")

        # Store in log for dashboard (in-memory)
        self.signal_log.append(signal)
        if len(self.signal_log) > 100:  # Keep last 100 signals
            self.signal_log.pop(0)

    async def run_ai_only_cycle(self):
        """
        AI-Only Trading Mode - Runs when no FlowAlgo data is available.
        Analyzes configured instruments using AI Strategy Suite and live market data.
        Perfect for overnight/weekend trading of futures, forex, and crypto.

        Uses forex/index CFD data from Polygon to analyze, then converts to
        trading tickers (futures) for signal execution.
        """
        if not AI_STRATEGY_AVAILABLE or not ai_strategy_suite:
            logger.warning("AI Strategy Suite not available for AI-only mode")
            return

        now = datetime.now()
        signals_generated = 0

        for instrument in self.ai_only_instruments:
            try:
                # Rate limit: Don't scan same instrument more than once per interval
                last_scan = self.last_ai_scan_time.get(instrument)
                if last_scan and (now - last_scan).total_seconds() < self.ai_only_scan_interval:
                    continue

                # Get Polygon ticker format for data fetching
                polygon_ticker = self.polygon_ticker_format.get(instrument, instrument)
                # Get trading ticker for signal
                trading_ticker = self.overnight_ticker_map.get(instrument, instrument)

                # Run AI analysis using Polygon ticker
                logger.info(f"🤖 AI-Only: Analyzing {instrument} (data: {polygon_ticker} → trade: {trading_ticker})")

                # Get multi-timeframe analysis for day trading context
                mtf_bias = 'neutral'
                mtf_bullish_pct = 0
                mtf_bearish_pct = 0
                mtf_confluences = []
                try:
                    mtf_analysis = market_data_service.get_multi_timeframe_analysis(polygon_ticker)
                    if mtf_analysis and 'error' not in mtf_analysis:
                        overall = mtf_analysis.get('overall', {})
                        mtf_bias = overall.get('bias', 'neutral')
                        mtf_bullish_pct = overall.get('bullish_alignment', 0)
                        mtf_bearish_pct = overall.get('bearish_alignment', 0)
                        mtf_confluences = mtf_analysis.get('confluences', [])
                        tfs_analyzed = mtf_analysis.get('timeframes', {})
                        logger.info(f"📊 MTF Analysis {polygon_ticker}: {mtf_bias} ({mtf_bullish_pct:.0f}% bull / {mtf_bearish_pct:.0f}% bear) - {len(tfs_analyzed)} TFs")
                except Exception as e:
                    logger.debug(f"MTF analysis failed for {polygon_ticker}: {e}")

                # Run technical and pattern analysis using Polygon ticker
                analyses = []
                for analysis_type in self.ai_analysis_types:
                    try:
                        if analysis_type == 'technical':
                            result = await ai_strategy_suite.analyze_technical(polygon_ticker)
                        elif analysis_type == 'patterns':
                            result = await ai_strategy_suite.analyze_patterns(polygon_ticker)
                        elif analysis_type == 'macro':
                            result = await ai_strategy_suite.analyze_macro(polygon_ticker)
                        else:
                            continue
                        analyses.append(result)
                    except Exception as e:
                        logger.debug(f"AI analysis {analysis_type} failed for {instrument}: {e}")

                if not analyses:
                    continue

                # Update last scan time
                self.last_ai_scan_time[instrument] = now

                # Compute composite recommendation
                buy_votes = 0
                sell_votes = 0
                total_confidence = 0

                for analysis in analyses:
                    rec = analysis.recommendation.lower()
                    conf = analysis.confidence

                    if 'buy' in rec:
                        buy_votes += 1
                        total_confidence += conf
                    elif 'sell' in rec:
                        sell_votes += 1
                        total_confidence += conf

                if buy_votes == 0 and sell_votes == 0:
                    continue  # Neutral - no signal

                avg_confidence = total_confidence / len(analyses) if analyses else 0

                # Only trade if confidence meets threshold
                if avg_confidence < self.ai_only_confidence_threshold:
                    logger.debug(f"🤖 {instrument}: Confidence {avg_confidence:.0f}% < {self.ai_only_confidence_threshold}% threshold")
                    continue

                # Determine action
                if buy_votes > sell_votes:
                    action = 'buy'
                    direction = 'bullish'
                elif sell_votes > buy_votes:
                    action = 'sell'
                    direction = 'bearish'
                else:
                    continue  # Tie - skip

                # Check if we already have an active position (avoid duplicates)
                last_signal = self.last_signal.get(trading_ticker)
                if last_signal and last_signal.action == action:
                    # Same direction - check if recent (within 30 min)
                    if (now - last_signal.timestamp).total_seconds() < 1800:
                        continue

                # Check if MTF bias conflicts with AI direction - require alignment
                mtf_aligned = False
                if direction == 'bullish' and mtf_bias in ['bullish', 'strong_bullish']:
                    mtf_aligned = True
                elif direction == 'bearish' and mtf_bias in ['bearish', 'strong_bearish']:
                    mtf_aligned = True
                elif mtf_bias == 'neutral':
                    mtf_aligned = True  # Neutral doesn't conflict

                # Generate signal with TRADING ticker (not data ticker)
                mtf_str = f"MTF: {mtf_bias} ({mtf_bullish_pct:.0f}%↑/{mtf_bearish_pct:.0f}%↓)"
                confluences_str = f" | {', '.join(mtf_confluences)}" if mtf_confluences else ""
                aligned_str = "✓aligned" if mtf_aligned else "⚠️conflicting"

                signal = SmartFlowSignal(
                    ticker=trading_ticker,  # Use futures/trading ticker
                    action=action,
                    score=avg_confidence,  # Use confidence as score
                    price=None,
                    source='SmartFlow-AI',
                    reason=f"AI-Only: {direction} ({buy_votes}B/{sell_votes}S) {mtf_str} [{aligned_str}]{confluences_str}",
                    confidence=avg_confidence,
                )

                # Store last signal by trading ticker
                self.last_signal[trading_ticker] = signal
                signals_generated += 1

                # Create dummy sentiment for posting
                dummy_sentiment = SentimentScore(
                    ticker=trading_ticker,
                    score=avg_confidence if action == 'buy' else -avg_confidence,
                    bullish_flows=buy_votes,
                    bearish_flows=sell_votes,
                    total_premium=0,
                    timestamp=now
                )

                logger.info(f"🤖 AI-Only {action.upper()}: {trading_ticker} (via {polygon_ticker}) confidence={avg_confidence:.0f}%")
                await self.post_signal_to_webhooks(signal, dummy_sentiment)

            except Exception as e:
                logger.error(f"AI-Only error for {instrument}: {e}")

        if signals_generated > 0:
            logger.info(f"🤖 AI-Only cycle complete: {signals_generated} signals generated")
        else:
            logger.debug("🤖 AI-Only cycle: No signals met threshold")

    async def run_cycle(self):
        """Run one SmartFlow analysis cycle"""
        if not self.enabled:
            return

        try:
            # Fetch fresh flow data
            flows = await self.fetch_flow_data()
            if not flows:
                # No flow data - switch to AI-only mode if enabled
                if self.enable_ai_only_mode and AI_STRATEGY_AVAILABLE:
                    logger.info("📊 SmartFlow: No flow data - running AI-only mode")
                    await self.run_ai_only_cycle()
                else:
                    logger.info("📊 SmartFlow cycle: No flow data available")
                return

            logger.info(f"📊 SmartFlow cycle: Processing {len(flows)} flows")

            # Tracked tickers - base + optional VIX/UVXY
            tracked_tickers = ['SPY', 'QQQ', 'GLD', 'IWM', 'DIA']
            if self.enable_vix_inverse:
                tracked_tickers.extend(['VIX', 'UVXY'])

            # Compute sentiment for each tracked ticker
            scores_summary = []
            for ticker in tracked_tickers:
                sentiment = self.compute_sentiment_score(flows, ticker)

                # Store in history
                self.score_history[ticker].append(sentiment)
                # Keep only last hour of data
                cutoff = datetime.now() - timedelta(hours=1)
                self.score_history[ticker] = [s for s in self.score_history[ticker] if s.timestamp >= cutoff]

                scores_summary.append(f"{ticker}:{sentiment.score:+.1f}")
                logger.debug(f"{ticker} sentiment: {sentiment.score:.2f} (bullish={sentiment.bullish_flows}, bearish={sentiment.bearish_flows})")

                # Save score history to database for charting
                self.save_score_history(sentiment)

                # Check if signal should be generated (pass flows for golden sweep detection)
                signal = await self.should_generate_signal(sentiment, ticker, flows)
                if signal:
                    await self.post_signal_to_webhooks(signal, sentiment)

            # Log summary after all tickers processed
            logger.info(f"📊 SmartFlow scores: {' | '.join(scores_summary)}")

        except Exception as e:
            logger.error(f"SmartFlow cycle error: {e}", exc_info=True)

    async def background_task(self):
        """Background task that runs SmartFlow cycles"""
        logger.info("🤖 SmartFlow background task started")

        while True:
            try:
                if self.enabled:
                    await self.run_cycle()

                # Wait for next cycle
                await asyncio.sleep(self.update_interval_seconds)

            except asyncio.CancelledError:
                logger.info("SmartFlow background task cancelled")
                break
            except Exception as e:
                logger.error(f"SmartFlow background task error: {e}")
                await asyncio.sleep(60)  # Back off on error

    def update_config(self, **kwargs):
        """Update SmartFlow configuration from database model"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.info(f"Updated SmartFlow config: {key}={value}")

    def _format_signal_with_est(self, v) -> dict:
        """Format a signal with EST timestamp"""
        from zoneinfo import ZoneInfo
        utc = ZoneInfo('UTC')
        est = ZoneInfo('America/New_York')
        ts_utc = v.timestamp.replace(tzinfo=utc)
        ts_est = ts_utc.astimezone(est).strftime('%I:%M:%S %p')

        return {
            'ticker': v.ticker,
            'action': v.action,
            'score': v.score,
            'confidence': getattr(v, 'confidence', None),
            'reason': getattr(v, 'reason', None) or (f"Bull={getattr(v, 'bullish_flows', 0)}, Bear={getattr(v, 'bearish_flows', 0)}" if hasattr(v, 'bullish_flows') else None),
            'timestamp': ts_est
        }

    def _get_recent_signals(self) -> list:
        """Get recent signals from memory or database"""
        # If we have signals in memory, use those
        if self.signal_log:
            results = []
            for s in self.signal_log[-20:]:
                confidence = getattr(s, 'confidence', None)
                reason = getattr(s, 'reason', None)

                # For FlowAlgo signals without AI data, build reason from flows
                if reason is None and hasattr(s, 'bullish_flows') and hasattr(s, 'bearish_flows'):
                    reason = f"Bull={s.bullish_flows}, Bear={s.bearish_flows}"

                # Convert timestamp to EST
                from zoneinfo import ZoneInfo
                utc = ZoneInfo('UTC')
                est = ZoneInfo('America/New_York')
                ts_utc = s.timestamp.replace(tzinfo=utc)
                ts_est = ts_utc.astimezone(est)

                results.append({
                    'ticker': s.ticker,
                    'action': s.action,
                    'score': s.score,
                    'confidence': confidence,  # None shows as N/A in UI
                    'reason': reason,          # None shows as "No details" in UI
                    'timestamp': ts_est.strftime('%I:%M:%S %p')  # EST time like "9:33:54 PM"
                })
            return results

        # Otherwise, fetch from database
        try:
            from app.models.smartflow_models import SmartFlowSignalLog
            from app.db.database import SessionLocal

            db = SessionLocal()
            try:
                signals = db.query(SmartFlowSignalLog).order_by(
                    SmartFlowSignalLog.created_at.desc()
                ).limit(20).all()

                from zoneinfo import ZoneInfo
                utc = ZoneInfo('UTC')
                est = ZoneInfo('America/New_York')

                results = []
                for s in signals:
                    ts_est = ''
                    if s.created_at:
                        ts_utc = s.created_at.replace(tzinfo=utc)
                        ts_est = ts_utc.astimezone(est).strftime('%I:%M:%S %p')

                    results.append({
                        'ticker': s.ticker,
                        'action': s.action,
                        'score': s.score,
                        'confidence': s.confidence,
                        'reason': s.reason or f"Bull={s.bullish_flows or 0}, Bear={s.bearish_flows or 0}",
                        'timestamp': ts_est  # EST time like "9:33:54 PM"
                    })
                return results
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Could not fetch signals from DB: {e}")
            return []

    def get_status(self) -> Dict:
        """Get current SmartFlow status for dashboard"""
        latest_scores = {}

        # Base tickers
        tracked_tickers = ['SPY', 'QQQ', 'GLD', 'IWM', 'DIA']
        # Add VIX if enabled
        if self.enable_vix_inverse:
            tracked_tickers.extend(['VIX', 'UVXY'])

        for ticker in tracked_tickers:
            if self.score_history[ticker]:
                latest = self.score_history[ticker][-1]
                # Convert to EST
                from zoneinfo import ZoneInfo
                utc = ZoneInfo('UTC')
                est = ZoneInfo('America/New_York')
                ts_utc = latest.timestamp.replace(tzinfo=utc)
                ts_est = ts_utc.astimezone(est).strftime('%I:%M:%S %p')

                latest_scores[ticker] = {
                    'score': latest.score,
                    'bullish_flows': latest.bullish_flows,
                    'bearish_flows': latest.bearish_flows,
                    'total_premium': latest.total_premium,
                    'timestamp': ts_est  # EST time
                }

        # Check for VIX bearish bias
        vix_bias = None
        if self.enable_vix_inverse and ('VIX' in latest_scores or 'UVXY' in latest_scores):
            vix_score = latest_scores.get('VIX', {}).get('score', 0) or latest_scores.get('UVXY', {}).get('score', 0)
            if vix_score < -2:
                vix_bias = "Bullish market (VIX bearish)"
            elif vix_score > 2:
                vix_bias = "Bearish market (VIX bullish)"

        return {
            'enabled': self.enabled,
            'latest_scores': latest_scores,
            'vix_bias': vix_bias,  # New field for dashboard
            'last_signals': {k: self._format_signal_with_est(v) for k, v in self.last_signal.items()},
            'recent_signals': self._get_recent_signals(),  # Last 20 signals from memory or DB
            'webhook_count': len(self.webhook_urls),
            'update_interval': self.update_interval_seconds,
            # Enhanced toggles
            'enable_vix_inverse': self.enable_vix_inverse,
            'enable_golden_sweeps': self.enable_golden_sweeps,
            'enable_leveraged_etfs': self.enable_leveraged_etfs,
            # Confirmation filter toggles
            'enable_price_confirmation': self.enable_price_confirmation,
            'enable_rsi_filter': self.enable_rsi_filter,
            'enable_volume_filter': self.enable_volume_filter,
            'enable_time_filter': self.enable_time_filter,
            'enable_fib_confluence': self.enable_fib_confluence,
            'min_confidence_score': self.min_confidence_score,
            # AI Strategy Suite
            'enable_ai_enhancement': self.enable_ai_enhancement,
            'ai_analysis_types': self.ai_analysis_types,
            'ai_available': AI_STRATEGY_AVAILABLE
        }


# Global instance
smartflow_service = SmartFlowService()
