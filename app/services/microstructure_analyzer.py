"""
Microstructure Analyzer - 2026 Alternative Data Edge
=====================================================

Non-TA signals that provide edge in saturated markets:
- Order book imbalance (bid/ask size ratio)
- Cumulative delta (aggressive buying vs selling)
- Level 2 depth analysis
- Trade flow toxicity (VPIN-like metric)
- Quote stuffing detection

Data sources:
- Polygon Level 2 (if available)
- IBKR TWS API (cheaper alternative)
- Exchange WebSocket feeds

Pi5 optimized: Rolling calculations, ~50ms per update
"""

import logging
import numpy as np
import asyncio
from typing import Dict, Optional, List, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from enum import Enum
import threading

logger = logging.getLogger(__name__)

# Try to import ibapi (Interactive Brokers)
try:
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
    IBKR_AVAILABLE = True
except ImportError:
    IBKR_AVAILABLE = False
    EClient = None
    EWrapper = None


class MicrostructureSignal(Enum):
    """Microstructure signal types"""
    STRONG_BID = "strong_bid"      # Aggressive buying, expect price up
    STRONG_ASK = "strong_ask"      # Aggressive selling, expect price down
    BALANCED = "balanced"          # No clear direction
    ABSORPTION = "absorption"      # Large orders being absorbed
    EXHAUSTION = "exhaustion"      # Momentum exhausting
    SWEEP = "sweep"                # Price sweeping through levels


@dataclass
class OrderBookLevel:
    """Single level of order book"""
    price: float
    size: int
    orders: int = 1  # Number of orders at this level
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class OrderBookSnapshot:
    """Complete order book snapshot"""
    ticker: str
    timestamp: datetime

    # Bid side (sorted high to low)
    bids: List[OrderBookLevel] = field(default_factory=list)

    # Ask side (sorted low to high)
    asks: List[OrderBookLevel] = field(default_factory=list)

    # Derived metrics
    bid_total_size: int = 0
    ask_total_size: int = 0
    imbalance_ratio: float = 0.0  # (bid - ask) / (bid + ask)

    # Depth at levels
    bid_depth_5: int = 0  # Size within 5 levels
    ask_depth_5: int = 0

    # Spread
    spread: float = 0.0
    spread_bps: float = 0.0
    mid_price: float = 0.0


@dataclass
class CumulativeDelta:
    """Cumulative delta tracking"""
    ticker: str
    timestamp: datetime

    # Delta (buy volume - sell volume)
    delta: float = 0.0  # Current bar delta
    cumulative_delta: float = 0.0  # Running total

    # Volume classification
    buy_volume: int = 0  # Trades at ask
    sell_volume: int = 0  # Trades at bid
    neutral_volume: int = 0  # Trades between bid/ask

    # Delta momentum
    delta_ma_5: float = 0.0  # 5-bar delta MA
    delta_zscore: float = 0.0  # How unusual is current delta

    # Divergence
    price_delta_divergence: bool = False  # Price up but delta down, or vice versa


@dataclass
class MicrostructureAnalysis:
    """Complete microstructure analysis"""
    ticker: str
    timestamp: datetime

    # Order book metrics
    order_book: Optional[OrderBookSnapshot] = None

    # Cumulative delta
    cum_delta: Optional[CumulativeDelta] = None

    # Combined signal
    signal: MicrostructureSignal = MicrostructureSignal.BALANCED
    signal_strength: float = 0.0  # 0-100

    # Trade flow toxicity (VPIN-like)
    vpin_estimate: float = 0.5  # 0.5 = balanced, >0.7 = toxic

    # Quote activity
    quote_intensity: float = 0.0  # Quotes per second
    is_quote_stuffing: bool = False  # Possible manipulation

    # Ensemble features (for ML)
    features: Dict[str, float] = field(default_factory=dict)

    # Valid until
    valid_for_seconds: int = 30


@dataclass
class MicrostructureConfig:
    """Configuration for microstructure analysis"""
    # Order book levels to track
    depth_levels: int = 10

    # Imbalance thresholds
    imbalance_strong_threshold: float = 0.3  # >30% imbalance = strong
    imbalance_weak_threshold: float = 0.1

    # Delta thresholds
    delta_zscore_threshold: float = 2.0  # >2 std = significant

    # VPIN parameters
    vpin_bucket_size: int = 50  # Volume bucket size
    vpin_lookback_buckets: int = 50

    # Quote stuffing detection
    quote_stuffing_threshold: float = 100  # Quotes per second

    # Data source priority
    use_polygon_l2: bool = True
    use_ibkr: bool = True

    # IBKR connection
    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 7497  # Paper trading port
    ibkr_client_id: int = 1


class MicrostructureAnalyzer:
    """
    Microstructure data analyzer for alternative alpha.

    Provides non-TA signals:
    - Order book imbalance (institutional footprint)
    - Cumulative delta (aggressive buyer/seller detection)
    - VPIN-like toxicity (informed trading detection)
    - Quote activity analysis
    """

    def __init__(self, config: Optional[MicrostructureConfig] = None):
        self.config = config or MicrostructureConfig()

        # Order book cache
        self.order_books: Dict[str, OrderBookSnapshot] = {}

        # Delta tracking
        self.delta_history: Dict[str, deque] = {}
        self.cumulative_deltas: Dict[str, float] = {}
        self.max_delta_history = 500

        # Trade classification
        self.trade_history: Dict[str, deque] = {}
        self.max_trade_history = 1000

        # Quote tracking for stuffing detection
        self.quote_counts: Dict[str, deque] = {}

        # VPIN tracking
        self.vpin_buckets: Dict[str, deque] = {}

        # IBKR client (if available)
        self.ibkr_client = None
        self.ibkr_connected = False

        # Callbacks for real-time updates
        self.on_book_update: Optional[Callable] = None
        self.on_trade: Optional[Callable] = None

        logger.info(
            f"MicrostructureAnalyzer initialized: "
            f"depth={self.config.depth_levels}, "
            f"IBKR_AVAILABLE={IBKR_AVAILABLE}"
        )

    # ========================================
    # ORDER BOOK ANALYSIS
    # ========================================

    def update_order_book(
        self,
        ticker: str,
        bids: List[Tuple[float, int]],  # [(price, size), ...]
        asks: List[Tuple[float, int]],
        timestamp: Optional[datetime] = None
    ) -> OrderBookSnapshot:
        """
        Update order book and calculate metrics.

        Args:
            ticker: Symbol
            bids: List of (price, size) tuples, sorted high to low
            asks: List of (price, size) tuples, sorted low to high
            timestamp: Optional timestamp

        Returns:
            OrderBookSnapshot with calculated metrics
        """
        ts = timestamp or datetime.now()

        snapshot = OrderBookSnapshot(
            ticker=ticker,
            timestamp=ts
        )

        # Convert to OrderBookLevel objects
        snapshot.bids = [
            OrderBookLevel(price=p, size=s, timestamp=ts)
            for p, s in bids[:self.config.depth_levels]
        ]
        snapshot.asks = [
            OrderBookLevel(price=p, size=s, timestamp=ts)
            for p, s in asks[:self.config.depth_levels]
        ]

        # Calculate totals
        snapshot.bid_total_size = sum(b.size for b in snapshot.bids)
        snapshot.ask_total_size = sum(a.size for a in snapshot.asks)

        # Imbalance ratio: (bid - ask) / (bid + ask)
        total = snapshot.bid_total_size + snapshot.ask_total_size
        if total > 0:
            snapshot.imbalance_ratio = (
                (snapshot.bid_total_size - snapshot.ask_total_size) / total
            )

        # Depth at 5 levels
        snapshot.bid_depth_5 = sum(b.size for b in snapshot.bids[:5])
        snapshot.ask_depth_5 = sum(a.size for a in snapshot.asks[:5])

        # Spread calculation
        if snapshot.bids and snapshot.asks:
            best_bid = snapshot.bids[0].price
            best_ask = snapshot.asks[0].price
            snapshot.spread = best_ask - best_bid
            snapshot.mid_price = (best_bid + best_ask) / 2
            if snapshot.mid_price > 0:
                snapshot.spread_bps = (snapshot.spread / snapshot.mid_price) * 10000

        # Cache
        self.order_books[ticker] = snapshot

        # Track quote intensity
        self._track_quote(ticker, ts)

        # Callback
        if self.on_book_update:
            self.on_book_update(snapshot)

        return snapshot

    def _track_quote(self, ticker: str, timestamp: datetime):
        """Track quote arrivals for stuffing detection."""
        if ticker not in self.quote_counts:
            self.quote_counts[ticker] = deque(maxlen=1000)

        self.quote_counts[ticker].append(timestamp)

    def get_quote_intensity(self, ticker: str, window_seconds: int = 1) -> float:
        """Calculate quotes per second over window."""
        if ticker not in self.quote_counts:
            return 0.0

        now = datetime.now()
        cutoff = now - timedelta(seconds=window_seconds)

        recent = [t for t in self.quote_counts[ticker] if t >= cutoff]
        return len(recent) / window_seconds

    # ========================================
    # CUMULATIVE DELTA
    # ========================================

    def classify_trade(
        self,
        ticker: str,
        price: float,
        size: int,
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Classify trade as buy or sell based on order book.

        Uses tick rule: Compare to last trade and bid/ask.
        - At/above ask = buy (aggressive buyer)
        - At/below bid = sell (aggressive seller)
        - Between = use tick rule

        Returns: 'buy', 'sell', or 'neutral'
        """
        book = self.order_books.get(ticker)

        if not book or not book.bids or not book.asks:
            return 'neutral'

        best_bid = book.bids[0].price
        best_ask = book.asks[0].price
        mid = book.mid_price

        if price >= best_ask:
            return 'buy'
        elif price <= best_bid:
            return 'sell'
        else:
            # Between bid and ask - use proximity
            if price > mid:
                return 'buy'
            elif price < mid:
                return 'sell'
            else:
                return 'neutral'

    def update_delta(
        self,
        ticker: str,
        price: float,
        size: int,
        side: Optional[str] = None,  # 'buy', 'sell', or None to auto-classify
        timestamp: Optional[datetime] = None
    ) -> CumulativeDelta:
        """
        Update cumulative delta with new trade.

        Args:
            ticker: Symbol
            price: Trade price
            size: Trade size
            side: Trade side (auto-classified if None)
            timestamp: Trade timestamp

        Returns:
            Updated CumulativeDelta
        """
        ts = timestamp or datetime.now()

        # Auto-classify if not provided
        if side is None:
            side = self.classify_trade(ticker, price, size, ts)

        # Initialize history
        if ticker not in self.delta_history:
            self.delta_history[ticker] = deque(maxlen=self.max_delta_history)
            self.cumulative_deltas[ticker] = 0.0
            self.trade_history[ticker] = deque(maxlen=self.max_trade_history)

        # Record trade
        trade = {
            'price': price,
            'size': size,
            'side': side,
            'timestamp': ts
        }
        self.trade_history[ticker].append(trade)

        # Calculate delta
        if side == 'buy':
            delta = size
        elif side == 'sell':
            delta = -size
        else:
            delta = 0

        # Update cumulative
        self.cumulative_deltas[ticker] += delta
        self.delta_history[ticker].append(delta)

        # Build result
        result = CumulativeDelta(
            ticker=ticker,
            timestamp=ts,
            delta=delta,
            cumulative_delta=self.cumulative_deltas[ticker]
        )

        # Calculate buy/sell volume
        recent_trades = list(self.trade_history[ticker])[-100:]
        result.buy_volume = sum(t['size'] for t in recent_trades if t['side'] == 'buy')
        result.sell_volume = sum(t['size'] for t in recent_trades if t['side'] == 'sell')
        result.neutral_volume = sum(t['size'] for t in recent_trades if t['side'] == 'neutral')

        # Delta moving average and z-score
        deltas = list(self.delta_history[ticker])
        if len(deltas) >= 5:
            result.delta_ma_5 = np.mean(deltas[-5:])

        if len(deltas) >= 20:
            delta_std = np.std(deltas[-20:])
            if delta_std > 0:
                result.delta_zscore = (delta - np.mean(deltas[-20:])) / delta_std

        # Callback
        if self.on_trade:
            self.on_trade(result)

        # Update VPIN
        self._update_vpin(ticker, side, size)

        return result

    # ========================================
    # VPIN (Volume-Synchronized Probability of Informed Trading)
    # ========================================

    def _update_vpin(self, ticker: str, side: str, size: int):
        """
        Update VPIN estimate.

        VPIN approximates the probability of informed trading by
        measuring order flow imbalance in volume buckets.
        """
        if ticker not in self.vpin_buckets:
            self.vpin_buckets[ticker] = deque(maxlen=self.config.vpin_lookback_buckets)

        # For simplicity, use each trade as a "micro-bucket"
        # In production, aggregate to fixed volume buckets

        if side == 'buy':
            imbalance = 1.0
        elif side == 'sell':
            imbalance = -1.0
        else:
            imbalance = 0.0

        self.vpin_buckets[ticker].append((size, imbalance))

    def get_vpin(self, ticker: str) -> float:
        """
        Get current VPIN estimate.

        Returns: 0 to 1, where >0.7 indicates high probability
                 of informed trading (toxic flow)
        """
        if ticker not in self.vpin_buckets:
            return 0.5

        buckets = list(self.vpin_buckets[ticker])
        if len(buckets) < 10:
            return 0.5

        # Calculate absolute order imbalance
        total_volume = sum(b[0] for b in buckets)
        if total_volume == 0:
            return 0.5

        # Sum of absolute imbalances
        abs_imbalance = sum(abs(b[0] * b[1]) for b in buckets)

        # VPIN = abs_imbalance / total_volume
        vpin = abs_imbalance / total_volume

        return min(1.0, vpin)

    # ========================================
    # COMBINED ANALYSIS
    # ========================================

    def analyze(
        self,
        ticker: str,
        include_features: bool = True
    ) -> MicrostructureAnalysis:
        """
        Run complete microstructure analysis.

        Args:
            ticker: Symbol to analyze
            include_features: Whether to build ML feature dict

        Returns:
            MicrostructureAnalysis with all metrics
        """
        now = datetime.now()

        analysis = MicrostructureAnalysis(
            ticker=ticker,
            timestamp=now
        )

        # Get order book
        analysis.order_book = self.order_books.get(ticker)

        # Get cumulative delta
        if ticker in self.delta_history and self.delta_history[ticker]:
            deltas = list(self.delta_history[ticker])
            cum_delta = self.cumulative_deltas.get(ticker, 0)

            analysis.cum_delta = CumulativeDelta(
                ticker=ticker,
                timestamp=now,
                delta=deltas[-1] if deltas else 0,
                cumulative_delta=cum_delta,
                delta_ma_5=np.mean(deltas[-5:]) if len(deltas) >= 5 else 0,
                delta_zscore=self._calculate_delta_zscore(ticker)
            )

        # VPIN
        analysis.vpin_estimate = self.get_vpin(ticker)

        # Quote intensity
        analysis.quote_intensity = self.get_quote_intensity(ticker)
        analysis.is_quote_stuffing = (
            analysis.quote_intensity > self.config.quote_stuffing_threshold
        )

        # Determine signal
        analysis.signal, analysis.signal_strength = self._determine_signal(analysis)

        # Build features for ML
        if include_features:
            analysis.features = self._build_features(analysis)

        return analysis

    def _calculate_delta_zscore(self, ticker: str) -> float:
        """Calculate z-score of recent delta."""
        if ticker not in self.delta_history:
            return 0.0

        deltas = list(self.delta_history[ticker])
        if len(deltas) < 20:
            return 0.0

        recent = deltas[-20:]
        mean = np.mean(recent)
        std = np.std(recent)

        if std == 0:
            return 0.0

        return (deltas[-1] - mean) / std

    def _determine_signal(
        self,
        analysis: MicrostructureAnalysis
    ) -> Tuple[MicrostructureSignal, float]:
        """
        Determine microstructure signal from analysis.

        Returns: (signal, strength 0-100)
        """
        signals = []

        # Order book imbalance signal
        if analysis.order_book:
            imb = analysis.order_book.imbalance_ratio

            if imb > self.config.imbalance_strong_threshold:
                signals.append(('bid', abs(imb) * 100))
            elif imb < -self.config.imbalance_strong_threshold:
                signals.append(('ask', abs(imb) * 100))

        # Delta signal
        if analysis.cum_delta:
            zscore = analysis.cum_delta.delta_zscore

            if zscore > self.config.delta_zscore_threshold:
                signals.append(('bid', min(100, abs(zscore) * 30)))
            elif zscore < -self.config.delta_zscore_threshold:
                signals.append(('ask', min(100, abs(zscore) * 30)))

        # VPIN signal (toxicity)
        if analysis.vpin_estimate > 0.7:
            # High VPIN = informed trading, be cautious
            # This is a warning, not directional
            pass

        # Combine signals
        if not signals:
            return MicrostructureSignal.BALANCED, 0.0

        # Vote
        bid_strength = sum(s[1] for s in signals if s[0] == 'bid')
        ask_strength = sum(s[1] for s in signals if s[0] == 'ask')

        if bid_strength > ask_strength:
            return MicrostructureSignal.STRONG_BID, min(100, bid_strength)
        elif ask_strength > bid_strength:
            return MicrostructureSignal.STRONG_ASK, min(100, ask_strength)
        else:
            return MicrostructureSignal.BALANCED, 0.0

    def _build_features(self, analysis: MicrostructureAnalysis) -> Dict[str, float]:
        """Build feature dict for ML ensemble."""
        features = {}

        # Order book features
        if analysis.order_book:
            book = analysis.order_book
            features['ob_imbalance'] = book.imbalance_ratio
            features['ob_spread_bps'] = book.spread_bps / 100  # Normalize
            features['ob_bid_depth_5'] = min(book.bid_depth_5 / 10000, 1.0)
            features['ob_ask_depth_5'] = min(book.ask_depth_5 / 10000, 1.0)
            features['ob_depth_ratio'] = (
                book.bid_depth_5 / (book.bid_depth_5 + book.ask_depth_5)
                if (book.bid_depth_5 + book.ask_depth_5) > 0 else 0.5
            )
        else:
            features['ob_imbalance'] = 0.0
            features['ob_spread_bps'] = 0.0
            features['ob_bid_depth_5'] = 0.0
            features['ob_ask_depth_5'] = 0.0
            features['ob_depth_ratio'] = 0.5

        # Delta features
        if analysis.cum_delta:
            delta = analysis.cum_delta
            features['delta_zscore'] = np.clip(delta.delta_zscore / 3, -1, 1)
            features['delta_ma_5'] = np.clip(delta.delta_ma_5 / 1000, -1, 1)
            features['cum_delta_normalized'] = np.clip(
                delta.cumulative_delta / 10000, -1, 1
            )

            total_vol = delta.buy_volume + delta.sell_volume + delta.neutral_volume
            if total_vol > 0:
                features['buy_volume_ratio'] = delta.buy_volume / total_vol
                features['sell_volume_ratio'] = delta.sell_volume / total_vol
            else:
                features['buy_volume_ratio'] = 0.5
                features['sell_volume_ratio'] = 0.5
        else:
            features['delta_zscore'] = 0.0
            features['delta_ma_5'] = 0.0
            features['cum_delta_normalized'] = 0.0
            features['buy_volume_ratio'] = 0.5
            features['sell_volume_ratio'] = 0.5

        # VPIN
        features['vpin'] = analysis.vpin_estimate

        # Quote intensity
        features['quote_intensity_norm'] = min(
            analysis.quote_intensity / self.config.quote_stuffing_threshold, 1.0
        )
        features['is_quote_stuffing'] = 1.0 if analysis.is_quote_stuffing else 0.0

        # Signal strength
        features['micro_signal_strength'] = analysis.signal_strength / 100

        return features

    # ========================================
    # IBKR INTEGRATION
    # ========================================

    def connect_ibkr(self) -> bool:
        """Connect to Interactive Brokers TWS/Gateway."""
        if not IBKR_AVAILABLE:
            logger.warning("IBKR API not available - install ibapi package")
            return False

        try:
            # Create wrapper and client
            # This is a simplified example - full implementation
            # would need proper EWrapper subclass
            logger.info("IBKR connection not fully implemented - use Polygon L2 instead")
            return False

        except Exception as e:
            logger.error(f"IBKR connection failed: {e}")
            return False

    # ========================================
    # STATUS
    # ========================================

    def get_status(self) -> Dict[str, Any]:
        """Get analyzer status."""
        return {
            'tracked_tickers': list(self.order_books.keys()),
            'delta_tickers': list(self.delta_history.keys()),
            'ibkr_connected': self.ibkr_connected,
            'config': {
                'depth_levels': self.config.depth_levels,
                'imbalance_threshold': self.config.imbalance_strong_threshold,
                'delta_zscore_threshold': self.config.delta_zscore_threshold,
            },
            'snapshots': {
                ticker: {
                    'imbalance': book.imbalance_ratio,
                    'spread_bps': book.spread_bps,
                    'age_ms': (datetime.now() - book.timestamp).total_seconds() * 1000
                }
                for ticker, book in self.order_books.items()
            }
        }


# Global instance
_microstructure_analyzer: Optional[MicrostructureAnalyzer] = None


def get_microstructure_analyzer() -> MicrostructureAnalyzer:
    """Get or create global microstructure analyzer."""
    global _microstructure_analyzer
    if _microstructure_analyzer is None:
        _microstructure_analyzer = MicrostructureAnalyzer()
    return _microstructure_analyzer
