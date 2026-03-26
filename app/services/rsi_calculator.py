"""
RSI Calculator for SmartFlow
=============================

Calculates RSI (Relative Strength Index) using ProjectX historical data.
"""

import logging
from typing import Optional
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RSICalculator:
    """Calculates RSI for symbols using historical price data"""

    def __init__(self):
        self.cache = {}  # Cache RSI values
        self.cache_ttl = 60  # Cache for 60 seconds

    async def get_rsi(
        self,
        symbol: str,
        period: int = 14,
        price_data: Optional[list] = None
    ) -> float:
        """
        Calculate RSI for a symbol.

        Args:
            symbol: Trading symbol
            period: RSI period (default 14)
            price_data: Optional list of price dictionaries with 'close' key

        Returns:
            RSI value (0-100)
        """
        try:
            # Check cache
            cache_key = f"{symbol}_{period}"
            if cache_key in self.cache:
                cached_rsi, cached_time = self.cache[cache_key]
                if (datetime.now() - cached_time).total_seconds() < self.cache_ttl:
                    return cached_rsi

            if price_data is None or len(price_data) < period + 1:
                # Not enough data - return neutral RSI
                logger.warning(f"Insufficient data for RSI calculation: {symbol}")
                return 50.0

            # Extract closing prices
            closes = [bar['close'] for bar in price_data[-(period + 1):]]

            # Calculate price changes
            deltas = np.diff(closes)

            # Separate gains and losses
            gains = deltas.copy()
            losses = deltas.copy()
            gains[gains < 0] = 0
            losses[losses > 0] = 0
            losses = abs(losses)

            # Calculate average gains and losses
            avg_gain = np.mean(gains)
            avg_loss = np.mean(losses)

            # Avoid division by zero
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100.0 - (100.0 / (1.0 + rs))

            # Cache result
            self.cache[cache_key] = (rsi, datetime.now())

            return float(rsi)

        except Exception as e:
            logger.error(f"RSI calculation error for {symbol}: {e}")
            return 50.0  # Return neutral on error


# Singleton instance
_rsi_calculator: Optional[RSICalculator] = None


def get_rsi_calculator() -> RSICalculator:
    """Get or create RSI calculator singleton"""
    global _rsi_calculator
    if _rsi_calculator is None:
        _rsi_calculator = RSICalculator()
    return _rsi_calculator
