"""
Rate Limiting Configuration

Provides rate limiting for sensitive endpoints using SlowAPI.
Different limits for different endpoint categories:
- Auth endpoints: 5/minute (login, register, password reset)
- Email endpoints: 3/minute (verification, password reset emails)
- General API: 100/minute
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


def get_real_client_ip(request: Request) -> str:
    """
    Get the real client IP address, handling proxies like Cloudflare.

    Priority:
    1. CF-Connecting-IP (Cloudflare)
    2. X-Real-IP (Nginx)
    3. X-Forwarded-For (first IP)
    4. request.client.host (direct connection)
    """
    # Cloudflare
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip

    # Nginx proxy
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Standard proxy header (take first IP)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Direct connection
    return get_remote_address(request)


# Create the limiter with real IP extraction
limiter = Limiter(key_func=get_real_client_ip)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for rate limit exceeded errors."""
    client_ip = get_real_client_ip(request)
    logger.warning(
        f"Rate limit exceeded: {request.url.path} from {client_ip} - limit: {exc.detail}"
    )
    return JSONResponse(
        status_code=429,
        content={
            "error": "Too many requests",
            "detail": "Rate limit exceeded. Please try again later.",
            "retry_after_seconds": 60,
        },
        headers={"Retry-After": "60"},
    )


# Rate limit strings for different endpoint categories
AUTH_RATE_LIMIT = "5/minute"  # Login, register, password reset
EMAIL_RATE_LIMIT = "3/minute"  # Email sending operations
API_RATE_LIMIT = "100/minute"  # General API calls
WEBHOOK_RATE_LIMIT = "60/minute"  # Webhook endpoints (higher for trading signals)
