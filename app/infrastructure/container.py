"""
Dependency Injection Container.

Wires infrastructure implementations to application use cases.
Follows hexagonal architecture: application depends on ports,
container provides concrete adapters.
"""
from typing import Dict, Optional

from app.domain.enums import BrokerType
from app.domain.ports.broker_port import BrokerPort
from app.domain.ports.event_port import EventPort
from app.domain.ports.repository_port import (
    SignalRepository,
    TradeRepository,
    OrderRepository,
    AccountRepository,
    PositionRepository,
)
from app.application.interfaces.unit_of_work import UnitOfWorkFactory

# Infrastructure implementations
from app.infrastructure.persistence import SQLAlchemyUnitOfWorkFactory, SessionFactory
from app.infrastructure.events import NatsEventPublisher, RedisEventPublisher, CompositeEventPublisher
from app.infrastructure.adapters import (
    TradeLockerAdapter,
    TopstepAdapter,
    TradovateAdapter,
    MT4Adapter,
    MT5Adapter,
)
from app.infrastructure.repositories import (
    SQLAlchemySignalRepository,
    SQLAlchemyTradeRepository,
    SQLAlchemyOrderRepository,
    SQLAlchemyAccountRepository,
    SQLAlchemyPositionRepository,
    SQLAlchemySymbolAliasRepository,
    AccountGroupRepository,
)

# Use cases
from app.application.use_cases import (
    ProcessSignalUseCase,
    GetSignalUseCase,
    ListSignalsUseCase,
    PlaceOrderUseCase,
    ClosePositionUseCase,
    ModifyPositionUseCase,
    GetPositionsUseCase,
    GetTradesUseCase,
    GetAccountsUseCase,
    GetAccountUseCase,
    ConnectAccountUseCase,
    SyncAccountUseCase,
    CreateAccountUseCase,
    UpdateAccountUseCase,
    DeleteAccountUseCase,
    TestConnectionUseCase,
    UpdateAccountSettingsUseCase,
    GetAccountSettingsUseCase,
    CreateAccountGroupUseCase,
    GetAccountGroupsUseCase,
    GetAccountGroupUseCase,
    UpdateAccountGroupUseCase,
    DeleteAccountGroupUseCase,
    AddAccountToGroupUseCase,
    RemoveAccountFromGroupUseCase,
)
from app.infrastructure.repositories.credential_repository import CredentialRepository


class Container:
    """
    DI Container for infrastructure wiring.

    Usage:
        container = Container()
        await container.initialize()

        # Get use cases with dependencies injected
        process_signal = container.process_signal_use_case()

        # Get broker adapter by type
        adapter = container.broker_adapter(BrokerType.TRADELOCKER)
    """

    def __init__(self):
        self._session_factory: Optional[SessionFactory] = None
        self._uow_factory: Optional[UnitOfWorkFactory] = None
        self._event_publisher: Optional[EventPort] = None
        self._broker_adapters: Dict[BrokerType, BrokerPort] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all infrastructure components."""
        if self._initialized:
            return

        # Session factory for database access
        self._session_factory = SessionFactory()

        # Unit of Work factory for transaction management
        self._uow_factory = SQLAlchemyUnitOfWorkFactory(self._session_factory)

        # Event publisher (composite with fallback)
        nats_publisher = NatsEventPublisher()
        redis_publisher = RedisEventPublisher()
        self._event_publisher = CompositeEventPublisher([nats_publisher, redis_publisher])
        await self._event_publisher.connect()

        # Broker adapters (lazy - connected on demand)
        self._broker_adapters = {
            BrokerType.TRADELOCKER: TradeLockerAdapter(),
            BrokerType.TOPSTEP: TopstepAdapter(),
            BrokerType.TRADOVATE: TradovateAdapter(),
            BrokerType.MT4: MT4Adapter(),
            BrokerType.MT5: MT5Adapter(),
        }

        self._initialized = True

    async def shutdown(self) -> None:
        """Cleanup all connections."""
        if self._event_publisher:
            try:
                await self._event_publisher.disconnect()
            except Exception:
                pass  # Ignore errors during shutdown

        for adapter in self._broker_adapters.values():
            try:
                # is_connected is an async method, not a property
                if await adapter.is_connected():
                    await adapter.disconnect()
            except Exception:
                # Log but don't fail shutdown
                pass

        self._initialized = False

    def _get_repositories(self):
        """Get repository instances from current session."""
        # Create a new session for this request
        session = self._session_factory.create()

        return (
            SQLAlchemySignalRepository(session),
            SQLAlchemyTradeRepository(session),
            SQLAlchemyOrderRepository(session),
            SQLAlchemyAccountRepository(session),
            SQLAlchemyPositionRepository(session),
            CredentialRepository(session),
        )

    def _get_symbol_alias_repository(self):
        """Get symbol alias repository instance."""
        session = self._session_factory.create()
        return SQLAlchemySymbolAliasRepository(session)

    # Use case factories
    def process_signal_use_case(self) -> ProcessSignalUseCase:
        """Create ProcessSignalUseCase with injected dependencies."""
        signal_repo, _, _, account_repo, _, _ = self._get_repositories()
        return ProcessSignalUseCase(
            signal_repository=signal_repo,
            account_repository=account_repo,
            brokers=self._broker_adapters,
            event_port=self._event_publisher,
        )

    def get_signal_use_case(self) -> GetSignalUseCase:
        """Create GetSignalUseCase with injected dependencies."""
        signal_repo, _, _, _, _, _ = self._get_repositories()
        return GetSignalUseCase(signal_repository=signal_repo)

    def list_signals_use_case(self) -> ListSignalsUseCase:
        """Create ListSignalsUseCase with injected dependencies."""
        signal_repo, _, _, _, _, _ = self._get_repositories()
        return ListSignalsUseCase(signal_repository=signal_repo)

    def place_order_use_case(self) -> PlaceOrderUseCase:
        """Create PlaceOrderUseCase with injected dependencies."""
        _, trade_repo, order_repo, account_repo, position_repo, _ = self._get_repositories()
        return PlaceOrderUseCase(
            trade_repository=trade_repo,
            order_repository=order_repo,
            position_repository=position_repo,
            account_repository=account_repo,
            brokers=self._broker_adapters,
            event_port=self._event_publisher,
        )

    def close_position_use_case(self) -> ClosePositionUseCase:
        """Create ClosePositionUseCase with injected dependencies."""
        _, trade_repo, order_repo, account_repo, position_repo, _ = self._get_repositories()
        return ClosePositionUseCase(
            trade_repository=trade_repo,
            order_repository=order_repo,
            position_repository=position_repo,
            account_repository=account_repo,
            brokers=self._broker_adapters,
            event_port=self._event_publisher,
        )

    def modify_position_use_case(self) -> ModifyPositionUseCase:
        """Create ModifyPositionUseCase with injected dependencies."""
        _, trade_repo, order_repo, account_repo, position_repo, _ = self._get_repositories()
        return ModifyPositionUseCase(
            trade_repository=trade_repo,
            order_repository=order_repo,
            position_repository=position_repo,
            account_repository=account_repo,
            brokers=self._broker_adapters,
            event_port=self._event_publisher,
        )

    def get_positions_use_case(self) -> GetPositionsUseCase:
        """Create GetPositionsUseCase with injected dependencies."""
        _, _, _, _, position_repo, _ = self._get_repositories()
        return GetPositionsUseCase(position_repository=position_repo)

    def get_trades_use_case(self) -> GetTradesUseCase:
        """Create GetTradesUseCase with injected dependencies."""
        _, trade_repo, _, _, _, _ = self._get_repositories()
        return GetTradesUseCase(trade_repository=trade_repo)

    def get_accounts_use_case(self) -> GetAccountsUseCase:
        """Create GetAccountsUseCase with injected dependencies."""
        _, _, _, account_repo, _, _ = self._get_repositories()
        return GetAccountsUseCase(account_repository=account_repo)

    def get_account_use_case(self) -> GetAccountUseCase:
        """Create GetAccountUseCase with injected dependencies."""
        _, _, _, account_repo, _, _ = self._get_repositories()
        return GetAccountUseCase(account_repository=account_repo)

    def connect_account_use_case(self) -> ConnectAccountUseCase:
        """Create ConnectAccountUseCase with injected dependencies."""
        _, _, _, account_repo, _, _ = self._get_repositories()
        return ConnectAccountUseCase(
            account_repository=account_repo,
            brokers=self._broker_adapters,
        )

    def sync_account_use_case(self) -> SyncAccountUseCase:
        """Create SyncAccountUseCase with injected dependencies."""
        _, _, order_repo, account_repo, position_repo, _ = self._get_repositories()
        return SyncAccountUseCase(
            account_repository=account_repo,
            position_repository=position_repo,
            order_repository=order_repo,
            brokers=self._broker_adapters,
        )

    def create_account_use_case(self) -> CreateAccountUseCase:
        """Create CreateAccountUseCase with injected dependencies."""
        _, _, _, account_repo, _, credential_repo = self._get_repositories()
        alias_repo = self._get_symbol_alias_repository()
        return CreateAccountUseCase(
            account_repository=account_repo,
            credential_repository=credential_repo,
            symbol_alias_repository=alias_repo,
        )

    def update_account_use_case(self) -> UpdateAccountUseCase:
        """Create UpdateAccountUseCase with injected dependencies."""
        _, _, _, account_repo, _, credential_repo = self._get_repositories()
        return UpdateAccountUseCase(
            account_repository=account_repo,
            credential_repository=credential_repo,
        )

    def delete_account_use_case(self) -> DeleteAccountUseCase:
        """Create DeleteAccountUseCase with injected dependencies."""
        _, _, _, account_repo, _, credential_repo = self._get_repositories()
        return DeleteAccountUseCase(
            account_repository=account_repo,
            credential_repository=credential_repo,
        )

    def test_connection_use_case(self) -> TestConnectionUseCase:
        """Create TestConnectionUseCase (no dependencies needed)."""
        return TestConnectionUseCase()

    def _get_account_group_repository(self) -> AccountGroupRepository:
        """Get account group repository instance."""
        session = self._session_factory.create()
        return AccountGroupRepository(session)

    def update_account_settings_use_case(self) -> UpdateAccountSettingsUseCase:
        """Create UpdateAccountSettingsUseCase with injected dependencies."""
        session = self._session_factory.create()
        return UpdateAccountSettingsUseCase(session)

    def get_account_settings_use_case(self) -> GetAccountSettingsUseCase:
        """Create GetAccountSettingsUseCase with injected dependencies."""
        session = self._session_factory.create()
        return GetAccountSettingsUseCase(session)

    def create_account_group_use_case(self) -> CreateAccountGroupUseCase:
        """Create CreateAccountGroupUseCase with injected dependencies."""
        return CreateAccountGroupUseCase(self._get_account_group_repository())

    def get_account_groups_use_case(self) -> GetAccountGroupsUseCase:
        """Create GetAccountGroupsUseCase with injected dependencies."""
        return GetAccountGroupsUseCase(self._get_account_group_repository())

    def get_account_group_use_case(self) -> GetAccountGroupUseCase:
        """Create GetAccountGroupUseCase with injected dependencies."""
        return GetAccountGroupUseCase(self._get_account_group_repository())

    def update_account_group_use_case(self) -> UpdateAccountGroupUseCase:
        """Create UpdateAccountGroupUseCase with injected dependencies."""
        return UpdateAccountGroupUseCase(self._get_account_group_repository())

    def delete_account_group_use_case(self) -> DeleteAccountGroupUseCase:
        """Create DeleteAccountGroupUseCase with injected dependencies."""
        return DeleteAccountGroupUseCase(self._get_account_group_repository())

    def add_account_to_group_use_case(self) -> AddAccountToGroupUseCase:
        """Create AddAccountToGroupUseCase with injected dependencies."""
        return AddAccountToGroupUseCase(self._get_account_group_repository())

    def remove_account_from_group_use_case(self) -> RemoveAccountFromGroupUseCase:
        """Create RemoveAccountFromGroupUseCase with injected dependencies."""
        return RemoveAccountFromGroupUseCase(self._get_account_group_repository())

    # Direct access to infrastructure
    def broker_adapter(self, broker_type: BrokerType) -> BrokerPort:
        """Get broker adapter by type."""
        return self._broker_adapters[broker_type]

    @property
    def event_publisher(self) -> EventPort:
        """Get the event publisher."""
        return self._event_publisher

    @property
    def uow_factory(self) -> UnitOfWorkFactory:
        """Get the unit of work factory."""
        return self._uow_factory


# Global container instance (singleton)
_container: Optional[Container] = None


def get_container() -> Container:
    """Get the global container instance."""
    global _container
    if _container is None:
        _container = Container()
    return _container


async def initialize_container() -> Container:
    """Initialize and return the global container."""
    container = get_container()
    if not container._initialized:
        await container.initialize()
    return container


async def shutdown_container() -> None:
    """Shutdown the global container."""
    global _container
    if _container is not None:
        await _container.shutdown()
        _container = None
