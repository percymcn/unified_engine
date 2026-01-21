"""
SymbolNormalizationService

Domain service that normalizes incoming TradingView symbols and resolves
them to broker-specific formats using alias lookup and fuzzy matching.
"""

import re
import logging
from typing import List, Optional, Set
from difflib import SequenceMatcher

from app.domain.entities.symbol_alias import SymbolAlias

logger = logging.getLogger(__name__)


class SymbolNormalizationService:
    """
    Domain service for symbol normalization and resolution.

    Handles:
    - Stripping common suffixes from TradingView symbols
    - Generating variations for fuzzy matching
    - Resolving symbols using alias lookup + fuzzy matching

    Usage:
        service = SymbolNormalizationService()

        # Normalize symbol
        base = service.normalize_symbol("US30.pro")  # Returns "US30"

        # Get variations
        variations = service.get_variations("US30")  # Returns ["US30", "US30.PRO", ...]

        # Resolve symbol (needs repository for alias lookup)
        resolved = await service.resolve_symbol(
            user_id=1,
            source_symbol="US30",
            broker_type="tradelocker",
            available_symbols=["US30.pro", "US30.raw", "EURUSD"],
            alias_repository=repo
        )
    """

    # Common suffix patterns to strip for base symbol extraction
    # Ordered from most specific to least specific for greedy matching
    SUFFIX_PATTERNS = [
        r'\.pro$',      # TradeLocker professional
        r'\.raw$',      # Raw spread accounts
        r'\.std$',      # Standard accounts
        r'\.mini$',     # Mini contracts
        r'\.micro$',    # Micro contracts
        r'PR$',         # Suffix variant
        r'RAW$',        # Suffix variant
        r'STD$',        # Suffix variant
        r'MINI$',       # Suffix variant
        r'MICRO$',      # Suffix variant
        r'_SB$',        # Spread betting
        r'\.SB$',       # Spread betting variant
        r'\.r$',        # Short raw indicator
        r'\.s$',        # Short standard indicator
        r'[_-]?\d{2}$', # Futures month codes like "NQ25" or "ES_25"
        r'[FGHJKMNQUVXZ]\d{1,2}$',  # CME futures month codes (H25, M25, etc.)
    ]

    # Known symbol mappings for common instruments across brokers
    KNOWN_MAPPINGS = {
        # Dow Jones
        'US30': {'tradovate': 'YM', 'projectx': 'YM'},
        'DJ30': {'tradovate': 'YM', 'projectx': 'YM'},
        'DOW': {'tradovate': 'YM', 'projectx': 'YM'},
        # S&P 500
        'US500': {'tradovate': 'ES', 'projectx': 'ES'},
        'SPX500': {'tradovate': 'ES', 'projectx': 'ES'},
        'SPX': {'tradovate': 'ES', 'projectx': 'ES'},
        # NASDAQ
        'NAS100': {'tradovate': 'NQ', 'projectx': 'NQ'},
        'USTEC': {'tradovate': 'NQ', 'projectx': 'NQ'},
        'NDX': {'tradovate': 'NQ', 'projectx': 'NQ'},
        # Gold
        'XAUUSD': {'tradovate': 'GC', 'projectx': 'GC'},
        'GOLD': {'tradovate': 'GC', 'projectx': 'GC'},
        # Oil
        'USOIL': {'tradovate': 'CL', 'projectx': 'CL'},
        'WTIUSD': {'tradovate': 'CL', 'projectx': 'CL'},
    }

    def __init__(self, fuzzy_threshold: float = 0.8):
        """
        Initialize the service.

        Args:
            fuzzy_threshold: Minimum similarity ratio for fuzzy matching (0-1)
        """
        self.fuzzy_threshold = fuzzy_threshold
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.SUFFIX_PATTERNS]

    def normalize_symbol(self, symbol: str) -> str:
        """
        Extract base symbol by removing common suffixes.

        Args:
            symbol: Raw symbol string (e.g., "US30.pro", "NQ25")

        Returns:
            Normalized base symbol (e.g., "US30", "NQ")

        Examples:
            normalize_symbol("US30.pro") -> "US30"
            normalize_symbol("US30PR") -> "US30"
            normalize_symbol("NQ25") -> "NQ"
            normalize_symbol("EURUSD") -> "EURUSD"
        """
        if not symbol:
            return ""

        result = symbol.upper().strip()

        # Apply each pattern until no more matches
        for pattern in self._compiled_patterns:
            result = pattern.sub('', result)

        return result

    def get_variations(self, base_symbol: str) -> List[str]:
        """
        Generate common variations for a base symbol.

        Used for fuzzy matching against broker's available symbols.

        Args:
            base_symbol: Normalized base symbol

        Returns:
            List of possible variations to try matching

        Examples:
            get_variations("US30") -> ["US30", "US30.PRO", "US30.RAW", "US30.STD", ...]
        """
        if not base_symbol:
            return []

        base = base_symbol.upper().strip()
        variations: Set[str] = {base}

        # Add suffix variations
        suffixes = [
            '.pro', '.raw', '.std', '.mini', '.micro',
            'PR', 'RAW', 'STD', 'MINI',
            '_SB', '.SB', '.r', '.s',
        ]
        for suffix in suffixes:
            variations.add(f"{base}{suffix}")
            variations.add(f"{base}{suffix.upper()}")

        # Add common forex/CFD variations
        if len(base) >= 6 and not any(c.isdigit() for c in base):
            # EURUSD -> EUR/USD, EUR_USD
            mid = len(base) // 2
            variations.add(f"{base[:mid]}/{base[mid:]}")
            variations.add(f"{base[:mid]}_{base[mid:]}")

        return list(variations)

    def get_known_mapping(self, source_symbol: str, broker_type: str) -> Optional[str]:
        """
        Get known symbol mapping for a broker.

        Args:
            source_symbol: TradingView symbol
            broker_type: Target broker

        Returns:
            Known target symbol or None
        """
        normalized = self.normalize_symbol(source_symbol)
        broker_mappings = self.KNOWN_MAPPINGS.get(normalized)

        if broker_mappings:
            return broker_mappings.get(broker_type.lower())

        return None

    def fuzzy_match(self, source: str, candidates: List[str]) -> Optional[str]:
        """
        Find best fuzzy match from candidates.

        Args:
            source: Source symbol to match
            candidates: List of available symbols to match against

        Returns:
            Best matching symbol or None if no match above threshold
        """
        if not source or not candidates:
            return None

        normalized_source = self.normalize_symbol(source)
        source_variations = self.get_variations(normalized_source)

        best_match = None
        best_ratio = 0.0

        for candidate in candidates:
            # Try exact match first (case-insensitive)
            if candidate.upper() == normalized_source:
                return candidate

            # Check if any variation matches exactly
            for variation in source_variations:
                if candidate.upper() == variation.upper():
                    return candidate

            # Try normalized candidate comparison
            normalized_candidate = self.normalize_symbol(candidate)
            if normalized_candidate == normalized_source:
                return candidate

            # Fuzzy matching as last resort
            ratio = SequenceMatcher(None, normalized_source, normalized_candidate).ratio()
            if ratio > best_ratio and ratio >= self.fuzzy_threshold:
                best_ratio = ratio
                best_match = candidate

        return best_match

    async def resolve_symbol(
        self,
        user_id: int,
        source_symbol: str,
        broker_type: str,
        available_symbols: List[str],
        alias_repository=None
    ) -> Optional[str]:
        """
        Resolve TradingView symbol to broker format.

        Resolution order:
        1. User-defined aliases (highest priority)
        2. Auto-detected aliases
        3. Known static mappings
        4. Fuzzy matching against available symbols

        Args:
            user_id: User ID for alias lookup
            source_symbol: TradingView symbol
            broker_type: Target broker type
            available_symbols: List of symbols available on broker
            alias_repository: Optional repository for alias lookup

        Returns:
            Resolved symbol or None if no match found
        """
        if not source_symbol:
            return None

        normalized = source_symbol.upper().strip()
        broker = broker_type.lower().strip()

        logger.debug(f"Resolving symbol: {normalized} for broker: {broker}")

        # 1. Check user aliases first (via repository)
        if alias_repository:
            try:
                # Try user-defined alias
                alias = await alias_repository.get_alias(
                    user_id=user_id,
                    source_symbol=normalized,
                    broker_type=broker
                )
                if alias:
                    logger.info(
                        f"Resolved {normalized} -> {alias.target_symbol} "
                        f"via {'auto-detected' if alias.is_auto_detected else 'user-defined'} alias"
                    )
                    return alias.target_symbol
            except Exception as e:
                logger.warning(f"Alias lookup failed: {e}")

        # 2. Check known static mappings
        known = self.get_known_mapping(normalized, broker)
        if known and known in available_symbols:
            logger.info(f"Resolved {normalized} -> {known} via known mapping")
            return known

        # 3. Try exact match in available symbols
        for symbol in available_symbols:
            if symbol.upper() == normalized:
                logger.debug(f"Exact match found: {symbol}")
                return symbol

        # 4. Try fuzzy matching
        match = self.fuzzy_match(normalized, available_symbols)
        if match:
            logger.info(f"Resolved {normalized} -> {match} via fuzzy matching")
            return match

        logger.warning(f"Could not resolve symbol {normalized} for {broker}")
        return None

    async def resolve_and_cache(
        self,
        user_id: int,
        source_symbol: str,
        broker_type: str,
        available_symbols: List[str],
        alias_repository=None
    ) -> Optional[str]:
        """
        Resolve symbol and optionally cache as auto-detected alias.

        Same as resolve_symbol, but if a fuzzy match is found,
        it creates an auto-detected alias for faster future lookups.

        Args:
            user_id: User ID for alias lookup/creation
            source_symbol: TradingView symbol
            broker_type: Target broker type
            available_symbols: List of symbols available on broker
            alias_repository: Repository for alias operations

        Returns:
            Resolved symbol or None if no match found
        """
        resolved = await self.resolve_symbol(
            user_id=user_id,
            source_symbol=source_symbol,
            broker_type=broker_type,
            available_symbols=available_symbols,
            alias_repository=alias_repository
        )

        # Cache the resolution as auto-detected alias
        if resolved and alias_repository:
            normalized = source_symbol.upper().strip()
            broker = broker_type.lower().strip()

            try:
                # Check if alias already exists
                existing = await alias_repository.get_alias(
                    user_id=user_id,
                    source_symbol=normalized,
                    broker_type=broker
                )
                if not existing:
                    # Create auto-detected alias
                    alias = SymbolAlias(
                        user_id=user_id,
                        source_symbol=normalized,
                        broker_type=broker,
                        target_symbol=resolved,
                        is_auto_detected=True
                    )
                    await alias_repository.create(alias)
                    logger.info(f"Cached auto-detected alias: {normalized} -> {resolved}")
            except Exception as e:
                logger.warning(f"Failed to cache alias: {e}")

        return resolved
