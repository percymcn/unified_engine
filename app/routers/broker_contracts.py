"""
Broker Contracts Router

Provides endpoints for:
- GET /api/v1/brokers/contracts - Returns broker credential schemas (public, no auth)
- GET /api/v1/brokers/status - Returns broker configuration status (requires auth)

This is the single source of truth for UI broker forms.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.routers.auth import get_current_user
from app.models.models import User
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/brokers", tags=["brokers"])

# Load contracts from JSON file
CONTRACTS_PATH = Path(__file__).parent.parent / "contracts" / "brokers.json"


class FieldOption(BaseModel):
    value: str
    label: str


class BrokerField(BaseModel):
    name: str
    backend_name: str
    type: str
    label: str
    description: Optional[str] = None
    options: Optional[List[FieldOption]] = None
    default: Optional[str] = None
    required_for: List[str] = []
    order: int = 0


class BrokerContract(BaseModel):
    id: str
    display_name: str
    enabled: bool
    auth_modes: List[str]
    default_auth_mode: str
    fields: List[BrokerField]
    test_connection_endpoint: str
    discover_accounts_endpoint: str
    notes: Optional[str] = None
    oauth_config: Optional[Dict[str, str]] = None
    alias_of: Optional[str] = None


class BrokerContractsResponse(BaseModel):
    version: str
    brokers: Dict[str, BrokerContract]


class BrokerStatusItem(BaseModel):
    id: str
    display_name: str
    enabled: bool
    configured: bool
    disabled_reason: Optional[str] = None
    auth_mode: Optional[str] = None


class BrokerStatusResponse(BaseModel):
    brokers: List[BrokerStatusItem]


def load_contracts() -> Dict[str, Any]:
    """Load broker contracts from JSON file."""
    try:
        if CONTRACTS_PATH.exists():
            with open(CONTRACTS_PATH, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load broker contracts: {e}")
    return {"version": "1.0.0", "brokers": {}}


def get_broker_config_status(broker_id: str) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Check if a broker is configured at the platform level.

    Returns:
        (configured, disabled_reason, auth_mode)
    """
    broker_configs = {
        "tradelocker": {
            "sdk": [
                getattr(settings, 'TRADELOCKER_USERNAME', None),
                getattr(settings, 'TRADELOCKER_PASSWORD', None),
                getattr(settings, 'TRADELOCKER_SERVER', None),
            ],
            "brand_api": [
                getattr(settings, 'TRADELOCKER_API_KEY', None),
            ]
        },
        "projectx": {
            "api_key": [
                getattr(settings, 'PROJECT_X_USERNAME', None),
                getattr(settings, 'PROJECT_X_API_KEY', None),
            ]
        },
        "topstep": {
            "api_key": [
                getattr(settings, 'PROJECT_X_USERNAME', None),
                getattr(settings, 'PROJECT_X_API_KEY', None),
            ]
        },
        "tradovate": {
            "oauth": [
                getattr(settings, 'TRADOVATE_CID', None),
                getattr(settings, 'TRADOVATE_SEC', None),
            ],
            "password": [
                getattr(settings, 'TRADOVATE_USER_ID', None),
                getattr(settings, 'TRADOVATE_PASSWORD', None),
            ]
        },
        "mt4": {
            "metaapi": [
                getattr(settings, 'METAAPI_TOKEN', None),
            ],
            "manager": [
                getattr(settings, 'MT4_MANAGER_LOGIN', None),
                getattr(settings, 'MT4_MANAGER_PASSWORD', None),
            ]
        },
        "mt5": {
            "metaapi": [
                getattr(settings, 'METAAPI_TOKEN', None),
            ],
            "manager": [
                getattr(settings, 'MT5_MANAGER_LOGIN', None),
                getattr(settings, 'MT5_MANAGER_PASSWORD', None),
            ]
        },
    }

    if broker_id not in broker_configs:
        return False, f"Unknown broker: {broker_id}", None

    broker_modes = broker_configs[broker_id]

    # Check each auth mode
    for mode, required_vars in broker_modes.items():
        if all(v for v in required_vars):
            return True, None, mode

    # Not configured - list missing vars
    missing = []
    for mode, required_vars in broker_modes.items():
        if not all(v for v in required_vars):
            missing.append(mode)

    # Per-user credentials always allowed
    return True, None, "user_provided"


@router.get("/contracts", response_model=BrokerContractsResponse)
async def get_broker_contracts():
    """
    Get broker credential contracts.

    Returns the canonical schema for each broker's credential fields.
    Used by UI to dynamically render broker forms.

    This endpoint is PUBLIC (no auth required) to support
    the add-account form before user has any accounts.
    """
    contracts_data = load_contracts()

    return BrokerContractsResponse(
        version=contracts_data.get("version", "1.0.0"),
        brokers={
            broker_id: BrokerContract(**broker_data)
            for broker_id, broker_data in contracts_data.get("brokers", {}).items()
        }
    )


@router.get("/status", response_model=BrokerStatusResponse)
async def get_broker_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get broker configuration status.

    Returns whether each broker is configured at the platform level.
    Requires authentication.

    For multi-user SaaS:
    - Platform owner sets ENV vars for shared credentials
    - Users can also provide their own credentials (always allowed)
    """
    contracts_data = load_contracts()
    brokers_config = contracts_data.get("brokers", {})

    status_list = []
    for broker_id, broker_data in brokers_config.items():
        configured, reason, auth_mode = get_broker_config_status(broker_id)

        status_list.append(BrokerStatusItem(
            id=broker_id,
            display_name=broker_data.get("display_name", broker_id),
            enabled=broker_data.get("enabled", True),
            configured=configured,
            disabled_reason=reason,
            auth_mode=auth_mode,
        ))

    return BrokerStatusResponse(brokers=status_list)
