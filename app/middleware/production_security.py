from fastapi import FastAPI, Request, Response
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
import time
import logging

logger = logging.getLogger(__name__)

# Rate limiting: 100 requests per minute per IP
rate_limiter = Limiter(key="100/min", max_calls=100, sync=True)

def _rate_limit_exceeded_handler(request: Request, exc: Exception):
    """Custom rate limit exceeded handler"""
    logger.warning(f"Rate limit exceeded for {get_remote_address(request)}")
    return Response(
        status_code=429,
        content={"error": "Rate limit exceeded", "retry_after": "60 seconds"},
        headers={"Retry-After": "60"}
    )

def create_production_middleware(app: FastAPI):
    """Add production hardening middleware to FastAPI app."""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3456", "https://tradeflow.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Rate limiting middleware
    app.add_middleware(
        rate_limiter,
        headers={
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "99"
        },
        exception_handler=_rate_limit_exceeded_handler,
    )
    
    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=315360; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self' http://localhost:3456 https://tradeflow.com; script-src 'self' 'unsafe-inline'; object-src 'self'; style-src 'self' 'unsafe-inline'"
        
        return response