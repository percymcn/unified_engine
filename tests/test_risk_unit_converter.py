"""
Unit tests for Risk Unit Converter Service

Tests conversion of broker-specific risk units (pips/points/percent) to absolute prices.
"""

import pytest
from app.domain.services.risk_unit_converter import (
    RiskUnitConverter,
    RiskUnitMode
)


class TestRiskUnitConverter:
    """Test risk unit conversion for different brokers"""

    def test_convert_pips_to_price_tradelocker_buy_sl(self):
        """Test converting pips to price for TradeLocker buy order stop loss"""
        # EURUSD at 1.0850, 50 pips stop loss
        # For buy: SL should be below entry (1.0850 - 0.0050 = 1.0800)
        result = RiskUnitConverter.convert_pips_to_price(
            pips=50.0,
            entry_price=1.0850,
            is_buy=True,
            is_stop_loss=True,
            digits=5
        )
        assert abs(result - 1.0800) < 0.0001, f"Expected ~1.0800, got {result}"

    def test_convert_pips_to_price_mt4_sell_tp(self):
        """Test converting pips to price for MT4 sell order take profit"""
        # GBPUSD at 1.2500, 100 pips take profit
        # For sell: TP should be below entry (1.2500 - 0.0100 = 1.2400)
        result = RiskUnitConverter.convert_pips_to_price(
            pips=100.0,
            entry_price=1.2500,
            is_buy=False,
            is_stop_loss=False,
            digits=5
        )
        assert abs(result - 1.2400) < 0.0001, f"Expected ~1.2400, got {result}"

    def test_convert_points_to_price_tradovate_buy_sl(self):
        """Test converting points to price for Tradovate buy order stop loss"""
        # ES futures at 4500.00, 10 points stop loss
        # For buy: SL should be below entry (4500.00 - 2.50 = 4497.50)
        # Tick size for ES is 0.25, so 10 points = 10 * 0.25 = 2.50
        result = RiskUnitConverter.convert_points_to_price(
            points=10.0,
            entry_price=4500.00,
            is_buy=True,
            is_stop_loss=True,
            tick_size=0.25
        )
        assert abs(result - 4497.50) < 0.01, f"Expected ~4497.50, got {result}"

    def test_convert_percent_to_price_projectx_buy_sl(self):
        """Test converting percent to price for ProjectX buy order stop loss"""
        # Account balance percentage: 2% stop loss
        # Entry price: 1.0850
        # For buy: SL should be below entry (1.0850 - 0.0217 = 1.0633)
        # Price distance = 1.0850 * 0.02 = 0.0217
        result = RiskUnitConverter.convert_percent_to_price(
            percent=2.0,
            entry_price=1.0850,
            is_buy=True,
            is_stop_loss=True
        )
        expected = 1.0850 - (1.0850 * 0.02)
        assert abs(result - expected) < 0.0001, f"Expected ~{expected}, got {result}"

    def test_convert_risk_unit_to_price_pips(self):
        """Test main conversion function with pips"""
        result = RiskUnitConverter.convert_risk_unit_to_price(
            value=50.0,
            mode=RiskUnitMode.PIPS,
            entry_price=1.0850,
            is_buy=True,
            is_stop_loss=True,
            digits=5
        )
        assert abs(result - 1.0800) < 0.0001

    def test_convert_risk_unit_to_price_points(self):
        """Test main conversion function with points"""
        result = RiskUnitConverter.convert_risk_unit_to_price(
            value=10.0,
            mode=RiskUnitMode.POINTS,
            entry_price=4500.00,
            is_buy=True,
            is_stop_loss=True,
            tick_size=0.25
        )
        assert abs(result - 4497.50) < 0.01

    def test_convert_risk_unit_to_price_percent(self):
        """Test main conversion function with percent"""
        result = RiskUnitConverter.convert_risk_unit_to_price(
            value=2.0,
            mode=RiskUnitMode.PERCENT,
            entry_price=1.0850,
            is_buy=True,
            is_stop_loss=True
        )
        expected = 1.0850 - (1.0850 * 0.02)
        assert abs(result - expected) < 0.0001

    def test_convert_risk_unit_to_price_already_absolute(self):
        """Test that price mode returns value as-is"""
        result = RiskUnitConverter.convert_risk_unit_to_price(
            value=1.0800,
            mode=RiskUnitMode.PRICE,
            entry_price=1.0850,
            is_buy=True,
            is_stop_loss=True
        )
        assert result == 1.0800

    def test_validation_negative_pips(self):
        """Test that negative pips raise ValueError"""
        with pytest.raises(ValueError, match="must be positive"):
            RiskUnitConverter.convert_pips_to_price(
                pips=-10.0,
                entry_price=1.0850,
                is_buy=True,
                is_stop_loss=True,
                digits=5
            )

    def test_validation_sl_correct_side_buy(self):
        """Test that stop loss is correctly placed below entry for buy orders"""
        # For buy, SL must be below entry
        result = RiskUnitConverter.convert_pips_to_price(
            pips=50.0,
            entry_price=1.0850,
            is_buy=True,
            is_stop_loss=True,
            digits=5
        )
        # SL should be below entry (1.0850 - 0.0050 = 1.0800)
        assert result < 1.0850, f"Stop loss {result} should be below entry 1.0850"
        assert abs(result - 1.0800) < 0.0001

    def test_validation_zero_entry_price(self):
        """Test that zero entry price raises ValueError"""
        with pytest.raises(ValueError, match="must be positive"):
            RiskUnitConverter.convert_pips_to_price(
                pips=50.0,
                entry_price=0.0,
                is_buy=True,
                is_stop_loss=True,
                digits=5
            )

    def test_jpy_pair_pip_size(self):
        """Test JPY pair uses correct pip size (0.01 for 3-4 digits)"""
        # USDJPY at 150.00, 50 pips stop loss
        # For 3-digit JPY: pip = 0.01
        result = RiskUnitConverter.convert_pips_to_price(
            pips=50.0,
            entry_price=150.00,
            is_buy=True,
            is_stop_loss=True,
            digits=3
        )
        # 150.00 - (50 * 0.01) = 150.00 - 0.50 = 149.50
        assert abs(result - 149.50) < 0.01

    def test_get_default_tick_size(self):
        """Test default tick size retrieval"""
        assert RiskUnitConverter.get_default_tick_size("tradovate") == 0.25
        assert RiskUnitConverter.get_default_tick_size("projectx") == 0.25
        assert RiskUnitConverter.get_default_tick_size("tradelocker") == 0.0001

    def test_get_default_digits(self):
        """Test default digits retrieval"""
        assert RiskUnitConverter.get_default_digits("tradelocker") == 5
        assert RiskUnitConverter.get_default_digits("mt4") == 5
        assert RiskUnitConverter.get_default_digits("mt5") == 5
