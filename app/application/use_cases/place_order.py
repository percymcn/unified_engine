"""
Place Order Use Case

Orchestrates order placement through the domain layer.
"""
import logging
from typing import Dict

from app.domain.services.trade_service import TradeService
from app.domain.entities.account import Account
from app.domain.value_objects import Symbol, Volume, Price, AccountId
from app.domain.enums import BrokerType, OrderStatus
from app.domain.ports.broker_port import BrokerPort
from app.domain.ports.repository_port import (
    TradeRepository, OrderRepository, PositionRepository, AccountRepository
)
from app.domain.ports.event_port import EventPort
from app.domain.exceptions import (
    InsufficientBalanceError, InvalidOrderError, AccountNotFoundError,
    AccountDisabledError
)

from app.application.dto.trade_dto import (
    PlaceOrderRequest,
    PlaceOrderResponse,
)

logger = logging.getLogger(__name__)


class PlaceOrderUseCase:
    """
    Use case for placing trading orders.

    Accepts: PlaceOrderRequest (DTO)
    Returns: PlaceOrderResponse (DTO)
    """

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

    async def execute(self, request: PlaceOrderRequest) -> PlaceOrderResponse:
        """
        Execute the order placement use case.

        1. Get account from repository
        2. Validate account is active and connected
        3. Place order through trade service
        4. Return response DTO
        """
        try:
            # Get account
            account = await self._account_repo.get_by_id(AccountId(request.account_id))
            if account is None:
                raise AccountNotFoundError(request.account_id)

            if not account.is_active:
                raise AccountDisabledError(request.account_id)

            if not account.is_connected:
                raise AccountDisabledError(request.account_id)

            # Convert request to domain types
            symbol = Symbol(request.symbol)
            volume = Volume(request.volume)
            price = Price(request.price) if request.price else None
            stop_loss = Price(request.stop_loss) if request.stop_loss else None
            take_profit = Price(request.take_profit) if request.take_profit else None

            # Place order through domain service
            order = await self._trade_service.place_order(
                account=account,
                symbol=symbol,
                order_type=request.order_type,
                volume=volume,
                price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                comment=request.comment,
            )

            return PlaceOrderResponse(
                order_id=order.id.value,
                status=order.status,
                broker_order_id=order.broker_order_id,
            )

        except AccountNotFoundError as e:
            logger.warning(f"Account not found: {e}")
            return PlaceOrderResponse(
                order_id="",
                status=OrderStatus.REJECTED,
                error=f"Account not found: {request.account_id}",
            )
        except AccountDisabledError as e:
            logger.warning(f"Account disabled: {e}")
            return PlaceOrderResponse(
                order_id="",
                status=OrderStatus.REJECTED,
                error=str(e),
            )
        except InsufficientBalanceError as e:
            logger.warning(f"Insufficient balance: {e}")
            return PlaceOrderResponse(
                order_id="",
                status=OrderStatus.REJECTED,
                error=str(e),
            )
        except InvalidOrderError as e:
            logger.warning(f"Invalid order: {e}")
            return PlaceOrderResponse(
                order_id="",
                status=OrderStatus.REJECTED,
                error=str(e),
            )
        except Exception as e:
            logger.exception(f"Unexpected error placing order: {e}")
            return PlaceOrderResponse(
                order_id="",
                status=OrderStatus.REJECTED,
                error=f"Internal error: {str(e)}",
            )
