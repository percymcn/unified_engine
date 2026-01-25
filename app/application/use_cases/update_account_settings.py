"""
Update Account Settings Use Case

Use case for updating per-account position sizing and risk limit settings.
"""
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database_models import TradingAccount, AccountGroup
from app.application.dto.account_settings_dto import (
    AccountSettingsRequest,
    AccountSettingsResponse,
    GetAccountSettingsRequest,
)
from app.domain.exceptions import AccountNotFoundError

logger = logging.getLogger(__name__)


class UpdateAccountSettingsUseCase:
    """Use case for updating account settings"""

    def __init__(self, session: Session):
        self._session = session

    async def execute(self, request: AccountSettingsRequest, user_id: int) -> AccountSettingsResponse:
        """
        Update account settings.

        Only updates fields that are provided (non-None) in the request.
        Validates account ownership before updating.
        """
        # Get account
        if isinstance(self._session, AsyncSession):
            stmt = select(TradingAccount).where(
                TradingAccount.id == request.account_id,
                TradingAccount.user_id == user_id
            )
            result = await self._session.execute(stmt)
            account = result.scalar_one_or_none()
        else:
            account = self._session.query(TradingAccount).filter(
                TradingAccount.id == request.account_id,
                TradingAccount.user_id == user_id
            ).first()

        if not account:
            raise AccountNotFoundError(f"Account {request.account_id} not found")

        # Build update dict from non-None values
        updates = {}

        # Position sizing
        if request.position_sizing_mode is not None:
            updates['position_sizing_mode'] = request.position_sizing_mode.value
        if request.fixed_lot_size is not None:
            self._validate_range(request.fixed_lot_size, 0.01, 100, "fixed_lot_size")
            updates['fixed_lot_size'] = request.fixed_lot_size
        if request.percent_of_balance is not None:
            self._validate_range(request.percent_of_balance, 0.1, 100, "percent_of_balance")
            updates['percent_of_balance'] = request.percent_of_balance
        if request.percent_of_equity is not None:
            self._validate_range(request.percent_of_equity, 0.1, 100, "percent_of_equity")
            updates['percent_of_equity'] = request.percent_of_equity
        if request.risk_percent_per_trade is not None:
            self._validate_range(request.risk_percent_per_trade, 0.1, 10, "risk_percent_per_trade")
            updates['risk_percent_per_trade'] = request.risk_percent_per_trade

        # Risk limits
        if request.max_position_size is not None:
            self._validate_range(request.max_position_size, 0.01, float('inf'), "max_position_size")
            updates['max_position_size'] = request.max_position_size
        if request.max_daily_loss is not None:
            self._validate_range(request.max_daily_loss, 0, float('inf'), "max_daily_loss")
            updates['max_daily_loss'] = request.max_daily_loss
        if request.max_daily_loss_pct is not None:
            self._validate_range(request.max_daily_loss_pct, 0, 100, "max_daily_loss_pct")
            updates['max_daily_loss_pct'] = request.max_daily_loss_pct
        if request.max_drawdown_pct is not None:
            self._validate_range(request.max_drawdown_pct, 0, 100, "max_drawdown_pct")
            updates['max_drawdown_pct'] = request.max_drawdown_pct
        if request.max_open_positions is not None:
            self._validate_range(request.max_open_positions, 1, 100, "max_open_positions")
            updates['max_open_positions'] = request.max_open_positions
        if request.max_daily_trades is not None:
            self._validate_range(request.max_daily_trades, 1, 1000, "max_daily_trades")
            updates['max_daily_trades'] = request.max_daily_trades
        if request.trade_cooldown_seconds is not None:
            self._validate_range(request.trade_cooldown_seconds, 0, 3600, "trade_cooldown_seconds")
            updates['trade_cooldown_seconds'] = request.trade_cooldown_seconds
        # Default stop loss/take profit (stored in broker-specific units)
        if request.default_stop_loss is not None:
            updates['default_stop_loss'] = request.default_stop_loss
        if request.default_take_profit is not None:
            updates['default_take_profit'] = request.default_take_profit

        # Grouping - validate group exists and belongs to user
        if request.group_id is not None:
            if request.group_id == 0:
                # Clear group assignment
                updates['group_id'] = None
                updates['group_name'] = None
                updates['group_color'] = None
            else:
                if isinstance(self._session, AsyncSession):
                    stmt = select(AccountGroup).where(
                        AccountGroup.id == request.group_id,
                        AccountGroup.user_id == user_id
                    )
                    result = await self._session.execute(stmt)
                    group = result.scalar_one_or_none()
                else:
                    group = self._session.query(AccountGroup).filter(
                        AccountGroup.id == request.group_id,
                        AccountGroup.user_id == user_id
                    ).first()
                if not group:
                    raise ValueError(f"Group {request.group_id} not found")
                updates['group_id'] = group.id
                updates['group_name'] = group.name
                updates['group_color'] = group.color

        # Routing
        if request.is_signal_enabled is not None:
            updates['is_signal_enabled'] = request.is_signal_enabled
        if request.signal_priority is not None:
            self._validate_range(request.signal_priority, 0, 100, "signal_priority")
            updates['signal_priority'] = request.signal_priority

        # Apply updates
        for field, value in updates.items():
            setattr(account, field, value)

        if isinstance(self._session, AsyncSession):
            await self._session.commit()
            await self._session.refresh(account)
        else:
            self._session.commit()
            self._session.refresh(account)

        logger.info(f"Updated settings for account {request.account_id}: {list(updates.keys())}")

        return self._to_response(account)

    def _validate_range(self, value: float, min_val: float, max_val: float, field_name: str):
        """Validate that value is within allowed range."""
        if value < min_val or value > max_val:
            raise ValueError(f"{field_name} must be between {min_val} and {max_val}")

    def _to_response(self, account: TradingAccount) -> AccountSettingsResponse:
        """Convert account to settings response."""
        return AccountSettingsResponse(
            account_id=account.id,
            position_sizing_mode=account.position_sizing_mode or "fixed",
            fixed_lot_size=account.fixed_lot_size or 0.01,
            percent_of_balance=account.percent_of_balance or 1.0,
            percent_of_equity=account.percent_of_equity or 1.0,
            risk_percent_per_trade=account.risk_percent_per_trade or 1.0,
            max_position_size=account.max_position_size,
            max_daily_loss=account.max_daily_loss,
            max_daily_loss_pct=account.max_daily_loss_pct,
            max_drawdown_pct=account.max_drawdown_pct,
            max_open_positions=account.max_open_positions,
            max_daily_trades=account.max_daily_trades,
            trade_cooldown_seconds=account.trade_cooldown_seconds,
            default_stop_loss=getattr(account, 'default_stop_loss', None),
            default_take_profit=getattr(account, 'default_take_profit', None),
            group_id=account.group_id,
            group_name=account.group_name,
            group_color=account.group_color,
            is_signal_enabled=account.is_signal_enabled if account.is_signal_enabled is not None else True,
            signal_priority=account.signal_priority or 0,
        )


class GetAccountSettingsUseCase:
    """Use case for getting account settings"""

    def __init__(self, session: Session):
        self._session = session

    async def execute(self, request: GetAccountSettingsRequest) -> AccountSettingsResponse:
        """Get current account settings."""
        if isinstance(self._session, AsyncSession):
            stmt = select(TradingAccount).where(
                TradingAccount.id == request.account_id,
                TradingAccount.user_id == request.user_id
            )
            result = await self._session.execute(stmt)
            account = result.scalar_one_or_none()
        else:
            account = self._session.query(TradingAccount).filter(
                TradingAccount.id == request.account_id,
                TradingAccount.user_id == request.user_id
            ).first()

        if not account:
            raise AccountNotFoundError(f"Account {request.account_id} not found")

        return AccountSettingsResponse(
            account_id=account.id,
            position_sizing_mode=account.position_sizing_mode or "fixed",
            fixed_lot_size=account.fixed_lot_size or 0.01,
            percent_of_balance=account.percent_of_balance or 1.0,
            percent_of_equity=account.percent_of_equity or 1.0,
            risk_percent_per_trade=account.risk_percent_per_trade or 1.0,
            max_position_size=account.max_position_size,
            max_daily_loss=account.max_daily_loss,
            max_daily_loss_pct=account.max_daily_loss_pct,
            max_drawdown_pct=account.max_drawdown_pct,
            max_open_positions=account.max_open_positions,
            max_daily_trades=account.max_daily_trades,
            trade_cooldown_seconds=account.trade_cooldown_seconds,
            default_stop_loss=getattr(account, 'default_stop_loss', None),
            default_take_profit=getattr(account, 'default_take_profit', None),
            group_id=account.group_id,
            group_name=account.group_name,
            group_color=account.group_color,
            is_signal_enabled=account.is_signal_enabled if account.is_signal_enabled is not None else True,
            signal_priority=account.signal_priority or 0,
        )
