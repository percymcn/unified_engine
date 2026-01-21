"""
Tests for Symbol Normalization Service

Tests cover:
- Symbol normalization (suffix stripping)
- Variation generation
- Known mappings lookup
- Fuzzy matching
- Full resolution flow
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.domain.services.symbol_normalization_service import SymbolNormalizationService
from app.domain.entities.symbol_alias import SymbolAlias


class TestSymbolNormalization:
    """Tests for normalize_symbol method"""

    def setup_method(self):
        self.service = SymbolNormalizationService()

    def test_normalize_symbol_strips_pro_suffix(self):
        """Should strip .pro suffix"""
        assert self.service.normalize_symbol("US30.pro") == "US30"
        assert self.service.normalize_symbol("US30.PRO") == "US30"

    def test_normalize_symbol_strips_raw_suffix(self):
        """Should strip .raw suffix"""
        assert self.service.normalize_symbol("EURUSD.raw") == "EURUSD"
        assert self.service.normalize_symbol("EURUSD.RAW") == "EURUSD"

    def test_normalize_symbol_strips_std_suffix(self):
        """Should strip .std suffix"""
        assert self.service.normalize_symbol("XAUUSD.std") == "XAUUSD"

    def test_normalize_symbol_strips_mini_suffix(self):
        """Should strip .mini suffix"""
        assert self.service.normalize_symbol("NQ.mini") == "NQ"
        assert self.service.normalize_symbol("NQMINI") == "NQ"

    def test_normalize_symbol_strips_sb_suffix(self):
        """Should strip spread betting suffix"""
        assert self.service.normalize_symbol("UK100_SB") == "UK100"
        assert self.service.normalize_symbol("UK100.SB") == "UK100"

    def test_normalize_symbol_strips_futures_month_codes(self):
        """Should strip futures month codes when delimited or CME-style"""
        # Delimited futures codes
        assert self.service.normalize_symbol("ES_25") == "ES"
        assert self.service.normalize_symbol("NQ-25") == "NQ"
        # CME front month codes (H=March, M=June, U=Sept, Z=Dec)
        assert self.service.normalize_symbol("NQH25") == "NQ"
        assert self.service.normalize_symbol("ESM25") == "ES"
        assert self.service.normalize_symbol("NQU25") == "NQ"
        assert self.service.normalize_symbol("ESZ25") == "ES"
        # Should NOT strip regular numbers (US30 is a valid symbol)
        assert self.service.normalize_symbol("NQ25") == "NQ25"  # No delimiter = keep as is
        assert self.service.normalize_symbol("ES25") == "ES25"  # No delimiter = keep as is

    def test_normalize_symbol_uppercase(self):
        """Should normalize to uppercase"""
        assert self.service.normalize_symbol("eurusd") == "EURUSD"
        assert self.service.normalize_symbol("Eurusd") == "EURUSD"

    def test_normalize_symbol_no_change(self):
        """Should return unchanged if no suffix"""
        assert self.service.normalize_symbol("EURUSD") == "EURUSD"
        assert self.service.normalize_symbol("US30") == "US30"
        assert self.service.normalize_symbol("NQ") == "NQ"

    def test_normalize_symbol_empty(self):
        """Should handle empty string"""
        assert self.service.normalize_symbol("") == ""

    def test_normalize_symbol_whitespace(self):
        """Should strip whitespace"""
        assert self.service.normalize_symbol(" US30 ") == "US30"


class TestGetVariations:
    """Tests for get_variations method"""

    def setup_method(self):
        self.service = SymbolNormalizationService()

    def test_get_variations_includes_base(self):
        """Should include base symbol in variations"""
        variations = self.service.get_variations("US30")
        assert "US30" in variations

    def test_get_variations_includes_suffixes(self):
        """Should include common suffix variations"""
        variations = self.service.get_variations("US30")
        assert "US30.pro" in variations or "US30.PRO" in variations
        assert "US30.raw" in variations or "US30.RAW" in variations

    def test_get_variations_forex_pairs(self):
        """Should generate forex pair variations"""
        variations = self.service.get_variations("EURUSD")
        # Should include slash and underscore variants
        assert "EUR/USD" in variations
        assert "EUR_USD" in variations

    def test_get_variations_empty(self):
        """Should return empty list for empty input"""
        assert self.service.get_variations("") == []


class TestKnownMappings:
    """Tests for get_known_mapping method"""

    def setup_method(self):
        self.service = SymbolNormalizationService()

    def test_known_mapping_us30_tradovate(self):
        """Should map US30 to YM for Tradovate"""
        assert self.service.get_known_mapping("US30", "tradovate") == "YM"

    def test_known_mapping_us500_tradovate(self):
        """Should map US500 to ES for Tradovate"""
        assert self.service.get_known_mapping("US500", "tradovate") == "ES"

    def test_known_mapping_nas100_tradovate(self):
        """Should map NAS100 to NQ for Tradovate"""
        assert self.service.get_known_mapping("NAS100", "tradovate") == "NQ"

    def test_known_mapping_xauusd_tradovate(self):
        """Should map XAUUSD to GC for Tradovate"""
        assert self.service.get_known_mapping("XAUUSD", "tradovate") == "GC"

    def test_known_mapping_no_match(self):
        """Should return None for unknown symbols"""
        assert self.service.get_known_mapping("UNKNOWN", "tradovate") is None

    def test_known_mapping_no_broker(self):
        """Should return None for unknown broker"""
        assert self.service.get_known_mapping("US30", "unknown_broker") is None


class TestFuzzyMatch:
    """Tests for fuzzy_match method"""

    def setup_method(self):
        self.service = SymbolNormalizationService()

    def test_fuzzy_match_exact(self):
        """Should return exact match"""
        candidates = ["EURUSD", "GBPUSD", "US30"]
        assert self.service.fuzzy_match("EURUSD", candidates) == "EURUSD"

    def test_fuzzy_match_case_insensitive(self):
        """Should match case-insensitively"""
        candidates = ["EURUSD", "GBPUSD", "US30"]
        assert self.service.fuzzy_match("eurusd", candidates) == "EURUSD"

    def test_fuzzy_match_with_suffix(self):
        """Should match when source has suffix"""
        candidates = ["US30.pro", "US30.raw", "EURUSD"]
        result = self.service.fuzzy_match("US30", candidates)
        # Should find US30.pro or US30.raw
        assert result is not None
        assert "US30" in result

    def test_fuzzy_match_variation(self):
        """Should match variations"""
        candidates = ["US30.PRO", "EURUSD", "GBPUSD"]
        result = self.service.fuzzy_match("US30", candidates)
        assert result == "US30.PRO"

    def test_fuzzy_match_no_match(self):
        """Should return None for no match"""
        candidates = ["EURUSD", "GBPUSD"]
        assert self.service.fuzzy_match("XYZABC", candidates) is None

    def test_fuzzy_match_empty_candidates(self):
        """Should return None for empty candidates"""
        assert self.service.fuzzy_match("US30", []) is None

    def test_fuzzy_match_threshold(self):
        """Should respect fuzzy threshold"""
        service = SymbolNormalizationService(fuzzy_threshold=0.95)
        candidates = ["EURUSD", "GBPUSD"]
        # "EUR" vs "EURUSD" - not similar enough at 0.95 threshold
        assert service.fuzzy_match("EUR", candidates) is None


class TestSymbolAlias:
    """Tests for SymbolAlias entity"""

    def test_create_valid_alias(self):
        """Should create valid alias"""
        alias = SymbolAlias(
            user_id=1,
            source_symbol="US30",
            broker_type="tradelocker",
            target_symbol="US30.pro"
        )
        assert alias.source_symbol == "US30"
        assert alias.broker_type == "tradelocker"
        assert alias.target_symbol == "US30.pro"

    def test_alias_normalizes_source(self):
        """Should normalize source symbol to uppercase"""
        alias = SymbolAlias(
            user_id=1,
            source_symbol="us30",
            broker_type="tradelocker",
            target_symbol="US30.pro"
        )
        assert alias.source_symbol == "US30"

    def test_alias_normalizes_broker(self):
        """Should normalize broker type to lowercase"""
        alias = SymbolAlias(
            user_id=1,
            source_symbol="US30",
            broker_type="TRADELOCKER",
            target_symbol="US30.pro"
        )
        assert alias.broker_type == "tradelocker"

    def test_alias_validates_empty_source(self):
        """Should reject empty source symbol"""
        with pytest.raises(Exception):  # ValidationError
            SymbolAlias(
                user_id=1,
                source_symbol="",
                broker_type="tradelocker",
                target_symbol="US30.pro"
            )

    def test_alias_validates_invalid_broker(self):
        """Should reject invalid broker type"""
        with pytest.raises(Exception):  # ValidationError
            SymbolAlias(
                user_id=1,
                source_symbol="US30",
                broker_type="invalid_broker",
                target_symbol="US30.pro"
            )

    def test_alias_validates_user_id(self):
        """Should reject invalid user_id"""
        with pytest.raises(Exception):  # ValidationError
            SymbolAlias(
                user_id=0,
                source_symbol="US30",
                broker_type="tradelocker",
                target_symbol="US30.pro"
            )

    def test_alias_update_target(self):
        """Should update target symbol"""
        alias = SymbolAlias(
            user_id=1,
            source_symbol="US30",
            broker_type="tradelocker",
            target_symbol="US30.pro"
        )
        alias.update_target("US30.raw")
        assert alias.target_symbol == "US30.raw"
        assert alias.is_auto_detected is False

    def test_alias_mark_auto_detected(self):
        """Should mark as auto-detected"""
        alias = SymbolAlias(
            user_id=1,
            source_symbol="US30",
            broker_type="tradelocker",
            target_symbol="US30.pro"
        )
        alias.mark_auto_detected()
        assert alias.is_auto_detected is True


class TestResolveSymbol:
    """Tests for resolve_symbol method"""

    def setup_method(self):
        self.service = SymbolNormalizationService()

    @pytest.mark.asyncio
    async def test_resolve_with_alias(self):
        """Should resolve using alias when available"""
        # Mock repository
        mock_repo = AsyncMock()
        mock_alias = SymbolAlias(
            id=1,
            user_id=1,
            source_symbol="US30",
            broker_type="tradelocker",
            target_symbol="US30.pro",
            is_auto_detected=False
        )
        mock_repo.get_alias.return_value = mock_alias

        result = await self.service.resolve_symbol(
            user_id=1,
            source_symbol="US30",
            broker_type="tradelocker",
            available_symbols=["US30.pro", "US30.raw"],
            alias_repository=mock_repo
        )

        assert result == "US30.pro"
        mock_repo.get_alias.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_with_known_mapping(self):
        """Should resolve using known mapping"""
        result = await self.service.resolve_symbol(
            user_id=1,
            source_symbol="US30",
            broker_type="tradovate",
            available_symbols=["YM", "ES", "NQ"],
            alias_repository=None
        )

        assert result == "YM"

    @pytest.mark.asyncio
    async def test_resolve_exact_match(self):
        """Should return exact match"""
        result = await self.service.resolve_symbol(
            user_id=1,
            source_symbol="EURUSD",
            broker_type="tradelocker",
            available_symbols=["EURUSD", "GBPUSD"],
            alias_repository=None
        )

        assert result == "EURUSD"

    @pytest.mark.asyncio
    async def test_resolve_fuzzy_match(self):
        """Should use fuzzy match as fallback"""
        result = await self.service.resolve_symbol(
            user_id=1,
            source_symbol="US30",
            broker_type="tradelocker",
            available_symbols=["US30.pro", "US30.raw", "EURUSD"],
            alias_repository=None
        )

        assert result in ["US30.pro", "US30.raw"]

    @pytest.mark.asyncio
    async def test_resolve_no_match(self):
        """Should return None when no match found"""
        result = await self.service.resolve_symbol(
            user_id=1,
            source_symbol="UNKNOWN_SYMBOL",
            broker_type="tradelocker",
            available_symbols=["EURUSD", "GBPUSD"],
            alias_repository=None
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_alias_priority_over_known(self):
        """User alias should take priority over known mapping"""
        mock_repo = AsyncMock()
        # User has custom alias for US30 -> YM_Custom
        mock_alias = SymbolAlias(
            id=1,
            user_id=1,
            source_symbol="US30",
            broker_type="tradovate",
            target_symbol="YM_Custom",
            is_auto_detected=False
        )
        mock_repo.get_alias.return_value = mock_alias

        result = await self.service.resolve_symbol(
            user_id=1,
            source_symbol="US30",
            broker_type="tradovate",
            available_symbols=["YM", "YM_Custom", "ES"],
            alias_repository=mock_repo
        )

        # Should use user's alias, not the known mapping
        assert result == "YM_Custom"


class TestResolveAndCache:
    """Tests for resolve_and_cache method"""

    def setup_method(self):
        self.service = SymbolNormalizationService()

    @pytest.mark.asyncio
    async def test_resolve_and_cache_creates_alias(self):
        """Should cache fuzzy match as auto-detected alias"""
        mock_repo = AsyncMock()
        mock_repo.get_alias.return_value = None  # No existing alias

        result = await self.service.resolve_and_cache(
            user_id=1,
            source_symbol="US30",
            broker_type="tradelocker",
            available_symbols=["US30.pro", "EURUSD"],
            alias_repository=mock_repo
        )

        assert result == "US30.pro"
        # Should have tried to create alias
        mock_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_and_cache_skips_existing(self):
        """Should not create alias if one already exists"""
        mock_repo = AsyncMock()
        # Existing alias exists
        mock_alias = SymbolAlias(
            id=1,
            user_id=1,
            source_symbol="US30",
            broker_type="tradelocker",
            target_symbol="US30.pro",
            is_auto_detected=True
        )
        mock_repo.get_alias.return_value = mock_alias

        result = await self.service.resolve_and_cache(
            user_id=1,
            source_symbol="US30",
            broker_type="tradelocker",
            available_symbols=["US30.pro", "EURUSD"],
            alias_repository=mock_repo
        )

        assert result == "US30.pro"
        # Should NOT have tried to create alias (already exists)
        mock_repo.create.assert_not_called()
