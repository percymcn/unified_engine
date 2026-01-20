"""
Signal Query Use Cases

Read-only use cases for retrieving signal data.
"""
import logging
from typing import Optional

from app.domain.ports.repository_port import SignalRepository
from app.domain.value_objects import SignalId
from app.domain.entities.signal import Signal

from app.application.dto.signal_dto import (
    SignalDTO,
    SignalListRequest,
    SignalListResponse,
)

logger = logging.getLogger(__name__)


class GetSignalUseCase:
    """Get a single signal by ID"""

    def __init__(self, signal_repository: SignalRepository):
        self._signal_repo = signal_repository

    async def execute(self, signal_id: str) -> Optional[SignalDTO]:
        """Get signal by ID, return DTO or None"""
        signal = await self._signal_repo.get_by_id(SignalId(signal_id))
        if signal is None:
            return None
        return self._to_dto(signal)

    def _to_dto(self, signal: Signal) -> SignalDTO:
        return SignalDTO(
            id=signal.id.value,
            source=signal.source,
            symbol=signal.symbol.value,
            action=signal.action,
            status=signal.status,
            volume=signal.volume.value if signal.volume else None,
            price=signal.price.value if signal.price else None,
            stop_loss=signal.stop_loss.price.value if signal.stop_loss else None,
            take_profit=signal.take_profit.price.value if signal.take_profit else None,
            comment=signal.comment,
            error_message=signal.error_message,
            created_at=signal.created_at,
            processed_at=signal.processed_at,
        )


class ListSignalsUseCase:
    """List signals with filtering"""

    def __init__(self, signal_repository: SignalRepository):
        self._signal_repo = signal_repository

    async def execute(self, request: SignalListRequest) -> SignalListResponse:
        """Get filtered list of signals"""
        if request.status:
            signals = await self._signal_repo.get_by_status(
                request.status, limit=request.limit
            )
        elif request.user_id:
            signals = await self._signal_repo.get_by_user(
                request.user_id, limit=request.limit, offset=request.offset
            )
        else:
            signals = await self._signal_repo.get_pending(limit=request.limit)

        signal_dtos = [self._to_dto(s) for s in signals]

        return SignalListResponse(
            signals=signal_dtos,
            total=len(signal_dtos),
            limit=request.limit,
            offset=request.offset,
        )

    def _to_dto(self, signal: Signal) -> SignalDTO:
        return SignalDTO(
            id=signal.id.value,
            source=signal.source,
            symbol=signal.symbol.value,
            action=signal.action,
            status=signal.status,
            volume=signal.volume.value if signal.volume else None,
            price=signal.price.value if signal.price else None,
            stop_loss=signal.stop_loss.price.value if signal.stop_loss else None,
            take_profit=signal.take_profit.price.value if signal.take_profit else None,
            comment=signal.comment,
            error_message=signal.error_message,
            created_at=signal.created_at,
            processed_at=signal.processed_at,
        )
