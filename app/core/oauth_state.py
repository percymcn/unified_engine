"""
OAuth State Management

Generates and validates OAuth state parameters to prevent CSRF attacks.
State tokens are stored in Redis with a short TTL.
"""

import secrets
import logging
from typing import Optional

from app.cache.redis_client import redis_client

logger = logging.getLogger(__name__)

# Redis key prefix for OAuth state tokens
STATE_PREFIX = "oauth_state:"
STATE_TTL_SECONDS = 600  # 10 minutes


async def generate_oauth_state() -> str:
    """
    Generate a cryptographically secure OAuth state token.

    The token is stored in Redis with a short TTL to prevent replay attacks.

    Returns:
        A unique state token string
    """
    # Generate a secure random token
    state = secrets.token_urlsafe(32)

    try:
        # Store in Redis with TTL
        key = f"{STATE_PREFIX}{state}"
        await redis_client.set(key, "1", expire=STATE_TTL_SECONDS)
        logger.debug(f"Generated OAuth state token (TTL={STATE_TTL_SECONDS}s)")
        return state
    except Exception as e:
        logger.error(f"Failed to store OAuth state in Redis: {e}")
        # Still return the state - worst case we can't validate it
        # but the flow shouldn't completely break
        return state


async def validate_oauth_state(state: Optional[str]) -> bool:
    """
    Validate an OAuth state token.

    The token is consumed (deleted) after validation to prevent replay.

    Args:
        state: The state token to validate

    Returns:
        True if the state is valid and was stored in Redis, False otherwise
    """
    if not state:
        logger.warning("OAuth callback missing state parameter - CSRF risk")
        return False

    try:
        key = f"{STATE_PREFIX}{state}"

        # Check if state exists
        exists = await redis_client.get(key)
        if not exists:
            logger.warning("Invalid or expired OAuth state token - possible CSRF attack")
            return False

        # Delete the state to prevent replay attacks
        await redis_client.delete(key)
        logger.debug("OAuth state token validated and consumed")
        return True

    except Exception as e:
        logger.error(f"Failed to validate OAuth state: {e}")
        # On Redis error, fail closed for security
        return False


async def validate_oauth_state_permissive(state: Optional[str]) -> bool:
    """
    Validate OAuth state with permissive fallback for legacy flows.

    This is a transitional function that:
    - Returns True if state is valid
    - Returns True if state is None (for backwards compatibility)
    - Returns False only if state is provided but invalid

    Use this during migration, then switch to strict validate_oauth_state.

    Args:
        state: The state token to validate (can be None)

    Returns:
        True if valid or not provided, False if provided but invalid
    """
    if state is None:
        # No state provided - allow for backwards compatibility
        # TODO: Make state required after frontend is updated
        logger.info("OAuth callback without state parameter - legacy flow accepted")
        return True

    return await validate_oauth_state(state)
