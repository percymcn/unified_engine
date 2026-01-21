"""
SymbolFormatDetector Service

Analyzes broker symbols to detect naming patterns (suffixes, prefixes, case).
Used during account connection to auto-configure symbol resolution.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Set
from collections import Counter

logger = logging.getLogger(__name__)


class SymbolFormatDetector:
    """
    Analyzes broker symbols to detect format patterns.

    Detects:
    - Common suffixes (.pro, .raw, .std, .mini, .micro)
    - Prefixes (t, m for mini, etc.)
    - Case patterns (upper, lower, mixed)
    - Separators (., _, -)

    Usage:
        detector = SymbolFormatDetector()

        # Get available symbols from broker
        symbols = await broker.get_symbols()

        # Detect format
        detected = detector.detect_format(symbols)
        # Returns: {"suffix": ".pro", "prefix": "", "case": "upper", "confidence": 0.95}

        # Build symbol map
        symbol_map = detector.build_symbol_map(symbols, detected)
        # Returns: {"EURUSD": "EURUSD.pro", "US30": "US30.pro"}
    """

    # Reference symbols for pattern detection - common instruments across all brokers
    REFERENCE_SYMBOLS = [
        # Major Forex pairs
        "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD", "USDCHF",
        # Cross pairs
        "EURJPY", "GBPJPY", "EURGBP", "AUDJPY",
        # Metals
        "XAUUSD", "XAGUSD", "GOLD",
        # Indices
        "US30", "US500", "NAS100", "GER40", "UK100", "JP225",
        # Crypto
        "BTCUSD", "ETHUSD",
        # Oil
        "USOIL", "WTIUSD", "UKOIL",
    ]

    # Known suffix patterns to detect
    KNOWN_SUFFIXES = [
        ".pro", ".raw", ".std", ".mini", ".micro",
        ".r", ".s", ".m", ".sb",
        "_SB", "_MINI", "_MICRO",
    ]

    # Known prefix patterns
    KNOWN_PREFIXES = [
        "t", "m", "mini", "micro",
    ]

    def __init__(self):
        """Initialize the detector with compiled patterns."""
        # Compile suffix detection patterns
        self._suffix_patterns = [
            (re.compile(rf'{re.escape(suffix)}$', re.IGNORECASE), suffix)
            for suffix in self.KNOWN_SUFFIXES
        ]

    def detect_format(self, available_symbols: List[str]) -> Dict[str, Any]:
        """
        Analyze symbols to detect format patterns.

        Args:
            available_symbols: List of symbols from broker

        Returns:
            Dictionary with detected patterns:
            {
                "suffix": ".pro" | "" | None,
                "prefix": "t" | "" | None,
                "case": "upper" | "lower" | "mixed",
                "separator": "." | "_" | "",
                "confidence": 0.0-1.0
            }
        """
        if not available_symbols:
            return {
                "suffix": None,
                "prefix": None,
                "case": "upper",
                "separator": "",
                "confidence": 0.0,
            }

        # Detect suffix patterns
        suffix, suffix_confidence = self._detect_suffix(available_symbols)

        # Detect prefix patterns
        prefix, prefix_confidence = self._detect_prefix(available_symbols)

        # Detect case pattern
        case_pattern = self._detect_case(available_symbols)

        # Detect common separator
        separator = self._detect_separator(available_symbols)

        # Calculate overall confidence
        # Higher confidence if we found consistent patterns
        total_confidence = 0.0
        pattern_count = 0

        if suffix:
            total_confidence += suffix_confidence
            pattern_count += 1

        if prefix:
            total_confidence += prefix_confidence
            pattern_count += 1

        # Case detection is generally reliable
        total_confidence += 0.8
        pattern_count += 1

        confidence = total_confidence / pattern_count if pattern_count > 0 else 0.5

        result = {
            "suffix": suffix,
            "prefix": prefix,
            "case": case_pattern,
            "separator": separator,
            "confidence": round(confidence, 2),
        }

        logger.info(f"Detected symbol format: {result}")
        return result

    def _detect_suffix(self, symbols: List[str]) -> tuple[Optional[str], float]:
        """Detect the most common suffix pattern."""
        suffix_counts: Counter = Counter()
        total_matches = 0

        for symbol in symbols:
            for pattern, suffix in self._suffix_patterns:
                if pattern.search(symbol):
                    # Normalize suffix to lowercase for counting
                    suffix_counts[suffix.lower()] += 1
                    total_matches += 1
                    break

        if not suffix_counts:
            return None, 0.0

        # Get most common suffix
        most_common_suffix, count = suffix_counts.most_common(1)[0]
        confidence = count / len(symbols) if len(symbols) > 0 else 0.0

        # Only return if at least 20% of symbols have this suffix
        if confidence >= 0.2:
            return most_common_suffix, confidence

        return None, 0.0

    def _detect_prefix(self, symbols: List[str]) -> tuple[Optional[str], float]:
        """Detect common prefix patterns."""
        prefix_counts: Counter = Counter()

        for symbol in symbols:
            lower = symbol.lower()
            for prefix in self.KNOWN_PREFIXES:
                if lower.startswith(prefix):
                    # Verify it's actually a prefix (not part of symbol like "mini")
                    remainder = lower[len(prefix):]
                    if len(remainder) >= 3:  # Valid symbol remainder
                        prefix_counts[prefix] += 1
                        break

        if not prefix_counts:
            return None, 0.0

        most_common_prefix, count = prefix_counts.most_common(1)[0]
        confidence = count / len(symbols) if len(symbols) > 0 else 0.0

        # Only return if at least 10% of symbols have this prefix
        if confidence >= 0.1:
            return most_common_prefix, confidence

        return None, 0.0

    def _detect_case(self, symbols: List[str]) -> str:
        """Detect case pattern (upper, lower, mixed)."""
        upper_count = 0
        lower_count = 0
        mixed_count = 0

        for symbol in symbols:
            # Only check alphabetic characters
            alpha_chars = [c for c in symbol if c.isalpha()]
            if not alpha_chars:
                continue

            if all(c.isupper() for c in alpha_chars):
                upper_count += 1
            elif all(c.islower() for c in alpha_chars):
                lower_count += 1
            else:
                mixed_count += 1

        total = upper_count + lower_count + mixed_count
        if total == 0:
            return "upper"  # Default

        # Return dominant pattern
        if upper_count >= lower_count and upper_count >= mixed_count:
            return "upper"
        elif lower_count >= upper_count and lower_count >= mixed_count:
            return "lower"
        else:
            return "mixed"

    def _detect_separator(self, symbols: List[str]) -> str:
        """Detect common separator character."""
        separator_counts = Counter()

        for symbol in symbols:
            if "." in symbol:
                separator_counts["."] += 1
            if "_" in symbol:
                separator_counts["_"] += 1
            if "-" in symbol:
                separator_counts["-"] += 1

        if not separator_counts:
            return ""

        most_common, count = separator_counts.most_common(1)[0]
        # Only return if at least 20% of symbols use this separator
        if count / len(symbols) >= 0.2:
            return most_common

        return ""

    def build_symbol_map(
        self,
        available_symbols: List[str],
        detected_format: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Build mapping from standard symbols to broker format.

        Args:
            available_symbols: List of symbols from broker
            detected_format: Output from detect_format()

        Returns:
            Mapping from standard symbol to broker format:
            {"EURUSD": "EURUSD.pro", "US30": "US30.pro", ...}
        """
        symbol_map: Dict[str, str] = {}

        # Create lowercase lookup for case-insensitive matching
        symbol_lookup = {s.upper(): s for s in available_symbols}

        suffix = detected_format.get("suffix", "") or ""
        prefix = detected_format.get("prefix", "") or ""
        case_pattern = detected_format.get("case", "upper")

        for ref_symbol in self.REFERENCE_SYMBOLS:
            # Try to find this reference symbol in available symbols
            match = self._find_symbol_match(ref_symbol, available_symbols, symbol_lookup, detected_format)

            if match:
                symbol_map[ref_symbol] = match
                logger.debug(f"Mapped {ref_symbol} -> {match}")

        logger.info(f"Built symbol map with {len(symbol_map)} mappings")
        return symbol_map

    def _find_symbol_match(
        self,
        ref_symbol: str,
        available_symbols: List[str],
        symbol_lookup: Dict[str, str],
        detected_format: Dict[str, Any]
    ) -> Optional[str]:
        """Find the best match for a reference symbol."""
        suffix = detected_format.get("suffix", "") or ""
        prefix = detected_format.get("prefix", "") or ""

        # Try direct match first
        if ref_symbol.upper() in symbol_lookup:
            return symbol_lookup[ref_symbol.upper()]

        # Try with detected suffix
        if suffix:
            candidate = f"{ref_symbol}{suffix}"
            if candidate.upper() in symbol_lookup:
                return symbol_lookup[candidate.upper()]

        # Try with detected prefix
        if prefix:
            candidate = f"{prefix}{ref_symbol}"
            if candidate.upper() in symbol_lookup:
                return symbol_lookup[candidate.upper()]

        # Try with both prefix and suffix
        if prefix and suffix:
            candidate = f"{prefix}{ref_symbol}{suffix}"
            if candidate.upper() in symbol_lookup:
                return symbol_lookup[candidate.upper()]

        # Try fuzzy matching - find symbols containing the reference
        for avail_symbol in available_symbols:
            # Check if available symbol contains the reference (case-insensitive)
            if ref_symbol.upper() in avail_symbol.upper():
                return avail_symbol

        return None

    def match_symbol(
        self,
        source_symbol: str,
        available_symbols: List[str],
        detected_format: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Find best match for a source symbol in available symbols.

        Args:
            source_symbol: Symbol to match (e.g., "EURUSD" or "US30")
            available_symbols: List of available broker symbols
            detected_format: Optional pre-detected format (for optimization)

        Returns:
            Matched broker symbol or None
        """
        if not source_symbol or not available_symbols:
            return None

        source_upper = source_symbol.upper().strip()
        symbol_lookup = {s.upper(): s for s in available_symbols}

        # Exact match (case-insensitive)
        if source_upper in symbol_lookup:
            return symbol_lookup[source_upper]

        # If we have detected format, try with suffix/prefix
        if detected_format:
            suffix = detected_format.get("suffix", "") or ""
            prefix = detected_format.get("prefix", "") or ""

            # Try with suffix
            if suffix:
                candidate = f"{source_upper}{suffix}"
                if candidate.upper() in symbol_lookup:
                    return symbol_lookup[candidate.upper()]

            # Try with prefix
            if prefix:
                candidate = f"{prefix}{source_upper}"
                if candidate.upper() in symbol_lookup:
                    return symbol_lookup[candidate.upper()]

            # Try with both
            if prefix and suffix:
                candidate = f"{prefix}{source_upper}{suffix}"
                if candidate.upper() in symbol_lookup:
                    return symbol_lookup[candidate.upper()]

        # Fuzzy: find symbols containing the source
        matches = []
        for avail in available_symbols:
            avail_upper = avail.upper()
            if source_upper in avail_upper:
                # Prefer shorter matches (more likely to be correct)
                matches.append((len(avail), avail))

        if matches:
            # Return shortest match
            matches.sort(key=lambda x: x[0])
            return matches[0][1]

        return None

    def get_format_description(self, detected_format: Dict[str, Any]) -> str:
        """
        Generate human-readable description of detected format.

        Args:
            detected_format: Output from detect_format()

        Returns:
            Description string like "Uppercase with .pro suffix"
        """
        parts = []

        case_pattern = detected_format.get("case", "upper")
        if case_pattern == "upper":
            parts.append("Uppercase")
        elif case_pattern == "lower":
            parts.append("Lowercase")
        else:
            parts.append("Mixed case")

        suffix = detected_format.get("suffix")
        if suffix:
            parts.append(f"with {suffix} suffix")

        prefix = detected_format.get("prefix")
        if prefix:
            parts.append(f"with {prefix} prefix")

        confidence = detected_format.get("confidence", 0)
        if confidence >= 0.8:
            parts.append("(high confidence)")
        elif confidence >= 0.5:
            parts.append("(medium confidence)")
        else:
            parts.append("(low confidence)")

        return " ".join(parts)
