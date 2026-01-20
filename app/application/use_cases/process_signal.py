"""
Process Signal Use Case

Orchestrates the complete signal-to-trade flow:
1. Convert DTO to domain entity
2. Delegate to domain service
3. Convert result back to DTO
"""
import logging
import uuid
from typing import Dict
from datetime import datetime

from app.domain.services.signal_service import SignalService
from app.domain.entities.signal import Signal
from app.domain.value_objects import SignalId, Symbol, Volume, Price, StopLoss, TakeProfit, AccountId
from app.domain.enums import SignalStatus, BrokerType
from app.domain.ports.broker_port import BrokerPort
from app.domain.ports.repository_port import SignalRepository, AccountRepository
from app.domain.ports.event_port import EventPort
from app.domain.exceptions import SignalValidationError, SignalProcessingError

from app.application.dto.signal_dto import (
    ProcessSignalRequest,
    ProcessSignalResponse,
)

logger = logging.getLogger(__name__)


class ProcessSignalUseCase:
    """
    Use case for processing trading signals.

    Accepts: ProcessSignalRequest (DTO)
    Returns: ProcessSignalResponse (DTO)

    Orchestrates:
    - DTO to domain entity conversion
    - Domain service invocation
    - Domain entity to DTO conversion
    """

    def __init__(
        self,
        signal_repository: SignalRepository,
        account_repository: AccountRepository,
        brokers: Dict[BrokerType, BrokerPort],
        event_port: EventPort,
    ):
        # Create domain service with injected ports
        self._signal_service = SignalService(
            signal_repository=signal_repository,
            account_repository=account_repository,
            brokers=brokers,
            event_port=event_port,
        )
        self._signal_repo = signal_repository

    async def execute(self, request: ProcessSignalRequest) -> ProcessSignalResponse:
        """
        Execute the signal processing use case.

        1. Validate request (already done by DTO)
        2. Convert DTO to domain entity
        3. Process through domain service
        4. Convert result to response DTO
        """
        try:
            # Convert DTO to domain entity
            signal = self._to_domain_entity(request)

            # Save initial signal
            await self._signal_repo.save(signal)

            # Process through domain service
            processed_signal = await self._signal_service.process_signal(signal)

            # Convert to response DTO
            return self._to_response_dto(processed_signal)

        except SignalValidationError as e:
            logger.warning(f"Signal validation failed: {e}")
            return ProcessSignalResponse(
                signal_id="",
                status=SignalStatus.FAILED,
                errors=[str(e)],
            )
        except SignalProcessingError as e:
            logger.error(f"Signal processing failed: {e}")
            return ProcessSignalResponse(
                signal_id=str(e.context.get("signal_id", "")),
                status=SignalStatus.FAILED,
                errors=[str(e)],
            )
        except Exception as e:
            logger.exception(f"Unexpected error processing signal: {e}")
            return ProcessSignalResponse(
                signal_id="",
                status=SignalStatus.FAILED,
                errors=[f"Internal error: {str(e)}"],
            )

    def _to_domain_entity(self, request: ProcessSignalRequest) -> Signal:
        """Convert request DTO to domain entity"""
        signal_id = SignalId(str(uuid.uuid4()))

        # Build optional value objects
        volume = Volume(request.volume) if request.volume else None
        price = Price(request.price) if request.price else None
        stop_loss = StopLoss(Price(request.stop_loss)) if request.stop_loss else None
        take_profit = TakeProfit(Price(request.take_profit)) if request.take_profit else None
        target_accounts = [AccountId(aid) for aid in request.target_account_ids]

        return Signal(
            id=signal_id,
            source=request.source,
            symbol=Symbol(request.symbol),
            action=request.action,
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            target_accounts=target_accounts,
            comment=request.comment,
            strategy_id=request.strategy_id,
            strategy_name=request.strategy_name,
            raw_payload=request.raw_payload,
        )

    def _to_response_dto(self, signal: Signal) -> ProcessSignalResponse:
        """Convert domain entity to response DTO"""
        errors = [signal.error_message] if signal.error_message else []

        return ProcessSignalResponse(
            signal_id=signal.id.value,
            status=signal.status,
            executions=1 if signal.is_processed else 0,
            errors=errors,
            processed_at=signal.processed_at,
        )
