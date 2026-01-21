"""
Use Cases - Application Business Rules

Use cases orchestrate domain services and entities to accomplish
specific application tasks.
"""

from app.application.use_cases.process_signal import ProcessSignalUseCase
from app.application.use_cases.get_signals import (
    GetSignalUseCase,
    ListSignalsUseCase,
)
from app.application.use_cases.place_order import PlaceOrderUseCase
from app.application.use_cases.manage_positions import (
    ClosePositionUseCase,
    ModifyPositionUseCase,
    GetPositionsUseCase,
    GetTradesUseCase,
)
from app.application.use_cases.manage_accounts import (
    GetAccountsUseCase,
    GetAccountUseCase,
    ConnectAccountUseCase,
    SyncAccountUseCase,
    CreateAccountUseCase,
    UpdateAccountUseCase,
    DeleteAccountUseCase,
)
from app.application.use_cases.test_connection import TestConnectionUseCase
from app.application.use_cases.check_contract_expirations import (
    CheckContractExpirationsUseCase,
    RolloverNotification,
    run_scheduled_check,
)
from app.application.use_cases.update_account_settings import (
    UpdateAccountSettingsUseCase,
    GetAccountSettingsUseCase,
)
from app.application.use_cases.manage_account_groups import (
    CreateAccountGroupUseCase,
    GetAccountGroupsUseCase,
    GetAccountGroupUseCase,
    UpdateAccountGroupUseCase,
    DeleteAccountGroupUseCase,
    AddAccountToGroupUseCase,
    RemoveAccountFromGroupUseCase,
)

__all__ = [
    # Signal use cases
    "ProcessSignalUseCase",
    "GetSignalUseCase",
    "ListSignalsUseCase",
    # Trade use cases
    "PlaceOrderUseCase",
    "ClosePositionUseCase",
    "ModifyPositionUseCase",
    "GetPositionsUseCase",
    "GetTradesUseCase",
    # Account use cases
    "GetAccountsUseCase",
    "GetAccountUseCase",
    "ConnectAccountUseCase",
    "SyncAccountUseCase",
    "CreateAccountUseCase",
    "UpdateAccountUseCase",
    "DeleteAccountUseCase",
    "TestConnectionUseCase",
    # Contract expiration use cases
    "CheckContractExpirationsUseCase",
    "RolloverNotification",
    "run_scheduled_check",
    # Account settings use cases
    "UpdateAccountSettingsUseCase",
    "GetAccountSettingsUseCase",
    # Account group use cases
    "CreateAccountGroupUseCase",
    "GetAccountGroupsUseCase",
    "GetAccountGroupUseCase",
    "UpdateAccountGroupUseCase",
    "DeleteAccountGroupUseCase",
    "AddAccountToGroupUseCase",
    "RemoveAccountFromGroupUseCase",
]
