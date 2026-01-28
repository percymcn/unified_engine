"""
AI Strategy Suite Router
Provides endpoints for Pine Script fixing, backtesting, and AI strategy coaching
"""

from fastapi import APIRouter
from .pine_fixer import router as pine_fixer_router

router = APIRouter(prefix="/ai-suite", tags=["AI Suite"])

router.include_router(pine_fixer_router)
