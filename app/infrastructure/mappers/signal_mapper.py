"""
Signal Mapper - bidirectional conversion between ORM and domain.

Handles conversion of Signal entities between persistence (SQLAlchemy)
and domain layers, including enum and value object transformations.
"""

from typing import Optional, List
from decimal import Decimal

from app.models.database_models import Signal as SignalORM
from app.domain.entities.signal import Signal
from app.domain.enums import SignalSource, SignalAction, SignalStatus
from app.domain.value_objects import SignalId, Symbol, Volume, Price, StopLoss, TakeProfit, AccountId


class SignalMapper:
    """
    Maps between Signal ORM model and Signal domain entity.

    Handles:
    - Enum conversion (str → domain enum)
    - Value object creation (str/float → Symbol/Volume/Price)
    - Optional field handling
    - List serialization for target_accounts
    """

    @staticmethod
    def to_entity(orm_model: SignalORM) -> Signal:
        """
        Convert ORM model to domain entity.

        Args:
            orm_model: SQLAlchemy Signal model

        Returns:
            Domain Signal entity
        """
        # Convert target_accounts from JSON list to domain AccountId list
        target_accounts = []
        if orm_model.target_accounts:
            target_accounts = [AccountId(str(acc_id)) for acc_id in orm_model.target_accounts]

        # Build optional value objects (column is 'volume' not 'quantity')
        volume = Volume(Decimal(str(orm_model.volume))) if orm_model.volume else None
        price = Price(Decimal(str(orm_model.price))) if orm_model.price else None
        stop_loss = StopLoss(Price(Decimal(str(orm_model.stop_loss)))) if orm_model.stop_loss else None
        take_profit = TakeProfit(Price(Decimal(str(orm_model.take_profit)))) if orm_model.take_profit else None

        # Handle source enum - may be stored as enum or string
        source_value = orm_model.source.value if hasattr(orm_model.source, 'value') else orm_model.source

        # Handle status - may be stored as string
        status = SignalMapper._map_status_to_domain(orm_model.status)

        return Signal(
            id=SignalId(str(orm_model.id)),  # Use integer ID from DB
            source=SignalSource(source_value),
            symbol=Symbol(orm_model.symbol),
            action=SignalAction(orm_model.action.lower()),  # Normalize to lowercase
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            target_accounts=target_accounts,
            status=status,
            comment=orm_model.comment,
            strategy_id=orm_model.strategy_id,
            strategy_name=orm_model.strategy_name,
            raw_payload=orm_model.raw_payload,
            created_at=orm_model.created_at,
            processed_at=orm_model.processed_at,
            error_message=orm_model.error_message,
        )

    @staticmethod
    def to_model(entity: Signal, orm_model: Optional[SignalORM] = None) -> SignalORM:
        """
        Convert domain entity to ORM model.

        Args:
            entity: Domain Signal entity
            orm_model: Existing ORM model to update (optional)

        Returns:
            SQLAlchemy Signal model
        """
        is_new = orm_model is None
        if is_new:
            orm_model = SignalORM()
            # For new signals, store the domain's UUID as signal_id for external tracking
            orm_model.signal_id = entity.id.value

        # Basic fields
        orm_model.source = entity.source.value
        orm_model.strategy_id = entity.strategy_id
        orm_model.strategy_name = entity.strategy_name
        orm_model.symbol = entity.symbol.value
        orm_model.action = entity.action.value.upper()  # ORM uses uppercase

        # Optional numeric fields (column is 'volume' not 'quantity')
        orm_model.volume = float(entity.volume.value) if entity.volume else None
        orm_model.price = float(entity.price.value) if entity.price else None
        orm_model.stop_loss = float(entity.stop_loss.price.value) if entity.stop_loss else None
        orm_model.take_profit = float(entity.take_profit.price.value) if entity.take_profit else None

        # Target accounts - convert to JSON-serializable list
        orm_model.target_accounts = [acc_id.value for acc_id in entity.target_accounts] if entity.target_accounts else []

        # Comment
        orm_model.comment = entity.comment

        # Status - store as string for DB
        status = SignalMapper._map_status_to_orm(entity.status)
        orm_model.status = status.value if hasattr(status, 'value') else str(status)

        # Metadata
        orm_model.raw_payload = entity.raw_payload
        orm_model.error_message = entity.error_message

        # Timestamps
        if entity.processed_at:
            orm_model.processed_at = entity.processed_at

        return orm_model

    @staticmethod
    def _map_status_to_domain(orm_status) -> SignalStatus:
        """Map ORM SignalStatus enum or string to domain SignalStatus"""
        from app.models.database_models import SignalStatus as ORMSignalStatus

        # Handle string status values
        if isinstance(orm_status, str):
            string_mapping = {
                "received": SignalStatus.PENDING,
                "pending": SignalStatus.PENDING,
                "processing": SignalStatus.PROCESSING,
                "executed": SignalStatus.PROCESSED,
                "processed": SignalStatus.PROCESSED,
                "failed": SignalStatus.FAILED,
                "ignored": SignalStatus.SKIPPED,
            }
            return string_mapping.get(orm_status.lower(), SignalStatus.PENDING)

        # Handle enum values
        mapping = {
            ORMSignalStatus.RECEIVED: SignalStatus.PENDING,
            ORMSignalStatus.PROCESSING: SignalStatus.PROCESSING,
            ORMSignalStatus.EXECUTED: SignalStatus.PROCESSED,
            ORMSignalStatus.FAILED: SignalStatus.FAILED,
            ORMSignalStatus.IGNORED: SignalStatus.SKIPPED,
        }
        return mapping.get(orm_status, SignalStatus.PENDING)

    @staticmethod
    def _map_status_to_orm(domain_status: SignalStatus):
        """Map domain SignalStatus to ORM SignalStatus enum"""
        from app.models.database_models import SignalStatus as ORMSignalStatus

        mapping = {
            SignalStatus.PENDING: ORMSignalStatus.RECEIVED,
            SignalStatus.PROCESSING: ORMSignalStatus.PROCESSING,
            SignalStatus.PROCESSED: ORMSignalStatus.EXECUTED,
            SignalStatus.FAILED: ORMSignalStatus.FAILED,
            SignalStatus.SKIPPED: ORMSignalStatus.IGNORED,
        }
        return mapping.get(domain_status, ORMSignalStatus.RECEIVED)
