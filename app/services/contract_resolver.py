"""
Contract Resolver Service

Handles futures contract resolution, rollover detection, and symbol mapping
for ProjectX/TopStep trading platform.

Features:
- Auto-resolves base symbols (MNQ) to active contracts (MNQH6)
- Detects contract rollover and updates mappings
- Caches active contracts for performance
- Supports all ProjectX tradeable instruments
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ContractInfo:
    """Information about a futures contract."""
    contract_id: str          # e.g., CON.F.US.MNQ.H26
    symbol: str               # e.g., MNQH6
    base_symbol: str          # e.g., MNQ
    symbol_id: str            # e.g., F.US.MNQ
    description: str          # e.g., Micro E-mini Nasdaq-100: March 2026
    tick_size: float          # e.g., 0.25
    tick_value: float         # e.g., 0.5 ($ per tick)
    is_active: bool           # True if this is the front-month contract
    expiry_month: str         # e.g., H (March), M (June), U (Sept), Z (Dec)
    expiry_year: int          # e.g., 26 (2026)
    last_updated: datetime = field(default_factory=datetime.now)


# Month code mapping
MONTH_CODES = {
    'F': 1, 'G': 2, 'H': 3, 'J': 4, 'K': 5, 'M': 6,
    'N': 7, 'Q': 8, 'U': 9, 'V': 10, 'X': 11, 'Z': 12
}

# Common futures with their front months (H=Mar, M=Jun, U=Sep, Z=Dec)
QUARTERLY_FUTURES = ['MNQ', 'MES', 'MYM', 'M2K', 'NQ', 'ES', 'YM', 'RTY']
MONTHLY_FUTURES = ['CL', 'MCL', 'GC', 'MGC', 'SI', 'NG']


class ContractResolver:
    """
    Resolves base symbols to active contracts and handles rollover.

    Usage:
        resolver = ContractResolver()
        await resolver.initialize(sdk_client)

        # Get active contract for a symbol
        contract = await resolver.get_active_contract("MNQ")
        # Returns: ContractInfo(contract_id='CON.F.US.MNQ.H26', ...)

        # Check if rollover needed
        if resolver.needs_rollover("MNQ"):
            await resolver.refresh_contract("MNQ")
    """

    # All tradeable instruments on ProjectX/TopStep
    TRADEABLE_SYMBOLS = {
        # Micro Index Futures
        'MNQ': {'name': 'Micro E-mini Nasdaq-100', 'tick_size': 0.25, 'tick_value': 0.5},
        'MES': {'name': 'Micro E-mini S&P 500', 'tick_size': 0.25, 'tick_value': 1.25},
        'MYM': {'name': 'Micro E-mini Dow', 'tick_size': 1.0, 'tick_value': 0.5},
        'M2K': {'name': 'Micro E-mini Russell 2000', 'tick_size': 0.1, 'tick_value': 0.5},

        # E-mini Index Futures
        'NQ': {'name': 'E-mini Nasdaq-100', 'tick_size': 0.25, 'tick_value': 5.0},
        'ES': {'name': 'E-mini S&P 500', 'tick_size': 0.25, 'tick_value': 12.5},
        'YM': {'name': 'E-mini Dow', 'tick_size': 1.0, 'tick_value': 5.0},
        'RTY': {'name': 'E-mini Russell 2000', 'tick_size': 0.1, 'tick_value': 5.0},

        # Energy Futures
        'CL': {'name': 'Crude Oil', 'tick_size': 0.01, 'tick_value': 10.0},
        'MCL': {'name': 'Micro Crude Oil', 'tick_size': 0.01, 'tick_value': 1.0},
        'NG': {'name': 'Natural Gas', 'tick_size': 0.001, 'tick_value': 10.0},

        # Metals Futures
        'GC': {'name': 'Gold', 'tick_size': 0.1, 'tick_value': 10.0},
        'MGC': {'name': 'Micro Gold', 'tick_size': 0.1, 'tick_value': 1.0},
        'SI': {'name': 'Silver', 'tick_size': 0.005, 'tick_value': 25.0},
        'SIL': {'name': 'Micro Silver', 'tick_size': 0.005, 'tick_value': 2.5},

        # Treasury Futures
        'ZB': {'name': '30-Year Treasury Bond', 'tick_size': 0.03125, 'tick_value': 31.25},
        'ZN': {'name': '10-Year Treasury Note', 'tick_size': 0.015625, 'tick_value': 15.625},
        'ZF': {'name': '5-Year Treasury Note', 'tick_size': 0.0078125, 'tick_value': 7.8125},
        'ZT': {'name': '2-Year Treasury Note', 'tick_size': 0.0078125, 'tick_value': 15.625},

        # Currency Futures
        '6E': {'name': 'Euro FX', 'tick_size': 0.00005, 'tick_value': 6.25},
        'M6E': {'name': 'Micro Euro FX', 'tick_size': 0.0001, 'tick_value': 1.25},
        '6J': {'name': 'Japanese Yen', 'tick_size': 0.0000005, 'tick_value': 6.25},
        '6B': {'name': 'British Pound', 'tick_size': 0.0001, 'tick_value': 6.25},
        'M6B': {'name': 'Micro British Pound', 'tick_size': 0.0001, 'tick_value': 0.625},
        '6A': {'name': 'Australian Dollar', 'tick_size': 0.0001, 'tick_value': 10.0},
        'M6A': {'name': 'Micro Australian Dollar', 'tick_size': 0.0001, 'tick_value': 1.0},
        '6C': {'name': 'Canadian Dollar', 'tick_size': 0.00005, 'tick_value': 5.0},

        # Crypto Futures
        'MBT': {'name': 'Micro Bitcoin', 'tick_size': 5.0, 'tick_value': 0.5},
        'BTC': {'name': 'Bitcoin', 'tick_size': 5.0, 'tick_value': 25.0},
    }

    # TradingView symbol mappings to ProjectX base symbols
    # TradingView uses formats like ES1!, MES1!, NQ1!, ESH2026, etc.
    TRADINGVIEW_SYMBOL_MAP = {
        # E-mini S&P 500
        'ES1!': 'ES', 'ESZ1!': 'ES', 'ESH1!': 'ES', 'ESM1!': 'ES', 'ESU1!': 'ES',
        # Micro E-mini S&P 500
        'MES1!': 'MES', 'MESZ1!': 'MES', 'MESH1!': 'MES', 'MESM1!': 'MES', 'MESU1!': 'MES',
        # E-mini Nasdaq
        'NQ1!': 'NQ', 'NQZ1!': 'NQ', 'NQH1!': 'NQ', 'NQM1!': 'NQ', 'NQU1!': 'NQ',
        # Micro E-mini Nasdaq
        'MNQ1!': 'MNQ', 'MNQZ1!': 'MNQ', 'MNQH1!': 'MNQ', 'MNQM1!': 'MNQ', 'MNQU1!': 'MNQ',
        # E-mini Dow
        'YM1!': 'YM', 'YMZ1!': 'YM', 'YMH1!': 'YM', 'YMM1!': 'YM', 'YMU1!': 'YM',
        # Micro E-mini Dow
        'MYM1!': 'MYM', 'MYMZ1!': 'MYM', 'MYMH1!': 'MYM', 'MYMM1!': 'MYM', 'MYMU1!': 'MYM',
        # E-mini Russell 2000
        'RTY1!': 'RTY', 'RTYZ1!': 'RTY', 'RTYH1!': 'RTY', 'RTYM1!': 'RTY', 'RTYU1!': 'RTY',
        # Micro E-mini Russell 2000
        'M2K1!': 'M2K', 'M2KZ1!': 'M2K', 'M2KH1!': 'M2K', 'M2KM1!': 'M2K', 'M2KU1!': 'M2K',
        # Crude Oil
        'CL1!': 'CL', 'CLZ1!': 'CL', 'CLH1!': 'CL', 'CLM1!': 'CL', 'CLU1!': 'CL',
        # Micro Crude Oil
        'MCL1!': 'MCL',
        # Gold
        'GC1!': 'GC', 'GCZ1!': 'GC', 'GCH1!': 'GC', 'GCM1!': 'GC', 'GCU1!': 'GC',
        # Micro Gold
        'MGC1!': 'MGC',
        # Natural Gas
        'NG1!': 'NG',
        # Micro Bitcoin
        'MBT1!': 'MBT',
        # Silver
        'SI1!': 'SI',
        # COMEX symbols (alternative TradingView format)
        'COMEX:ES1!': 'ES', 'COMEX:MES1!': 'MES', 'COMEX:GC1!': 'GC', 'COMEX:MGC1!': 'MGC',
        'CME_MINI:ES1!': 'ES', 'CME_MINI:NQ1!': 'NQ',
        # Currency futures
        '6E1!': '6E', 'M6E1!': 'M6E', '6J1!': '6J', '6B1!': '6B', '6A1!': '6A', '6C1!': '6C',
    }

    @classmethod
    def normalize_symbol(cls, symbol: str) -> str:
        """
        Normalize a TradingView symbol to ProjectX base symbol.

        Handles various TradingView formats:
        - ES1! -> ES
        - MES1! -> MES
        - ESH2026 -> ES
        - COMEX:GC1! -> GC
        - Already valid symbols pass through

        Args:
            symbol: Input symbol from TradingView or other source

        Returns:
            Normalized base symbol for ProjectX
        """
        if not symbol:
            return symbol

        # Uppercase for consistency
        symbol_upper = symbol.upper().strip()

        # Direct mapping check
        if symbol_upper in cls.TRADINGVIEW_SYMBOL_MAP:
            return cls.TRADINGVIEW_SYMBOL_MAP[symbol_upper]

        # Already a valid ProjectX base symbol?
        if symbol_upper in cls.TRADEABLE_SYMBOLS:
            return symbol_upper

        # Strip exchange prefix (COMEX:, CME_MINI:, etc.)
        if ':' in symbol_upper:
            symbol_upper = symbol_upper.split(':')[-1]
            # Check again after stripping prefix
            if symbol_upper in cls.TRADINGVIEW_SYMBOL_MAP:
                return cls.TRADINGVIEW_SYMBOL_MAP[symbol_upper]
            if symbol_upper in cls.TRADEABLE_SYMBOLS:
                return symbol_upper

        # Handle continuous contracts (ES1!, MES1!, etc.)
        if symbol_upper.endswith('1!'):
            base = symbol_upper[:-2]
            if base in cls.TRADEABLE_SYMBOLS:
                return base

        # Handle month codes (ESH2026, ESH26, ESH6)
        # Pattern: BASE + MONTH_CODE + YEAR
        import re
        match = re.match(r'^([A-Z0-9]+)([FGHJKMNQUVXZ])(\d{1,4})$', symbol_upper)
        if match:
            base = match.group(1)
            if base in cls.TRADEABLE_SYMBOLS:
                return base

        # Handle symbols with ! anywhere
        if '!' in symbol_upper:
            clean = symbol_upper.replace('!', '')
            # Try stripping numbers from the end
            base = re.sub(r'\d+$', '', clean)
            if base in cls.TRADEABLE_SYMBOLS:
                return base

        # Fallback: return as-is
        logger.warning(f"Could not normalize symbol: {symbol} -> returning as-is")
        return symbol_upper

    def __init__(self, cache_ttl_minutes: int = 60):
        """
        Initialize the contract resolver.

        Args:
            cache_ttl_minutes: How long to cache contract info before refresh
        """
        self._client = None
        self._cache: Dict[str, ContractInfo] = {}
        self._cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self, sdk_client) -> bool:
        """
        Initialize with SDK client and load active contracts.

        Args:
            sdk_client: ProjectX SDK client instance

        Returns:
            True if initialization successful
        """
        self._client = sdk_client

        try:
            # Pre-load common contracts
            common_symbols = ['MNQ', 'MES', 'MYM', 'NQ', 'ES', 'MCL', 'MGC', 'M2K']
            for symbol in common_symbols:
                await self.get_active_contract(symbol)

            self._initialized = True
            logger.info(f"ContractResolver initialized with {len(self._cache)} contracts")
            return True
        except Exception as e:
            logger.error(f"ContractResolver initialization failed: {e}")
            return False

    async def get_active_contract(self, base_symbol: str) -> Optional[ContractInfo]:
        """
        Get the active contract for a base symbol.

        Args:
            base_symbol: Base symbol like MNQ, ES, CL

        Returns:
            ContractInfo for the active contract or None
        """
        base_symbol = base_symbol.upper().strip()

        # Check cache first
        if base_symbol in self._cache:
            cached = self._cache[base_symbol]
            if datetime.now() - cached.last_updated < self._cache_ttl:
                return cached

        # Fetch from SDK
        async with self._lock:
            try:
                instruments = await self._client.search_instruments(base_symbol)

                if not instruments:
                    logger.warning(f"No instruments found for {base_symbol}")
                    return None

                # Find the active contract (first result is usually active)
                for inst in instruments:
                    inst_id = getattr(inst, 'id', '')
                    if base_symbol.upper() in inst_id.upper():
                        contract = self._parse_instrument(inst, base_symbol)
                        if contract:
                            self._cache[base_symbol] = contract
                            logger.info(f"Resolved {base_symbol} -> {contract.contract_id}")
                            return contract

                # Fallback to first result
                contract = self._parse_instrument(instruments[0], base_symbol)
                if contract:
                    self._cache[base_symbol] = contract
                return contract

            except Exception as e:
                logger.error(f"Error getting contract for {base_symbol}: {e}")
                return None

    def _parse_instrument(self, inst, base_symbol: str) -> Optional[ContractInfo]:
        """Parse SDK instrument into ContractInfo."""
        try:
            contract_id = getattr(inst, 'id', '')
            symbol = getattr(inst, 'name', '')
            symbol_id = getattr(inst, 'symbolId', '')
            description = getattr(inst, 'description', '')
            tick_size = float(getattr(inst, 'tickSize', 0.25))
            tick_value = float(getattr(inst, 'tickValue', 1.0))
            is_active = getattr(inst, 'activeContract', True)

            # Parse expiry from contract_id (e.g., CON.F.US.MNQ.H26)
            parts = contract_id.split('.')
            expiry_code = parts[-1] if len(parts) >= 5 else ''
            expiry_month = expiry_code[0] if expiry_code else 'H'
            expiry_year = int(expiry_code[1:]) if len(expiry_code) > 1 else 26

            return ContractInfo(
                contract_id=contract_id,
                symbol=symbol,
                base_symbol=base_symbol.upper(),
                symbol_id=symbol_id,
                description=description,
                tick_size=tick_size,
                tick_value=tick_value,
                is_active=is_active,
                expiry_month=expiry_month,
                expiry_year=expiry_year,
            )
        except Exception as e:
            logger.error(f"Error parsing instrument: {e}")
            return None

    def needs_rollover(self, base_symbol: str) -> bool:
        """
        Check if a contract needs rollover (approaching expiry).

        Args:
            base_symbol: Base symbol to check

        Returns:
            True if contract should be rolled
        """
        if base_symbol not in self._cache:
            return True

        contract = self._cache[base_symbol]

        # Check if cache is stale
        if datetime.now() - contract.last_updated > self._cache_ttl:
            return True

        # Check if approaching expiry (within 5 days of month end for quarterly)
        now = datetime.now()
        expiry_month = MONTH_CODES.get(contract.expiry_month, 3)
        expiry_year = 2000 + contract.expiry_year

        # Quarterly futures expire 3rd Friday of the month
        # We should roll ~1 week before
        if base_symbol in QUARTERLY_FUTURES:
            # Simple check: if we're in the expiry month and past the 10th
            if now.year == expiry_year and now.month == expiry_month and now.day > 10:
                return True

        return False

    async def refresh_contract(self, base_symbol: str) -> Optional[ContractInfo]:
        """
        Force refresh of contract info (for rollover).

        Args:
            base_symbol: Base symbol to refresh

        Returns:
            Updated ContractInfo
        """
        base_symbol = base_symbol.upper()

        # Clear cache
        if base_symbol in self._cache:
            del self._cache[base_symbol]

        # Fetch fresh
        return await self.get_active_contract(base_symbol)

    async def refresh_all(self) -> int:
        """
        Refresh all cached contracts.

        Returns:
            Number of contracts refreshed
        """
        symbols = list(self._cache.keys())
        count = 0

        for symbol in symbols:
            contract = await self.refresh_contract(symbol)
            if contract:
                count += 1

        logger.info(f"Refreshed {count} contracts")
        return count

    def get_contract_id(self, base_symbol: str) -> Optional[str]:
        """
        Get the contract ID for a base symbol from cache.

        Args:
            base_symbol: Base symbol

        Returns:
            Contract ID or None
        """
        base_symbol = base_symbol.upper()
        if base_symbol in self._cache:
            return self._cache[base_symbol].contract_id
        return None

    def get_all_tradeable_symbols(self) -> List[str]:
        """Get list of all tradeable symbols."""
        return list(self.TRADEABLE_SYMBOLS.keys())

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get static info about a symbol."""
        return self.TRADEABLE_SYMBOLS.get(symbol.upper())

    def calculate_position_value(
        self,
        base_symbol: str,
        contracts: int,
        price_change: float
    ) -> float:
        """
        Calculate P&L for a position.

        Args:
            base_symbol: Symbol
            contracts: Number of contracts
            price_change: Price change in points

        Returns:
            Dollar value of the move
        """
        if base_symbol not in self._cache:
            # Use static info
            info = self.TRADEABLE_SYMBOLS.get(base_symbol.upper(), {})
            tick_size = info.get('tick_size', 0.25)
            tick_value = info.get('tick_value', 1.0)
        else:
            contract = self._cache[base_symbol]
            tick_size = contract.tick_size
            tick_value = contract.tick_value

        ticks = price_change / tick_size
        return ticks * tick_value * contracts


# Global instance
_resolver: Optional[ContractResolver] = None


def get_contract_resolver() -> ContractResolver:
    """Get or create the global ContractResolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = ContractResolver()
    return _resolver
