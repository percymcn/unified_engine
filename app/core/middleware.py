"""
Middleware for request ID tracking and enhanced logging
"""
import uuid
import time
import logging
from contextvars import ContextVar
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Context variable for request ID - thread/async safe
_request_id_ctx: ContextVar[str] = ContextVar('request_id', default='no-request-id')

def get_current_request_id() -> str:
    """Get the current request ID from context."""
    return _request_id_ctx.get()

# Set up the log record factory ONCE at module load (not per-request)
_original_factory = logging.getLogRecordFactory()

def _request_id_record_factory(*args, **kwargs):
    """Log record factory that adds request_id from context variable."""
    record = _original_factory(*args, **kwargs)
    record.request_id = _request_id_ctx.get()
    return record

# Install once at import time
logging.setLogRecordFactory(_request_id_record_factory)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add request ID to all requests for tracing"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or get request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Add to request state
        request.state.request_id = request_id

        # Set context variable for this request (async-safe)
        token = _request_id_ctx.set(request_id)

        try:
            # Process request
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}"

            # Log request
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.4f}s - "
                f"Request-ID: {request_id}"
            )

            return response
        finally:
            # Reset context variable
            _request_id_ctx.reset(token)
