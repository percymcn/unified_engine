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
]
