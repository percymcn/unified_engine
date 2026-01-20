"""
Position Management Use Cases

Use cases for closing and modifying positions.
"""
import logging
from typing import Dict, List

from app.domain.services.trade_service import TradeService
from app.domain.entities.position import Position
from app.domain.entities.trade import Trade
from app.domain.value_objects import PositionId, Volume, Price, AccountId
from app.domain.enums import BrokerType, TradeStatus
from app.domain.ports.broker_port import BrokerPort
from app.domain.ports.repository_port import (
    TradeRepository, OrderRepository, PositionRepository, AccountRepository
)
from app.domain.ports.event_port import EventPort
from app.domain.exceptions import (
    PositionNotFoundError, AccountNotFoundError, AccountDisabledError,
    BusinessRuleViolation
)

from app.application.dto.trade_dto import (
    ClosePositionRequest,
    ClosePositionResponse,
    ModifyPositionRequest,
    PositionDTO,
    TradeDTO,
    TradeListRequest,
    TradeListResponse,
)

logger = logging.getLogger(__name__)


class ClosePositionUseCase:
    """Use case for closing positions"""

    def __init__(
        self,
        trade_repository: TradeRepository,
        order_repository: OrderRepository,
        position_repository: PositionRepository,
        account_repository: AccountRepository,
        brokers: Dict[BrokerType, BrokerPort],
        event_port: EventPort,
    ):
        self._trade_service = TradeService(
            trade_repository=trade_repository,
            order_repository=order_repository,
            position_repository=position_repository,
            account_repository=account_repository,
            brokers=brokers,
            event_port=event_port,
        )
        self._account_repo = account_repository

    async def execute(self, request: ClosePositionRequest) -> ClosePositionResponse:
        """Close a position (fully or partially)"""
        try:
            # Get account
            account = await self._account_repo.get_by_id(AccountId(request.account_id))
            if account is None:
                raise AccountNotFoundError(request.account_id)

            # Convert request to domain types
            position_id = PositionId(request.position_id)
            volume = Volume(request.volume) if request.volume else None

            # Close through domain service
            trade = await self._trade_service.close_position(
                account=account,
                position_id=position_id,
                volume=volume,
            )

            return ClosePositionResponse(
                trade_id=trade.trade_id,
                realized_pnl=trade.realized_pnl.amount,
                status=trade.status,
            )

        except PositionNotFoundError as e:
            logger.warning(f"Position not found: {e}")
            return ClosePositionResponse(
                trade_id="",
                realized_pnl=0,
                status=TradeStatus.CLOSED,
                error=f"Position not found: {request.position_id}",
            )
        except AccountNotFoundError as e:
            logger.warning(f"Account not found: {e}")
            return ClosePositionResponse(
                trade_id="",
                realized_pnl=0,
                status=TradeStatus.CLOSED,
                error=f"Account not found: {request.account_id}",
            )
        except Exception as e:
            logger.exception(f"Unexpected error closing position: {e}")
            return ClosePositionResponse(
                trade_id="",
                realized_pnl=0,
                status=TradeStatus.CLOSED,
                error=f"Internal error: {str(e)}",
            )


class ModifyPositionUseCase:
    """Use case for modifying position SL/TP"""

    def __init__(
        self,
        trade_repository: TradeRepository,
        order_repository: OrderRepository,
        position_repository: PositionRepository,
        account_repository: AccountRepository,
        brokers: Dict[BrokerType, BrokerPort],
        event_port: EventPort,
    ):
        self._trade_service = TradeService(
            trade_repository=trade_repository,
            order_repository=order_repository,
            position_repository=position_repository,
            account_repository=account_repository,
            brokers=brokers,
            event_port=event_port,
        )
        self._account_repo = account_repository
        self._position_repo = position_repository

    async def execute(self, request: ModifyPositionRequest) -> PositionDTO:
        """Modify position stop loss / take profit"""
        # Get account
        account = await self._account_repo.get_by_id(AccountId(request.account_id))
        if account is None:
            raise AccountNotFoundError(request.account_id)

        # Convert request to domain types
        position_id = PositionId(request.position_id)
        stop_loss = Price(request.stop_loss) if request.stop_loss else None
        take_profit = Price(request.take_profit) if request.take_profit else None

        # Modify through domain service
        position = await self._trade_service.modify_position(
            account=account,
            position_id=position_id,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        return self._to_dto(position)

    def _to_dto(self, position: Position) -> PositionDTO:
        return PositionDTO(
            id=position.id.value,
            account_id=position.account_id,
            symbol=position.symbol.value,
            side=position.side.value,
            volume=position.volume.value,
            open_price=position.open_price.value,
            current_price=position.current_price.value,
            unrealized_pnl=position.unrealized_pnl,
            stop_loss=position.stop_loss.value if position.stop_loss else None,
            take_profit=position.take_profit.value if position.take_profit else None,
            open_time=position.open_time,
        )


class GetPositionsUseCase:
    """Use case for getting open positions"""

    def __init__(self, position_repository: PositionRepository):
        self._position_repo = position_repository

    async def execute(self, account_id: str) -> List[PositionDTO]:
        """Get open positions for account"""
        positions = await self._position_repo.get_open_by_account(account_id)
        return [self._to_dto(p) for p in positions]

    def _to_dto(self, position: Position) -> PositionDTO:
        return PositionDTO(
            id=position.id.value,
            account_id=position.account_id,
            symbol=position.symbol.value,
            side=position.side.value,
            volume=position.volume.value,
            open_price=position.open_price.value,
            current_price=position.current_price.value,
            unrealized_pnl=position.unrealized_pnl,
            stop_loss=position.stop_loss.value if position.stop_loss else None,
            take_profit=position.take_profit.value if position.take_profit else None,
            open_time=position.open_time,
        )


class GetTradesUseCase:
    """Use case for getting trade history"""

    def __init__(self, trade_repository: TradeRepository):
        self._trade_repo = trade_repository

    async def execute(self, request: TradeListRequest) -> TradeListResponse:
        """Get trades for account"""
        trades = await self._trade_repo.get_by_account(
            request.account_id,
            limit=request.limit,
            offset=request.offset,
        )
        return TradeListResponse(
            trades=[self._to_dto(t) for t in trades],
            total=len(trades),
        )

    def _to_dto(self, trade: Trade) -> TradeDTO:
        return TradeDTO(
            trade_id=trade.trade_id,
            account_id=trade.account_id,
            symbol=trade.symbol.value,
            order_type=trade.order_type,
            volume=trade.volume.value,
            open_price=trade.open_price.value,
            close_price=trade.close_price.value if trade.close_price else None,
            realized_pnl=trade.realized_pnl.amount,
            status=trade.status,
            open_time=trade.open_time,
            close_time=trade.close_time,
        )
