"""
Correlation Filter Service

Prevents taking highly correlated trades simultaneously.
For example, if you're long ES, it may block another long NQ signal.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
import pytz

from app.models.database_models import (
    SymbolCorrelation,
    CorrelationFilterSettings,
    TradeJournal,
    TradingAccount,
)

logger = logging.getLogger(__name__)

# Pre-defined correlations for common pairs
# These are approximate and should be updated with real data
DEFAULT_CORRELATIONS = {
    # US Index futures (highly correlated)
    ('ES', 'NQ'): 0.92,
    ('ES', 'YM'): 0.95,
    ('NQ', 'YM'): 0.88,
    ('MES', 'MNQ'): 0.92,
    ('MES', 'MYM'): 0.95,
    ('MNQ', 'MYM'): 0.88,
    ('ES', 'MES'): 0.99,
    ('NQ', 'MNQ'): 0.99,
    ('YM', 'MYM'): 0.99,
    ('US30', 'US500'): 0.95,
    ('US500', 'USTEC'): 0.92,
    ('US30', 'USTEC'): 0.88,
    ('NAS100', 'SPX500'): 0.92,

    # Forex pairs with USD
    ('EURUSD', 'GBPUSD'): 0.85,
    ('EURUSD', 'AUDUSD'): 0.70,
    ('GBPUSD', 'AUDUSD'): 0.65,
    ('USDCHF', 'USDJPY'): 0.60,

    # Negative correlations
    ('EURUSD', 'USDCHF'): -0.95,
    ('GBPUSD', 'USDCHF'): -0.85,
    ('XAUUSD', 'USDX'): -0.80,

    # Commodities
    ('XAUUSD', 'XAGUSD'): 0.90,
    ('USOIL', 'UKOIL'): 0.98,
    ('OIL', 'USOIL'): 0.99,

    # Crypto
    ('BTCUSD', 'ETHUSD'): 0.85,
    ('BTCUSD', 'LTCUSD'): 0.75,
}


class CorrelationFilterService:
    """
    Service for filtering trades based on symbol correlations.
    """

    def __init__(self, db: Session):
        self.db = db

    def should_allow_trade(
        self,
        user_id: int,
        account_id: int,
        symbol: str,
        side: str
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Check if a trade should be allowed based on existing positions.

        Returns:
            (should_allow, reason_if_blocked, correlation_value)
        """
        # Get user settings
        settings = self.db.query(CorrelationFilterSettings).filter(
            CorrelationFilterSettings.user_id == user_id
        ).first()

        if not settings or not settings.enabled:
            return True, None, None

        # Normalize symbol
        normalized_symbol = self._normalize_symbol(symbol)

        # Get open trades for this user
        open_trades = self.db.query(TradeJournal).filter(
            TradeJournal.user_id == user_id,
            TradeJournal.status == 'open'
        ).all()

        if not open_trades:
            return True, None, None

        for trade in open_trades:
            trade_symbol = self._normalize_symbol(trade.symbol)

            if trade_symbol == normalized_symbol:
                continue  # Same symbol is handled by position limits

            # Get correlation
            correlation = self.get_correlation(normalized_symbol, trade_symbol)

            if correlation is None:
                continue

            # Check positive correlation (same direction trades)
            if correlation >= settings.max_positive_correlation:
                if trade.side == side:  # Both same direction
                    reason = f"High correlation ({correlation:.2f}) with open {trade.side.upper()} {trade.symbol}"

                    if settings.action_on_correlation == 'block':
                        return False, reason, correlation
                    elif settings.action_on_correlation == 'warn':
                        logger.warning(f"Correlation warning for {symbol}: {reason}")
                        return True, None, correlation

            # Check negative correlation (opposite direction would be like same)
            if correlation <= settings.max_negative_correlation:
                # For negative correlation, opposite directions are correlated
                opposite_side = 'sell' if side == 'buy' else 'buy'
                if trade.side == opposite_side:  # Opposite directions with negative correlation
                    reason = f"Negative correlation ({correlation:.2f}) with open {trade.side.upper()} {trade.symbol}"

                    if settings.action_on_correlation == 'block':
                        return False, reason, correlation

        return True, None, None

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for correlation lookup."""
        symbol = symbol.upper()
        # Remove common suffixes
        for suffix in ['.PRO', '.STD', '1!', '!', '.Z', '.F', '_SB', '.ECN']:
            symbol = symbol.replace(suffix, '')
        return symbol

    def get_correlation(self, symbol_a: str, symbol_b: str) -> Optional[float]:
        """
        Get correlation between two symbols.
        First checks database, then falls back to defaults.
        """
        # Normalize
        symbol_a = self._normalize_symbol(symbol_a)
        symbol_b = self._normalize_symbol(symbol_b)

        # Check database
        db_correlation = self.db.query(SymbolCorrelation).filter(
            ((SymbolCorrelation.symbol_a == symbol_a) & (SymbolCorrelation.symbol_b == symbol_b)) |
            ((SymbolCorrelation.symbol_a == symbol_b) & (SymbolCorrelation.symbol_b == symbol_a))
        ).first()

        if db_correlation:
            return db_correlation.correlation

        # Check defaults
        for (a, b), corr in DEFAULT_CORRELATIONS.items():
            if (symbol_a == a and symbol_b == b) or (symbol_a == b and symbol_b == a):
                return corr

        # Check if symbols share a base currency (simplified forex check)
        if len(symbol_a) == 6 and len(symbol_b) == 6:
            # Both are forex pairs
            a_base, a_quote = symbol_a[:3], symbol_a[3:]
            b_base, b_quote = symbol_b[:3], symbol_b[3:]

            if a_base == b_base or a_quote == b_quote:
                return 0.5  # Moderate correlation assumed
            if a_base == b_quote or a_quote == b_base:
                return -0.5  # Moderate negative correlation

        return None

    def get_all_correlations(self) -> List[Dict[str, Any]]:
        """Get all stored correlations."""
        db_correlations = self.db.query(SymbolCorrelation).all()

        correlations = []

        # Add database correlations
        for c in db_correlations:
            correlations.append({
                'symbol_a': c.symbol_a,
                'symbol_b': c.symbol_b,
                'correlation': c.correlation,
                'source': 'database',
                'calculated_at': c.calculated_at.isoformat() if c.calculated_at else None
            })

        # Add default correlations not in database
        db_pairs = {(c.symbol_a, c.symbol_b) for c in db_correlations}
        db_pairs.update({(c.symbol_b, c.symbol_a) for c in db_correlations})

        for (a, b), corr in DEFAULT_CORRELATIONS.items():
            if (a, b) not in db_pairs and (b, a) not in db_pairs:
                correlations.append({
                    'symbol_a': a,
                    'symbol_b': b,
                    'correlation': corr,
                    'source': 'default',
                    'calculated_at': None
                })

        return correlations

    def set_correlation(
        self,
        symbol_a: str,
        symbol_b: str,
        correlation: float
    ) -> SymbolCorrelation:
        """Set or update a correlation value."""
        symbol_a = self._normalize_symbol(symbol_a)
        symbol_b = self._normalize_symbol(symbol_b)

        # Ensure consistent ordering
        if symbol_a > symbol_b:
            symbol_a, symbol_b = symbol_b, symbol_a

        existing = self.db.query(SymbolCorrelation).filter(
            SymbolCorrelation.symbol_a == symbol_a,
            SymbolCorrelation.symbol_b == symbol_b
        ).first()

        if existing:
            existing.correlation = correlation
            existing.calculated_at = datetime.now(pytz.UTC)
        else:
            existing = SymbolCorrelation(
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                correlation=correlation
            )
            self.db.add(existing)

        self.db.commit()
        return existing

    def get_settings(self, user_id: int) -> Optional[CorrelationFilterSettings]:
        """Get user's correlation filter settings."""
        return self.db.query(CorrelationFilterSettings).filter(
            CorrelationFilterSettings.user_id == user_id
        ).first()

    def update_settings(self, user_id: int, **kwargs) -> CorrelationFilterSettings:
        """Update user's correlation filter settings."""
        settings = self.get_settings(user_id)

        if not settings:
            settings = CorrelationFilterSettings(user_id=user_id)
            self.db.add(settings)

        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        self.db.commit()
        self.db.refresh(settings)
        return settings

    def get_correlated_open_positions(
        self,
        user_id: int,
        symbol: str,
        min_correlation: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Get open positions that are correlated with the given symbol."""
        normalized = self._normalize_symbol(symbol)

        open_trades = self.db.query(TradeJournal).filter(
            TradeJournal.user_id == user_id,
            TradeJournal.status == 'open'
        ).all()

        correlated = []
        for trade in open_trades:
            trade_symbol = self._normalize_symbol(trade.symbol)
            if trade_symbol == normalized:
                continue

            correlation = self.get_correlation(normalized, trade_symbol)
            if correlation and abs(correlation) >= min_correlation:
                correlated.append({
                    'trade_id': trade.id,
                    'symbol': trade.symbol,
                    'side': trade.side,
                    'quantity': trade.quantity,
                    'entry_price': trade.entry_price,
                    'correlation': correlation
                })

        return correlated
