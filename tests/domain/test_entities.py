"""Tests for domain entities"""
import pytest
from decimal import Decimal
from datetime import datetime

from app.domain.entities.signal import Signal
from app.domain.entities.trade import Trade
from app.domain.entities.order import Order
from app.domain.entities.account import Account
from app.domain.entities.position import Position
from app.domain.value_objects import (
    SignalId, Symbol, Volume, Price, AccountId, OrderId, PositionId, Money, StopLoss, TakeProfit
)
from app.domain.enums import (
    SignalSource, SignalAction, SignalStatus, OrderType, OrderStatus,
    BrokerType, AccountType, TradeStatus, PositionSide
)
from app.domain.exceptions import (
    SignalValidationError, BusinessRuleViolation, ValidationError,
    InsufficientBalanceError, AccountDisabledError
)


class TestSignal:
    def test_create_close_signal_without_volume(self):
        """CLOSE signals don't require volume"""
        signal = Signal(
            id=SignalId("sig-1"),
            source=SignalSource.TRADINGVIEW,
            symbol=Symbol("EURUSD"),
            action=SignalAction.CLOSE,
        )
        assert signal.status == SignalStatus.PENDING

    def test_buy_signal_without_volume_raises_error(self):
        """BUY signals require volume"""
        with pytest.raises(SignalValidationError, match="Volume required"):
            Signal(
                id=SignalId("sig-1"),
                source=SignalSource.TRADINGVIEW,
                symbol=Symbol("EURUSD"),
                action=SignalAction.BUY,
                volume=None,
            )

    def test_sell_signal_without_volume_raises_error(self):
        """SELL signals require volume"""
        with pytest.raises(SignalValidationError, match="Volume required"):
            Signal(
                id=SignalId("sig-1"),
                source=SignalSource.API,
                symbol=Symbol("GBPUSD"),
                action=SignalAction.SELL,
                volume=None,
            )

    def test_signal_state_transitions(self):
        """Test valid state transitions"""
        signal = Signal(
            id=SignalId("sig-1"),
            source=SignalSource.API,
            symbol=Symbol("GBPUSD"),
            action=SignalAction.BUY,
            volume=Volume(Decimal("1.0")),
        )
        assert signal.is_pending

        signal.mark_processing()
        assert signal.status == SignalStatus.PROCESSING

        signal.mark_processed()
        assert signal.is_processed
        assert signal.processed_at is not None

    def test_cannot_process_non_pending_signal(self):
        signal = Signal(
            id=SignalId("sig-1"),
            source=SignalSource.API,
            symbol=Symbol("USDJPY"),
            action=SignalAction.CLOSE,
        )
        signal.mark_processing()
        signal.mark_processed()

        with pytest.raises(BusinessRuleViolation, match="Cannot process signal"):
            signal.mark_processing()

    def test_mark_failed(self):
        signal = Signal(
            id=SignalId("sig-1"),
            source=SignalSource.TRADINGVIEW,
            symbol=Symbol("EURUSD"),
            action=SignalAction.CLOSE,
        )
        signal.mark_failed("Test error")
        assert signal.is_failed
        assert signal.error_message == "Test error"
        assert signal.processed_at is not None

    def test_mark_skipped(self):
        signal = Signal(
            id=SignalId("sig-1"),
            source=SignalSource.TRADINGVIEW,
            symbol=Symbol("EURUSD"),
            action=SignalAction.CLOSE,
        )
        signal.mark_skipped("No accounts")
        assert signal.status == SignalStatus.SKIPPED
        assert signal.error_message == "No accounts"

    def test_add_target_account(self):
        signal = Signal(
            id=SignalId("sig-1"),
            source=SignalSource.API,
            symbol=Symbol("EURUSD"),
            action=SignalAction.CLOSE,
        )
        signal.add_target_account(AccountId("acc-1"))
        assert AccountId("acc-1") in signal.target_accounts

    def test_add_duplicate_target_account_skipped(self):
        signal = Signal(
            id=SignalId("sig-1"),
            source=SignalSource.API,
            symbol=Symbol("EURUSD"),
            action=SignalAction.CLOSE,
        )
        signal.add_target_account(AccountId("acc-1"))
        signal.add_target_account(AccountId("acc-1"))
        assert signal.target_accounts.count(AccountId("acc-1")) == 1


class TestTrade:
    def test_create_trade(self):
        trade = Trade(
            trade_id="t-1",
            broker_trade_id="broker-123",
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            order_type=OrderType.BUY,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            open_time=datetime.utcnow(),
        )
        assert trade.is_open
        assert trade.status == TradeStatus.OPEN

    def test_close_trade_calculates_pnl(self):
        trade = Trade(
            trade_id="t-1",
            broker_trade_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            order_type=OrderType.BUY,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            open_time=datetime.utcnow(),
        )
        trade.close(Price(Decimal("1.1050")))

        assert trade.is_closed
        assert trade.realized_pnl.amount > 0

    def test_cannot_close_already_closed_trade(self):
        trade = Trade(
            trade_id="t-1",
            broker_trade_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            order_type=OrderType.BUY,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            open_time=datetime.utcnow(),
        )
        trade.close(Price(Decimal("1.1050")))

        with pytest.raises(BusinessRuleViolation, match="Cannot close trade"):
            trade.close(Price(Decimal("1.1100")))

    def test_partial_close_trade(self):
        trade = Trade(
            trade_id="t-1",
            broker_trade_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            order_type=OrderType.BUY,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            open_time=datetime.utcnow(),
        )
        closed_part = trade.partial_close(Volume(Decimal("0.5")), Price(Decimal("1.1050")))

        assert trade.status == TradeStatus.PARTIALLY_CLOSED
        assert trade.volume.value == Decimal("0.5")
        assert closed_part.is_closed
        assert closed_part.volume.value == Decimal("0.5")

    def test_update_sl_tp(self):
        trade = Trade(
            trade_id="t-1",
            broker_trade_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            order_type=OrderType.BUY,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            open_time=datetime.utcnow(),
        )
        trade.update_sl_tp(
            stop_loss=Price(Decimal("1.0950")),
            take_profit=Price(Decimal("1.1100"))
        )
        assert trade.stop_loss.value == Decimal("1.0950")
        assert trade.take_profit.value == Decimal("1.1100")


class TestOrder:
    def test_market_order_no_price_required(self):
        order = Order(
            id=OrderId("o-1"),
            broker_order_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            order_type=OrderType.BUY,
            volume=Volume(Decimal("1.0")),
        )
        assert order.is_pending
        assert order.is_market_order

    def test_limit_order_requires_price(self):
        with pytest.raises(ValidationError, match="requires price"):
            Order(
                id=OrderId("o-1"),
                broker_order_id=None,
                account_id="acc-1",
                symbol=Symbol("EURUSD"),
                order_type=OrderType.BUY_LIMIT,
                volume=Volume(Decimal("1.0")),
                price=None,  # Missing price
            )

    def test_fill_order(self):
        order = Order(
            id=OrderId("o-1"),
            broker_order_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            order_type=OrderType.BUY,
            volume=Volume(Decimal("1.0")),
        )
        order.fill(Volume(Decimal("1.0")), Price(Decimal("1.1000")))

        assert order.is_filled
        assert order.status == OrderStatus.EXECUTED

    def test_partial_fill_order(self):
        order = Order(
            id=OrderId("o-1"),
            broker_order_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            order_type=OrderType.BUY,
            volume=Volume(Decimal("1.0")),
        )
        order.fill(Volume(Decimal("0.5")), Price(Decimal("1.1000")))
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.remaining_volume == Decimal("0.5")

    def test_cancel_order(self):
        order = Order(
            id=OrderId("o-1"),
            broker_order_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            order_type=OrderType.BUY,
            volume=Volume(Decimal("1.0")),
        )
        order.cancel()
        assert order.status == OrderStatus.CANCELLED

    def test_cannot_cancel_executed_order(self):
        order = Order(
            id=OrderId("o-1"),
            broker_order_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            order_type=OrderType.BUY,
            volume=Volume(Decimal("1.0")),
        )
        order.fill(Volume(Decimal("1.0")), Price(Decimal("1.1000")))

        with pytest.raises(BusinessRuleViolation, match="Cannot cancel executed"):
            order.cancel()

    def test_reject_order(self):
        order = Order(
            id=OrderId("o-1"),
            broker_order_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            order_type=OrderType.BUY,
            volume=Volume(Decimal("1.0")),
        )
        order.reject("Insufficient margin")
        assert order.status == OrderStatus.REJECTED
        assert order.comment == "Insufficient margin"


class TestAccount:
    def test_create_account(self):
        account = Account(
            id=AccountId("acc-1"),
            user_id=1,
            broker=BrokerType.MT5,
            account_type=AccountType.DEMO,
            balance=Money(Decimal("10000")),
            equity=Money(Decimal("10000")),
        )
        assert account.free_margin == Decimal("10000")

    def test_check_margin_for_trade(self):
        account = Account(
            id=AccountId("acc-1"),
            user_id=1,
            broker=BrokerType.MT5,
            account_type=AccountType.DEMO,
            balance=Money(Decimal("10000")),
            equity=Money(Decimal("10000")),
        )
        assert account.check_margin_for_trade(Money(Decimal("5000")))
        assert not account.check_margin_for_trade(Money(Decimal("15000")))

    def test_reserve_margin(self):
        account = Account(
            id=AccountId("acc-1"),
            user_id=1,
            broker=BrokerType.MT5,
            account_type=AccountType.DEMO,
            balance=Money(Decimal("10000")),
            equity=Money(Decimal("10000")),
        )
        account.reserve_margin(Money(Decimal("2000")))
        assert account.margin.amount == Decimal("2000")
        assert account.free_margin == Decimal("8000")

    def test_insufficient_margin_raises_error(self):
        account = Account(
            id=AccountId("acc-1"),
            user_id=1,
            broker=BrokerType.MT5,
            account_type=AccountType.DEMO,
            balance=Money(Decimal("1000")),
            equity=Money(Decimal("1000")),
        )
        with pytest.raises(InsufficientBalanceError):
            account.reserve_margin(Money(Decimal("2000")))

    def test_release_margin(self):
        account = Account(
            id=AccountId("acc-1"),
            user_id=1,
            broker=BrokerType.MT5,
            account_type=AccountType.DEMO,
            balance=Money(Decimal("10000")),
            equity=Money(Decimal("10000")),
        )
        account.reserve_margin(Money(Decimal("2000")))
        account.release_margin(Money(Decimal("1000")))
        assert account.margin.amount == Decimal("1000")
        assert account.free_margin == Decimal("9000")

    def test_disabled_account_cannot_update(self):
        account = Account(
            id=AccountId("acc-1"),
            user_id=1,
            broker=BrokerType.MT5,
            account_type=AccountType.DEMO,
            balance=Money(Decimal("10000")),
            equity=Money(Decimal("10000")),
        )
        account.deactivate()
        with pytest.raises(AccountDisabledError):
            account.update_balance(Money(Decimal("11000")))

    def test_realize_pnl(self):
        account = Account(
            id=AccountId("acc-1"),
            user_id=1,
            broker=BrokerType.MT5,
            account_type=AccountType.DEMO,
            balance=Money(Decimal("10000")),
            equity=Money(Decimal("10000")),
        )
        account.realize_pnl(Money(Decimal("500")))
        assert account.balance.amount == Decimal("10500")
        assert account.equity.amount == Decimal("10500")

    def test_margin_level(self):
        account = Account(
            id=AccountId("acc-1"),
            user_id=1,
            broker=BrokerType.MT5,
            account_type=AccountType.DEMO,
            balance=Money(Decimal("10000")),
            equity=Money(Decimal("8000")),
            margin=Money(Decimal("2000")),
        )
        # Margin level = equity / margin * 100 = 8000 / 2000 * 100 = 400%
        assert account.margin_level == Decimal("400")

    def test_margin_call_detection(self):
        account = Account(
            id=AccountId("acc-1"),
            user_id=1,
            broker=BrokerType.MT5,
            account_type=AccountType.DEMO,
            balance=Money(Decimal("10000")),
            equity=Money(Decimal("900")),
            margin=Money(Decimal("1000")),
        )
        # 90% margin level < 100%
        assert account.is_margin_call

    def test_connect_disconnect(self):
        account = Account(
            id=AccountId("acc-1"),
            user_id=1,
            broker=BrokerType.MT5,
            account_type=AccountType.DEMO,
            balance=Money(Decimal("10000")),
            equity=Money(Decimal("10000")),
        )
        assert not account.is_connected
        account.connect()
        assert account.is_connected
        account.disconnect()
        assert not account.is_connected


class TestPosition:
    def test_unrealized_pnl_long(self):
        position = Position(
            id=PositionId("pos-1"),
            broker_position_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            side=PositionSide.LONG,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            current_price=Price(Decimal("1.1050")),
            open_time=datetime.utcnow(),
        )
        # Price went up 50 pips, long position should profit
        assert position.unrealized_pnl > 0

    def test_unrealized_pnl_short(self):
        position = Position(
            id=PositionId("pos-1"),
            broker_position_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            side=PositionSide.SHORT,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            current_price=Price(Decimal("1.0950")),
            open_time=datetime.utcnow(),
        )
        # Price went down 50 pips, short position should profit
        assert position.unrealized_pnl > 0

    def test_stop_loss_validation_long(self):
        position = Position(
            id=PositionId("pos-1"),
            broker_position_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            side=PositionSide.LONG,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            current_price=Price(Decimal("1.1000")),
            open_time=datetime.utcnow(),
        )
        # SL above current price should fail for LONG
        with pytest.raises(ValidationError, match="below current price"):
            position.update_sl_tp(stop_loss=Price(Decimal("1.1050")))

    def test_stop_loss_validation_short(self):
        position = Position(
            id=PositionId("pos-1"),
            broker_position_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            side=PositionSide.SHORT,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            current_price=Price(Decimal("1.1000")),
            open_time=datetime.utcnow(),
        )
        # SL below current price should fail for SHORT
        with pytest.raises(ValidationError, match="above current price"):
            position.update_sl_tp(stop_loss=Price(Decimal("1.0950")))

    def test_update_price(self):
        position = Position(
            id=PositionId("pos-1"),
            broker_position_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            side=PositionSide.LONG,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            current_price=Price(Decimal("1.1000")),
            open_time=datetime.utcnow(),
        )
        position.update_price(Price(Decimal("1.1050")))
        assert position.current_price.value == Decimal("1.1050")

    def test_partial_close(self):
        position = Position(
            id=PositionId("pos-1"),
            broker_position_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            side=PositionSide.LONG,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            current_price=Price(Decimal("1.1050")),
            open_time=datetime.utcnow(),
        )
        remaining = position.partial_close(Volume(Decimal("0.5")))
        assert remaining.value == Decimal("0.5")
        assert position.volume.value == Decimal("0.5")

    def test_close_position(self):
        position = Position(
            id=PositionId("pos-1"),
            broker_position_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            side=PositionSide.LONG,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            current_price=Price(Decimal("1.1050")),
            open_time=datetime.utcnow(),
        )
        assert position.is_active
        position.close()
        assert not position.is_active

    def test_add_to_position(self):
        position = Position(
            id=PositionId("pos-1"),
            broker_position_id=None,
            account_id="acc-1",
            symbol=Symbol("EURUSD"),
            side=PositionSide.LONG,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.1000")),
            current_price=Price(Decimal("1.1000")),
            open_time=datetime.utcnow(),
        )
        position.add_to_position(Volume(Decimal("1.0")), Price(Decimal("1.1100")))
        assert position.volume.value == Decimal("2.0")
        # Average price should be (1.1000 + 1.1100) / 2 = 1.1050
        assert position.open_price.value == Decimal("1.1050")
