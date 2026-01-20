"""
Account Mapper - bidirectional conversion between ORM and domain.

Handles conversion of Account entities between persistence (SQLAlchemy)
and domain layers, including Money value objects and broker type mapping.
"""

from typing import Optional
from decimal import Decimal

from app.models.database_models import TradingAccount as AccountORM
from app.models.database_models import BrokerType as ORMBrokerType, AccountType as ORMAccountType
from app.domain.entities.account import Account
from app.domain.enums import BrokerType, AccountType
from app.domain.value_objects import AccountId, Money


class AccountMapper:
    """
    Maps between TradingAccount ORM model and Account domain entity.

    Handles:
    - BrokerType and AccountType enum conversion
    - Money value object creation (balance, equity, margin)
    - Credential fields (encrypted_api_key, encrypted_api_secret)
    - Status flags (is_active, is_connected)
    """

    @staticmethod
    def to_entity(orm_model: AccountORM) -> Account:
        """
        Convert ORM model to domain entity.

        Args:
            orm_model: SQLAlchemy TradingAccount model

        Returns:
            Domain Account entity
        """
        # Map ORM broker type to domain broker type
        broker = AccountMapper._map_broker_to_domain(orm_model.broker)
        account_type = AccountMapper._map_account_type_to_domain(orm_model.account_type)

        # Create Money value objects
        balance = Money(Decimal(str(orm_model.balance or 0.0)), orm_model.currency)
        equity = Money(Decimal(str(orm_model.equity or 0.0)), orm_model.currency)
        margin = Money(Decimal(str(orm_model.margin or 0.0)), orm_model.currency)

        return Account(
            id=AccountId(str(orm_model.id)),
            user_id=orm_model.user_id,
            broker=broker,
            account_type=account_type,
            balance=balance,
            equity=equity,
            margin=margin,
            leverage=int(orm_model.leverage or 100),
            is_active=orm_model.is_active,
            is_connected=orm_model.is_connected,
            currency=orm_model.currency,
            server=orm_model.account_name,  # Map account_name → server
            last_sync=orm_model.last_sync,
            created_at=orm_model.created_at,
        )

    @staticmethod
    def to_model(entity: Account, orm_model: Optional[AccountORM] = None) -> AccountORM:
        """
        Convert domain entity to ORM model.

        Args:
            entity: Domain Account entity
            orm_model: Existing ORM model to update (optional)

        Returns:
            SQLAlchemy TradingAccount model
        """
        if orm_model is None:
            orm_model = AccountORM()

        # Map domain enums to ORM enums
        orm_model.broker = AccountMapper._map_broker_to_orm(entity.broker)
        orm_model.account_type = AccountMapper._map_account_type_to_orm(entity.account_type)

        # User and account info
        orm_model.user_id = entity.user_id
        orm_model.account_number = entity.id.value  # Use domain ID as account_number if not set
        orm_model.account_name = entity.server

        # Financial fields
        orm_model.currency = entity.currency
        orm_model.leverage = float(entity.leverage)
        orm_model.balance = float(entity.balance.amount)
        orm_model.equity = float(entity.equity.amount)
        orm_model.margin = float(entity.margin.amount)

        # Calculate free_margin for ORM
        orm_model.free_margin = float(entity.free_margin)

        # Calculate margin_level for ORM (if margin > 0)
        if entity.margin.amount > 0:
            orm_model.margin_level = float((entity.equity.amount / entity.margin.amount) * 100)
        else:
            orm_model.margin_level = 0.0

        # Status flags
        orm_model.is_active = entity.is_active
        orm_model.is_connected = entity.is_connected

        # Timestamps
        orm_model.last_sync = entity.last_sync
        orm_model.created_at = entity.created_at

        return orm_model

    @staticmethod
    def _map_broker_to_domain(orm_broker: ORMBrokerType) -> BrokerType:
        """Map ORM BrokerType to domain BrokerType"""
        mapping = {
            ORMBrokerType.TRADELOCKER: BrokerType.TRADELOCKER,
            ORMBrokerType.TRADOVATE: BrokerType.TRADOVATE,
            ORMBrokerType.TOPSTEP: BrokerType.TOPSTEP,
            ORMBrokerType.MT4: BrokerType.MT4,
            ORMBrokerType.MT5: BrokerType.MT5,
            ORMBrokerType.PROJECTX: BrokerType.PROJECTX,
        }
        # TRUFOREX in ORM doesn't exist in domain, default to PROJECTX
        return mapping.get(orm_broker, BrokerType.PROJECTX)

    @staticmethod
    def _map_broker_to_orm(domain_broker: BrokerType) -> ORMBrokerType:
        """Map domain BrokerType to ORM BrokerType"""
        mapping = {
            BrokerType.TRADELOCKER: ORMBrokerType.TRADELOCKER,
            BrokerType.TRADOVATE: ORMBrokerType.TRADOVATE,
            BrokerType.TOPSTEP: ORMBrokerType.TOPSTEP,
            BrokerType.MT4: ORMBrokerType.MT4,
            BrokerType.MT5: ORMBrokerType.MT5,
            BrokerType.PROJECTX: ORMBrokerType.PROJECTX,
        }
        return mapping.get(domain_broker, ORMBrokerType.PROJECTX)

    @staticmethod
    def _map_account_type_to_domain(orm_type: ORMAccountType) -> AccountType:
        """Map ORM AccountType to domain AccountType"""
        mapping = {
            ORMAccountType.LIVE: AccountType.LIVE,
            ORMAccountType.DEMO: AccountType.DEMO,
            ORMAccountType.EVALUATION: AccountType.EVALUATION,
        }
        # FUNDED in ORM maps to EVALUATION in domain
        if orm_type == ORMAccountType.FUNDED:
            return AccountType.EVALUATION
        return mapping.get(orm_type, AccountType.DEMO)

    @staticmethod
    def _map_account_type_to_orm(domain_type: AccountType) -> ORMAccountType:
        """Map domain AccountType to ORM AccountType"""
        mapping = {
            AccountType.LIVE: ORMAccountType.LIVE,
            AccountType.DEMO: ORMAccountType.DEMO,
            AccountType.EVALUATION: ORMAccountType.EVALUATION,
        }
        return mapping.get(domain_type, ORMAccountType.DEMO)
