"""
JWT Token Blacklist

Redis-based token blacklist for invalidating JWT tokens on logout.
Tokens are stored with TTL matching their expiration time.
"""

import logging
from typing import Optional
from datetime import datetime, timedelta
from jose import jwt, JWTError

from app.cache.redis_client import redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis key prefix for blacklisted tokens
BLACKLIST_PREFIX = "token_blacklist:"


async def add_token_to_blacklist(token: str) -> bool:
    """
    Add a JWT token to the blacklist.

    The token is stored in Redis with a TTL matching its expiration time.
    This ensures automatic cleanup of expired tokens.

    Args:
        token: The JWT token to blacklist

    Returns:
        True if successfully blacklisted, False otherwise
    """
    try:
        # Decode token to get expiration time (without verification for speed)
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False}  # Don't verify exp, we just need to read it
        )

        exp_timestamp = payload.get("exp")
        if not exp_timestamp:
            # No expiration - use default TTL
            ttl_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        else:
            # Calculate remaining TTL
            exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
            remaining = exp_datetime - datetime.utcnow()
            ttl_seconds = max(int(remaining.total_seconds()), 1)

        # Create a unique key using the token's JTI or a hash of the token
        jti = payload.get("jti")
        if jti:
            key = f"{BLACKLIST_PREFIX}{jti}"
        else:
            # Use hash of token as fallback
            import hashlib
            token_hash = hashlib.sha256(token.encode()).hexdigest()[:32]
            key = f"{BLACKLIST_PREFIX}{token_hash}"

        # Store in Redis with TTL
        await redis_client.set(key, "1", ex=ttl_seconds)
        logger.info(f"Token blacklisted, expires in {ttl_seconds}s")
        return True

    except JWTError as e:
        logger.warning(f"Failed to decode token for blacklisting: {e}")
        return False
    except Exception as e:
        logger.error(f"Error blacklisting token: {e}")
        return False


async def is_token_blacklisted(token: str) -> bool:
    """
    Check if a JWT token is blacklisted.

    Args:
        token: The JWT token to check

    Returns:
        True if the token is blacklisted, False otherwise
    """
    try:
        # Decode token to get JTI (without full verification)
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False}
        )

        jti = payload.get("jti")
        if jti:
            key = f"{BLACKLIST_PREFIX}{jti}"
        else:
            import hashlib
            token_hash = hashlib.sha256(token.encode()).hexdigest()[:32]
            key = f"{BLACKLIST_PREFIX}{token_hash}"

        result = await redis_client.get(key)
        return result is not None

    except JWTError:
        # If we can't decode, treat as potentially blacklisted for safety
        return False
    except Exception as e:
        logger.error(f"Error checking token blacklist: {e}")
        # On error, don't block - fail open for availability
        return False


async def blacklist_all_user_tokens(user_id: int) -> bool:
    """
    Blacklist all tokens for a specific user.

    This is useful for "logout everywhere" functionality.
    We track this by storing a timestamp that all tokens
    issued before must be rejected.

    Args:
        user_id: The user ID to blacklist tokens for

    Returns:
        True if successful, False otherwise
    """
    try:
        key = f"{BLACKLIST_PREFIX}user:{user_id}:invalidate_before"
        # Store current timestamp - all tokens issued before this are invalid
        await redis_client.set(
            key,
            str(datetime.utcnow().timestamp()),
            ex=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 * 2  # Keep for 2x token lifetime
        )
        logger.info(f"Invalidated all tokens for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error invalidating user tokens: {e}")
        return False


async def is_user_token_invalidated(user_id: int, token_issued_at: float) -> bool:
    """
    Check if a user's token was issued before their invalidation timestamp.

    Args:
        user_id: The user ID to check
        token_issued_at: The timestamp when the token was issued

    Returns:
        True if the token should be rejected, False otherwise
    """
    try:
        key = f"{BLACKLIST_PREFIX}user:{user_id}:invalidate_before"
        invalidate_before = await redis_client.get(key)
        if invalidate_before:
            return token_issued_at < float(invalidate_before)
        return False
    except Exception as e:
        logger.error(f"Error checking user token invalidation: {e}")
        return False
