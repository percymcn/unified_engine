"""
Tests for Symbol Auto-Detection (Plan 20-02)

Tests:
1. SymbolFormatDetector - pattern detection and symbol mapping
2. Integration with test connection (symbol detection on connection)
3. Auto-alias creation flow
"""

import pytest
from typing import List

from app.domain.services.symbol_format_detector import SymbolFormatDetector


class TestSymbolFormatDetector:
    """Tests for SymbolFormatDetector service."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return SymbolFormatDetector()

    # -------------------
    # Suffix Detection Tests
    # -------------------

    def test_detect_pro_suffix(self, detector: SymbolFormatDetector):
        """Should detect .pro suffix pattern."""
        symbols = [
            "EURUSD.pro", "GBPUSD.pro", "USDJPY.pro",
            "XAUUSD.pro", "US30.pro", "NAS100.pro"
        ]
        result = detector.detect_format(symbols)

        assert result["suffix"] == ".pro"
        assert result["case"] == "upper"
        assert result["confidence"] >= 0.8

    def test_detect_raw_suffix(self, detector: SymbolFormatDetector):
        """Should detect .raw suffix pattern."""
        symbols = [
            "EURUSD.raw", "GBPUSD.raw", "USDJPY.raw",
            "XAUUSD.raw", "US30.raw", "NAS100.raw"
        ]
        result = detector.detect_format(symbols)

        assert result["suffix"] == ".raw"
        assert result["confidence"] >= 0.8

    def test_detect_std_suffix(self, detector: SymbolFormatDetector):
        """Should detect .std suffix pattern."""
        symbols = [
            "EURUSD.std", "GBPUSD.std", "USDJPY.std",
            "AUDUSD.std", "NZDUSD.std"
        ]
        result = detector.detect_format(symbols)

        assert result["suffix"] == ".std"

    def test_detect_no_suffix(self, detector: SymbolFormatDetector):
        """Should return None suffix when no consistent pattern."""
        symbols = [
            "EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
            "XAUUSD", "US30", "NAS100"
        ]
        result = detector.detect_format(symbols)

        assert result["suffix"] is None
        assert result["case"] == "upper"

    def test_detect_mixed_suffixes(self, detector: SymbolFormatDetector):
        """Should detect most common suffix when mixed."""
        symbols = [
            "EURUSD.pro", "GBPUSD.pro", "USDJPY.pro",  # 3 .pro
            "XAUUSD.raw", "NZDUSD.raw",  # 2 .raw
            "US30", "NAS100"  # 2 no suffix
        ]
        result = detector.detect_format(symbols)

        # Should detect .pro as it's most common
        assert result["suffix"] == ".pro"

    # -------------------
    # Case Detection Tests
    # -------------------

    def test_detect_uppercase(self, detector: SymbolFormatDetector):
        """Should detect uppercase pattern."""
        symbols = ["EURUSD", "GBPUSD", "XAUUSD", "US30"]
        result = detector.detect_format(symbols)

        assert result["case"] == "upper"

    def test_detect_lowercase(self, detector: SymbolFormatDetector):
        """Should detect lowercase pattern."""
        symbols = ["eurusd", "gbpusd", "xauusd", "us30"]
        result = detector.detect_format(symbols)

        assert result["case"] == "lower"

    def test_detect_mixed_case(self, detector: SymbolFormatDetector):
        """Should detect mixed case pattern."""
        symbols = ["EURusd", "GBPusd", "XAUusd"]
        result = detector.detect_format(symbols)

        assert result["case"] == "mixed"

    # -------------------
    # Symbol Map Building Tests
    # -------------------

    def test_build_symbol_map_with_suffix(self, detector: SymbolFormatDetector):
        """Should build correct mapping with suffix."""
        symbols = [
            "EURUSD.pro", "GBPUSD.pro", "USDJPY.pro",
            "XAUUSD.pro", "US30.pro", "NAS100.pro", "BTCUSD.pro"
        ]
        detected = detector.detect_format(symbols)
        symbol_map = detector.build_symbol_map(symbols, detected)

        assert symbol_map.get("EURUSD") == "EURUSD.pro"
        assert symbol_map.get("US30") == "US30.pro"
        assert symbol_map.get("NAS100") == "NAS100.pro"
        assert symbol_map.get("XAUUSD") == "XAUUSD.pro"

    def test_build_symbol_map_no_suffix(self, detector: SymbolFormatDetector):
        """Should build correct mapping without suffix."""
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US30", "NAS100"]
        detected = detector.detect_format(symbols)
        symbol_map = detector.build_symbol_map(symbols, detected)

        # Direct mapping when no suffix
        assert symbol_map.get("EURUSD") == "EURUSD"
        assert symbol_map.get("US30") == "US30"

    def test_build_symbol_map_finds_partial_matches(self, detector: SymbolFormatDetector):
        """Should find symbols containing reference symbols."""
        # TradeLocker-style symbols with instrument prefixes
        symbols = [
            "FX:EURUSD.pro", "FX:GBPUSD.pro",
            "IDX:US30.pro", "IDX:NAS100.pro"
        ]
        detected = detector.detect_format(symbols)
        symbol_map = detector.build_symbol_map(symbols, detected)

        # Should find symbols containing the reference
        assert "EURUSD" in symbol_map or any("EURUSD" in v for v in symbol_map.values())

    # -------------------
    # Symbol Matching Tests
    # -------------------

    def test_match_symbol_exact(self, detector: SymbolFormatDetector):
        """Should match exact symbols."""
        symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        match = detector.match_symbol("EURUSD", symbols)

        assert match == "EURUSD"

    def test_match_symbol_case_insensitive(self, detector: SymbolFormatDetector):
        """Should match case-insensitively."""
        symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        match = detector.match_symbol("eurusd", symbols)

        assert match == "EURUSD"

    def test_match_symbol_with_format(self, detector: SymbolFormatDetector):
        """Should match using detected format."""
        symbols = ["EURUSD.pro", "GBPUSD.pro", "USDJPY.pro"]
        detected = {"suffix": ".pro", "prefix": None, "case": "upper"}

        match = detector.match_symbol("EURUSD", symbols, detected)
        assert match == "EURUSD.pro"

    def test_match_symbol_fuzzy_contains(self, detector: SymbolFormatDetector):
        """Should find symbol containing source."""
        symbols = ["EURUSD.pro", "EURUSD.raw", "GBPUSD.pro"]
        match = detector.match_symbol("EURUSD", symbols)

        # Should match one of the EURUSD variants
        assert "EURUSD" in match

    def test_match_symbol_not_found(self, detector: SymbolFormatDetector):
        """Should return None for unmatched symbol."""
        symbols = ["GBPUSD", "USDJPY", "AUDUSD"]
        match = detector.match_symbol("EURUSD", symbols)

        assert match is None

    # -------------------
    # Edge Cases
    # -------------------

    def test_empty_symbols_list(self, detector: SymbolFormatDetector):
        """Should handle empty symbol list."""
        result = detector.detect_format([])

        assert result["suffix"] is None
        assert result["confidence"] == 0.0

    def test_single_symbol(self, detector: SymbolFormatDetector):
        """Should handle single symbol."""
        result = detector.detect_format(["EURUSD.pro"])

        assert result["suffix"] == ".pro"
        assert result["case"] == "upper"

    def test_symbols_with_numbers(self, detector: SymbolFormatDetector):
        """Should correctly handle symbols with numbers."""
        symbols = ["US30.pro", "US500.pro", "NAS100.pro", "GER40.pro"]
        result = detector.detect_format(symbols)

        assert result["suffix"] == ".pro"
        symbol_map = detector.build_symbol_map(symbols, result)
        assert symbol_map.get("US30") == "US30.pro"
        assert symbol_map.get("NAS100") == "NAS100.pro"

    def test_format_description(self, detector: SymbolFormatDetector):
        """Should generate human-readable description."""
        detected = {"suffix": ".pro", "prefix": None, "case": "upper", "confidence": 0.9}
        desc = detector.get_format_description(detected)

        assert "Uppercase" in desc
        assert ".pro" in desc
        assert "high confidence" in desc


class TestSymbolFormatDetectorIntegration:
    """Integration tests with realistic broker symbol lists."""

    @pytest.fixture
    def detector(self):
        return SymbolFormatDetector()

    def test_tradelocker_style_symbols(self, detector: SymbolFormatDetector):
        """Test with TradeLocker-style symbols."""
        symbols = [
            "EURUSD.pro", "GBPUSD.pro", "USDJPY.pro", "AUDUSD.pro",
            "NZDUSD.pro", "USDCAD.pro", "USDCHF.pro",
            "XAUUSD.pro", "XAGUSD.pro",
            "US30.pro", "US500.pro", "NAS100.pro", "GER40.pro",
            "BTCUSD.pro", "ETHUSD.pro"
        ]

        detected = detector.detect_format(symbols)
        assert detected["suffix"] == ".pro"

        symbol_map = detector.build_symbol_map(symbols, detected)

        # All reference symbols should be mapped
        assert len(symbol_map) > 10

        # Specific checks
        assert symbol_map.get("EURUSD") == "EURUSD.pro"
        assert symbol_map.get("US30") == "US30.pro"
        assert symbol_map.get("XAUUSD") == "XAUUSD.pro"

    def test_mt5_style_symbols(self, detector: SymbolFormatDetector):
        """Test with MT5-style symbols (no suffix, uppercase)."""
        symbols = [
            "EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
            "NZDUSD", "USDCAD", "USDCHF",
            "XAUUSD", "XAGUSD",
            "US30", "US500", "NAS100", "GER40",
            "BTCUSD", "ETHUSD"
        ]

        detected = detector.detect_format(symbols)
        assert detected["suffix"] is None
        assert detected["case"] == "upper"

        symbol_map = detector.build_symbol_map(symbols, detected)

        # Direct mapping
        assert symbol_map.get("EURUSD") == "EURUSD"
        assert symbol_map.get("US30") == "US30"

    def test_tradovate_style_futures(self, detector: SymbolFormatDetector):
        """Test with Tradovate-style futures symbols."""
        # Tradovate uses ES, NQ, YM for indices, GC for gold, CL for oil
        symbols = [
            "ES", "NQ", "YM", "RTY",
            "GC", "SI", "CL", "NG",
            "6E", "6B", "6J"  # FX futures
        ]

        detected = detector.detect_format(symbols)
        assert detected["suffix"] is None
        assert detected["case"] == "upper"

        symbol_map = detector.build_symbol_map(symbols, detected)

        # Futures don't match TradingView-style names directly
        # The KNOWN_MAPPINGS in SymbolNormalizationService handles this


class TestBrokerSymbolFormatModel:
    """Tests for BrokerSymbolFormat model (database table)."""

    def test_model_import(self):
        """Should be able to import BrokerSymbolFormat model."""
        from app.models.models import BrokerSymbolFormat

        assert BrokerSymbolFormat.__tablename__ == "broker_symbol_formats"

    def test_model_columns(self):
        """Should have correct columns."""
        from app.models.models import BrokerSymbolFormat

        # Check column names exist
        columns = BrokerSymbolFormat.__table__.columns.keys()
        assert "id" in columns
        assert "account_id" in columns
        assert "detected_patterns" in columns
        assert "sample_symbols" in columns
        assert "common_symbols_map" in columns
        assert "detected_at" in columns


class TestAutoAliasCreation:
    """Tests for auto-alias creation flow."""

    def test_create_account_dto_has_symbol_fields(self):
        """CreateAccountRequest should have symbol detection fields."""
        from app.application.dto.account_dto import CreateAccountRequest
        from app.domain.enums import BrokerType, AccountType

        request = CreateAccountRequest(
            user_id=1,
            broker=BrokerType.TRADELOCKER,
            account_type=AccountType.DEMO,
            credentials={"api_key": "test"},
            account_id="12345",
            detected_format={"suffix": ".pro", "case": "upper"},
            symbol_map={"EURUSD": "EURUSD.pro", "US30": "US30.pro"},
            sample_symbols=["EURUSD.pro", "GBPUSD.pro", "US30.pro"]
        )

        assert request.detected_format == {"suffix": ".pro", "case": "upper"}
        assert request.symbol_map == {"EURUSD": "EURUSD.pro", "US30": "US30.pro"}
        assert len(request.sample_symbols) == 3

    def test_create_account_response_has_alias_count(self):
        """CreateAccountResponse should have auto_aliases_created field."""
        from app.application.dto.account_dto import CreateAccountResponse
        from app.domain.enums import BrokerType

        response = CreateAccountResponse(
            account_id="test-id",
            broker=BrokerType.TRADELOCKER,
            is_active=True,
            auto_aliases_created=15
        )

        assert response.auto_aliases_created == 15

    def test_test_connection_response_has_detection_fields(self):
        """TestConnectionResponse should have symbol detection fields."""
        from app.application.dto.account_dto import TestConnectionResponse

        response = TestConnectionResponse(
            success=True,
            status="connected",
            message="Connected",
            detected_format={"suffix": ".pro", "case": "upper", "confidence": 0.95},
            symbol_map={"EURUSD": "EURUSD.pro"},
            sample_symbols=["EURUSD.pro", "GBPUSD.pro"]
        )

        assert response.detected_format["suffix"] == ".pro"
        assert response.detected_format["confidence"] == 0.95
        assert response.symbol_map["EURUSD"] == "EURUSD.pro"
        assert len(response.sample_symbols) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
