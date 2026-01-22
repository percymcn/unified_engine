"""
Symbol Specifications Service

Retrieves symbol specifications for position sizing calculations.
Falls back to sensible defaults when broker API unavailable.
"""
from typing import Dict, Optional
from dataclasses import dataclass
import logging

from app.domain.services.position_sizing_service import SymbolSpecs

logger = logging.getLogger(__name__)


# Default specs for common instruments
DEFAULT_SPECS: Dict[str, SymbolSpecs] = {
    # Forex majors
    "EURUSD": SymbolSpecs(min_lot=0.01, max_lot=100, lot_step=0.01, contract_size=100000, pip_value=10.0, digits=5),
    "GBPUSD": SymbolSpecs(min_lot=0.01, max_lot=100, lot_step=0.01, contract_size=100000, pip_value=10.0, digits=5),
    "USDJPY": SymbolSpecs(min_lot=0.01, max_lot=100, lot_step=0.01, contract_size=100000, pip_value=9.0, digits=3),
    "AUDUSD": SymbolSpecs(min_lot=0.01, max_lot=100, lot_step=0.01, contract_size=100000, pip_value=10.0, digits=5),
    "USDCAD": SymbolSpecs(min_lot=0.01, max_lot=100, lot_step=0.01, contract_size=100000, pip_value=10.0, digits=5),
    "NZDUSD": SymbolSpecs(min_lot=0.01, max_lot=100, lot_step=0.01, contract_size=100000, pip_value=10.0, digits=5),
    "USDCHF": SymbolSpecs(min_lot=0.01, max_lot=100, lot_step=0.01, contract_size=100000, pip_value=10.0, digits=5),

    # Indices
    "US30": SymbolSpecs(min_lot=0.01, max_lot=50, lot_step=0.01, contract_size=1, pip_value=1.0, digits=1),
    "NAS100": SymbolSpecs(min_lot=0.01, max_lot=50, lot_step=0.01, contract_size=1, pip_value=1.0, digits=1),
    "SPX500": SymbolSpecs(min_lot=0.01, max_lot=50, lot_step=0.01, contract_size=1, pip_value=1.0, digits=1),
    "US500": SymbolSpecs(min_lot=0.01, max_lot=50, lot_step=0.01, contract_size=1, pip_value=1.0, digits=1),

    # Futures (ES, NQ, etc.)
    "ES": SymbolSpecs(min_lot=1, max_lot=100, lot_step=1, contract_size=50, pip_value=12.50, digits=2),
    "NQ": SymbolSpecs(min_lot=1, max_lot=100, lot_step=1, contract_size=20, pip_value=5.0, digits=2),
    "MES": SymbolSpecs(min_lot=1, max_lot=100, lot_step=1, contract_size=5, pip_value=1.25, digits=2),
    "MNQ": SymbolSpecs(min_lot=1, max_lot=100, lot_step=1, contract_size=2, pip_value=0.50, digits=2),
    "YM": SymbolSpecs(min_lot=1, max_lot=100, lot_step=1, contract_size=5, pip_value=5.0, digits=0),
    "MYM": SymbolSpecs(min_lot=1, max_lot=100, lot_step=1, contract_size=0.5, pip_value=0.50, digits=0),
    "RTY": SymbolSpecs(min_lot=1, max_lot=100, lot_step=1, contract_size=50, pip_value=5.0, digits=1),
    "M2K": SymbolSpecs(min_lot=1, max_lot=100, lot_step=1, contract_size=5, pip_value=0.50, digits=1),

    # Gold
    "XAUUSD": SymbolSpecs(min_lot=0.01, max_lot=50, lot_step=0.01, contract_size=100, pip_value=1.0, digits=2),
    "GOLD": SymbolSpecs(min_lot=0.01, max_lot=50, lot_step=0.01, contract_size=100, pip_value=1.0, digits=2),

    # Oil
    "USOIL": SymbolSpecs(min_lot=0.01, max_lot=100, lot_step=0.01, contract_size=1000, pip_value=10.0, digits=2),
    "UKOIL": SymbolSpecs(min_lot=0.01, max_lot=100, lot_step=0.01, contract_size=1000, pip_value=10.0, digits=2),
    "CL": SymbolSpecs(min_lot=1, max_lot=100, lot_step=1, contract_size=1000, pip_value=10.0, digits=2),
}


class SymbolSpecsService:
    """
    Retrieves symbol specifications for position sizing calculations.

    Falls back to defaults when broker API unavailable.
    """

    def __init__(self, broker_adapters: dict = None):
        """
        Initialize service with optional broker adapters.

        Args:
            broker_adapters: Dict of broker_type -> broker adapter with get_symbol_specs method
        """
        self._brokers = broker_adapters or {}

    async def get_specs(
        self,
        symbol: str,
        broker_type: str = None
    ) -> SymbolSpecs:
        """
        Get symbol specifications.

        Args:
            symbol: Trading symbol
            broker_type: Optional broker type for live specs

        Returns:
            SymbolSpecs for the symbol
        """
        # Try to get from broker if available
        if broker_type and broker_type in self._brokers:
            try:
                broker = self._brokers[broker_type]
                if hasattr(broker, 'get_symbol_specs'):
                    specs = await broker.get_symbol_specs(symbol)
                    if specs:
                        return SymbolSpecs(
                            min_lot=specs.get('min_lot', 0.01),
                            max_lot=specs.get('max_lot', 100),
                            lot_step=specs.get('lot_step', 0.01),
                            contract_size=specs.get('contract_size', 100000),
                            pip_value=specs.get('pip_value', 10.0),
                            digits=specs.get('digits', 5)
                        )
            except Exception as e:
                logger.debug(f"Failed to get specs from broker {broker_type}: {e}")

        # Normalize symbol for lookup
        normalized = self._normalize_symbol(symbol)

        # Check defaults
        if normalized in DEFAULT_SPECS:
            logger.debug(f"Using default specs for {normalized}")
            return DEFAULT_SPECS[normalized]

        # Generic fallback
        logger.debug(f"Using inferred specs for {symbol}")
        return self._infer_specs(symbol)

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for lookup"""
        # Remove common suffixes
        for suffix in ['.pro', '.raw', '.std', 'pro', 'raw', '_SB', '.a', '.b']:
            if symbol.upper().endswith(suffix.upper()):
                symbol = symbol[:-len(suffix)]

        # Strip futures month codes (e.g., ESH25 -> ES, NQM25 -> NQ)
        symbol_upper = symbol.upper()
        # Check if ends with month code + year (e.g., H25, M26)
        if len(symbol_upper) >= 3:
            potential_month = symbol_upper[-3]
            potential_year = symbol_upper[-2:]
            if potential_month in 'FGHJKMNQUVXZ' and potential_year.isdigit():
                symbol = symbol_upper[:-3]

        return symbol.upper()

    def _infer_specs(self, symbol: str) -> SymbolSpecs:
        """Infer specs based on symbol name patterns"""
        symbol_upper = symbol.upper()

        # Indices
        if any(idx in symbol_upper for idx in ['US30', 'DJ30', 'DOW', 'YM']):
            return DEFAULT_SPECS.get("US30", SymbolSpecs())
        if any(idx in symbol_upper for idx in ['NAS', 'NDX', 'US100', 'NQ']):
            return DEFAULT_SPECS.get("NAS100", SymbolSpecs())
        if any(idx in symbol_upper for idx in ['SPX', 'SP500', 'US500', 'ES']):
            return DEFAULT_SPECS.get("SPX500", SymbolSpecs())

        # Futures - check for specific patterns
        if 'MES' in symbol_upper:
            return DEFAULT_SPECS.get("MES", SymbolSpecs())
        if 'MNQ' in symbol_upper:
            return DEFAULT_SPECS.get("MNQ", SymbolSpecs())
        if 'MYM' in symbol_upper:
            return DEFAULT_SPECS.get("MYM", SymbolSpecs())
        if 'M2K' in symbol_upper or 'MRTY' in symbol_upper:
            return DEFAULT_SPECS.get("M2K", SymbolSpecs())

        # Full size futures
        if symbol_upper.startswith('ES') or symbol_upper == 'ES':
            return DEFAULT_SPECS.get("ES", SymbolSpecs())
        if symbol_upper.startswith('NQ') or symbol_upper == 'NQ':
            return DEFAULT_SPECS.get("NQ", SymbolSpecs())
        if symbol_upper.startswith('YM') or symbol_upper == 'YM':
            return DEFAULT_SPECS.get("YM", SymbolSpecs())
        if symbol_upper.startswith('RTY') or symbol_upper == 'RTY':
            return DEFAULT_SPECS.get("RTY", SymbolSpecs())

        # Gold
        if 'XAU' in symbol_upper or 'GOLD' in symbol_upper:
            return DEFAULT_SPECS.get("XAUUSD", SymbolSpecs())

        # Oil
        if 'CL' in symbol_upper or 'OIL' in symbol_upper:
            return DEFAULT_SPECS.get("USOIL", SymbolSpecs())

        # Check if looks like forex pair (6-7 chars, contains USD/EUR/GBP/JPY)
        if len(symbol_upper) in [6, 7]:
            for currency in ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'NZD', 'CHF']:
                if currency in symbol_upper:
                    # Assume standard forex specs
                    digits = 3 if 'JPY' in symbol_upper else 5
                    pip_value = 9.0 if 'JPY' in symbol_upper else 10.0
                    return SymbolSpecs(
                        min_lot=0.01, max_lot=100, lot_step=0.01,
                        contract_size=100000, pip_value=pip_value, digits=digits
                    )

        # Default forex specs for unknown symbols
        logger.warning(f"Unknown symbol {symbol}, using default forex specs")
        return SymbolSpecs()
