"""
Middleware for request ID tracking and enhanced logging
"""
import uuid
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add request ID to all requests for tracing"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or get request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Add to request state
        request.state.request_id = request_id
        
        # Add to logger context
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.request_id = request_id
            return record
        
        logging.setLogRecordFactory(record_factory)
        
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
        
        # Restore logger factory
        logging.setLogRecordFactory(old_factory)
        
        return response
