"""
Crypto Funding Rates & Open Interest Service
=============================================

Alternative data for crypto trading (often higher Sharpe than spot TA):
- Funding rates (Binance, Bybit perpetuals)
- Open interest changes
- Long/short ratio
- Liquidation data

Funding rates > 0.03% = market crowded long = fade
Funding rates < -0.01% = market crowded short = buy

Pi5 optimized: REST API polling, ~100ms per request
"""

import logging
import aiohttp
import asyncio
import os
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class CryptoExchange(Enum):
    """Supported crypto exchanges"""
    BINANCE = "binance"
    BYBIT = "bybit"


@dataclass
class FundingRate:
    """Funding rate data"""
    symbol: str
    exchange: CryptoExchange
    timestamp: datetime

    # Funding rate (as decimal, e.g., 0.0001 = 0.01%)
    funding_rate: float = 0.0
    funding_rate_pct: float = 0.0  # As percentage

    # Predicted next funding
    predicted_funding_rate: float = 0.0

    # Historical context
    funding_rate_8h_avg: float = 0.0
    funding_rate_24h_avg: float = 0.0
    funding_rate_zscore: float = 0.0  # How unusual

    # Next funding time
    next_funding_time: Optional[datetime] = None
    minutes_to_funding: float = 0.0


@dataclass
class OpenInterest:
    """Open interest data"""
    symbol: str
    exchange: CryptoExchange
    timestamp: datetime

    # Current OI
    open_interest: float = 0.0  # In contracts
    open_interest_usd: float = 0.0  # In USD

    # Changes
    oi_change_1h_pct: float = 0.0
    oi_change_4h_pct: float = 0.0
    oi_change_24h_pct: float = 0.0

    # Context
    oi_percentile_30d: float = 50.0  # Where current OI sits in 30-day range


@dataclass
class LongShortRatio:
    """Long/short ratio data"""
    symbol: str
    exchange: CryptoExchange
    timestamp: datetime

    # Ratios
    long_short_ratio: float = 1.0  # >1 = more longs
    long_account_pct: float = 50.0
    short_account_pct: float = 50.0

    # Top traders
    top_trader_long_short_ratio: float = 1.0

    # Position ratios
    long_position_pct: float = 50.0
    short_position_pct: float = 50.0


@dataclass
class Liquidation:
    """Recent liquidation data"""
    symbol: str
    exchange: CryptoExchange
    timestamp: datetime

    # Recent liquidations
    long_liquidations_1h: float = 0.0  # USD
    short_liquidations_1h: float = 0.0
    total_liquidations_1h: float = 0.0

    # Liquidation imbalance
    liquidation_ratio: float = 1.0  # long/short liquidations


@dataclass
class CryptoFundingAnalysis:
    """Complete crypto funding analysis"""
    symbol: str
    timestamp: datetime

    # Core data
    funding: Optional[FundingRate] = None
    open_interest: Optional[OpenInterest] = None
    long_short: Optional[LongShortRatio] = None
    liquidations: Optional[Liquidation] = None

    # Combined signal
    signal: str = 'neutral'  # 'bullish', 'bearish', 'neutral'
    signal_strength: float = 0.0  # 0-100

    # Specific signals
    crowded_long: bool = False
    crowded_short: bool = False
    oi_building: bool = False
    oi_unwinding: bool = False

    # Ensemble features
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class CryptoFundingConfig:
    """Configuration for crypto funding service"""
    # Binance API
    binance_base_url: str = "https://fapi.binance.com"
    binance_api_key: str = ""

    # Bybit API
    bybit_base_url: str = "https://api.bybit.com"
    bybit_api_key: str = ""

    # Thresholds
    high_funding_threshold: float = 0.0003  # 0.03% = crowded
    low_funding_threshold: float = -0.0001  # -0.01% = oversold

    # OI change thresholds
    significant_oi_change_pct: float = 5.0  # >5% change in 1h

    # Update intervals
    funding_update_interval_minutes: int = 5
    oi_update_interval_minutes: int = 1

    # Tracked symbols
    tracked_symbols: List[str] = field(default_factory=lambda: [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"
    ])


class CryptoFundingService:
    """
    Crypto funding rates and open interest service.

    Provides alternative alpha signals:
    - Crowded trade detection via funding rates
    - Smart money positioning via OI changes
    - Sentiment via long/short ratios
    """

    def __init__(self, config: Optional[CryptoFundingConfig] = None):
        self.config = config or CryptoFundingConfig()

        # Load API keys from environment
        self.config.binance_api_key = os.getenv('BINANCE_API_KEY', '')
        self.config.bybit_api_key = os.getenv('BYBIT_API_KEY', '')

        # HTTP session
        self.session: Optional[aiohttp.ClientSession] = None

        # Cache
        self.funding_cache: Dict[str, FundingRate] = {}
        self.oi_cache: Dict[str, OpenInterest] = {}
        self.ls_cache: Dict[str, LongShortRatio] = {}

        # History for z-scores
        self.funding_history: Dict[str, deque] = {}
        self.oi_history: Dict[str, deque] = {}
        self.max_history = 500

        # Last update times
        self.last_funding_update: Dict[str, datetime] = {}
        self.last_oi_update: Dict[str, datetime] = {}

        logger.info(
            f"CryptoFundingService initialized: "
            f"symbols={self.config.tracked_symbols}, "
            f"binance_key={'set' if self.config.binance_api_key else 'not set'}"
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session

    async def close(self):
        """Close session."""
        if self.session and not self.session.closed:
            await self.session.close()

    # ========================================
    # BINANCE API
    # ========================================

    async def fetch_binance_funding_rate(
        self,
        symbol: str
    ) -> Optional[FundingRate]:
        """
        Fetch funding rate from Binance Futures.

        API: GET /fapi/v1/fundingRate
        """
        try:
            session = await self._get_session()

            url = f"{self.config.binance_base_url}/fapi/v1/fundingRate"
            params = {
                'symbol': symbol,
                'limit': 100  # Get recent history
            }

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.warning(f"Binance funding API returned {response.status}")
                    return None

                data = await response.json()

                if not data:
                    return None

                # Most recent funding
                latest = data[-1]

                result = FundingRate(
                    symbol=symbol,
                    exchange=CryptoExchange.BINANCE,
                    timestamp=datetime.now(),
                    funding_rate=float(latest.get('fundingRate', 0)),
                    funding_rate_pct=float(latest.get('fundingRate', 0)) * 100
                )

                # Calculate averages from history
                rates = [float(d.get('fundingRate', 0)) for d in data]

                if len(rates) >= 3:
                    result.funding_rate_8h_avg = np.mean(rates[-3:])  # ~24h of 8h funding

                if len(rates) >= 9:
                    result.funding_rate_24h_avg = np.mean(rates[-9:])  # ~72h

                # Z-score
                if len(rates) >= 20:
                    mean = np.mean(rates)
                    std = np.std(rates)
                    if std > 0:
                        result.funding_rate_zscore = (result.funding_rate - mean) / std

                # Next funding time (Binance: every 8 hours at 00:00, 08:00, 16:00 UTC)
                now = datetime.utcnow()
                next_funding_hour = ((now.hour // 8) + 1) * 8
                if next_funding_hour >= 24:
                    next_funding_hour = 0
                    next_day = now + timedelta(days=1)
                    result.next_funding_time = next_day.replace(
                        hour=next_funding_hour, minute=0, second=0, microsecond=0
                    )
                else:
                    result.next_funding_time = now.replace(
                        hour=next_funding_hour, minute=0, second=0, microsecond=0
                    )

                result.minutes_to_funding = (
                    result.next_funding_time - now
                ).total_seconds() / 60

                # Cache
                self.funding_cache[symbol] = result

                # Track history
                if symbol not in self.funding_history:
                    self.funding_history[symbol] = deque(maxlen=self.max_history)
                self.funding_history[symbol].append(result.funding_rate)

                return result

        except Exception as e:
            logger.error(f"Binance funding fetch failed for {symbol}: {e}")
            return None

    async def fetch_binance_open_interest(
        self,
        symbol: str
    ) -> Optional[OpenInterest]:
        """
        Fetch open interest from Binance Futures.

        API: GET /fapi/v1/openInterest
        """
        try:
            session = await self._get_session()

            # Current OI
            url = f"{self.config.binance_base_url}/fapi/v1/openInterest"
            params = {'symbol': symbol}

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()

                result = OpenInterest(
                    symbol=symbol,
                    exchange=CryptoExchange.BINANCE,
                    timestamp=datetime.now(),
                    open_interest=float(data.get('openInterest', 0))
                )

            # Get OI history for changes
            hist_url = f"{self.config.binance_base_url}/futures/data/openInterestHist"
            hist_params = {
                'symbol': symbol,
                'period': '5m',
                'limit': 288  # ~24h of 5-min data
            }

            async with session.get(hist_url, params=hist_params) as response:
                if response.status == 200:
                    hist_data = await response.json()

                    if hist_data:
                        ois = [float(d.get('sumOpenInterest', 0)) for d in hist_data]

                        # Calculate changes
                        if len(ois) >= 12:  # 1 hour
                            oi_1h_ago = ois[-12]
                            if oi_1h_ago > 0:
                                result.oi_change_1h_pct = (
                                    (result.open_interest - oi_1h_ago) / oi_1h_ago * 100
                                )

                        if len(ois) >= 48:  # 4 hours
                            oi_4h_ago = ois[-48]
                            if oi_4h_ago > 0:
                                result.oi_change_4h_pct = (
                                    (result.open_interest - oi_4h_ago) / oi_4h_ago * 100
                                )

                        if len(ois) >= 288:  # 24 hours
                            oi_24h_ago = ois[0]
                            if oi_24h_ago > 0:
                                result.oi_change_24h_pct = (
                                    (result.open_interest - oi_24h_ago) / oi_24h_ago * 100
                                )

                        # Percentile
                        if ois:
                            result.oi_percentile_30d = (
                                np.searchsorted(np.sort(ois), result.open_interest)
                                / len(ois) * 100
                            )

            # Cache
            self.oi_cache[symbol] = result

            # Track history
            if symbol not in self.oi_history:
                self.oi_history[symbol] = deque(maxlen=self.max_history)
            self.oi_history[symbol].append(result.open_interest)

            return result

        except Exception as e:
            logger.error(f"Binance OI fetch failed for {symbol}: {e}")
            return None

    async def fetch_binance_long_short_ratio(
        self,
        symbol: str
    ) -> Optional[LongShortRatio]:
        """
        Fetch long/short ratio from Binance Futures.

        API: GET /futures/data/globalLongShortAccountRatio
        """
        try:
            session = await self._get_session()

            url = f"{self.config.binance_base_url}/futures/data/globalLongShortAccountRatio"
            params = {
                'symbol': symbol,
                'period': '5m',
                'limit': 1
            }

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()

                if not data:
                    return None

                latest = data[-1]

                result = LongShortRatio(
                    symbol=symbol,
                    exchange=CryptoExchange.BINANCE,
                    timestamp=datetime.now(),
                    long_short_ratio=float(latest.get('longShortRatio', 1)),
                    long_account_pct=float(latest.get('longAccount', 50)),
                    short_account_pct=float(latest.get('shortAccount', 50))
                )

            # Get top trader ratio
            top_url = f"{self.config.binance_base_url}/futures/data/topLongShortAccountRatio"

            async with session.get(top_url, params=params) as response:
                if response.status == 200:
                    top_data = await response.json()
                    if top_data:
                        result.top_trader_long_short_ratio = float(
                            top_data[-1].get('longShortRatio', 1)
                        )

            # Cache
            self.ls_cache[symbol] = result

            return result

        except Exception as e:
            logger.error(f"Binance L/S ratio fetch failed for {symbol}: {e}")
            return None

    # ========================================
    # BYBIT API
    # ========================================

    async def fetch_bybit_funding_rate(
        self,
        symbol: str
    ) -> Optional[FundingRate]:
        """
        Fetch funding rate from Bybit.

        API: GET /v5/market/funding/history
        """
        try:
            session = await self._get_session()

            url = f"{self.config.bybit_base_url}/v5/market/funding/history"
            params = {
                'category': 'linear',
                'symbol': symbol,
                'limit': 100
            }

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()

                result_data = data.get('result', {}).get('list', [])
                if not result_data:
                    return None

                latest = result_data[0]

                result = FundingRate(
                    symbol=symbol,
                    exchange=CryptoExchange.BYBIT,
                    timestamp=datetime.now(),
                    funding_rate=float(latest.get('fundingRate', 0)),
                    funding_rate_pct=float(latest.get('fundingRate', 0)) * 100
                )

                # Calculate averages
                rates = [float(d.get('fundingRate', 0)) for d in result_data]

                if len(rates) >= 3:
                    result.funding_rate_8h_avg = np.mean(rates[:3])

                if len(rates) >= 20:
                    mean = np.mean(rates)
                    std = np.std(rates)
                    if std > 0:
                        result.funding_rate_zscore = (result.funding_rate - mean) / std

                return result

        except Exception as e:
            logger.error(f"Bybit funding fetch failed for {symbol}: {e}")
            return None

    async def fetch_bybit_open_interest(
        self,
        symbol: str
    ) -> Optional[OpenInterest]:
        """
        Fetch open interest from Bybit.

        API: GET /v5/market/open-interest
        """
        try:
            session = await self._get_session()

            url = f"{self.config.bybit_base_url}/v5/market/open-interest"
            params = {
                'category': 'linear',
                'symbol': symbol,
                'intervalTime': '5min',
                'limit': 200
            }

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()

                result_data = data.get('result', {}).get('list', [])
                if not result_data:
                    return None

                latest = result_data[0]

                result = OpenInterest(
                    symbol=symbol,
                    exchange=CryptoExchange.BYBIT,
                    timestamp=datetime.now(),
                    open_interest=float(latest.get('openInterest', 0))
                )

                # Calculate changes from history
                ois = [float(d.get('openInterest', 0)) for d in result_data]

                if len(ois) >= 12:
                    oi_1h_ago = ois[11]
                    if oi_1h_ago > 0:
                        result.oi_change_1h_pct = (
                            (result.open_interest - oi_1h_ago) / oi_1h_ago * 100
                        )

                if len(ois) >= 48:
                    oi_4h_ago = ois[47]
                    if oi_4h_ago > 0:
                        result.oi_change_4h_pct = (
                            (result.open_interest - oi_4h_ago) / oi_4h_ago * 100
                        )

                return result

        except Exception as e:
            logger.error(f"Bybit OI fetch failed for {symbol}: {e}")
            return None

    # ========================================
    # COMBINED ANALYSIS
    # ========================================

    async def analyze(
        self,
        symbol: str,
        exchange: CryptoExchange = CryptoExchange.BINANCE
    ) -> CryptoFundingAnalysis:
        """
        Run complete crypto funding analysis.

        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            exchange: Exchange to use

        Returns:
            CryptoFundingAnalysis with all metrics
        """
        analysis = CryptoFundingAnalysis(
            symbol=symbol,
            timestamp=datetime.now()
        )

        # Fetch data based on exchange
        if exchange == CryptoExchange.BINANCE:
            analysis.funding = await self.fetch_binance_funding_rate(symbol)
            analysis.open_interest = await self.fetch_binance_open_interest(symbol)
            analysis.long_short = await self.fetch_binance_long_short_ratio(symbol)
        else:
            analysis.funding = await self.fetch_bybit_funding_rate(symbol)
            analysis.open_interest = await self.fetch_bybit_open_interest(symbol)

        # Determine signals
        self._analyze_signals(analysis)

        # Build features
        analysis.features = self._build_features(analysis)

        # Log
        logger.info(
            f"📊 Crypto {symbol}: funding={analysis.funding.funding_rate_pct:.4f}% "
            f"OI_1h={analysis.open_interest.oi_change_1h_pct if analysis.open_interest else 0:.1f}% "
            f"signal={analysis.signal} ({analysis.signal_strength:.0f})"
        )

        return analysis

    def _analyze_signals(self, analysis: CryptoFundingAnalysis):
        """Determine trading signals from funding data."""
        signals = []

        # Funding rate signals
        if analysis.funding:
            fr = analysis.funding.funding_rate

            if fr > self.config.high_funding_threshold:
                # Crowded long - bearish signal
                analysis.crowded_long = True
                signals.append(('bearish', abs(fr) * 10000))  # Scale for strength

            elif fr < self.config.low_funding_threshold:
                # Crowded short - bullish signal
                analysis.crowded_short = True
                signals.append(('bullish', abs(fr) * 10000))

        # OI signals
        if analysis.open_interest:
            oi = analysis.open_interest

            if oi.oi_change_1h_pct > self.config.significant_oi_change_pct:
                analysis.oi_building = True
                # OI building with positive funding = more bullish
                # OI building with negative funding = more bearish
                if analysis.funding and analysis.funding.funding_rate > 0:
                    signals.append(('bullish', oi.oi_change_1h_pct * 2))
                elif analysis.funding and analysis.funding.funding_rate < 0:
                    signals.append(('bearish', oi.oi_change_1h_pct * 2))

            elif oi.oi_change_1h_pct < -self.config.significant_oi_change_pct:
                analysis.oi_unwinding = True
                # OI unwinding typically means trend weakening

        # Long/short ratio signals
        if analysis.long_short:
            ls = analysis.long_short

            if ls.long_account_pct > 65:
                signals.append(('bearish', (ls.long_account_pct - 50) * 2))

            elif ls.short_account_pct > 65:
                signals.append(('bullish', (ls.short_account_pct - 50) * 2))

        # Combine signals
        bullish_strength = sum(s[1] for s in signals if s[0] == 'bullish')
        bearish_strength = sum(s[1] for s in signals if s[0] == 'bearish')

        if bullish_strength > bearish_strength:
            analysis.signal = 'bullish'
            analysis.signal_strength = min(100, bullish_strength)
        elif bearish_strength > bullish_strength:
            analysis.signal = 'bearish'
            analysis.signal_strength = min(100, bearish_strength)
        else:
            analysis.signal = 'neutral'
            analysis.signal_strength = 0

    def _build_features(self, analysis: CryptoFundingAnalysis) -> Dict[str, float]:
        """Build feature dict for ML ensemble."""
        features = {}

        # Funding features
        if analysis.funding:
            fr = analysis.funding
            features['funding_rate'] = fr.funding_rate * 10000  # Scale
            features['funding_zscore'] = np.clip(fr.funding_rate_zscore / 3, -1, 1)
            features['minutes_to_funding'] = min(fr.minutes_to_funding / 480, 1.0)
        else:
            features['funding_rate'] = 0.0
            features['funding_zscore'] = 0.0
            features['minutes_to_funding'] = 0.5

        # OI features
        if analysis.open_interest:
            oi = analysis.open_interest
            features['oi_change_1h'] = np.clip(oi.oi_change_1h_pct / 20, -1, 1)
            features['oi_change_4h'] = np.clip(oi.oi_change_4h_pct / 30, -1, 1)
            features['oi_percentile'] = oi.oi_percentile_30d / 100
        else:
            features['oi_change_1h'] = 0.0
            features['oi_change_4h'] = 0.0
            features['oi_percentile'] = 0.5

        # Long/short features
        if analysis.long_short:
            ls = analysis.long_short
            features['long_short_ratio'] = np.clip((ls.long_short_ratio - 1) * 2, -1, 1)
            features['long_pct'] = ls.long_account_pct / 100
        else:
            features['long_short_ratio'] = 0.0
            features['long_pct'] = 0.5

        # Signal features
        features['crowded_long'] = 1.0 if analysis.crowded_long else 0.0
        features['crowded_short'] = 1.0 if analysis.crowded_short else 0.0
        features['oi_building'] = 1.0 if analysis.oi_building else 0.0
        features['oi_unwinding'] = 1.0 if analysis.oi_unwinding else 0.0

        return features

    async def analyze_all(self) -> Dict[str, CryptoFundingAnalysis]:
        """Analyze all tracked symbols."""
        results = {}

        for symbol in self.config.tracked_symbols:
            try:
                results[symbol] = await self.analyze(symbol)
            except Exception as e:
                logger.error(f"Analysis failed for {symbol}: {e}")

        return results

    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        return {
            'tracked_symbols': self.config.tracked_symbols,
            'binance_configured': bool(self.config.binance_api_key),
            'bybit_configured': bool(self.config.bybit_api_key),
            'cached_funding': list(self.funding_cache.keys()),
            'cached_oi': list(self.oi_cache.keys()),
            'thresholds': {
                'high_funding': self.config.high_funding_threshold * 100,
                'low_funding': self.config.low_funding_threshold * 100,
            }
        }


# Import numpy for calculations
import numpy as np

# Global instance
_crypto_funding_service: Optional[CryptoFundingService] = None


async def get_crypto_funding_service() -> CryptoFundingService:
    """Get or create global crypto funding service."""
    global _crypto_funding_service
    if _crypto_funding_service is None:
        _crypto_funding_service = CryptoFundingService()
    return _crypto_funding_service
