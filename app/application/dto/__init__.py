"""
Data Transfer Objects (DTOs)

DTOs define the data structures for communication between
the application layer and external layers (API, CLI, etc.).
"""

from app.application.dto.signal_dto import (
    ProcessSignalRequest,
    ProcessSignalResponse,
    SignalDTO,
    SignalListRequest,
    SignalListResponse,
)

from app.application.dto.trade_dto import (
    PlaceOrderRequest,
    PlaceOrderResponse,
    ClosePositionRequest,
    ClosePositionResponse,
    ModifyPositionRequest,
    PositionDTO,
    TradeDTO,
    TradeListRequest,
    TradeListResponse,
)

from app.application.dto.account_dto import (
    AccountDTO,
    AccountSummaryDTO,
    GetAccountsRequest,
    GetAccountsResponse,
    ConnectAccountRequest,
    ConnectAccountResponse,
    SyncAccountRequest,
    SyncAccountResponse,
)

from app.application.dto.account_settings_dto import (
    PositionSizingMode,
    AccountSettingsRequest,
    AccountSettingsResponse,
    GetAccountSettingsRequest,
)

from app.application.dto.account_group_dto import (
    CreateAccountGroupRequest,
    UpdateAccountGroupRequest,
    DeleteAccountGroupRequest,
    GetAccountGroupsRequest,
    AddAccountToGroupRequest,
    RemoveAccountFromGroupRequest,
    AccountGroupResponse,
    AccountGroupListResponse,
    AccountGroupOperationResponse,
)

__all__ = [
    # Signal DTOs
    "ProcessSignalRequest",
    "ProcessSignalResponse",
    "SignalDTO",
    "SignalListRequest",
    "SignalListResponse",
    # Trade DTOs
    "PlaceOrderRequest",
    "PlaceOrderResponse",
    "ClosePositionRequest",
    "ClosePositionResponse",
    "ModifyPositionRequest",
    "PositionDTO",
    "TradeDTO",
    "TradeListRequest",
    "TradeListResponse",
    # Account DTOs
    "AccountDTO",
    "AccountSummaryDTO",
    "GetAccountsRequest",
    "GetAccountsResponse",
    "ConnectAccountRequest",
    "ConnectAccountResponse",
    "SyncAccountRequest",
    "SyncAccountResponse",
    # Account Settings DTOs
    "PositionSizingMode",
    "AccountSettingsRequest",
    "AccountSettingsResponse",
    "GetAccountSettingsRequest",
    # Account Group DTOs
    "CreateAccountGroupRequest",
    "UpdateAccountGroupRequest",
    "DeleteAccountGroupRequest",
    "GetAccountGroupsRequest",
    "AddAccountToGroupRequest",
    "RemoveAccountFromGroupRequest",
    "AccountGroupResponse",
    "AccountGroupListResponse",
    "AccountGroupOperationResponse",
]
