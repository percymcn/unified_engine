import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def safe_parse_webhook_payload(payload: Any) -> Dict[str, Any]:
    """
    Safely parse webhook payload, handling string or dict inputs.
    
    This function addresses the 'str' object has no attribute 'get' error
    by ensuring the payload is properly parsed as a dictionary.
    """
    if payload is None:
        return {}
    
    # If it's already a dict, return as-is
    if isinstance(payload, dict):
        return payload
    
    # If it's a string, try to parse as JSON
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                return parsed
            else:
                logger.warning(f"Webhook payload is valid JSON but not a dict: {type(parsed)}")
                return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse webhook payload JSON: {e}")
            return {}
    
    # If it's a list or other type, convert to dict
    try:
        if hasattr(payload, '__dict__'):
            return payload.__dict__
        elif hasattr(payload, 'model_dump'):
            return payload.model_dump()
        else:
            logger.warning(f"Webhook payload type not supported: {type(payload)}")
            return {}
    except Exception as e:
        logger.error(f"Error converting webhook payload to dict: {e}")
        return {}

def safe_get_field(payload: Dict[str, Any], field: str, default: Any = None) -> Any:
    """
    Safely get a field from a parsed payload with proper type checking.
    """
    if not isinstance(payload, dict):
        return default
    
    value = payload.get(field, default)
    
    # Handle nested structures safely
    if isinstance(value, dict):
        return value
    elif isinstance(value, (list, tuple)):
        return value
    elif hasattr(value, '__dict__'):
        return value.__dict__
    elif hasattr(value, 'model_dump'):
        return value.model_dump()
    else:
        return value

def validate_webhook_payload_structure(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate webhook payload structure and extract required fields.
    """
    # Handle TradingView-style payloads
    if 'symbol' in payload:
        return {
            'symbol': safe_get_field(payload, 'symbol'),
            'action': safe_get_field(payload, 'action', '').lower(),
            'price': float(safe_get_field(payload, 'price', 0.0)),
            'volume': float(safe_get_field(payload, 'volume', 0.01)),
            'strategy': safe_get_field(payload, 'strategy', {}),
            'strategy_name': safe_get_field(payload, 'strategy', {}).get('id'),
            'strategy_version': safe_get_field(payload, 'strategy', {}).get('version'),
            'comment': safe_get_field(payload, 'comment'),
            'target_account_ids': safe_get_field(payload, 'target_account_ids'),
        }
    
    # Handle nested structure with strategy object
    if 'strategy' in payload and isinstance(payload.get('strategy'), dict):
        strategy = payload['strategy']
        return {
            'symbol': safe_get_field(payload, 'symbol'),
            'action': safe_get_field(payload, 'action', '').lower(),
            'price': float(safe_get_field(payload, 'price', 0.0)),
            'volume': float(safe_get_field(payload, 'volume', 0.01)),
            'strategy': strategy,
            'strategy_name': safe_get_field(strategy, 'id'),
            'strategy_version': safe_get_field(strategy, 'version'),
            'comment': safe_get_field(payload, 'comment'),
            'target_account_ids': safe_get_field(payload, 'target_account_ids'),
        }
    
    # Default structure for unknown payload formats
    return {
        'symbol': safe_get_field(payload, 'symbol'),
        'action': safe_get_field(payload, 'action', '').lower(),
        'price': float(safe_get_field(payload, 'price', 0.0)),
        'volume': float(safe_get_field(payload, 'volume', 0.01)),
        'strategy': {},
        'strategy_name': None,
        'strategy_version': None,
        'comment': safe_get_field(payload, 'comment'),
        'target_account_ids': safe_get_field(payload, 'target_account_ids'),
    }