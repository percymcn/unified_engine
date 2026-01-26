// Fix for the str.get() error in webhooks.py
// The issue is likely caused by trying to call .get() on a string instead of a dict

import json
from fastapi import HTTPException

def safe_get_payload_field(payload, field, default=None):
    """Safely get a field from a payload dict or nested dict"""
    if isinstance(payload, dict):
        return payload.get(field, default)
    elif isinstance(payload, str):
        # If payload is a string, try to parse it as JSON
        try:
            parsed = json.loads(payload)
            return parsed.get(field, default)
        except json.JSONDecodeError:
            return default
    return default

def validate_webhook_payload(payload):
    """Validate and normalize webhook payload"""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")
    
    return payload