"""Tests for domain value objects"""
import pytest
from decimal import Decimal

from app.domain.value_objects import (
    Money, Volume, Price, Symbol, AccountId, SignalId, OrderId, PositionId,
    StopLoss, TakeProfit
)
from app.domain.exceptions import ValidationError


class TestMoney:
    def test_create_valid_money(self):
        m = Money(Decimal("100.50"))
        assert m.amount == Decimal("100.50")
        assert m.currency == "USD"

    def test_create_with_currency(self):
        m = Money(Decimal("100"), "EUR")
        assert m.currency == "EUR"

    def test_currency_normalized_to_uppercase(self):
        m = Money(Decimal("100"), "eur")
        assert m.currency == "EUR"

    def test_negative_amount_raises_error(self):
        with pytest.raises(ValidationError, match="cannot be negative"):
            Money(Decimal("-10"))

    def test_invalid_currency_raises_error(self):
        with pytest.raises(ValidationError, match="3-letter"):
            Money(Decimal("100"), "US")

    def test_add_same_currency(self):
        m1 = Money(Decimal("100"))
        m2 = Money(Decimal("50"))
        result = m1 + m2
        assert result.amount == Decimal("150")

    def test_add_different_currency_raises_error(self):
        m1 = Money(Decimal("100"), "USD")
        m2 = Money(Decimal("50"), "EUR")
        with pytest.raises(ValidationError, match="different currencies"):
            m1 + m2

    def test_subtract_same_currency(self):
        m1 = Money(Decimal("100"))
        m2 = Money(Decimal("30"))
        result = m1 - m2
        assert result.amount == Decimal("70")

    def test_subtract_different_currency_raises_error(self):
        m1 = Money(Decimal("100"), "USD")
        m2 = Money(Decimal("50"), "EUR")
        with pytest.raises(ValidationError, match="different currencies"):
            m1 - m2

    def test_money_is_immutable(self):
        m = Money(Decimal("100"))
        with pytest.raises(Exception):  # FrozenInstanceError
            m.amount = Decimal("200")


class TestVolume:
    def test_create_valid_volume(self):
        v = Volume(Decimal("1.5"))
        assert v.value == Decimal("1.5")

    def test_zero_volume_raises_error(self):
        with pytest.raises(ValidationError, match="must be positive"):
            Volume(Decimal("0"))

    def test_negative_volume_raises_error(self):
        with pytest.raises(ValidationError, match="must be positive"):
            Volume(Decimal("-1"))

    def test_volume_is_immutable(self):
        v = Volume(Decimal("1.0"))
        with pytest.raises(Exception):  # FrozenInstanceError
            v.value = Decimal("2.0")


class TestPrice:
    def test_create_valid_price(self):
        p = Price(Decimal("1.1234"))
        assert p.value == Decimal("1.1234")

    def test_zero_price_allowed(self):
        p = Price(Decimal("0"))
        assert p.value == Decimal("0")

    def test_negative_price_raises_error(self):
        with pytest.raises(ValidationError, match="cannot be negative"):
            Price(Decimal("-1.5"))

    def test_price_is_immutable(self):
        p = Price(Decimal("1.1000"))
        with pytest.raises(Exception):  # FrozenInstanceError
            p.value = Decimal("1.2000")


class TestSymbol:
    def test_create_valid_symbol(self):
        s = Symbol("eurusd")
        assert s.value == "EURUSD"  # Uppercased

    def test_symbol_normalized_to_uppercase(self):
        s = Symbol("GbpUsD")
        assert s.value == "GBPUSD"

    def test_empty_symbol_raises_error(self):
        with pytest.raises(ValidationError, match="between 1 and 20"):
            Symbol("")

    def test_long_symbol_raises_error(self):
        with pytest.raises(ValidationError, match="between 1 and 20"):
            Symbol("A" * 21)

    def test_symbol_is_immutable(self):
        s = Symbol("EURUSD")
        with pytest.raises(Exception):  # FrozenInstanceError
            s.value = "GBPUSD"


class TestIdentifiers:
    def test_account_id(self):
        aid = AccountId("acc-123")
        assert aid.value == "acc-123"

    def test_empty_account_id_raises_error(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            AccountId("")

    def test_signal_id(self):
        sid = SignalId("sig-456")
        assert sid.value == "sig-456"

    def test_empty_signal_id_raises_error(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            SignalId("")

    def test_order_id(self):
        oid = OrderId("ord-789")
        assert oid.value == "ord-789"

    def test_empty_order_id_raises_error(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            OrderId("")

    def test_position_id(self):
        pid = PositionId("pos-012")
        assert pid.value == "pos-012"

    def test_empty_position_id_raises_error(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            PositionId("")

    def test_identifiers_are_immutable(self):
        aid = AccountId("acc-1")
        with pytest.raises(Exception):  # FrozenInstanceError
            aid.value = "acc-2"


class TestStopLoss:
    def test_create_stop_loss(self):
        sl = StopLoss(Price(Decimal("1.0900")))
        assert sl.price.value == Decimal("1.0900")

    def test_stop_loss_is_immutable(self):
        sl = StopLoss(Price(Decimal("1.0900")))
        with pytest.raises(Exception):  # FrozenInstanceError
            sl.price = Price(Decimal("1.0800"))


class TestTakeProfit:
    def test_create_take_profit(self):
        tp = TakeProfit(Price(Decimal("1.1100")))
        assert tp.price.value == Decimal("1.1100")

    def test_take_profit_is_immutable(self):
        tp = TakeProfit(Price(Decimal("1.1100")))
        with pytest.raises(Exception):  # FrozenInstanceError
            tp.price = Price(Decimal("1.1200"))
