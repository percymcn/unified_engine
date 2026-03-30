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
import threading
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import requests
from sqlalchemy.orm import Session
from app.services.market_data_service import market_data_service
from app.db.database import SessionLocal
from app.models.smartflow_models import SmartFlowConfig, SmartFlowSignalLog, SmartFlowScoreHistory

# Deterministic Indicators (NO AI for entries)
try:
    from app.services.indicators import DeterministicIndicators, IndicatorConfig, get_indicator_engine
    DETERMINISTIC_AVAILABLE = True
except ImportError:
    DETERMINISTIC_AVAILABLE = False
    DeterministicIndicators = None
    get_indicator_engine = None

# Trade Journal for forward testing
try:
    from app.services.trade_logger import TradeJournalService, get_trade_journal
    TRADE_JOURNAL_AVAILABLE = True
except ImportError:
    TRADE_JOURNAL_AVAILABLE = False
    TradeJournalService = None
    get_trade_journal = None

# AI Strategy Suite integration (optional)
try:
    from app.services.ai_strategy_suite import ai_strategy_suite, AnalysisType
    AI_STRATEGY_AVAILABLE = True
except ImportError:
    AI_STRATEGY_AVAILABLE = False
    ai_strategy_suite = None

# ========================================
# ELITE QUANT MODULES (2026 Upgrades)
# ========================================

# Regime Detection (ADX + Hurst + Volatility)
# Prefer v2 (GARCH-based) when available, fallback to v1
try:
    from app.services.regime_detector_v2 import get_regime_detector_v2, RegimeDetectorV2, RegimeState
    REGIME_DETECTOR_V2_AVAILABLE = True
    get_regime_detector = get_regime_detector_v2
    RegimeDetector = RegimeDetectorV2
    MarketRegime = RegimeState
    REGIME_DETECTOR_AVAILABLE = True
except ImportError:
    REGIME_DETECTOR_V2_AVAILABLE = False
    try:
        from app.services.regime_detector import get_regime_detector, RegimeDetector, MarketRegime
        REGIME_DETECTOR_AVAILABLE = True
    except ImportError:
        REGIME_DETECTOR_AVAILABLE = False
        get_regime_detector = None
        RegimeDetector = None
        MarketRegime = None

# Ensemble Meta-Model Scorer
try:
    from app.services.ensemble_scorer import get_ensemble_scorer, EnsembleScorer, SignalInput, SignalSource
    ENSEMBLE_SCORER_AVAILABLE = True
except ImportError:
    ENSEMBLE_SCORER_AVAILABLE = False
    get_ensemble_scorer = None
    EnsembleScorer = None
    SignalInput = None
    SignalSource = None

# Elite Risk Manager (Kelly + VaR)
try:
    from app.services.risk_manager import get_risk_manager, RiskManager
    RISK_MANAGER_AVAILABLE = True
except ImportError:
    RISK_MANAGER_AVAILABLE = False
    get_risk_manager = None
    RiskManager = None

# Adaptive Learning & Drift Detection
try:
    from app.services.adaptive_learning import get_adaptive_manager, AdaptiveLearningManager
    ADAPTIVE_LEARNING_AVAILABLE = True
except ImportError:
    ADAPTIVE_LEARNING_AVAILABLE = False
    get_adaptive_manager = None
    AdaptiveLearningManager = None

# Unusual Whales Premium Flow Data
try:
    from app.services.unusual_whales_service import get_unusual_whales_service, UnusualWhalesService, FlowSentiment
    UNUSUAL_WHALES_AVAILABLE = True
except ImportError:
    UNUSUAL_WHALES_AVAILABLE = False
    get_unusual_whales_service = None
    UnusualWhalesService = None
    FlowSentiment = None

# Microstructure Analysis (Order book, VPIN)
try:
    from app.services.microstructure_analyzer import get_microstructure_analyzer, MicrostructureSignal
    MICROSTRUCTURE_AVAILABLE = True
except ImportError:
    MICROSTRUCTURE_AVAILABLE = False
    get_microstructure_analyzer = None
    MicrostructureSignal = None

# Crypto Funding Rate Service
try:
    from app.services.crypto_funding_service import get_crypto_funding_service, CryptoFundingAnalysis
    CRYPTO_FUNDING_AVAILABLE = True
except ImportError:
    CRYPTO_FUNDING_AVAILABLE = False
    get_crypto_funding_service = None
    CryptoFundingAnalysis = None

# OpenClaw AI Enhancement (Signal Quality Validation)
try:
    from app.services.openclaw_client import get_openclaw_client, OpenClawClient
    from app.services.rsi_calculator import get_rsi_calculator, RSICalculator
    OPENCLAW_AVAILABLE = True
except ImportError:
    OPENCLAW_AVAILABLE = False
    get_openclaw_client = None
    OpenClawClient = None
    get_rsi_calculator = None
    RSICalculator = None

# Key Levels & Confluence Service (NEW)
try:
    from app.services.levels_service import (
        get_levels_service, get_news_sentiment,
        LevelsService, FibonacciLevels, DailyLevels, ConfluenceResult
    )
    LEVELS_SERVICE_AVAILABLE = True
except ImportError:
    LEVELS_SERVICE_AVAILABLE = False
    get_levels_service = None
    get_news_sentiment = None
    LevelsService = None
    FibonacciLevels = None
    DailyLevels = None
    ConfluenceResult = None

# VWAP Service (NEW)
try:
    from app.services.vwap_service import (
        VWAPService, VWAPConfig, VWAPResult, VWAPBias,
        VWAPConfluence, get_vwap_features_for_ensemble
    )
    VWAP_SERVICE_AVAILABLE = True
except ImportError:
    VWAP_SERVICE_AVAILABLE = False
    VWAPService = None
    VWAPConfig = None
    VWAPResult = None
    VWAPBias = None
    VWAPConfluence = None
    get_vwap_features_for_ensemble = None


# LuxAlgo Native Indicator Engine (5 ported indicators)
try:
    from app.services.luxalgo_engine import get_luxalgo_engine, LuxAlgoEngine
    LUXALGO_AVAILABLE = True
except ImportError:
    LUXALGO_AVAILABLE = False
    get_luxalgo_engine = None
    LuxAlgoEngine = None

logger = logging.getLogger(__name__)

# --- LuxAlgo background cache (avoids 1-2s blocking on every signal eval) ---
_luxalgo_cache = {'results': None, 'timestamp': None}
_cache_lock = threading.Lock()


def _refresh_luxalgo_cache():
    """Refresh LuxAlgo results in a background daemon thread."""
    try:
        engine = get_luxalgo_engine()
        results = engine.run_once()
        with _cache_lock:
            _luxalgo_cache['results'] = results
            _luxalgo_cache['timestamp'] = datetime.utcnow()
    except Exception as e:
        logger.warning(f"LuxAlgo cache refresh failed: {e}")


def get_luxalgo_boost(direction: str, symbol: str) -> float:
    """Return LuxAlgo confidence boost fraction (0.0-0.15) without blocking."""
    with _cache_lock:
        cache = _luxalgo_cache.copy()
    # Trigger background refresh if stale (>60s) or never populated
    if cache["timestamp"] is None or \
            (datetime.utcnow() - cache["timestamp"]).total_seconds() > 60:
        threading.Thread(target=_refresh_luxalgo_cache, daemon=True).start()
        return 0.0   # non-blocking: return 0 until cache is warm
    # Use cached results to compute boost
    if cache["results"]:
        agreeing = sum(
            1 for r in cache["results"].values()
            if r.get("signal") == direction and r.get("confidence", 0) >= 0.65
        )
        return min(0.15, agreeing * 0.05)  # +5% per agreeing indicator, max +15%
    return 0.0
# ---------------------------------------------------------------------------


# Fire-and-forget thread pool for webhook posts
_webhook_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="smartflow_webhook")


def _fire_and_forget_webhook_post(api_url: str, payload: dict, webhook_key: str, signal_info: str, timeout: int = 120):
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
        self.score_threshold_buy = 3.0  # TUNED: Lowered from 4.0 to generate more signals
        self.score_threshold_sell = -3.0  # TUNED: Lowered from -4.0 to generate more signals
        self.close_threshold = 1.0  # Close when score returns near zero after extreme
        self.score_window_minutes = 10  # TUNED: Widened from 5 to catch more flow
        self.update_interval_seconds = 45  # Compute scores every 45s
        self.per_ticker_delay_seconds = 5  # Prevent CPU spikes during per-ticker scans

        # Enhanced toggles
        self.enable_vix_inverse = False
        self.enable_golden_sweeps = False
        self.enable_leveraged_etfs = False
        self.vix_golden_threshold = 100000.0  # VIX golden sweep threshold
        self.min_premium = 20000.0  # TUNED: Lowered from 30k to catch more opportunities

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
        self.enable_ai_only_mode = True  # Trade using only AI analysis when no flow data (crypto, forex, overnight futures)
        self.ai_only_scan_interval = 900  # Scan every 15 minutes in AI-only mode (cost optimization: 66% reduction)
        self.ai_only_confidence_threshold = 70.0  # Minimum AI confidence to trade

        # DUPLICATE PREVENTION: Track recent signals to prevent spam
        self.signal_cooldown_seconds = 300  # 5 minutes between same ticker+action signals
        self.recent_signal_cache: Dict[str, datetime] = {}  # key: "ticker:action" -> last_sent_time

        self.ai_only_instruments = [
            # Futures (primary paper trading)
            'MES', 'MNQ', 'NQ', 'RTY', 'MYM', 'GC', 'MGC',  # Includes MNQ
            # CFD Indices
            'US30', 'US500', 'USTEC', 'NAS100',  # US30 = Dow CFD
            # Forex pairs
            'USDJPY', 'GBPJPY', 'EURUSD', 'GBPUSD', 'XAUUSD',
            # Crypto
            'BTCUSD', 'ETHUSD',
        ]
        self.last_ai_scan_time: Dict[str, datetime] = {}  # Track last AI scan per instrument

        # ========================================
        # DETERMINISTIC MODE (NO AI for entries)
        # ========================================
        # Uses real multi-timeframe indicators: EMA9/21, RSI14, MACD, ATR14
        # Entry rules: >=4/5 TFs aligned, confidence >=75%, R:R configurable
        self.enable_deterministic_mode = True  # Uses background thread for data fetching
        self.deterministic_scan_interval = 300  # Scan every 5 minutes (saves resources)
        self.deterministic_min_confidence = 75.0  # Minimum confidence score
        self.deterministic_min_aligned_tfs = 4  # Min TFs aligned (out of 5)
        self.deterministic_require_higher_tf = True  # 1h and 4h must agree
        self.last_deterministic_scan: Dict[str, datetime] = {}  # Track last scan per ticker

        # R:R Configuration (tune for backtesting: 1.5, 2.0, 3.0)
        self.deterministic_min_rr = 3.0  # OPTIMAL: 1:3 R:R (risk 1 to make 3)
        self.deterministic_rr_presets = {
            'aggressive': {'stop_mult': 1.0, 'target_mult': 1.5, 'min_rr': 1.5},  # Tighter stops, more trades
            'balanced': {'stop_mult': 1.5, 'target_mult': 3.0, 'min_rr': 2.0},    # Default ATR-based
            'conservative': {'stop_mult': 2.0, 'target_mult': 6.0, 'min_rr': 3.0}, # Wider stops, fewer trades
            'pct_optimal': {'pct_stop': 0.2, 'pct_target': 0.6, 'min_rr': 3.0},   # OPTIMAL: 0.2% SL, 0.6% TP
        }
        self.deterministic_rr_preset = 'pct_optimal'  # CHANGED: Use PCT-based (PF 1.41, Sharpe 2.02)

        # Percentage-based stops (backtest winner: PF 1.41, Sharpe 2.02, MaxDD 4.68%)
        self.use_pct_stops = True  # ENABLED: Use % stops instead of ATR
        self.pct_stop_loss = 0.2   # 0.2% stop loss
        self.pct_take_profit = 0.6 # 0.6% take profit (1:3 R:R)

        # Deterministic instruments (same as AI-only but for indicator-based trading)
        self.deterministic_instruments = [
            # Futures (via SPY, QQQ, IWM, GLD, DIA data)
            'MES', 'NQ', 'MNQ', 'RTY', 'GC', 'MYM',
            # CFD Indices
            'US30', 'US500', 'USTEC', 'NAS100',
            # Forex pairs
            'USDJPY', 'GBPJPY',
            # Crypto (direct Polygon data)
            'BTCUSD', 'ETHUSD',
        ]

        # Trade journaling (forward testing)
        self.enable_trade_journal = True  # Log all signals for backtesting

        # ========================================
        # QUICK MODE (5-minute momentum scalping)
        # ========================================
        # Fast signals based on 5m timeframe only - momentum focused
        # Entry rules: EMA9/21 crossover + RSI momentum + optional 15m confirmation
        # Higher frequency, more trades, faster entry/exit
        self.enable_quick_mode = True  # Toggle for quick mode (can run alongside deterministic)
        self.quick_scan_interval = 60  # Scan every 1 minute for quick entries
        self.quick_min_confidence = 60.0  # Lower confidence threshold (momentum > confirmation)
        self.quick_require_15m_confirmation = True  # Optional 15m trend filter
        self.last_quick_scan: Dict[str, datetime] = {}  # Track last scan per ticker

        # Quick mode signal criteria
        self.quick_ema_crossover_bars = 3  # EMA cross within last 3 bars (fresh cross)
        self.quick_rsi_momentum_threshold = 55  # RSI > 55 for bullish momentum (< 45 for bearish)
        self.quick_min_rr = 1.5  # Lower R:R for quick trades (scalping)
        self.quick_atr_stop_multiplier = 1.0  # Tighter stops for quick mode
        self.quick_atr_target_multiplier = 1.5  # Quick targets
        self.quick_require_volume = True  # REQUIRE volume confirmation (>1.2x avg)
        self.quick_min_volume_ratio = 1.2  # Minimum relative volume for Quick Mode signals

        # Quick mode instruments (same as deterministic)
        self.quick_instruments = [
            # Futures
            'MES', 'NQ', 'MNQ', 'RTY', 'GC', 'MYM',
            # CFD Indices
            'US30', 'US500', 'USTEC', 'NAS100',
            # Forex pairs
            'USDJPY', 'GBPJPY',
            # Crypto
            'BTCUSD', 'ETHUSD',
        ]

        # ========================================
        # STRATEGY PERFORMANCE TRACKING
        # ========================================
        # Track performance per strategy for A/B comparison
        self.strategy_stats: Dict[str, Dict] = {
            'deterministic': {
                'signals_generated': 0,
                'trades_won': 0,
                'trades_lost': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'avg_rr_achieved': 0.0,
                'last_signal_time': None,
            },
            'quick_5m': {
                'signals_generated': 0,
                'trades_won': 0,
                'trades_lost': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'avg_rr_achieved': 0.0,
                'last_signal_time': None,
            }
        }

        # ========================================
        # MTF ANALYSIS STORAGE (for UI dashboard)
        # ========================================
        # Stores latest multi-timeframe analysis per instrument for UI display
        self.latest_mtf_analysis: Dict[str, Dict] = {}  # {instrument: {tf: analysis}}
        self.recent_signal_log: List[Dict] = []  # Last 50 signals for UI display
        self.max_recent_signals = 50

        # ========================================
        # KEY LEVELS & CONFLUENCE (NEW)
        # ========================================
        self.enable_levels_confluence = LEVELS_SERVICE_AVAILABLE  # Use key levels if available
        self.levels_confluence_min_deterministic = 65.0  # Min confluence for deterministic signals
        self.levels_confluence_min_quick = 55.0          # Min confluence for quick mode signals
        self.levels_cache: Dict[str, Any] = {}           # Cache levels per instrument
        self.levels_cache_ttl_minutes = 60               # Cache TTL

        # Fibonacci levels
        self.use_fib_targets = True                      # Use Fib extensions as targets
        self.fib_target_levels = ['1.272', '1.618']      # Which Fib extensions to use

        # ========================================
        # REGIME-ASYMMETRIC LOGIC (NEW)
        # ========================================
        # Different requirements for longs vs shorts based on regime
        self.enable_regime_asymmetric = True

        # Trending Up: Stricter requirements for longs
        self.uptrend_flow_require = 'MEDIUM'             # TUNED: Lowered from HIGH to allow more long entries
        self.uptrend_fib_extensions = True               # Use Fib extensions as targets
        self.uptrend_imbalance_min = 0.35                # TUNED: Lowered from 0.45 to catch more opportunities
        self.uptrend_rr_min = 3.0                        # TUNED: Lowered from 4.0 for better entry timing
        self.uptrend_target_pct = 0.8                    # 0.8% target (from 0.2% risk = 1:4)
        self.uptrend_ensemble_min_probability = 0.66     # Override base 0.62 in trending_up

        # Trending Down: PDH/PDL magnets for shorts
        self.downtrend_flow_require = 'MEDIUM'           # MEDIUM+ flow for shorts in downtrend
        self.downtrend_pdh_pdl_targets = True            # Use PDH/PDL as targets
        self.downtrend_rr_min = 3.0                      # 1:3 R:R in downtrend

        # ========================================
        # TRAILING STOP CONFIGURATION (ENHANCED)
        # ========================================
        self.enable_trailing_stop = True
        self.trailing_breakeven_trigger = 2.0            # Move to breakeven after 2x risk
        self.trailing_partial_exit_trigger = 3.0         # Partial exit at 3x risk
        self.trailing_partial_exit_pct = 50.0            # Exit 50% at partial
        self.trailing_atr_multiplier = 1.0               # Trail with 1x ATR
        self.trailing_positions: Dict[str, Dict] = {}    # Track trailing positions
        # VWAP/EMA21 trailing (NEW)
        self.trailing_to_vwap = True                     # Trail to VWAP after 2x
        self.trailing_to_ema21 = True                    # Also consider EMA21
        self.trailing_vwap_buffer_pct = 0.1              # 0.1% buffer below VWAP for longs
        self.trailing_partial_at_3x = True               # Close 50% at 3x risk
        self.trailing_remainder_to_vwap = True           # Trail remainder to VWAP - buffer
        # VWAP Band Trailing (1σ/2σ)
        self.vwap_band_trailing = True                   # Use VWAP bands for trailing
        self.vwap_sigma_buffer = 1.0                     # Trail to VWAP - 1σ in trending
        self.vwap_mean_revert_target_sigma = 1.0         # Target 1σ band in mean-reverting
        self.vwap_mean_revert_stop_sigma = 2.0           # Stop at 2σ in mean-reverting

        # ========================================
        # NEWS SENTIMENT (ENHANCED)
        # ========================================
        self.enable_news_sentiment = True
        self.news_sentiment_boost_min = 0.08             # Min +8% probability boost
        self.news_sentiment_boost_max = 0.12             # Max +12% probability boost
        self.news_sentiment_threshold = 0.5              # Min sentiment score for boost
        self.news_sentiment_flow_require = 'MEDIUM'      # Min flow for news boost
        self.news_sentiment_cache: Dict[str, Any] = {}   # Cache news sentiment
        self.news_sentiment_cache_ttl_minutes = 60       # Cache hourly

        # ========================================
        # VWAP CONFLUENCE (NEW)
        # ========================================
        self.enable_vwap_confluence = True               # Use VWAP for confluence
        self.vwap_distance_threshold_pct = 0.5           # Max distance for confluence (0.5%)
        self.vwap_confluence_boost = 0.12                # +12% probability boost
        self.vwap_tight_distance_pct = 0.3               # Tight distance for extra boost
        self.vwap_tight_boost = 0.15                     # +15% boost when tight
        self.vwap_mean_reversion_boost = 0.18            # +18% for mean-reversion near VWAP
        self.vwap_min_bias_for_long = 0.4                # Min bias for long in trending up
        self.vwap_trailing_enabled = True                # Use VWAP for trailing reference
        self.vwap_cache: Dict[str, Any] = {}             # Cache VWAP per instrument
        self.vwap_cache_ttl_minutes = 1                  # Cache TTL (update frequently)

        # ========================================
        # PROJECTX REALTIME DATA (NEW)
        # ========================================
        self.use_projectx_realtime = True                # Use ProjectX for realtime data
        self.projectx_symbols = [
            'MES', 'MNQ', 'NQ', 'RTY', 'GC', 'MYM', 'YM', 'MGC'
        ]

        # ========================================
        # FLOW CONFIRMATION (Unusual Whales Premium)
        # ========================================
        # Enable REAL flow confirmation with Unusual Whales API
        self.use_flow_confirmation = True  # ENABLED: Require UW flow confirmation for signals
        self.use_polygon_options_flow = False  # Disabled - using UW instead
        self.use_flowalgo_flow = False  # Not using FlowAlgo
        self.use_unusual_whales_flow = True  # ENABLED: Use Unusual Whales premium flow data
        self.min_flow_conviction = "MEDIUM"  # Require MEDIUM, HIGH, or EXTREME conviction
        self.flow_conviction_prob_boost = 0.10  # Add 10% prob for HIGH/EXTREME conviction

        # ========================================
        # LATENCY TRACKING
        # ========================================
        self.latency_history: List[Dict] = []  # Track signal-to-webhook latency
        self.latency_target_ms = 2000  # Target <2s end-to-end

        # ========================================
        # DATA FRESHNESS & SIGNAL EXPIRY
        # ========================================
        self.data_freshness_threshold_sec = 300  # Data older than 5min = stale
        self.signal_ttl_minutes = 10  # Signals expire after 10 minutes (critical for quant)
        self.enable_stale_data_alerts = True  # Log warnings when using stale/mock data
        self.last_data_freshness: Dict[str, str] = {}  # Track freshness per instrument: 'fresh', 'stale', 'mock'
        self.stale_data_signals_blocked = 0  # Count of signals blocked due to stale data

        # ========================================
        # ELITE QUANT MODULE INTEGRATION
        # ========================================
        self.enable_regime_detection = REGIME_DETECTOR_AVAILABLE  # Use regime detector if available
        self.enable_ensemble_scoring = ENSEMBLE_SCORER_AVAILABLE  # Use ensemble if available
        self.enable_risk_manager = RISK_MANAGER_AVAILABLE  # Use risk manager if available
        self.ensemble_min_probability = 62.0  # LOWERED: 62% gate (was 68%) - match forward test stability
        self.current_regime: Dict[str, str] = {}  # Cache regime per instrument

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

    async def check_flow_conviction(self, ticker: str, direction: str, sentiment: SentimentScore) -> Tuple[bool, str, float]:
        """
        Check flow conviction using the SAME sentiment data that generated the signal.

        CRITICAL FIX: Previously queried Unusual Whales API separately, which created
        a data mismatch - SmartFlow score calculated from aggregated flows could be
        bullish while UW query returned bearish, causing contradictory blocks.

        Now uses the sentiment object that was already computed from the same flows.

        Args:
            ticker: Stock/ETF ticker (SPY, QQQ, etc.)
            direction: 'buy' or 'sell'
            sentiment: SentimentScore object from compute_sentiment_score

        Returns:
            (passes, reason, prob_boost)
            - passes: True if flow confirms direction
            - reason: Explanation string
            - prob_boost: Probability boost to apply (0.0 to 0.15)
        """
        if not self.use_flow_confirmation:
            return True, "Flow confirmation disabled", 0.0

        # Use the sentiment that was ALREADY calculated from the same flows
        bullish_count = sentiment.bullish_flows
        bearish_count = sentiment.bearish_flows
        total_flows = bullish_count + bearish_count

        if total_flows == 0:
            return True, "No flows to analyze", 0.0

        # Calculate flow agreement percentage
        if direction == 'buy':
            agreement_pct = (bullish_count / total_flows) * 100 if total_flows > 0 else 0
            flow_direction = "bullish" if bullish_count > bearish_count else "bearish"
        else:  # sell
            agreement_pct = (bearish_count / total_flows) * 100 if total_flows > 0 else 0
            flow_direction = "bearish" if bearish_count > bullish_count else "bullish"

        # Determine conviction level from agreement percentage
        conviction = "LOW"
        if agreement_pct >= 80:
            conviction = "EXTREME"
        elif agreement_pct >= 65:
            conviction = "HIGH"
        elif agreement_pct >= 55:
            conviction = "MEDIUM"

        # Check if flow direction matches signal direction
        signal_flow_match = (
            (direction == 'buy' and bullish_count > bearish_count) or
            (direction == 'sell' and bearish_count > bullish_count)
        )

        # Conviction level check
        conviction_levels = ["LOW", "MEDIUM", "HIGH", "EXTREME"]
        min_conviction_idx = conviction_levels.index(self.min_flow_conviction)
        current_conviction_idx = conviction_levels.index(conviction)

        if current_conviction_idx < min_conviction_idx:
            return False, f"Low flow conviction ({conviction} < {self.min_flow_conviction}, {agreement_pct:.0f}% agreement)", 0.0

        # CRITICAL: Only block if conviction is HIGH/EXTREME AND direction mismatches
        # This prevents blocking signals that the system itself generated
        if not signal_flow_match and conviction in ["HIGH", "EXTREME"]:
            return False, f"Flow {flow_direction} contradicts {direction} ({conviction} conviction, {agreement_pct:.0f}% agreement)", 0.0

        # Calculate probability boost based on agreement
        prob_boost = 0.0
        if signal_flow_match:
            if conviction == "EXTREME":
                prob_boost = 0.15
            elif conviction == "HIGH":
                prob_boost = 0.10
            elif conviction == "MEDIUM":
                prob_boost = 0.05

        reason = f"Flow: {bullish_count}B/{bearish_count}B ({conviction}, {agreement_pct:.0f}% {direction})"
        return True, reason, prob_boost

    async def check_microstructure_filter(self, ticker: str, direction: str) -> Tuple[bool, str]:
        """
        Check microstructure (order book imbalance, VPIN) for signal confirmation.

        Args:
            ticker: Stock/ETF ticker
            direction: 'buy' or 'sell'

        Returns:
            (passes, reason)
        """
        if not MICROSTRUCTURE_AVAILABLE:
            return True, "Microstructure not available"

        try:
            analyzer = get_microstructure_analyzer()
            analysis = await analyzer.analyze(ticker)

            if not analysis:
                return True, "No microstructure data"

            # Imbalance filter: >0.3 = strong bid, <-0.3 = strong ask
            imbalance = analysis.order_book.imbalance_ratio if analysis.order_book else 0.0
            vpin = analysis.vpin_estimate

            # Check imbalance alignment
            if direction == 'buy' and imbalance < -0.3:
                return False, f"Strong ask imbalance ({imbalance:.2f}) contradicts BUY"
            if direction == 'sell' and imbalance > 0.3:
                return False, f"Strong bid imbalance ({imbalance:.2f}) contradicts SELL"

            # VPIN toxicity filter (>0.7 = toxic, avoid)
            if vpin > 0.75:
                return False, f"High VPIN toxicity ({vpin:.2f}) - avoiding"

            return True, f"Microstructure OK: imbalance={imbalance:.2f}, VPIN={vpin:.2f}"

        except Exception as e:
            logger.debug(f"Microstructure check failed: {e}")
            return True, f"Microstructure check error"

    async def check_crypto_funding_bias(self, ticker: str, direction: str) -> Tuple[bool, str, float]:
        """
        Check crypto funding rate for bias adjustment.

        Funding > +0.03% = crowded long = fade (bias shorts)
        Funding < -0.01% = crowded short = fade (bias longs)

        Args:
            ticker: Crypto ticker (BTCUSD, ETHUSD)
            direction: 'buy' or 'sell'

        Returns:
            (passes, reason, prob_adjustment)
        """
        crypto_tickers = ['BTCUSD', 'ETHUSD', 'BTC', 'ETH', 'SOLUSD']
        if ticker not in crypto_tickers:
            return True, "Not crypto", 0.0

        if not CRYPTO_FUNDING_AVAILABLE:
            return True, "Funding service not available", 0.0

        try:
            funding_service = get_crypto_funding_service()
            # Map to Binance symbol format
            symbol_map = {'BTCUSD': 'BTCUSDT', 'ETHUSD': 'ETHUSDT', 'SOLUSD': 'SOLUSDT'}
            symbol = symbol_map.get(ticker, f"{ticker}T")

            analysis = await funding_service.analyze(symbol)

            if not analysis or not analysis.funding:
                return True, "No funding data", 0.0

            funding_rate = analysis.funding.funding_rate_pct

            # Crowded long: funding > 0.03% -> bias shorts
            if funding_rate > 0.03:
                if direction == 'buy':
                    return False, f"Crowded long (funding +{funding_rate:.3f}%) - fade BUY", 0.0
                else:
                    return True, f"Crowded long confirms SELL (funding +{funding_rate:.3f}%)", 0.08

            # Crowded short: funding < -0.01% -> bias longs
            if funding_rate < -0.01:
                if direction == 'sell':
                    return False, f"Crowded short (funding {funding_rate:.3f}%) - fade SELL", 0.0
                else:
                    return True, f"Crowded short confirms BUY (funding {funding_rate:.3f}%)", 0.08

            return True, f"Neutral funding ({funding_rate:.3f}%)", 0.0

        except Exception as e:
            logger.debug(f"Funding rate check failed: {e}")
            return True, f"Funding check error", 0.0

    async def check_levels_confluence(
        self,
        ticker: str,
        current_price: float,
        direction: str,
        flow_conviction: str = 'NONE',
        regime: str = 'neutral',
        imbalance: float = 0.0,
        mode: str = 'deterministic'
    ) -> Tuple[bool, str, 'ConfluenceResult']:
        """
        Check key levels confluence for signal confirmation.

        Args:
            ticker: Symbol
            current_price: Current price
            direction: 'buy' or 'sell'
            flow_conviction: Flow conviction level
            regime: Current market regime
            imbalance: Order book imbalance
            mode: 'deterministic' or 'quick' (different thresholds)

        Returns:
            (passes, reason, confluence_result)
        """
        if not self.enable_levels_confluence or not LEVELS_SERVICE_AVAILABLE:
            return True, "Levels confluence disabled", None

        try:
            levels_service = get_levels_service()

            # Get PDH/PDL
            daily_levels = await levels_service.calculate_pdh_pdl(ticker)
            if not daily_levels:
                return True, "No daily levels data", None

            # Get Fibonacci levels
            swing_high, swing_low, trend = await levels_service.detect_swing_points(ticker)
            fibs = None
            if swing_high > 0 and swing_low > 0:
                fibs = levels_service.calculate_fib_levels(swing_high, swing_low, trend)

            # Calculate confluence score
            confluence = levels_service.get_confluence_score(
                price=current_price,
                pdh=daily_levels.pdh,
                pdl=daily_levels.pdl,
                fibs=fibs,
                flow_conviction=flow_conviction,
                regime=regime,
                imbalance=imbalance,
                direction='long' if direction == 'buy' else 'short'
            )

            # Get threshold based on mode
            min_confluence = (
                self.levels_confluence_min_quick if mode == 'quick'
                else self.levels_confluence_min_deterministic
            )

            if confluence.score < min_confluence:
                return False, f"Levels confluence {confluence.score:.0f}% < {min_confluence}% ({confluence.nearest_level})", confluence

            logger.info(f"📍 Levels confluence OK: {confluence.score:.0f}% "
                       f"(nearest={confluence.nearest_level}@{confluence.nearest_distance_pct:.2f}%, "
                       f"levels_nearby={confluence.levels_nearby})")

            return True, f"Levels confluence {confluence.score:.0f}%", confluence

        except Exception as e:
            logger.warning(f"Levels confluence check failed: {e}")
            return True, f"Levels check error: {e}", None

    async def check_regime_asymmetric_filter(
        self,
        ticker: str,
        direction: str,
        regime: str,
        flow_conviction: str,
        imbalance: float,
        fibs: Optional['FibonacciLevels'] = None,
        daily_levels: Optional['DailyLevels'] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Apply regime-asymmetric logic for longs vs shorts.

        Trending Up: Require HIGH/EXTREME flow + Fib extensions + imbalance > 0.45 for longs
        Trending Down: MEDIUM+ flow + PDH/PDL magnets for shorts

        Returns:
            (passes, reason, adjusted_params)
            adjusted_params: {target_pct, stop_pct, min_rr, target_level}
        """
        if not self.enable_regime_asymmetric:
            return True, "Regime-asymmetric disabled", {}

        regime_lower = regime.lower().replace('-', '_')
        adjusted_params = {}

        # ========================================
        # TRENDING UP: Stricter requirements for longs
        # ========================================
        if regime_lower == 'trending_up':
            if direction == 'buy':
                # Require HIGH or EXTREME flow for longs in uptrend
                flow_levels = ['HIGH', 'EXTREME']
                if self.uptrend_flow_require == 'EXTREME':
                    flow_levels = ['EXTREME']

                if flow_conviction.upper() not in flow_levels:
                    return False, f"Uptrend longs require {self.uptrend_flow_require}+ flow (got {flow_conviction})", {}

                # Require minimum imbalance
                if imbalance < self.uptrend_imbalance_min:
                    return False, f"Uptrend longs require imbalance > {self.uptrend_imbalance_min} (got {imbalance:.2f})", {}

                # Adjust R:R to 1:4 or 1:5 with trailing
                adjusted_params['target_pct'] = self.uptrend_target_pct  # 0.8%
                adjusted_params['stop_pct'] = self.pct_stop_loss         # 0.2%
                adjusted_params['min_rr'] = self.uptrend_rr_min          # 4.0

                # Use Fib extension as target if available
                if self.uptrend_fib_extensions and fibs:
                    adjusted_params['target_level'] = f"Fib 1.272 @ {fibs.ext_1272:.2f}"

                logger.info(f"📈 Uptrend LONG params: target={adjusted_params['target_pct']}%, "
                           f"R:R={adjusted_params['min_rr']}, trailing enabled")

            else:  # shorts in uptrend
                # Be cautious with shorts in uptrend
                adjusted_params['min_rr'] = 5.0  # Require very high R:R for counter-trend
                logger.debug(f"⚠️ Counter-trend SHORT in uptrend - requiring R:R >= 5")

        # ========================================
        # TRENDING DOWN: PDH/PDL magnets for shorts
        # ========================================
        elif regime_lower == 'trending_down':
            if direction == 'sell':
                # MEDIUM+ flow for shorts in downtrend
                flow_levels = ['MEDIUM', 'HIGH', 'EXTREME']
                if self.downtrend_flow_require == 'HIGH':
                    flow_levels = ['HIGH', 'EXTREME']

                if flow_conviction.upper() not in flow_levels:
                    return False, f"Downtrend shorts require {self.downtrend_flow_require}+ flow (got {flow_conviction})", {}

                # Use PDH/PDL as target magnets
                if self.downtrend_pdh_pdl_targets and daily_levels:
                    adjusted_params['target_level'] = f"PDL @ {daily_levels.pdl:.2f}"
                    adjusted_params['stop_level'] = f"PDH @ {daily_levels.pdh:.2f}"

                adjusted_params['min_rr'] = self.downtrend_rr_min  # 3.0

                logger.info(f"📉 Downtrend SHORT params: target=PDL, R:R={adjusted_params['min_rr']}")

            else:  # longs in downtrend
                # Be cautious with longs in downtrend
                adjusted_params['min_rr'] = 5.0
                logger.debug(f"⚠️ Counter-trend LONG in downtrend - requiring R:R >= 5")

        return True, f"Regime-asymmetric filter passed ({regime})", adjusted_params

    def manage_trailing_stop(
        self,
        ticker: str,
        entry_price: float,
        current_price: float,
        stop_loss: float,
        take_profit: float,
        direction: str,
        atr: float = 0.0,
        vwap: float = 0.0,
        ema21: float = 0.0,
        vwap_lower_1std: float = 0.0,
        vwap_upper_1std: float = 0.0,
        regime: str = ''
    ) -> Dict[str, Any]:
        """
        Manage trailing stop for open position with VWAP/EMA21/Band integration.

        Logic:
        - After 2x risk hit → trail stop to current VWAP or EMA21 (whichever closer)
        - At 2.5x risk in trending → trail to VWAP - 1σ buffer
        - At 3x risk → close 50% position, trail remainder to VWAP - 0.1% buffer
        - Continue trailing with VWAP/EMA21 or ATR fallback

        Returns:
            {
                'new_stop': float,
                'partial_exit': bool,
                'partial_exit_pct': float,
                'action': str ('none', 'move_to_breakeven', 'partial_exit', 'trail_vwap', 'trail_ema', 'trail_atr'),
                'trail_reference': str ('vwap', 'ema21', 'atr', 'none')
            }
        """
        if not self.enable_trailing_stop:
            return {'new_stop': stop_loss, 'partial_exit': False, 'action': 'none', 'trail_reference': 'none'}

        position_key = f"{ticker}:{direction}"

        # Initialize tracking if needed
        if position_key not in self.trailing_positions:
            self.trailing_positions[position_key] = {
                'entry': entry_price,
                'original_stop': stop_loss,
                'current_stop': stop_loss,
                'breakeven_hit': False,
                'partial_exit_done': False,
                'highest_profit_pct': 0.0,
                'trail_mode': 'none'  # 'vwap', 'ema21', 'atr'
            }

        tracking = self.trailing_positions[position_key]

        # Calculate current profit in R-multiples
        risk = abs(entry_price - stop_loss)
        if risk <= 0:
            return {'new_stop': stop_loss, 'partial_exit': False, 'action': 'none', 'trail_reference': 'none'}

        if direction == 'buy':
            current_profit = current_price - entry_price
            profit_r = current_profit / risk
        else:
            current_profit = entry_price - current_price
            profit_r = current_profit / risk

        tracking['highest_profit_pct'] = max(tracking['highest_profit_pct'], profit_r)

        result = {
            'new_stop': tracking['current_stop'],
            'partial_exit': False,
            'partial_exit_pct': 0.0,
            'action': 'none',
            'trail_reference': tracking.get('trail_mode', 'none')
        }

        # ========================================
        # 2x RISK: Trail to VWAP or EMA21 (whichever closer to price)
        # ========================================
        if not tracking['breakeven_hit'] and profit_r >= self.trailing_breakeven_trigger:
            tracking['breakeven_hit'] = True

            # Calculate trail references
            trail_stop = entry_price  # Default to breakeven
            trail_mode = 'breakeven'

            if self.trailing_to_vwap and vwap > 0 and self.trailing_to_ema21 and ema21 > 0:
                # Choose whichever is closer to current price (tighter stop)
                if direction == 'buy':
                    # For longs: higher value = tighter stop
                    if vwap > ema21:
                        trail_stop = vwap
                        trail_mode = 'vwap'
                    else:
                        trail_stop = ema21
                        trail_mode = 'ema21'
                else:
                    # For shorts: lower value = tighter stop
                    if vwap < ema21:
                        trail_stop = vwap
                        trail_mode = 'vwap'
                    else:
                        trail_stop = ema21
                        trail_mode = 'ema21'
            elif self.trailing_to_vwap and vwap > 0:
                trail_stop = vwap
                trail_mode = 'vwap'
            elif self.trailing_to_ema21 and ema21 > 0:
                trail_stop = ema21
                trail_mode = 'ema21'

            # Ensure stop is better than entry (not worse)
            if direction == 'buy':
                trail_stop = max(trail_stop, entry_price)
            else:
                trail_stop = min(trail_stop, entry_price)

            tracking['trail_mode'] = trail_mode
            tracking['current_stop'] = trail_stop
            result['new_stop'] = trail_stop
            result['action'] = f'trail_{trail_mode}'
            result['trail_reference'] = trail_mode
            logger.info(f"📊 {ticker} 2x trailing: Stop → {trail_mode.upper()} @ {trail_stop:.2f}")

        # ========================================
        # 2.5x RISK (TRENDING): Trail to VWAP - 1σ buffer
        # ========================================
        if (self.vwap_band_trailing and
            tracking['breakeven_hit'] and
            not tracking.get('sigma_trail_hit') and
            profit_r >= 2.5 and
            regime in ['trending_up', 'trending_down']):

            tracking['sigma_trail_hit'] = True

            # Use VWAP band for tighter trailing
            if direction == 'buy' and vwap_lower_1std > 0:
                # Long: trail to VWAP - 1σ (lower band)
                sigma_stop = vwap_lower_1std
                if sigma_stop > tracking['current_stop']:
                    tracking['current_stop'] = sigma_stop
                    tracking['trail_mode'] = 'vwap_1sigma'
                    result['new_stop'] = sigma_stop
                    result['action'] = 'trail_vwap_1sigma'
                    result['trail_reference'] = 'vwap_1sigma'
                    logger.info(f"📊 {ticker} 2.5x trending: Stop → VWAP-1σ @ {sigma_stop:.2f}")
            elif direction == 'sell' and vwap_upper_1std > 0:
                # Short: trail to VWAP + 1σ (upper band)
                sigma_stop = vwap_upper_1std
                if sigma_stop < tracking['current_stop']:
                    tracking['current_stop'] = sigma_stop
                    tracking['trail_mode'] = 'vwap_1sigma'
                    result['new_stop'] = sigma_stop
                    result['action'] = 'trail_vwap_1sigma'
                    result['trail_reference'] = 'vwap_1sigma'
                    logger.info(f"📊 {ticker} 2.5x trending: Stop → VWAP+1σ @ {sigma_stop:.2f}")

        # ========================================
        # 3x RISK: Partial exit 50%, trail remainder to VWAP - buffer
        # ========================================
        if self.trailing_partial_at_3x and not tracking['partial_exit_done'] and profit_r >= self.trailing_partial_exit_trigger:
            tracking['partial_exit_done'] = True
            result['partial_exit'] = True
            result['partial_exit_pct'] = self.trailing_partial_exit_pct
            result['action'] = 'partial_exit'

            # Tighten stop for remainder to VWAP - buffer
            if self.trailing_remainder_to_vwap and vwap > 0:
                buffer = vwap * (self.trailing_vwap_buffer_pct / 100)
                if direction == 'buy':
                    new_stop = vwap - buffer
                    if new_stop > tracking['current_stop']:
                        tracking['current_stop'] = new_stop
                        result['new_stop'] = new_stop
                else:
                    new_stop = vwap + buffer
                    if new_stop < tracking['current_stop']:
                        tracking['current_stop'] = new_stop
                        result['new_stop'] = new_stop

            logger.info(f"📊 {ticker} 3x trailing: Partial exit {self.trailing_partial_exit_pct}% @ {profit_r:.1f}R, "
                       f"remainder trail to VWAP-{self.trailing_vwap_buffer_pct}%")

        # ========================================
        # CONTINUOUS TRAIL: Update VWAP/EMA21/ATR stops
        # ========================================
        if tracking['breakeven_hit']:
            trail_mode = tracking.get('trail_mode', 'atr')
            new_stop = tracking['current_stop']

            if trail_mode == 'vwap' and vwap > 0:
                buffer = vwap * (self.trailing_vwap_buffer_pct / 100) if tracking['partial_exit_done'] else 0
                if direction == 'buy':
                    candidate_stop = vwap - buffer
                    if candidate_stop > new_stop:
                        new_stop = candidate_stop
                else:
                    candidate_stop = vwap + buffer
                    if candidate_stop < new_stop:
                        new_stop = candidate_stop

            elif trail_mode == 'vwap_1sigma':
                # Trail to VWAP band (1σ)
                if direction == 'buy' and vwap_lower_1std > 0:
                    if vwap_lower_1std > new_stop:
                        new_stop = vwap_lower_1std
                elif direction == 'sell' and vwap_upper_1std > 0:
                    if vwap_upper_1std < new_stop:
                        new_stop = vwap_upper_1std

            elif trail_mode == 'ema21' and ema21 > 0:
                if direction == 'buy':
                    if ema21 > new_stop:
                        new_stop = ema21
                else:
                    if ema21 < new_stop:
                        new_stop = ema21

            elif atr > 0:
                # Fallback to ATR trailing
                trail_distance = atr * self.trailing_atr_multiplier
                if direction == 'buy':
                    candidate_stop = current_price - trail_distance
                    if candidate_stop > new_stop:
                        new_stop = candidate_stop
                        trail_mode = 'atr'
                else:
                    candidate_stop = current_price + trail_distance
                    if candidate_stop < new_stop:
                        new_stop = candidate_stop
                        trail_mode = 'atr'

            if new_stop != tracking['current_stop']:
                tracking['current_stop'] = new_stop
                result['new_stop'] = new_stop
                result['action'] = f'trail_{trail_mode}'
                result['trail_reference'] = trail_mode

        return result

    def calculate_mean_revert_targets(
        self,
        current_price: float,
        direction: str,
        vwap: float,
        vwap_lower_1std: float,
        vwap_upper_1std: float,
        vwap_lower_2std: float,
        vwap_upper_2std: float
    ) -> Dict[str, float]:
        """
        Calculate VWAP-band based targets and stops for mean-reverting regime.

        In mean-reverting:
        - Target: 1σ band (reversion toward VWAP)
        - Stop: 2σ band (breakout failure)

        Returns:
            {'target': float, 'stop': float, 'rr_ratio': float}
        """
        if vwap <= 0 or vwap_lower_1std <= 0:
            return {'target': 0, 'stop': 0, 'rr_ratio': 0}

        if direction == 'buy':
            # Long in mean-reverting: price below VWAP, expect reversion up
            target = vwap_upper_1std  # Target upper 1σ band
            stop = vwap_lower_2std     # Stop at lower 2σ band
            distance_to_target = target - current_price
            distance_to_stop = current_price - stop
        else:
            # Short in mean-reverting: price above VWAP, expect reversion down
            target = vwap_lower_1std   # Target lower 1σ band
            stop = vwap_upper_2std     # Stop at upper 2σ band
            distance_to_target = current_price - target
            distance_to_stop = stop - current_price

        # Calculate R:R
        rr_ratio = distance_to_target / distance_to_stop if distance_to_stop > 0 else 0

        logger.debug(f"Mean-revert targets: direction={direction}, target={target:.2f}, "
                    f"stop={stop:.2f}, R:R={rr_ratio:.2f}")

        return {
            'target': target,
            'stop': stop,
            'rr_ratio': rr_ratio,
            'target_distance': distance_to_target,
            'stop_distance': distance_to_stop
        }

    async def check_news_sentiment(self, ticker: str, direction: str) -> Tuple[bool, str, float]:
        """
        Check news sentiment for probability boost/penalty.

        Returns:
            (passes, reason, prob_boost)
        """
        if not self.enable_news_sentiment or not LEVELS_SERVICE_AVAILABLE:
            return True, "News sentiment disabled", 0.0

        try:
            news_service = get_news_sentiment()
            sentiment = await news_service.get_sentiment(ticker)

            if sentiment.headline_count == 0:
                return True, "No news data", 0.0

            # Check if sentiment aligns with direction
            if direction == 'buy' and sentiment.sentiment_score > 0.3:
                boost = min(sentiment.boost, self.news_sentiment_boost_max)
                return True, f"Positive news: {sentiment.sentiment_score:.2f}", boost
            elif direction == 'sell' and sentiment.sentiment_score < -0.3:
                boost = min(abs(sentiment.boost), self.news_sentiment_boost_max)
                return True, f"Negative news: {sentiment.sentiment_score:.2f}", boost
            elif abs(sentiment.sentiment_score) > 0.5:
                # Strong opposing sentiment - apply penalty
                if (direction == 'buy' and sentiment.sentiment_score < -0.5) or \
                   (direction == 'sell' and sentiment.sentiment_score > 0.5):
                    return True, f"Opposing news: {sentiment.sentiment_score:.2f}", -0.03

            return True, f"Neutral news: {sentiment.sentiment_score:.2f}", 0.0

        except Exception as e:
            logger.debug(f"News sentiment check failed: {e}")
            return True, "News check error", 0.0

    async def check_vwap_confluence(
        self,
        ticker: str,
        direction: str,
        current_price: float,
        regime: str,
        price_data: Optional[Any] = None
    ) -> Tuple[bool, str, float, Optional[VWAPConfluence]]:
        """
        Check VWAP confluence for trade entry.

        Implements regime-aware VWAP gating:
        - Trending Up + Long: Require price near/above VWAP (bias >= 0.4)
        - Trending Down + Short: Require price near/below VWAP (bias <= -0.4)
        - Mean Reverting: Prefer price very close to VWAP

        Args:
            ticker: Trading symbol
            direction: 'buy' or 'sell'
            current_price: Current price
            regime: Current regime ('trending_up', 'trending_down', etc.)
            price_data: Optional price DataFrame (if available)

        Returns:
            (passes, reason, prob_boost, vwap_confluence)
        """
        if not self.enable_vwap_confluence or not VWAP_SERVICE_AVAILABLE:
            return True, "VWAP confluence disabled", 0.0, None

        try:
            # Check cache first
            cache_key = f"{ticker}:vwap"
            cached = self.vwap_cache.get(cache_key)
            now = datetime.now()

            vwap_result = None
            if cached:
                cache_time, cached_vwap = cached
                if (now - cache_time).seconds < (self.vwap_cache_ttl_minutes * 60):
                    vwap_result = cached_vwap

            # Calculate VWAP if not cached
            if vwap_result is None:
                vwap_service = VWAPService(VWAPConfig(
                    distance_threshold_pct=self.vwap_distance_threshold_pct,
                    tight_distance_pct=self.vwap_tight_distance_pct,
                    confluence_boost=self.vwap_confluence_boost,
                    tight_confluence_boost=self.vwap_tight_boost,
                    mean_reversion_boost=self.vwap_mean_reversion_boost,
                    min_vwap_bias_for_long=self.vwap_min_bias_for_long,
                    trailing_enabled=self.vwap_trailing_enabled
                ))

                # Try to get price data for VWAP calculation
                if price_data is not None and hasattr(price_data, 'empty') and not price_data.empty:
                    vwap_result = vwap_service.get_current_vwap(price_data, session_reset=True)
                else:
                    # Try to get historical bars from market data service
                    try:
                        import pandas as pd
                        bars = await market_data_service.get_historical_bars(
                            ticker,
                            resolution='1',
                            limit=500  # ~8 hours of 1-min bars
                        )
                        if bars:
                            df = pd.DataFrame([{
                                'high': b.high,
                                'low': b.low,
                                'close': b.close,
                                'volume': b.volume,
                                'timestamp': b.timestamp
                            } for b in bars])
                            vwap_result = vwap_service.get_current_vwap(df, session_reset=True)
                    except Exception as e:
                        logger.debug(f"Failed to get bars for VWAP: {e}")

                if vwap_result:
                    self.vwap_cache[cache_key] = (now, vwap_result)

            # If no VWAP data available, pass the filter
            if vwap_result is None or vwap_result.vwap <= 0:
                return True, "No VWAP data", 0.0, None

            # Check VWAP confluence
            vwap_service = VWAPService(VWAPConfig(
                distance_threshold_pct=self.vwap_distance_threshold_pct,
                tight_distance_pct=self.vwap_tight_distance_pct,
                confluence_boost=self.vwap_confluence_boost,
                tight_confluence_boost=self.vwap_tight_boost,
                mean_reversion_boost=self.vwap_mean_reversion_boost,
                min_vwap_bias_for_long=self.vwap_min_bias_for_long,
                trailing_enabled=self.vwap_trailing_enabled
            ))

            confluence = vwap_service.check_vwap_confluence(
                current_price=current_price,
                vwap_result=vwap_result,
                direction=direction,
                regime=regime
            )

            if not confluence.passes_filter:
                logger.info(f"📊 VWAP REJECTED: {ticker} {direction.upper()} - {confluence.reason}")
                return False, confluence.reason, 0.0, confluence

            # Log VWAP confluence
            if confluence.probability_boost > 0:
                logger.info(
                    f"📊 VWAP confluence: {ticker} {direction.upper()} "
                    f"distance={confluence.bias.distance_pct:.3f}% "
                    f"bias={confluence.bias.bias_score:.2f} "
                    f"boost=+{confluence.probability_boost:.1%} "
                    f"quality={confluence.entry_quality}"
                )

            return True, confluence.reason, confluence.probability_boost, confluence

        except Exception as e:
            logger.debug(f"VWAP confluence check failed: {e}")
            return True, "VWAP check error", 0.0, None

    async def get_projectx_realtime_price(self, ticker: str) -> Optional[float]:
        """
        Get realtime price from ProjectX for futures symbols.

        Returns:
            Current price or None if not available
        """
        if not self.use_projectx_realtime:
            return None

        if ticker not in self.projectx_symbols:
            return None

        try:
            # Use market data service which has ProjectX integration
            if hasattr(market_data_service, 'get_quote'):
                quote = await market_data_service.get_quote(ticker)
                if quote and hasattr(quote, 'last_price'):
                    return quote.last_price
            return None
        except Exception as e:
            logger.debug(f"ProjectX price fetch failed for {ticker}: {e}")
            return None

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

    # Correlation groups for US indices (highly correlated - should not trade opposite directions)
    CORRELATION_GROUPS = {
        'us_indices': {
            'symbols': ['MES', 'ES', 'SPY', 'SPX500', 'US500', 'NQ', 'MNQ', 'NAS100', 'USTEC', 'QQQ',
                       'YM', 'MYM', 'US30', 'DIA', 'RTY', 'M2K', 'IWM'],
            'threshold': 0.85,  # High correlation threshold
        },
        'gold': {
            'symbols': ['GC', 'MGC', 'XAUUSD', 'GLD'],
            'threshold': 0.90,
        },
        'crypto': {
            'symbols': ['BTCUSD', 'BTC', 'ETHUSD', 'ETH'],
            'threshold': 0.80,
        }
    }

    def _get_correlated_symbols(self, ticker: str) -> List[str]:
        """Get list of symbols correlated with the given ticker."""
        normalized = ticker.upper().replace('.PRO', '').replace('1!', '').replace('!', '')

        for group_name, group_data in self.CORRELATION_GROUPS.items():
            if any(sym in normalized or normalized in sym for sym in group_data['symbols']):
                return [sym for sym in group_data['symbols'] if sym != normalized]
        return []

    async def check_position_before_signal(self, ticker: str, signal_direction: str) -> Tuple[bool, str]:
        """
        Check actual broker position before deciding to send/skip signal.

        INCLUDES CORRELATION FILTER:
        - Blocks signals that conflict with existing positions on correlated instruments
        - Example: If MES is SHORT, blocks BUY signals for NQ/NAS100/ES

        Returns:
            (should_send: bool, reason: str)
        """
        position = await self.get_broker_positions(ticker)

        if not position['has_position']:
            # No direct position - check CORRELATED positions
            correlated_symbols = self._get_correlated_symbols(ticker)

            for corr_symbol in correlated_symbols:
                corr_position = await self.get_broker_positions(corr_symbol)

                if corr_position['has_position']:
                    corr_direction = corr_position['direction']

                    # Block if correlated position is going OPPOSITE direction
                    if signal_direction == 'buy' and corr_direction == 'short':
                        logger.warning(f"🚫 CORRELATION BLOCK: {ticker} BUY blocked - {corr_symbol} is SHORT (pnl={corr_position['unrealized_pnl']:.2f})")
                        return False, f"correlation_block: {corr_symbol} is short"

                    if signal_direction == 'sell' and corr_direction == 'long':
                        logger.warning(f"🚫 CORRELATION BLOCK: {ticker} SELL blocked - {corr_symbol} is LONG (pnl={corr_position['unrealized_pnl']:.2f})")
                        return False, f"correlation_block: {corr_symbol} is long"

                    # If same direction, that's fine - allow the trade
                    if (signal_direction == 'buy' and corr_direction == 'long') or \
                       (signal_direction == 'sell' and corr_direction == 'short'):
                        logger.info(f"✅ CORRELATION OK: {ticker} {signal_direction.upper()} aligns with {corr_symbol} {corr_direction.upper()}")

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
                          post_errors: str = None, engine_type: str = None,
                          router_decision = None) -> Optional[int]:
        """
        Save a signal to the database for ML learning.

        Args:
            engine_type: Engine that generated signal ('flow', 'ai_enhancement', 'ai_only', 'deterministic', 'quick')
                        If None, auto-detect from signal.source
            router_decision: Phase 8A - RouterDecision object with routing metadata

        Returns the signal_log ID if successful, None otherwise.
        """
        # Auto-detect engine_type from signal source if not provided
        if engine_type is None:
            source = getattr(signal, 'source', 'SmartFlow')
            if 'AI' in source:
                engine_type = 'ai_only'
            elif 'Deterministic' in source:
                engine_type = 'deterministic'
            elif 'Quick' in source:
                engine_type = 'quick'
            else:
                engine_type = 'flow'

        # Phase 8A: Enhance engine_type with strategy_id if router decision available
        if router_decision:
            engine_type = f"{engine_type}:{router_decision.selected_strategy_id}"
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
                    engine_type=engine_type,  # Phase 0.5: Engine source tracking
                    webhooks_posted=webhooks_posted or [],
                    post_successful=post_successful,
                    post_errors=post_errors
                )

                db.add(signal_log)
                db.commit()
                db.refresh(signal_log)

                # Phase 8A: Log routing metadata if available
                routing_info = ""
                if router_decision:
                    routing_info = (
                        f" [Router: {router_decision.selected_strategy_id}, "
                        f"regime={router_decision.current_regime}, "
                        f"source={router_decision.decision_source}]"
                    )

                logger.info(
                    f"📊 Signal saved to DB: id={signal_log.id} {signal.ticker} {signal.action} "
                    f"score={signal.score:.1f}{routing_info}"
                )
                return signal_log.id

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to save signal to DB: {e}")
            return None

    def _update_signal_log_post_status(
        self,
        signal_log_id: int,
        webhooks_posted: List[str],
        post_successful: bool,
        post_errors: Optional[str]
    ) -> None:
        try:
            db = SessionLocal()
            try:
                signal_log = db.query(SmartFlowSignalLog).filter(
                    SmartFlowSignalLog.id == signal_log_id
                ).first()
                if not signal_log:
                    logger.warning(f"Signal log {signal_log_id} not found for post status update")
                    return

                signal_log.webhooks_posted = webhooks_posted or []
                signal_log.post_successful = post_successful
                signal_log.post_errors = post_errors
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            logger.error(f"Failed to update signal log {signal_log_id} post status: {exc}")

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

    def load_recent_scores_from_db(self):
        """
        Load recent scores from database into in-memory cache on startup.
        Loads last 24 hours of data per ticker to populate score_history.
        """
        try:
            db = SessionLocal()
            try:
                from datetime import timedelta
                from zoneinfo import ZoneInfo; cutoff = datetime.now(ZoneInfo("America/New_York")) - timedelta(hours=24)

                # Query recent scores for each ticker
                tickers = ['SPY', 'QQQ', 'IWM', 'DIA', 'GLD']
                for ticker in tickers:
                    scores = db.query(SmartFlowScoreHistory).filter(
                        SmartFlowScoreHistory.ticker == ticker,
                        SmartFlowScoreHistory.timestamp >= cutoff
                    ).order_by(SmartFlowScoreHistory.timestamp.asc()).all()

                    # Convert DB records to SentimentScore objects
                    for score_entry in scores:
                        sentiment = SentimentScore(
                            ticker=score_entry.ticker,
                            score=score_entry.score,
                            bullish_flows=score_entry.bullish_flows,
                            bearish_flows=score_entry.bearish_flows,
                            total_premium=score_entry.total_premium,
                            timestamp=score_entry.timestamp
                        )
                        self.score_history[ticker].append(sentiment)

                    logger.info(f"Loaded {len(scores)} historical scores for {ticker}")

                logger.info(f"Cache initialized with historical data from database")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to load score history from DB: {e}")

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

                # Feed outcome to adaptive learning system
                if ADAPTIVE_LEARNING_AVAILABLE and pnl is not None:
                    try:
                        adaptive_mgr = get_adaptive_manager()
                        ticker = signal_log.ticker if signal_log else "UNKNOWN"
                        is_win = pnl > 0
                        adaptive_mgr.record_performance(ticker, pnl, is_win)
                        logger.debug(f"📊 Adaptive learning: recorded {ticker} outcome pnl={pnl:.2f}")
                    except Exception as adapt_e:
                        logger.warning(f"Adaptive learning record failed: {adapt_e}")

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

                # Get most recent successful ENTRY signal (buy or sell only, not close).
                # This avoids attaching outcomes to rejected / unposted / close-only signals.
                signal = db.query(SmartFlowSignalLog).filter(
                    SmartFlowSignalLog.ticker.in_(ticker_variants),
                    SmartFlowSignalLog.action.in_(['buy', 'sell']),  # Exclude 'close'
                    SmartFlowSignalLog.post_successful == True
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


        # 7. LuxAlgo consensus boost (up to +15 points) -- cached, non-blocking
        if LUXALGO_AVAILABLE:
            try:
                lux_boost_pct = get_luxalgo_boost(signal_direction, ticker)
                if lux_boost_pct > 0:
                    lux_boost_pts = lux_boost_pct * 100  # 0.0-15.0 points
                    score += lux_boost_pts
                    details['luxalgo_boost'] = lux_boost_pts
                    logger.info(
                        f"LuxAlgo boost for {ticker} {signal_direction}: "
                        f"+{lux_boost_pts:.1f}pts (cached)"
                    )
            except Exception as lux_e:
                logger.debug(f"LuxAlgo confidence check failed: {lux_e}")

        return min(score, 100.0), details

    # Comprehensive crypto ticker set used across all market-hours checks
    CRYPTO_TICKERS = {
        'BTCUSD', 'BTCUSDT', 'BTC', 'ETHUSD', 'ETHUSDT', 'ETH',
        'SOLUSD', 'SOLUSDT', 'SOL', 'XRPUSD', 'LTCUSD', 'DOGEUSD',
        'ADAUSD', 'DOTUSD', 'AVAXUSD', 'MATICUSD', 'LINKUSD',
    }

    def check_time_filter(self, ticker: str = None) -> bool:
        """
        Check if current time is within trading window (EST timezone).
        Crypto tickers (24/7 markets) always pass this filter.

        Returns:
            True if time is OK, False if should skip
        """
        if not self.enable_time_filter:
            return True

        # Crypto trades 24/7 — never block
        if ticker and ticker.upper() in self.CRYPTO_TICKERS:
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

        # Time filter check (crypto bypasses — trades 24/7)
        if not self.check_time_filter(ticker=ticker):
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

        # ========================================
        # FLOW CONFIRMATION (using SAME sentiment data)
        # ========================================
        flow_prob_boost = 0.0
        if self.use_flow_confirmation and signal_direction in ['buy', 'sell']:
            flow_passes, flow_reason, flow_prob_boost = await self.check_flow_conviction(ticker, signal_direction, sentiment)
            if not flow_passes:
                logger.warning(f"🚫 BLOCKED: {ticker} {signal_direction.upper()} - {flow_reason}")
                return None
            logger.info(f"✅ Flow conviction: {flow_reason} (+{flow_prob_boost*100:.0f}% boost)")

        # ========================================
        # MICROSTRUCTURE FILTER (Imbalance, VPIN)
        # ========================================
        if signal_direction in ['buy', 'sell']:
            micro_passes, micro_reason = await self.check_microstructure_filter(ticker, signal_direction)
            if not micro_passes:
                logger.warning(f"🚫 BLOCKED: {ticker} {signal_direction.upper()} - {micro_reason}")
                return None
            if "OK" in micro_reason:
                logger.debug(f"✅ Microstructure: {micro_reason}")

        # ========================================
        # CRYPTO FUNDING RATE BIAS
        # ========================================
        funding_prob_boost = 0.0
        if signal_direction in ['buy', 'sell']:
            funding_passes, funding_reason, funding_prob_boost = await self.check_crypto_funding_bias(ticker, signal_direction)
            if not funding_passes:
                logger.warning(f"🚫 BLOCKED: {ticker} {signal_direction.upper()} - {funding_reason}")
                return None
            if funding_prob_boost > 0:
                logger.info(f"✅ Funding rate: {funding_reason} (+{funding_prob_boost*100:.0f}% boost)")

        # Calculate confidence score
        confidence, conf_details = self.calculate_confidence_score(sentiment, ticker, signal_direction, flows)

        # Apply flow and funding probability boosts
        confidence = min(100, confidence + (flow_prob_boost * 100) + (funding_prob_boost * 100))

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

        # Adaptive learning: check for strategy decay
        decay_mult = 1.0
        if ADAPTIVE_LEARNING_AVAILABLE:
            try:
                adaptive_mgr = get_adaptive_manager()
                decay = adaptive_mgr.calculate_decay(ticker)
                if decay.should_reduce_size:
                    decay_mult = decay.recommended_size_mult
                    logger.warning(f"📉 Strategy decay detected for {ticker}: Sharpe_30d={decay.sharpe_30d:.2f} → size mult={decay_mult:.2f}")
                    # Store for position sizing later
                    if not hasattr(self, '_decay_multipliers'):
                        self._decay_multipliers = {}
                    self._decay_multipliers[ticker] = decay_mult
            except Exception as adapt_e:
                logger.debug(f"Adaptive decay check failed: {adapt_e}")

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
        import time
        from zoneinfo import ZoneInfo
        EST = ZoneInfo('America/New_York')

        webhook_start_time = time.time()
        now_est = datetime.now(EST).replace(tzinfo=None)

        webhooks_posted = []
        post_errors = []
        all_successful = True
        signal_log_id = None  # Initialize for ML tracking

        # Calculate signal-to-webhook latency (if signal has processing time)
        signal_latency_ms = 0.0
        if hasattr(signal, 'timestamp') and signal.timestamp:
            signal_age = (now_est - signal.timestamp).total_seconds() * 1000
            signal_latency_ms = signal_age

        # SAFETY CHECK 1: Block signals below configured minimum confidence.
        min_confidence_required = getattr(self, 'min_confidence_score', 30.0)
        if signal.confidence is not None and signal.confidence < min_confidence_required:
            logger.warning(
                f"🚫 BLOCKED: {signal.ticker} {signal.action} - confidence {signal.confidence}% too low "
                f"(min {min_confidence_required}%)"
            )
            return

        # SAFETY CHECK 1B: Block invalid execution prices for entry signals.
        execution_price = getattr(signal, 'entry_price', None) or getattr(signal, 'price', None)
        if signal.action.lower() in ('buy', 'sell') and execution_price is not None and execution_price <= 0:
            logger.warning(
                f"🚫 BLOCKED: {signal.ticker} {signal.action} - invalid execution price {execution_price}"
            )
            return

        # SAFETY CHECK 2: Block duplicate signals (same ticker+action within cooldown)
        if self.is_duplicate_signal(signal.ticker, signal.action):
            logger.info(f"⏸️ SKIPPED: {signal.ticker} {signal.action} - duplicate within cooldown period")
            return

        # SAFETY CHECK 3: Signal Expiry (Critical for Quant)
        # Signals older than TTL are stale - market conditions may have changed
        if hasattr(signal, 'timestamp') and signal.timestamp:
            signal_age_minutes = (now_est - signal.timestamp).total_seconds() / 60
            if signal_age_minutes > self.signal_ttl_minutes:
                logger.warning(f"⏳ EXPIRED: {signal.ticker} {signal.action} - signal {signal_age_minutes:.1f}min old (TTL={self.signal_ttl_minutes}min)")
                return

        # SAFETY CHECK 4: Data Freshness Alert
        # If using stale or mock data, log warning but continue (can be made blocking)
        data_freshness = self.last_data_freshness.get(signal.ticker, 'unknown')
        if self.enable_stale_data_alerts and data_freshness in ['stale', 'mock']:
            logger.warning(f"⚠️ DATA QUALITY: {signal.ticker} {signal.action} generated with {data_freshness.upper()} data")
            # Optional: block signals from stale data (uncomment to enable)
            # self.stale_data_signals_blocked += 1
            # return

        # Phase 8A: Get current router decision for routing metadata
        router_decision = getattr(self, '_current_router_decision', None)

        if not self.webhook_urls:
            logger.warning("No webhook URLs configured for SmartFlow")
            # Auto-reload webhook URLs from database if missing
            from app.db.database import SessionLocal
            from app.models.smartflow_models import SmartFlowConfig
            try:
                db = SessionLocal()
                configs = db.query(SmartFlowConfig).filter(SmartFlowConfig.enabled == True).all()
                for config in configs:
                    if config.webhook_urls:
                        self.webhook_urls = config.webhook_urls
                        logger.info(f"Auto-reloaded {len(config.webhook_urls)} webhook(s)")
                        break
                db.close()
            except Exception as e:
                logger.warning(f"Failed to auto-reload webhooks: {e}")
            if not self.webhook_urls:
                self.save_signal_to_db(signal, sentiment, [], False, "No webhooks configured", router_decision=router_decision)
                return
            # Still save signal to DB even if no webhooks
            self.save_signal_to_db(signal, sentiment, [], False, "No webhooks configured",
                                   router_decision=router_decision)
            return

        # Pre-save signal ONCE before posting to webhooks (for ML tracking)
        if signal_log_id is None:
            signal_log_id = self.save_signal_to_db(
                signal=signal,
                sentiment=sentiment,
                webhooks_posted=[],  # Will update after all posts
                post_successful=True,
                post_errors=None,
                router_decision=router_decision
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

                    # Determine strategy_id and engine for routing (ALWAYS required)
                    # Priority: router_decision > allocation_decision > reason-based detection
                    selected_strategy_id = None
                    selected_engine = None

                    # Try router decision first
                    if router_decision and hasattr(router_decision, 'selected_strategy_id'):
                        selected_strategy_id = router_decision.selected_strategy_id
                        selected_engine = getattr(router_decision, 'selected_engine', None)

                    # Try allocation decision
                    allocation_decision = getattr(self, '_current_allocation_decision', None)
                    if not selected_strategy_id and allocation_decision and allocation_decision.selected_strategies:
                        top_strategy = max(allocation_decision.selected_strategies, key=lambda s: s.allocation_weight)
                        selected_strategy_id = top_strategy.strategy_id

                    # Fallback: detect from signal.reason
                    if not selected_strategy_id:
                        reason_lower = signal.reason.lower() if signal.reason else ''
                        if 'deterministic' in reason_lower or 'mtf' in reason_lower:
                            selected_strategy_id = 'deterministic_v1'
                            selected_engine = 'deterministic'
                        elif 'ai' in reason_lower or 'claude' in reason_lower:
                            selected_strategy_id = 'ai_v1_proxy'
                            selected_engine = 'ai'
                        elif 'quick' in reason_lower or 'momentum' in reason_lower:
                            selected_strategy_id = 'quick_v1'
                            selected_engine = 'quick'
                        elif 'flow' in reason_lower or 'fss' in reason_lower or 'options' in reason_lower:
                            selected_strategy_id = 'flow_v1'
                            selected_engine = 'flow'
                        else:
                            selected_strategy_id = 'unified_v1'  # Default
                            selected_engine = 'unified'

                    # Derive engine from strategy_id if not set
                    if not selected_engine and selected_strategy_id:
                        if selected_strategy_id.startswith('deterministic'):
                            selected_engine = 'deterministic'
                        elif selected_strategy_id.startswith('ai'):
                            selected_engine = 'ai'
                        elif selected_strategy_id.startswith('quick'):
                            selected_engine = 'quick'
                        elif selected_strategy_id.startswith('flow'):
                            selected_engine = 'flow'
                        else:
                            selected_engine = 'unified'

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
                        'smartflow_signal_log_id': signal_log_id,  # Include for ML outcome tracking
                        # ROUTING FIELDS (ALWAYS included for rules-based routing)
                        'strategy_id': selected_strategy_id,  # Used by webhook_execute for rules_based routing
                        'selected_engine': selected_engine,
                    }

                    # Phase 9: Add allocation metadata (optional, backward-compatible)
                    if allocation_decision and allocation_decision.selected_strategies:
                        # Get top strategy by weight
                        top_strategy = max(allocation_decision.selected_strategies, key=lambda s: s.allocation_weight)
                        payload['allocation_weight'] = top_strategy.allocation_weight
                        payload['strategy_score'] = top_strategy.adjusted_score
                        if top_strategy.ai_adjustment != 0:
                            payload['ai_adjustment'] = top_strategy.ai_adjustment
                        if allocation_decision.current_regime:
                            payload['market_regime'] = allocation_decision.current_regime

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
                            post_errors=None,
                            router_decision=router_decision
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

                    # Phase 9: Add allocation metadata (optional, backward-compatible)
                    allocation_decision = getattr(self, '_current_allocation_decision', None)
                    if allocation_decision and allocation_decision.selected_strategies:
                        # Get top strategy by weight
                        top_strategy = max(allocation_decision.selected_strategies, key=lambda s: s.allocation_weight)
                        payload['allocation_weight'] = top_strategy.allocation_weight
                        payload['strategy_score'] = top_strategy.adjusted_score
                        payload['selected_strategy_id'] = top_strategy.strategy_id
                        if top_strategy.ai_adjustment != 0:
                            payload['ai_adjustment'] = top_strategy.ai_adjustment
                        if allocation_decision.current_regime:
                            payload['market_regime'] = allocation_decision.current_regime

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
            post_errors_text = "; ".join(post_errors) if post_errors else None
            self._update_signal_log_post_status(
                signal_log_id=signal_log_id,
                webhooks_posted=webhooks_posted,
                post_successful=all_successful and bool(webhooks_posted),
                post_errors=post_errors_text,
            )

        # Store in log for dashboard (in-memory)
        self.signal_log.append(signal)
        if len(self.signal_log) > 100:  # Keep last 100 signals
            self.signal_log.pop(0)

        # ========================================
        # LATENCY TRACKING
        # ========================================
        webhook_post_time = (time.time() - webhook_start_time) * 1000  # ms
        total_latency_ms = signal_latency_ms + webhook_post_time

        latency_record = {
            'timestamp': now_est.strftime('%Y-%m-%d %H:%M:%S'),
            'ticker': signal.ticker,
            'action': signal.action,
            'signal_age_ms': signal_latency_ms,
            'webhook_post_ms': webhook_post_time,
            'total_latency_ms': total_latency_ms,
            'under_target': total_latency_ms < self.latency_target_ms
        }

        # Store in history (keep last 100)
        self.latency_history.append(latency_record)
        if len(self.latency_history) > 100:
            self.latency_history.pop(0)

        # Log latency with color coding
        if total_latency_ms < self.latency_target_ms:
            logger.info(f"⚡ LATENCY: {signal.ticker} {signal.action} → {total_latency_ms:.0f}ms (✅ under {self.latency_target_ms}ms target)")
        else:
            logger.warning(f"🐌 LATENCY: {signal.ticker} {signal.action} → {total_latency_ms:.0f}ms (⚠️ over {self.latency_target_ms}ms target)")

    def _get_ai_only_instruments_for_time(self, now: datetime) -> List[str]:
        """Return AI-only instruments adjusted for weekend crypto-only guard."""
        instruments = list(self.ai_only_instruments or [])
        weekday = now.weekday()
        hour = now.hour

        # Weekend guard: Saturday all day, Sunday before 5pm EST -> crypto only
        if weekday == 5 or (weekday == 6 and hour < 17):
            return [i for i in instruments if i.upper() in self.CRYPTO_TICKERS]

        return instruments

    def _get_configured_scan_instruments(self) -> List[str]:
        instruments = list(self.ai_only_instruments or [])
        if not instruments:
            instruments = list(self.deterministic_instruments or [])
        supported = []
        for instrument in instruments:
            if market_data_service.is_supported_ticker(instrument):
                supported.append(instrument)
            else:
                logger.debug(f"Skipping unsupported ticker (no preferred data source): {instrument}")
        return supported

    def _resolve_data_ticker(self, instrument: str) -> str:
        if market_data_service.is_polygon_only_ticker(instrument):
            return market_data_service.normalize_forex_ticker(instrument)
        return instrument

    def _should_skip_polygon_only(self, ticker: str) -> bool:
        if market_data_service.is_polygon_only_ticker(ticker):
            remaining = market_data_service.get_polygon_rate_limit_remaining()
            if remaining < 2:
                logger.info(f"⏸️ Skipping {ticker}: Polygon budget low ({remaining} remaining)")
                return True
        return False

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

        from zoneinfo import ZoneInfo
        EST = ZoneInfo('America/New_York')
        now = datetime.now(EST).replace(tzinfo=None)
        signals_generated = 0

        instruments = self._get_ai_only_instruments_for_time(now)
        for instrument in instruments:
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

                # Compute composite recommendation with MTF-weighted voting
                # This ensures AI follows actual market direction
                buy_votes = 0.0
                sell_votes = 0.0
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

                # Apply MTF bias weighting - follow actual market direction
                # If market is 70% bearish, boost sell votes by 0.7
                # If market is 70% bullish, boost buy votes by 0.7
                mtf_buy_boost = mtf_bullish_pct / 100.0  # 0.0 to 1.0
                mtf_sell_boost = mtf_bearish_pct / 100.0  # 0.0 to 1.0

                weighted_buy_votes = buy_votes + (buy_votes * mtf_buy_boost * 0.5)  # Up to +50% boost
                weighted_sell_votes = sell_votes + (sell_votes * mtf_sell_boost * 0.5)  # Up to +50% boost

                logger.debug(f"🤖 {instrument}: Raw votes B:{buy_votes}/S:{sell_votes} → Weighted B:{weighted_buy_votes:.2f}/S:{weighted_sell_votes:.2f} (MTF: {mtf_bullish_pct:.0f}%↑/{mtf_bearish_pct:.0f}%↓)")

                avg_confidence = total_confidence / len(analyses) if analyses else 0

                # Only trade if confidence meets threshold
                if avg_confidence < self.ai_only_confidence_threshold:
                    logger.debug(f"🤖 {instrument}: Confidence {avg_confidence:.0f}% < {self.ai_only_confidence_threshold}% threshold")
                    continue

                # Determine action using weighted votes
                if weighted_buy_votes > weighted_sell_votes:
                    action = 'buy'
                    direction = 'bullish'
                elif weighted_sell_votes > weighted_buy_votes:
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

                # Block signals that CONFLICT with strong MTF bias (>55%)
                # This prevents buying in strong downtrends and selling in strong uptrends
                mtf_aligned = False
                if direction == 'bullish':
                    if mtf_bearish_pct >= 55:
                        # Strong bearish market - block buy signal
                        logger.info(f"🚫 {instrument}: Blocking BUY - market is {mtf_bearish_pct:.0f}% bearish")
                        continue
                    mtf_aligned = mtf_bullish_pct >= 40 or mtf_bias in ['bullish', 'strong_bullish', 'neutral']
                elif direction == 'bearish':
                    if mtf_bullish_pct >= 55:
                        # Strong bullish market - block sell signal
                        logger.info(f"🚫 {instrument}: Blocking SELL - market is {mtf_bullish_pct:.0f}% bullish")
                        continue
                    mtf_aligned = mtf_bearish_pct >= 40 or mtf_bias in ['bearish', 'strong_bearish', 'neutral']

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

    def _is_market_open(self, instrument: str, now: datetime) -> Tuple[bool, str]:
        """
        Check if market is open for the given instrument.

        Returns:
            (is_open, reason) - True if market is open, with reason string

        Market Hours (EST):
        - Crypto (BTCUSD, ETHUSD): 24/7
        - Futures (MES, NQ, RTY, GC, MYM): Sun 6pm - Fri 5pm (with daily break 5-6pm)
        - Equities/ETFs: Mon-Fri 9:30am - 4pm
        """
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        hour = now.hour
        minute = now.minute

        # Crypto trades 24/7 — use comprehensive set
        if instrument.upper() in self.CRYPTO_TICKERS:
            return True, "crypto_24_7"

        # Forex trades 24/5 (Sun 5pm - Fri 5pm EST)
        forex_instruments = {'USDJPY', 'GBPJPY', 'EURUSD', 'GBPUSD', 'XAUUSD'}
        if instrument in forex_instruments:
            # Saturday: fully closed
            if weekday == 5:
                return False, "weekend_sat"
            # Sunday: opens at 5pm EST
            if weekday == 6:
                if hour < 17:
                    return False, "weekend_sun_before_open"
                return True, "forex_open"
            # Friday: closes at 5pm EST
            if weekday == 4:
                if hour >= 17:
                    return False, "weekend_fri_closed"
                return True, "forex_open"
            # Mon-Thu: 24 hours
            return True, "forex_open"

        # CFD Indices: Same as futures (Sun 6pm - Fri 5pm EST)
        cfd_instruments = {'US30', 'US500', 'USTEC', 'NAS100'}
        if instrument in cfd_instruments:
            # Saturday: fully closed
            if weekday == 5:
                return False, "weekend_sat"
            # Sunday: opens at 6pm EST
            if weekday == 6:
                if hour < 18:
                    return False, "weekend_sun_before_open"
                return True, "cfd_open"
            # Friday: closes at 5pm EST
            if weekday == 4:
                if hour >= 17:
                    return False, "weekend_fri_closed"
                return True, "cfd_open"
            # Mon-Thu: open except 5-6pm maintenance
            if 17 <= hour < 18:
                return False, "daily_maintenance"
            return True, "cfd_open"

        # Futures: Sunday 6pm EST to Friday 5pm EST
        # Daily maintenance break: 5pm-6pm EST (Mon-Thu)
        futures_instruments = {'MES', 'NQ', 'RTY', 'GC', 'MYM', 'MNQ', 'M2K', 'MGC'}
        if instrument in futures_instruments:
            # Saturday: fully closed
            if weekday == 5:
                return False, "weekend_sat"

            # Sunday: opens at 6pm EST
            if weekday == 6:
                if hour < 18:
                    return False, "weekend_sun_before_open"
                return True, "futures_open"

            # Friday: closes at 5pm EST
            if weekday == 4:
                if hour >= 17:
                    return False, "weekend_fri_closed"
                return True, "futures_open"

            # Mon-Thu: open except 5-6pm maintenance
            if 17 <= hour < 18:
                return False, "daily_maintenance"

            return True, "futures_open"

        # Default: assume equity hours (Mon-Fri 9:30am-4pm EST)
        if weekday >= 5:  # Saturday or Sunday
            return False, "weekend"

        # Pre-market starts 4am, regular 9:30am-4pm, after-hours until 8pm
        if hour < 4 or hour >= 20:
            return False, "outside_hours"

        return True, "equity_hours"

    def _fetch_instrument_data_sync(self, instrument: str, data_ticker: str, indicator_engine) -> Dict:
        """
        Synchronous helper to fetch multi-timeframe data for one instrument.
        Runs in a background thread to avoid blocking the event loop.
        """
        bars_by_tf = {}
        timeframes = ['5m', '15m', '30m', '1h', '4h']

        for tf in timeframes:
            try:
                # Convert timeframe to market_data_service format
                if tf == '5m':
                    bars = market_data_service.get_bars(data_ticker, timespan='minute', multiplier=5, limit=100)
                elif tf == '15m':
                    bars = market_data_service.get_bars(data_ticker, timespan='minute', multiplier=15, limit=100)
                elif tf == '30m':
                    bars = market_data_service.get_bars(data_ticker, timespan='minute', multiplier=30, limit=100)
                elif tf == '1h':
                    bars = market_data_service.get_bars(data_ticker, timespan='hour', multiplier=1, limit=100)
                elif tf == '4h':
                    bars = market_data_service.get_bars(data_ticker, timespan='hour', multiplier=4, limit=50)
                else:
                    continue

                if bars and len(bars) > 0:
                    bars_by_tf[tf] = indicator_engine.bars_to_dataframe(bars)
                    logger.debug(f"  {tf}: {len(bars)} bars fetched")

            except Exception as e:
                logger.debug(f"  {tf}: Failed to fetch bars - {e}")

        return bars_by_tf

    async def run_deterministic_cycle(self):
        """
        DETERMINISTIC Trading Mode - Uses real multi-timeframe indicators.
        NO AI/LLM involvement for entries - pure mathematical signals.

        Entry Rules:
        - EMA9 > EMA21 (or <) + RSI alignment
        - >=4/5 timeframes must agree
        - 1h and 4h must confirm direction
        - R:R >= 2:1 using ATR-based stops/targets
        - Confidence >= 75%

        All signals are logged to trade journal for forward testing.

        NOTE: Data fetching runs in background thread to avoid blocking event loop.
        """
        if not DETERMINISTIC_AVAILABLE:
            logger.warning("Deterministic indicators not available - install pandas-ta")
            return

        from zoneinfo import ZoneInfo
        EST = ZoneInfo('America/New_York')
        now = datetime.now(EST).replace(tzinfo=None)

        # Initialize indicator engine with our config
        try:
            indicator_config = IndicatorConfig(
                min_aligned_timeframes=self.deterministic_min_aligned_tfs,
                require_higher_tf_agreement=self.deterministic_require_higher_tf,
                min_confidence_score=self.deterministic_min_confidence,
                min_risk_reward=self.deterministic_min_rr
            )
            indicator_engine = get_indicator_engine(indicator_config)
        except Exception as e:
            logger.error(f"Failed to initialize indicator engine: {e}")
            return

        # Initialize trade journal
        trade_journal = None
        if TRADE_JOURNAL_AVAILABLE and self.enable_trade_journal:
            try:
                trade_journal = get_trade_journal()
            except Exception as e:
                logger.warning(f"Trade journal not available: {e}")

        signals_generated = 0

        for instrument in self._get_configured_scan_instruments():
            try:
                # Check if market is open for this instrument
                market_open, market_reason = self._is_market_open(instrument, now)
                if not market_open:
                    logger.debug(f"⏸️ Skipping {instrument}: market closed ({market_reason})")
                    continue

                # Rate limit: Don't scan same instrument more than once per interval
                last_scan = self.last_deterministic_scan.get(instrument)
                if last_scan and (now - last_scan).total_seconds() < self.deterministic_scan_interval:
                    continue

                if self._should_skip_polygon_only(instrument):
                    continue

                data_ticker = self._resolve_data_ticker(instrument)

                logger.info(f"📊 Deterministic: Analyzing {instrument} (data: {data_ticker})")

                # Fetch data in background thread to avoid blocking event loop
                bars_by_tf = await asyncio.to_thread(
                    self._fetch_instrument_data_sync,
                    instrument,
                    data_ticker,
                    indicator_engine
                )

                if len(bars_by_tf) < 3:
                    logger.debug(f"Insufficient timeframes for {instrument}: {len(bars_by_tf)}/5")
                    continue

                # Update last scan time
                self.last_deterministic_scan[instrument] = now

                # Run multi-timeframe analysis
                mtf_signal = indicator_engine.analyze_multi_timeframe(instrument, bars_by_tf)

                # Store MTF analysis for UI dashboard
                if hasattr(mtf_signal, 'tf_results') and mtf_signal.tf_results:
                    self.latest_mtf_analysis[instrument] = {}
                    for tf, tf_data in mtf_signal.tf_results.items():
                        self.latest_mtf_analysis[instrument][tf] = {
                            'timeframe': tf,
                            'close': tf_data.close,
                            'ema9': tf_data.ema9,
                            'ema21': tf_data.ema21,
                            'rsi14': tf_data.rsi14,
                            'macd_histogram': tf_data.macd_histogram,
                            'atr14': tf_data.atr14,
                            'volume_ratio': getattr(tf_data, 'volume_ratio', 1.0),
                            'volume_delta': getattr(tf_data, 'volume_delta', 0),
                            'bias': tf_data.bias,
                            'bias_strength': tf_data.bias_strength,
                            'ema_bullish': tf_data.ema9 > tf_data.ema21,
                            'rsi_bullish': tf_data.rsi14 > 50,
                            'macd_bullish': tf_data.macd_histogram > 0,
                            'volume_bullish': getattr(tf_data, 'volume_ratio', 1.0) > 1.2,
                        }

                # Log ALL signals to trade journal (for forward testing)
                if trade_journal:
                    try:
                        await trade_journal.log_signal(
                            ticker=instrument,
                            action=mtf_signal.action if mtf_signal.should_trade else 'none',
                            entry_price=mtf_signal.entry_price,
                            stop_loss=mtf_signal.stop_loss,
                            take_profit=mtf_signal.take_profit,
                            confidence=mtf_signal.confidence_score,
                            aligned_tfs=mtf_signal.aligned_bullish if mtf_signal.overall_bias == 'bullish' else mtf_signal.aligned_bearish,
                            bias=mtf_signal.overall_bias,
                            atr=mtf_signal.atr_for_stops,
                            risk_reward=mtf_signal.risk_reward_ratio,
                            rejection_reason=mtf_signal.rejection_reason if not mtf_signal.should_trade else None,
                            source='deterministic'
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log signal to journal: {e}")

                # Only generate webhook signal if conditions met
                if not mtf_signal.should_trade:
                    logger.info(f"📊 {instrument}: {mtf_signal.overall_bias.upper()} but NOT trading - {mtf_signal.rejection_reason}")
                    continue

                # Check for duplicate signal
                if self.is_duplicate_signal(instrument, mtf_signal.action):
                    logger.info(f"⏸️ SKIPPED: {instrument} {mtf_signal.action} - duplicate within cooldown")
                    continue

                # Build signal reason
                aligned_count = mtf_signal.aligned_bullish if mtf_signal.overall_bias == 'bullish' else mtf_signal.aligned_bearish
                reason = (
                    f"MTF: {mtf_signal.overall_bias.upper()} ({aligned_count}/5 TFs) | "
                    f"Conf={mtf_signal.confidence_score:.0f}% | "
                    f"R:R={mtf_signal.risk_reward_ratio:.1f}:1 | "
                    f"Entry={mtf_signal.entry_price:.2f} SL={mtf_signal.stop_loss:.2f} TP={mtf_signal.take_profit:.2f}"
                )

                # Create SmartFlow signal
                signal = SmartFlowSignal(
                    ticker=instrument,
                    action=mtf_signal.action,
                    score=mtf_signal.confidence_score,
                    price=mtf_signal.entry_price,
                    source='SmartFlow-Deterministic',
                    reason=reason,
                    confidence=mtf_signal.confidence_score,
                )

                # Store last signal
                self.last_signal[instrument] = signal
                signals_generated += 1

                # Add to recent signals log for UI
                self.recent_signal_log.append({
                    'ticker': instrument,
                    'action': mtf_signal.action,
                    'score': mtf_signal.confidence_score,
                    'confidence': mtf_signal.confidence_score,
                    'reason': reason,
                    'timestamp': now.strftime('%I:%M:%S %p'),
                    'strategy': 'deterministic'
                })
                # Keep only last N signals
                if len(self.recent_signal_log) > self.max_recent_signals:
                    self.recent_signal_log = self.recent_signal_log[-self.max_recent_signals:]

                # Update strategy stats
                self.strategy_stats['deterministic']['signals_generated'] += 1
                self.strategy_stats['deterministic']['last_signal_time'] = now.isoformat()

                # Create dummy sentiment for webhook posting
                dummy_sentiment = SentimentScore(
                    ticker=instrument,
                    score=mtf_signal.confidence_score if mtf_signal.action == 'buy' else -mtf_signal.confidence_score,
                    bullish_flows=mtf_signal.aligned_bullish,
                    bearish_flows=mtf_signal.aligned_bearish,
                    total_premium=0,
                    timestamp=now
                )

                logger.info(f"📊 DETERMINISTIC {mtf_signal.action.upper()}: {instrument} conf={mtf_signal.confidence_score:.0f}% R:R={mtf_signal.risk_reward_ratio:.1f}")
                await self.post_signal_to_webhooks(signal, dummy_sentiment)

            except Exception as e:
                logger.error(f"Deterministic error for {instrument}: {e}", exc_info=True)
            finally:
                await asyncio.sleep(self.per_ticker_delay_seconds)

        if signals_generated > 0:
            logger.info(f"📊 Deterministic cycle complete: {signals_generated} signals generated")
        else:
            logger.debug("📊 Deterministic cycle: No signals met criteria")

    async def run_quick_cycle(self):
        """
        QUICK MODE Trading - Fast 5-minute momentum signals.

        Unlike deterministic mode (which requires 4-5 TF alignment), quick mode:
        - Uses 5m timeframe primarily for entries
        - Optional 15m confirmation for trend filter
        - Lower confidence threshold (60% vs 75%)
        - Tighter stops, quicker targets (R:R 1.5:1)
        - More signals, faster execution

        Best for: Momentum plays, scalping, crypto volatility

        NOTE: Runs in parallel with deterministic mode for A/B comparison.
        """
        if not DETERMINISTIC_AVAILABLE:
            logger.warning("Quick mode requires pandas-ta indicators")
            return

        from zoneinfo import ZoneInfo
        EST = ZoneInfo('America/New_York')
        now = datetime.now(EST).replace(tzinfo=None)

        # Initialize indicator engine (simpler config for quick mode)
        try:
            indicator_config = IndicatorConfig(
                min_aligned_timeframes=1,  # Only need 5m (+ optional 15m)
                require_higher_tf_agreement=False,  # No 1h/4h requirement
                min_confidence_score=self.quick_min_confidence,
                min_risk_reward=self.quick_min_rr
            )
            indicator_engine = get_indicator_engine(indicator_config)
        except Exception as e:
            logger.error(f"Failed to initialize quick mode indicator engine: {e}")
            return

        # Initialize trade journal
        trade_journal = None
        if TRADE_JOURNAL_AVAILABLE and self.enable_trade_journal:
            try:
                trade_journal = get_trade_journal()
            except Exception as e:
                logger.warning(f"Trade journal not available: {e}")

        signals_generated = 0

        for instrument in self._get_configured_scan_instruments():
            try:
                # Check if market is open
                market_open, market_reason = self._is_market_open(instrument, now)
                if not market_open:
                    continue

                # Rate limit: Don't scan same instrument more than once per interval
                last_scan = self.last_quick_scan.get(instrument)
                if last_scan and (now - last_scan).total_seconds() < self.quick_scan_interval:
                    continue

                if self._should_skip_polygon_only(instrument):
                    continue

                data_ticker = self._resolve_data_ticker(instrument)

                # Fetch only 5m and optionally 15m data (fast)
                timeframes_to_fetch = ['5m']
                if self.quick_require_15m_confirmation:
                    timeframes_to_fetch.append('15m')

                bars_by_tf = await asyncio.to_thread(
                    self._fetch_quick_data_sync,
                    instrument,
                    data_ticker,
                    timeframes_to_fetch,
                    indicator_engine
                )

                if '5m' not in bars_by_tf or bars_by_tf['5m'] is None:
                    continue

                # Update last scan time
                self.last_quick_scan[instrument] = now

                # Analyze 5m data for quick signal
                quick_signal = self._analyze_quick_signal(
                    instrument, bars_by_tf, indicator_engine
                )

                if not quick_signal:
                    continue

                # Unpack quick signal
                action, confidence, entry_price, stop_loss, take_profit, reason = quick_signal

                # Log to trade journal with 'quick_5m' strategy tag
                if trade_journal:
                    try:
                        await trade_journal.log_signal(
                            ticker=instrument,
                            action=action,
                            entry_price=entry_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            confidence=confidence,
                            aligned_tfs=1 if not self.quick_require_15m_confirmation else 2,
                            bias=action,
                            atr=abs(entry_price - stop_loss),
                            risk_reward=self.quick_min_rr,
                            rejection_reason=None,
                            source='quick_5m'  # Strategy tag for tracking
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log quick signal to journal: {e}")

                # Check for duplicate
                if self.is_duplicate_signal(instrument, action):
                    logger.debug(f"⏸️ Quick mode: {instrument} {action} duplicate - skipping")
                    continue

                # Build reason string
                full_reason = f"QUICK-5M: {reason} | Conf={confidence:.0f}% | R:R={self.quick_min_rr}:1"

                # Create signal
                signal = SmartFlowSignal(
                    ticker=instrument,
                    action=action,
                    score=confidence,
                    price=entry_price,
                    source='SmartFlow-Quick5m',
                    reason=full_reason,
                    confidence=confidence,
                )

                # Update strategy stats
                self.strategy_stats['quick_5m']['signals_generated'] += 1
                self.strategy_stats['quick_5m']['last_signal_time'] = now.isoformat()

                self.last_signal[instrument] = signal
                signals_generated += 1

                # Add to recent signals log for UI
                self.recent_signal_log.append({
                    'ticker': instrument,
                    'action': action,
                    'score': confidence,
                    'confidence': confidence,
                    'reason': full_reason,
                    'timestamp': now.strftime('%I:%M:%S %p'),
                    'strategy': 'quick_5m'
                })
                # Keep only last N signals
                if len(self.recent_signal_log) > self.max_recent_signals:
                    self.recent_signal_log = self.recent_signal_log[-self.max_recent_signals:]

                # Create dummy sentiment for webhook
                dummy_sentiment = SentimentScore(
                    ticker=instrument,
                    score=confidence if action == 'buy' else -confidence,
                    bullish_flows=1 if action == 'buy' else 0,
                    bearish_flows=0 if action == 'buy' else 1,
                    total_premium=0,
                    timestamp=now
                )

                logger.info(f"⚡ QUICK {action.upper()}: {instrument} conf={confidence:.0f}% | {reason}")
                await self.post_signal_to_webhooks(signal, dummy_sentiment)

            except Exception as e:
                logger.error(f"Quick mode error for {instrument}: {e}", exc_info=True)
            finally:
                await asyncio.sleep(self.per_ticker_delay_seconds)

        if signals_generated > 0:
            logger.info(f"⚡ Quick mode cycle complete: {signals_generated} signals generated")

    def _fetch_quick_data_sync(self, instrument: str, data_ticker: str,
                                timeframes: List[str], indicator_engine) -> Dict:
        """Synchronous helper for quick mode - fetches only needed timeframes."""
        bars_by_tf = {}

        for tf in timeframes:
            try:
                # Determine limit based on timeframe
                limit = 100 if tf == '5m' else 50

                if tf == '5m':
                    bars = market_data_service.get_bars(data_ticker, timespan='minute', multiplier=5, limit=limit)
                elif tf == '15m':
                    bars = market_data_service.get_bars(data_ticker, timespan='minute', multiplier=15, limit=limit)
                else:
                    bars = None

                if bars and len(bars) >= 20:
                    bars_by_tf[tf] = bars

            except Exception as e:
                logger.debug(f"Quick mode: Failed to fetch {tf} for {instrument}: {e}")

        return bars_by_tf

    def _analyze_quick_signal(self, instrument: str, bars_by_tf: Dict,
                               indicator_engine) -> Optional[Tuple]:
        """
        Analyze 5m data for quick entry signal.

        Returns: (action, confidence, entry, stop, target, reason) or None
        """
        bars_5m = bars_by_tf.get('5m')
        if not bars_5m or len(bars_5m) < 30:
            return None

        try:
            import pandas as pd

            def _bars_to_df(bars):
                rows = []
                for bar in bars or []:
                    rows.append({
                        'timestamp': getattr(bar, 'timestamp', None),
                        'open': float(getattr(bar, 'open', 0) or 0),
                        'high': float(getattr(bar, 'high', 0) or 0),
                        'low': float(getattr(bar, 'low', 0) or 0),
                        'close': float(getattr(bar, 'close', 0) or 0),
                        'volume': float(getattr(bar, 'volume', 0) or 0),
                    })
                return pd.DataFrame(rows)

            tf_analysis = indicator_engine.calculate_indicators(_bars_to_df(bars_5m), '5m')

            if not tf_analysis:
                return None

            # Extract key values from single-timeframe analysis
            close = tf_analysis.close
            ema9 = tf_analysis.ema9
            ema21 = tf_analysis.ema21
            rsi = tf_analysis.rsi14
            macd_hist = tf_analysis.macd_histogram
            atr = tf_analysis.atr14
            volume_ratio = getattr(tf_analysis, 'volume_ratio', 1.0)

            # ========================================
            # VOLUME CONFIRMATION CHECK (REQUIRED)
            # ========================================
            # Quick mode now REQUIRES volume > 1.2x average to confirm momentum
            if self.quick_require_volume and volume_ratio < self.quick_min_volume_ratio:
                logger.debug(f"⏸️ Quick mode: {instrument} rejected - volume {volume_ratio:.1f}x < {self.quick_min_volume_ratio}x required")
                return None

            # Quick mode criteria:
            # 1. Fresh EMA crossover (EMA9 just crossed EMA21)
            # 2. RSI momentum (not overbought/oversold, showing direction)
            # 3. MACD histogram confirms direction
            # 4. Volume > 1.2x average (now required)

            # Check for bullish setup
            bullish_ema = ema9 > ema21
            bullish_rsi = 40 < rsi < 70  # Not oversold, not overbought
            bullish_macd = macd_hist > 0
            rsi_momentum_bull = rsi > self.quick_rsi_momentum_threshold
            volume_confirms = volume_ratio >= self.quick_min_volume_ratio

            # Check for bearish setup
            bearish_ema = ema9 < ema21
            bearish_rsi = 30 < rsi < 60
            bearish_macd = macd_hist < 0
            rsi_momentum_bear = rsi < (100 - self.quick_rsi_momentum_threshold)

            # Optional 15m confirmation
            bars_15m = bars_by_tf.get('15m')
            tf_15m_bullish = True  # Default if not required
            tf_15m_bearish = True

            if self.quick_require_15m_confirmation and bars_15m:
                try:
                    tf_15m = indicator_engine.calculate_indicators(_bars_to_df(bars_15m), '15m')
                    if tf_15m:
                        tf_15m_bullish = tf_15m.ema9 > tf_15m.ema21
                        tf_15m_bearish = tf_15m.ema9 < tf_15m.ema21
                except Exception:
                    pass

            # Calculate confidence score (0-100)
            bullish_score = 0
            bearish_score = 0

            # EMA crossover (40 points)
            if bullish_ema:
                bullish_score += 40
            if bearish_ema:
                bearish_score += 40

            # RSI momentum (25 points)
            if rsi_momentum_bull:
                bullish_score += 25
            if rsi_momentum_bear:
                bearish_score += 25

            # MACD direction (20 points)
            if bullish_macd:
                bullish_score += 20
            if bearish_macd:
                bearish_score += 20

            # 15m confirmation (15 points)
            if tf_15m_bullish:
                bullish_score += 15
            if tf_15m_bearish:
                bearish_score += 15

            # Determine signal
            action = None
            confidence = 0
            reason_parts = []

            if bullish_score >= self.quick_min_confidence and bullish_score > bearish_score:
                action = 'buy'
                confidence = bullish_score
                if bullish_ema:
                    reason_parts.append("EMA9>21")
                if rsi_momentum_bull:
                    reason_parts.append(f"RSI={rsi:.0f}")
                if bullish_macd:
                    reason_parts.append("MACD+")
                if tf_15m_bullish and self.quick_require_15m_confirmation:
                    reason_parts.append("15m-OK")
                if volume_confirms:
                    reason_parts.append(f"Vol={volume_ratio:.1f}x")  # Volume confirmation

            elif bearish_score >= self.quick_min_confidence and bearish_score > bullish_score:
                action = 'sell'
                confidence = bearish_score
                if bearish_ema:
                    reason_parts.append("EMA9<21")
                if rsi_momentum_bear:
                    reason_parts.append(f"RSI={rsi:.0f}")
                if bearish_macd:
                    reason_parts.append("MACD-")
                if tf_15m_bearish and self.quick_require_15m_confirmation:
                    reason_parts.append("15m-OK")
                if volume_confirms:
                    reason_parts.append(f"Vol={volume_ratio:.1f}x")  # Volume confirmation

            if not action:
                return None

            # Calculate stop and target using ATR
            entry_price = close
            if action == 'buy':
                stop_loss = close - (atr * self.quick_atr_stop_multiplier)
                take_profit = close + (atr * self.quick_atr_target_multiplier)
            else:
                stop_loss = close + (atr * self.quick_atr_stop_multiplier)
                take_profit = close - (atr * self.quick_atr_target_multiplier)

            reason = " | ".join(reason_parts)
            return (action, confidence, entry_price, stop_loss, take_profit, reason)

        except Exception as e:
            logger.error(f"Quick signal analysis error for {instrument}: {e}")
            return None

    async def run_strategy_engine_cycle(self, engine_type: str):
        """
        Run one of the 4 strategy engines for live signal generation.

        Engine types:
        - breakout: Compression + structural level breakouts
        - trend: Pullback entries in sustained trends
        - mean_reversion: Return to fair value in ranges
        - liquidity_reversal: False breakout / stop hunt detection

        Each engine uses the same signal context but applies different logic.
        """
        from zoneinfo import ZoneInfo
        EST = ZoneInfo('America/New_York')
        now = datetime.now(EST).replace(tzinfo=None)

        # Import strategy engines
        try:
            from app.services.strategy_engines import (
                get_engine, SignalContext, TradingSignal
            )
        except ImportError as e:
            logger.error(f"Strategy engines not available: {e}")
            return

        # Get the engine instance
        try:
            engine = get_engine(engine_type)
            logger.info(f"🎯 Running {engine_type} engine: {engine.strategy_id}")
        except Exception as e:
            logger.error(f"Failed to get {engine_type} engine: {e}")
            return

        # Initialize trade journal
        trade_journal = None
        if TRADE_JOURNAL_AVAILABLE and self.enable_trade_journal:
            try:
                trade_journal = get_trade_journal()
            except Exception as e:
                logger.warning(f"Trade journal not available: {e}")

        signals_generated = 0

        instruments = self._get_configured_scan_instruments()

        for instrument in instruments:
            try:
                await asyncio.sleep(0)  # Yield control

                # Check if market is open
                market_open, market_reason = self._is_market_open(instrument, now)
                if not market_open:
                    continue

                # Rate limit using engine-specific cache
                cache_key = f"{engine_type}_{instrument}"
                last_scan = getattr(self, '_strategy_engine_last_scan', {}).get(cache_key)
                scan_interval = getattr(self, 'deterministic_scan_interval', 60)
                if last_scan and (now - last_scan).total_seconds() < scan_interval:
                    continue

                if self._should_skip_polygon_only(instrument):
                    continue

                data_ticker = self._resolve_data_ticker(instrument)

                # Fetch market data (reuse deterministic data fetching)
                try:
                    indicator_config = IndicatorConfig(
                        min_aligned_timeframes=1,
                        require_higher_tf_agreement=False,
                        min_confidence_score=60.0,
                        min_risk_reward=1.5
                    )
                    indicator_engine = get_indicator_engine(indicator_config)

                    bars_by_tf = await asyncio.to_thread(
                        self._fetch_instrument_data_sync,
                        instrument,
                        data_ticker,
                        indicator_engine
                    )
                except Exception as e:
                    logger.debug(f"{engine_type} engine: data fetch failed for {instrument}: {e}")
                    continue

                if len(bars_by_tf) < 1:
                    continue

                # Update scan time
                if not hasattr(self, '_strategy_engine_last_scan'):
                    self._strategy_engine_last_scan = {}
                self._strategy_engine_last_scan[cache_key] = now

                # Build SignalContext from market data
                # Use the best available timeframe
                primary_tf = next(iter(bars_by_tf.keys()), '5m')
                df = bars_by_tf.get(primary_tf)

                if df is None or len(df) < 20:
                    continue

                context = SignalContext(
                    ticker=instrument,
                    df=df,
                    timestamp=now,
                    timeframe=primary_tf,
                    regime='neutral',  # Will be enriched by engine
                    flow_features={}  # Can add flow features if available
                )

                # Generate signal using the strategy engine
                signal = engine.generate_signal(context)

                if not signal or signal.direction == 'none' or not signal.is_valid:
                    if signal and signal.invalidation_reason:
                        logger.debug(f"{engine_type}: {instrument} - {signal.invalidation_reason}")
                    continue

                # Valid signal - convert to webhook format
                action = 'buy' if signal.direction == 'long' else 'sell'
                confidence = signal.confidence

                # Build signal for webhook
                webhook_signal = SmartFlowSignal(
                    ticker=instrument,
                    action=action,
                    score=confidence,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    entry_price=signal.entry_price,
                    reason=f"{engine_type.upper()}: {signal.reason or 'Strategy signal'}",
                    strategy='deterministic',  # Map to existing strategy type for webhook compatibility
                    confidence=confidence
                )

                # Update stats
                stat_key = f'{engine_type}_engine'
                if stat_key not in self.strategy_stats:
                    self.strategy_stats[stat_key] = {'signals_generated': 0, 'last_signal_time': None}
                self.strategy_stats[stat_key]['signals_generated'] += 1
                self.strategy_stats[stat_key]['last_signal_time'] = now.isoformat()

                self.last_signal[instrument] = webhook_signal
                signals_generated += 1

                # Add to recent signals log
                self.recent_signal_log.append({
                    'ticker': instrument,
                    'action': action,
                    'score': confidence,
                    'confidence': confidence,
                    'reason': signal.reason or f'{engine_type} signal',
                    'timestamp': now.strftime('%I:%M:%S %p'),
                    'strategy': f'{engine_type}_engine'
                })
                if len(self.recent_signal_log) > self.max_recent_signals:
                    self.recent_signal_log = self.recent_signal_log[-self.max_recent_signals:]

                # Log to trade journal
                if trade_journal:
                    try:
                        trade_journal.log_signal(
                            ticker=instrument,
                            action=action,
                            strategy=f'{engine_type}_engine',
                            entry=signal.entry_price,
                            stop=signal.stop_loss,
                            target=signal.take_profit,
                            confidence=confidence,
                            reason=signal.reason or f'{engine_type} signal'
                        )
                    except Exception as e:
                        logger.debug(f"Trade journal error: {e}")

                # Create dummy sentiment for webhook
                dummy_sentiment = SentimentScore(
                    ticker=instrument,
                    score=confidence if action == 'buy' else -confidence,
                    bullish_flows=1 if action == 'buy' else 0,
                    bearish_flows=0 if action == 'buy' else 1,
                    total_premium=0,
                    timestamp=now
                )

                logger.info(f"🎯 {engine_type.upper()} {action.upper()}: {instrument} "
                           f"conf={confidence:.0f}% entry={signal.entry_price:.2f} "
                           f"SL={signal.stop_loss:.2f} TP={signal.take_profit:.2f}")
                await self.post_signal_to_webhooks(webhook_signal, dummy_sentiment)

            except Exception as e:
                logger.error(f"{engine_type} engine error for {instrument}: {e}", exc_info=True)

        if signals_generated > 0:
            logger.info(f"🎯 {engine_type.upper()} engine cycle complete: {signals_generated} signals")

    async def run_cycle(self):
        """Run one SmartFlow analysis cycle"""
        if not self.enabled:
            return

        try:
            # Phase 8A: ADAPTIVE ROUTER INTEGRATION
            # Detect regime and route to best engine/strategy
            router_decision = None
            try:
                # Use global RegimeDetector alias (v2 if available, else v1)
                from app.services.smartflow_engine_router import get_router, DecisionSource
                from app.services.market_data_service import MarketDataService
                from app.db.database import SessionLocal
                import pandas as pd

                # Get market data for regime detection (use SPY as market proxy)
                market_data_service = MarketDataService()
                bars = market_data_service.get_bars('SPY', timespan='day', multiplier=1, limit=50)

                if bars and len(bars) > 0:
                    # Convert bars to DataFrame for regime detection
                    df = pd.DataFrame([{
                        'timestamp': bar.timestamp,
                        'open': bar.open,
                        'high': bar.high,
                        'low': bar.low,
                        'close': bar.close,
                        'volume': bar.volume
                    } for bar in bars])

                    # Fetch correlated assets for cross-asset analysis (MNQ/NQ→QQQ, MYM/US30→DIA, etc.)
                    correlation_tickers = {}
                    for corr_ticker in ['QQQ', 'IWM', 'DIA']:
                        try:
                            corr_bars = market_data_service.get_bars(corr_ticker, timespan='minute', multiplier=5, limit=100)
                            if corr_bars and len(corr_bars) > 20:
                                correlation_tickers[corr_ticker] = pd.DataFrame([{
                                    'timestamp': bar.timestamp,
                                    'open': bar.open,
                                    'high': bar.high,
                                    'low': bar.low,
                                    'close': bar.close,
                                    'volume': bar.volume
                                } for bar in corr_bars])
                        except Exception as corr_err:
                            logger.debug(f"Could not fetch {corr_ticker} for correlation: {corr_err}")

                    # Detect regime with cross-asset correlation
                    detector = RegimeDetector()
                    regime_analysis = detector.detect_regime(df, 'SPY', correlation_tickers=correlation_tickers if correlation_tickers else None)
                    logger.info(
                        f"📊 Regime detected: {regime_analysis.primary_regime} "
                        f"(confidence: {regime_analysis.classification_confidence:.2f})"
                    )

                    # Get router decision with db session for strategy registry
                    db = SessionLocal()
                    try:
                        router = get_router(db)
                        router_decision = router.route_signal_request(
                            regime=regime_analysis.primary_regime,
                            regime_confidence=regime_analysis.classification_confidence
                        )

                        logger.info(
                            f"🎯 Router decision: {router_decision.selected_engine} / "
                            f"{router_decision.selected_strategy_id} "
                            f"(source: {router_decision.decision_source}, "
                            f"status: {router_decision.strategy_status})"
                        )
                    finally:
                        db.close()
                else:
                    logger.warning("Could not get market data for regime detection - using default routing")

            except Exception as e:
                logger.error(f"Router decision error: {e} - using default engine selection")

            # Phase 9: PORTFOLIO ALLOCATOR INTEGRATION
            # Score eligible strategies and compute allocation weights
            allocation_decision = None
            try:
                from app.services.strategy_allocator import StrategyAllocator
                from app.services.ai_feature_engine import get_ai_feature_engine
                from app.db.database import SessionLocal

                # Get AI features for signal ticker (if available)
                ai_features = None
                try:
                    ai_engine = get_ai_feature_engine()
                    # Use regime from regime_analysis if available
                    current_regime = regime_analysis.primary_regime.value if 'regime_analysis' in locals() and regime_analysis else None
                    ai_features = ai_engine.get_feature_dict('SPY', regime=current_regime)
                    logger.info(f"🤖 AI features: bias={ai_features['overall_ai_bias']:.3f}, conf={ai_features['confidence']:.2f}")
                except Exception as ai_err:
                    logger.debug(f"AI feature generation error: {ai_err}")

                # Get allocation decision
                db = SessionLocal()
                try:
                    allocator = StrategyAllocator(db)

                    # If router selected a specific strategy from comparison data, use it
                    # Otherwise (DEFAULT source), let allocator use ALL eligible strategies
                    strategy_ids = None
                    engine_type = None
                    if router_decision and router_decision.decision_source != DecisionSource.DEFAULT:
                        # Router has comparison-backed decision - use specific strategy
                        if router_decision.selected_strategy_id:
                            strategy_ids = [router_decision.selected_strategy_id]
                        elif router_decision.selected_engine:
                            engine_type = router_decision.selected_engine
                    # When DEFAULT source, strategy_ids=None means allocator picks ALL eligible

                    # Compute allocation with AI features
                    allocation_decision = allocator.compute_allocation(
                        strategy_ids=strategy_ids,
                        engine_type=engine_type,
                        regime=regime_analysis.primary_regime.value if 'regime_analysis' in locals() and regime_analysis else None,
                        regime_confidence=regime_analysis.classification_confidence if 'regime_analysis' in locals() and regime_analysis else None,
                        ai_features=ai_features
                    )

                    # Store allocation decision for signal metadata
                    self._current_allocation_decision = allocation_decision

                    # Log allocation summary
                    if allocation_decision.selected_strategies:
                        weights_str = ", ".join(
                            f"{s.strategy_id}:{s.allocation_weight:.2f}"
                            for s in allocation_decision.selected_strategies
                        )
                        logger.info(f"💰 Allocation weights: {weights_str}")
                    else:
                        logger.warning("⚠️ No strategies selected by allocator")

                finally:
                    db.close()

            except Exception as e:
                logger.error(f"Allocator decision error: {e} - continuing with router-only selection")
                self._current_allocation_decision = None

            # Phase 8A: Use router decision to control engine execution
            # If router made a decision, use it; otherwise use default flags
            if router_decision:
                selected_engine = router_decision.selected_engine

                # Respect slim-map honesty: if the selected engine is not eligible in the
                # current runtime mode, fall back to unified instead of silently running it.
                try:
                    from app.services.smartflow_engine_router import (
                        SLIM_MAP_ENABLED,
                        is_engine_slim_map_eligible,
                    )
                    if SLIM_MAP_ENABLED and not is_engine_slim_map_eligible(selected_engine):
                        logger.warning(
                            f"⚠️ Router selected non-slim-map engine '{selected_engine}'. Falling back to 'unified'."
                        )
                        selected_engine = 'unified'
                        router_decision.selected_engine = 'unified'
                        router_decision.decision_reason = (
                            f"{router_decision.decision_reason} | fallback_to_unified_due_to_slim_map"
                        )
                except Exception as e:
                    logger.warning(f"Router eligibility check failed: {e}")

                # Enable only the selected engine
                run_deterministic = (selected_engine == 'deterministic')
                run_quick = (selected_engine == 'quick')
                run_unified = (selected_engine == 'unified')
                run_ai = (selected_engine == 'ai')
                run_flow = (selected_engine == 'flow')

                # Phase 14: 4 Core Strategy Engines
                run_breakout = (selected_engine == 'breakout')
                run_trend = (selected_engine == 'trend')
                run_mean_reversion = (selected_engine == 'mean_reversion')
                run_liquidity_reversal = (selected_engine == 'liquidity_reversal')

                # Store decision for signal metadata
                self._current_router_decision = router_decision
            else:
                # Fallback to original behavior (hardcoded flags)
                run_deterministic = self.enable_deterministic_mode
                run_quick = self.enable_quick_mode
                run_unified = False  # Not implemented yet
                run_ai = self.enable_ai_only_mode
                run_flow = False  # Flow runs separately below

                # Phase 14: Strategy engines default off unless router selects
                run_breakout = False
                run_trend = False
                run_mean_reversion = False
                run_liquidity_reversal = False

                self._current_router_decision = None

            # QUICK MODE: Primary engine - runs first for fast momentum entries
            if run_quick and DETERMINISTIC_AVAILABLE:
                try:
                    await self.run_quick_cycle()
                except Exception as e:
                    logger.error(f"Quick mode cycle error: {e}")

            # DETERMINISTIC MODE: Secondary engine - runs after quick for confirmation signals
            if run_deterministic and DETERMINISTIC_AVAILABLE:
                try:
                    await self.run_deterministic_cycle()
                except Exception as e:
                    logger.error(f"Deterministic cycle error: {e}")

            # BREAKOUT ENGINE: Compression + structural level breakouts
            if run_breakout:
                try:
                    await self.run_strategy_engine_cycle('breakout')
                except Exception as e:
                    logger.error(f"Breakout engine error: {e}")

            # TREND ENGINE: Pullback entries in sustained trends
            if run_trend:
                try:
                    await self.run_strategy_engine_cycle('trend')
                except Exception as e:
                    logger.error(f"Trend engine error: {e}")

            # MEAN REVERSION ENGINE: Return to fair value in ranges
            if run_mean_reversion:
                try:
                    await self.run_strategy_engine_cycle('mean_reversion')
                except Exception as e:
                    logger.error(f"Mean reversion engine error: {e}")

            # LIQUIDITY REVERSAL ENGINE: False breakout / stop hunt detection
            if run_liquidity_reversal:
                try:
                    await self.run_strategy_engine_cycle('liquidity_reversal')
                except Exception as e:
                    logger.error(f"Liquidity reversal engine error: {e}")

            # AI-ONLY MODE: Run for 24/7 markets (crypto, forex) or after hours
            # This runs INDEPENDENTLY of flow data and router decisions
            if self.enable_ai_only_mode and AI_STRATEGY_AVAILABLE:
                try:
                    # Use module-level datetime import (don't shadow it)
                    now = datetime.now()
                    # Check if we're outside regular market hours (9:30 AM - 4:00 PM EST)
                    is_after_hours = now.hour < 9 or now.hour >= 16 or (now.hour == 9 and now.minute < 30)
                    is_weekend = now.weekday() >= 5

                    if is_after_hours or is_weekend:
                        logger.info(f"🌙 SmartFlow: After hours/weekend - running AI-only mode for 24/7 markets (crypto, forex, futures)")
                        await self.run_ai_only_cycle()
                except Exception as e:
                    logger.error(f"AI-only mode error: {e}", exc_info=True)

            # Fetch fresh flow data
            flows = await self.fetch_flow_data()
            if not flows:
                # No flow data during market hours - run AI-only if enabled
                if self.enable_ai_only_mode and AI_STRATEGY_AVAILABLE:
                    logger.info("📊 SmartFlow: No flow data - running AI-only mode (crypto, forex, futures)")
                    await self.run_ai_only_cycle()
                else:
                    logger.info("📊 SmartFlow cycle: No flow data available")
                return

            logger.info(f"📊 SmartFlow cycle: Processing {len(flows)} flows")

            tracked_tickers = self._get_configured_scan_instruments()

            # Compute sentiment for each tracked ticker
            scores_summary = []
            for ticker in tracked_tickers:
                if self._should_skip_polygon_only(ticker):
                    continue
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
                    # OpenClaw AI signal validation (if available)
                    # OpenClaw validation removed - signals pass through directly
                    signal.reason = (signal.reason or '') + ' | OpenClaw: BYPASSED'
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

        tracked_tickers = self._get_configured_scan_instruments()

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
            'ai_available': AI_STRATEGY_AVAILABLE,
            # Deterministic Mode (NO AI for entries)
            'enable_deterministic_mode': self.enable_deterministic_mode,
            'deterministic_available': DETERMINISTIC_AVAILABLE,
            'deterministic_min_confidence': self.deterministic_min_confidence,
            'deterministic_min_rr': self.deterministic_min_rr,
            'deterministic_min_aligned_tfs': self.deterministic_min_aligned_tfs,
            'deterministic_instruments': self.deterministic_instruments,
            'deterministic_scan_interval': self.deterministic_scan_interval,
            'deterministic_rr_preset': self.deterministic_rr_preset,
            'deterministic_rr_presets': self.deterministic_rr_presets,
            # Trade Journal
            'enable_trade_journal': self.enable_trade_journal,
            'trade_journal_available': TRADE_JOURNAL_AVAILABLE,
            # Flow Confirmation (A/B Testing)
            'use_flow_confirmation': self.use_flow_confirmation,
            'use_polygon_options_flow': self.use_polygon_options_flow,
            # Quick Mode (5-minute momentum)
            'enable_quick_mode': self.enable_quick_mode,
            'quick_scan_interval': self.quick_scan_interval,
            'quick_min_confidence': self.quick_min_confidence,
            'quick_require_15m_confirmation': self.quick_require_15m_confirmation,
            'quick_min_rr': self.quick_min_rr,
            'quick_instruments': self.quick_instruments,
            # Strategy Performance Tracking (from DB, not in-memory)
            'strategy_stats': self._get_strategy_stats_from_db(),
            # MTF Analysis (for UI dashboard)
            'mtf_analysis': self.latest_mtf_analysis,
            # Recent signals log
            'recent_signals': self.recent_signal_log[-20:] if self.recent_signal_log else [],
            # Flow data source toggles
            'use_flowalgo_flow': self.use_flowalgo_flow,
            # Latency Stats
            'latency_target_ms': self.latency_target_ms,
            'latency_stats': self._get_latency_stats(),
            # ========================================
            # ELITE QUANT MODULES (2026)
            # ========================================
            'regime_detector_available': REGIME_DETECTOR_AVAILABLE,
            'enable_regime_detection': self.enable_regime_detection,
            'ensemble_scorer_available': ENSEMBLE_SCORER_AVAILABLE,
            'enable_ensemble_scoring': self.enable_ensemble_scoring,
            'ensemble_min_probability': self.ensemble_min_probability,
            'risk_manager_available': RISK_MANAGER_AVAILABLE,
            'enable_risk_manager': self.enable_risk_manager,
            'current_regime': self.current_regime,  # Current regime per instrument
            # Data Freshness & Signal Expiry
            'signal_ttl_minutes': self.signal_ttl_minutes,
            'enable_stale_data_alerts': self.enable_stale_data_alerts,
            'data_freshness': self.last_data_freshness,
            'stale_data_signals_blocked': self.stale_data_signals_blocked,
            # Quick Mode volume requirements
            'quick_require_volume': self.quick_require_volume,
            'quick_min_volume_ratio': self.quick_min_volume_ratio,
            # ========================================
            # ADAPTIVE LEARNING (2026)
            # ========================================
            'adaptive_learning_available': ADAPTIVE_LEARNING_AVAILABLE,
            'regime_detector_v2_available': REGIME_DETECTOR_V2_AVAILABLE if 'REGIME_DETECTOR_V2_AVAILABLE' in dir() else False,
            'adaptive_learning_status': self._get_adaptive_learning_status(),
        }

    def _get_adaptive_learning_status(self) -> Dict[str, Any]:
        """Get adaptive learning system status."""
        if not ADAPTIVE_LEARNING_AVAILABLE:
            return {'available': False}
        try:
            mgr = get_adaptive_manager()
            return {
                'available': True,
                **mgr.get_status()
            }
        except Exception as e:
            return {'available': False, 'error': str(e)}

    def _get_strategy_stats_from_db(self) -> Dict[str, Dict]:
        """
        Get actual strategy stats from database instead of in-memory counters.
        This ensures stats persist across container restarts.
        """
        from app.core.database import SessionLocal
        from sqlalchemy import text

        # Default stats structure
        default_stats = {
            'deterministic': {
                'signals_generated': 0,
                'trades_won': 0,
                'trades_lost': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'avg_rr_achieved': 0.0,
                'last_signal_time': None,
            },
            'quick_5m': {
                'signals_generated': 0,
                'trades_won': 0,
                'trades_lost': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'avg_rr_achieved': 0.0,
                'last_signal_time': None,
            }
        }

        try:
            db = SessionLocal()

            # Query for strategy stats by mode (30-day window)
            query = text('''
                WITH mode_stats AS (
                    SELECT
                        CASE
                            WHEN reason ILIKE '%QUICK%' THEN 'quick_5m'
                            WHEN reason ILIKE '%Deterministic%' OR reason ILIKE '%MTF:%' OR reason ILIKE '%aligned%' THEN 'deterministic'
                            ELSE NULL
                        END as mode,
                        COUNT(*) as signals_generated,
                        SUM(CASE WHEN so.is_winner = true OR (so.is_winner IS NULL AND el.pnl > 0) THEN 1 ELSE 0 END) as trades_won,
                        SUM(CASE WHEN so.is_winner = false OR (so.is_winner IS NULL AND el.pnl < 0) THEN 1 ELSE 0 END) as trades_lost,
                        SUM(COALESCE(so.pnl, el.pnl, 0)) as total_pnl,
                        MAX(sl.created_at) as last_signal_time
                    FROM smartflow_signal_logs sl
                    LEFT JOIN smartflow_signal_outcomes so ON so.signal_log_id = sl.id
                    LEFT JOIN execution_logs el ON el.smartflow_signal_log_id = sl.id AND el.status = 'success'
                    WHERE sl.created_at > NOW() - INTERVAL '30 days'
                    GROUP BY mode
                )
                SELECT mode, signals_generated, trades_won, trades_lost, total_pnl, last_signal_time
                FROM mode_stats
                WHERE mode IS NOT NULL
            ''')

            results = db.execute(query).fetchall()

            for row in results:
                mode, signals, wins, losses, pnl, last_time = row
                if mode in default_stats:
                    closed = (wins or 0) + (losses or 0)
                    default_stats[mode] = {
                        'signals_generated': signals or 0,
                        'trades_won': wins or 0,
                        'trades_lost': losses or 0,
                        'total_pnl': round(float(pnl or 0), 2),
                        'win_rate': round((wins / closed * 100), 1) if closed > 0 else 0.0,
                        'avg_rr_achieved': 0.0,  # Would need trade journal for accurate R:R
                        'last_signal_time': last_time.isoformat() if last_time else None,
                    }

            db.close()
        except Exception as e:
            logger.warning(f"Could not fetch strategy stats from DB: {e}")

        return default_stats

    def _get_latency_stats(self) -> Dict[str, Any]:
        """Calculate latency statistics from history."""
        if not self.latency_history:
            return {
                'count': 0,
                'avg_ms': 0,
                'min_ms': 0,
                'max_ms': 0,
                'under_target_pct': 0,
                'recent': []
            }

        latencies = [r['total_latency_ms'] for r in self.latency_history]
        under_target = sum(1 for r in self.latency_history if r['under_target'])

        return {
            'count': len(latencies),
            'avg_ms': sum(latencies) / len(latencies),
            'min_ms': min(latencies),
            'max_ms': max(latencies),
            'under_target_pct': (under_target / len(latencies)) * 100,
            'recent': self.latency_history[-10:]  # Last 10 records
        }


# Global instance
smartflow_service = SmartFlowService()

# Load historical scores from database into cache on startup
smartflow_service.load_recent_scores_from_db()
