"""
Broker Field Length Limits and Validation

Centralizes field length limits for all supported brokers.
Each broker has different restrictions on comment, clientId, and other text fields.

References:
- MetaAPI: https://metaapi.cloud/docs/client/clientIdUsage/
- MT4: 31 character comment limit
- MT5: 31 character comment limit (when using clientId, combined <= 26)
- TradeLocker: Uses strategyId (no documented limit)
- ProjectX: Uses description field
- Tradovate: Uses customTag field
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


# Broker-specific field length limits
BROKER_LIMITS = {
    "mt4": {
        "comment": 31,
        "clientId": 32,
        "combined_comment_clientId": 26,  # When both are used
    },
    "mt5": {
        "comment": 31,
        "clientId": 32,
        "combined_comment_clientId": 26,  # When both are used via MetaAPI
    },
    "metaapi": {
        "comment": 26,  # Safe limit when clientId might be auto-generated
        "clientId": 32,
    },
    "tradelocker": {
        "strategyId": 50,  # Conservative estimate
        "comment": 100,  # No documented limit, using safe default
    },
    "projectx": {
        "description": 100,  # No documented limit
        "comment": 100,
    },
    "tradovate": {
        "customTag": 50,
        "text": 100,
        "comment": 100,
    },
    # Default for unknown brokers
    "default": {
        "comment": 26,  # Conservative
        "clientId": 26,
    }
}


def get_broker_limit(broker: str, field: str) -> int:
    """Get the maximum length for a field on a specific broker.

    Args:
        broker: Broker name (mt4, mt5, tradelocker, etc.)
        field: Field name (comment, clientId, etc.)

    Returns:
        Maximum allowed length for the field
    """
    broker_lower = broker.lower()
    limits = BROKER_LIMITS.get(broker_lower, BROKER_LIMITS["default"])
    return limits.get(field, BROKER_LIMITS["default"].get(field, 26))


def truncate_field(value: Optional[str], max_length: int) -> Optional[str]:
    """Truncate a field value to the maximum allowed length.

    Args:
        value: The string value to truncate
        max_length: Maximum allowed length

    Returns:
        Truncated string or original if within limit
    """
    if value is None:
        return None
    if len(value) <= max_length:
        return value
    truncated = value[:max_length]
    logger.debug(f"Truncated field from {len(value)} to {max_length} chars: '{value[:20]}...' -> '{truncated}'")
    return truncated


def truncate_comment(comment: Optional[str], broker: str = "default") -> Optional[str]:
    """Truncate comment field for a specific broker.

    Args:
        comment: The comment string
        broker: Broker name to get appropriate limit

    Returns:
        Truncated comment
    """
    max_length = get_broker_limit(broker, "comment")
    return truncate_field(comment, max_length)


def truncate_client_id(client_id: Optional[str], broker: str = "default") -> Optional[str]:
    """Truncate clientId field for a specific broker.

    Args:
        client_id: The clientId string
        broker: Broker name to get appropriate limit

    Returns:
        Truncated clientId
    """
    max_length = get_broker_limit(broker, "clientId")
    return truncate_field(client_id, max_length)


def validate_trade_fields(
    broker: str,
    comment: Optional[str] = None,
    client_id: Optional[str] = None,
    strategy_id: Optional[str] = None,
    description: Optional[str] = None
) -> dict:
    """Validate and truncate all trade-related text fields for a broker.

    Args:
        broker: Broker name
        comment: Trade comment
        client_id: Client ID (for MetaAPI)
        strategy_id: Strategy ID (for TradeLocker)
        description: Description (for ProjectX)

    Returns:
        Dict with validated/truncated field values
    """
    broker_lower = broker.lower()
    result = {}

    # Handle comment
    if comment is not None:
        result["comment"] = truncate_comment(comment, broker_lower)

    # Handle clientId (mainly MetaAPI)
    if client_id is not None:
        result["client_id"] = truncate_client_id(client_id, broker_lower)

    # Handle strategyId (TradeLocker)
    if strategy_id is not None:
        max_len = get_broker_limit(broker_lower, "strategyId")
        result["strategy_id"] = truncate_field(strategy_id, max_len)

    # Handle description (ProjectX)
    if description is not None:
        max_len = get_broker_limit(broker_lower, "description")
        result["description"] = truncate_field(description, max_len)

    return result


def generate_short_comment(signal_id: str, prefix: str = "S") -> str:
    """Generate a short comment from a signal ID.

    Creates a comment like "S_abc123" that fits within all broker limits.

    Args:
        signal_id: Full signal UUID
        prefix: Prefix character (default "S" for Signal)

    Returns:
        Short comment string (max 10 chars)
    """
    # Use first 6 chars of UUID for uniqueness
    short_id = signal_id.replace("-", "")[:6]
    return f"{prefix}_{short_id}"
