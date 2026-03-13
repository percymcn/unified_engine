"""
AI Strategy Suite API Router
=============================

API endpoints for the institutional-grade AI analysis suite.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

from app.services.ai_strategy_suite import (
    ai_strategy_suite,
    AnalysisType,
    AnalysisResult
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai-strategy", tags=["AI Strategy Suite"])


# ==========================================
# REQUEST/RESPONSE MODELS
# ==========================================

class AnalysisRequest(BaseModel):
    """Request for single analysis"""
    ticker: str = Field(..., description="Stock/ETF symbol", example="SPY")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class MultiAnalysisRequest(BaseModel):
    """Request for multiple analyses"""
    ticker: str = Field(..., description="Stock/ETF symbol")
    analyses: Optional[List[str]] = Field(
        None,
        description="Analysis types to run (default: technical, patterns, macro)"
    )
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class AnalysisResponse(BaseModel):
    """Single analysis response"""
    analysis_type: str
    ticker: str
    timestamp: str
    recommendation: str
    confidence: float
    summary: str
    data: Dict[str, Any]
    from_cache: bool = False
    processing_time_ms: int = 0


class CompositeAnalysisResponse(BaseModel):
    """Composite analysis response"""
    ticker: str
    analyses: Dict[str, AnalysisResponse]
    composite: Dict[str, Any]
    timestamp: str


class QuickSignalResponse(BaseModel):
    """Quick signal enhancement response"""
    ticker: str
    smartflow_enhancement: Dict[str, Any]
    recommendation: str
    confidence_boost: float
    signal_strength: float
    supporting_analyses: List[str]


# ==========================================
# INDIVIDUAL ANALYSIS ENDPOINTS
# ==========================================

@router.post("/technical", response_model=AnalysisResponse)
async def analyze_technical(request: AnalysisRequest):
    """
    Citadel-Grade Technical Analysis

    Analyzes trend direction, support/resistance, moving averages,
    RSI, MACD, Bollinger Bands, chart patterns, and Fibonacci levels.
    """
    try:
        result = await ai_strategy_suite.analyze_technical(
            request.ticker,
            request.context
        )

        return AnalysisResponse(
            analysis_type=result.analysis_type,
            ticker=result.ticker,
            timestamp=result.timestamp.isoformat(),
            recommendation=result.recommendation,
            confidence=result.confidence,
            summary=result.summary,
            data=result.data,
            from_cache=result.from_cache,
            processing_time_ms=result.processing_time_ms
        )
    except Exception as e:
        logger.error(f"Technical analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dcf-valuation", response_model=AnalysisResponse)
async def analyze_dcf_valuation(request: AnalysisRequest):
    """
    Morgan Stanley-Style DCF Valuation

    Provides 5-year revenue projections, operating margins,
    free cash flow analysis, WACC, terminal value, and fair value estimate.
    """
    try:
        result = await ai_strategy_suite.analyze_dcf_valuation(
            request.ticker,
            request.context
        )

        return AnalysisResponse(
            analysis_type=result.analysis_type,
            ticker=result.ticker,
            timestamp=result.timestamp.isoformat(),
            recommendation=result.recommendation,
            confidence=result.confidence,
            summary=result.summary,
            data=result.data,
            from_cache=result.from_cache,
            processing_time_ms=result.processing_time_ms
        )
    except Exception as e:
        logger.error(f"DCF analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk", response_model=AnalysisResponse)
async def analyze_risk(request: AnalysisRequest):
    """
    Bridgewater-Inspired Risk Analysis

    Analyzes correlation risk, sector concentration, interest rate sensitivity,
    recession stress test, liquidity risk, and tail risk scenarios.
    """
    try:
        result = await ai_strategy_suite.analyze_risk(
            request.ticker,
            portfolio=request.context.get("portfolio") if request.context else None,
            context=request.context
        )

        return AnalysisResponse(
            analysis_type=result.analysis_type,
            ticker=result.ticker,
            timestamp=result.timestamp.isoformat(),
            recommendation=result.recommendation,
            confidence=result.confidence,
            summary=result.summary,
            data=result.data,
            from_cache=result.from_cache,
            processing_time_ms=result.processing_time_ms
        )
    except Exception as e:
        logger.error(f"Risk analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/earnings", response_model=AnalysisResponse)
async def analyze_earnings(request: AnalysisRequest):
    """
    JPMorgan-Level Earnings Breakdown

    Analyzes last 4 quarters vs estimates, revenue/EPS consensus,
    key metrics, segment breakdown, management guidance, and implied moves.
    """
    try:
        result = await ai_strategy_suite.analyze_earnings(
            request.ticker,
            request.context
        )

        return AnalysisResponse(
            analysis_type=result.analysis_type,
            ticker=result.ticker,
            timestamp=result.timestamp.isoformat(),
            recommendation=result.recommendation,
            confidence=result.confidence,
            summary=result.summary,
            data=result.data,
            from_cache=result.from_cache,
            processing_time_ms=result.processing_time_ms
        )
    except Exception as e:
        logger.error(f"Earnings analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patterns", response_model=AnalysisResponse)
async def analyze_patterns(request: AnalysisRequest):
    """
    Renaissance Technologies Pattern Finder

    Finds seasonal patterns, day-of-week patterns, event correlations,
    insider activity, institutional ownership, short interest, and unusual options.
    """
    try:
        result = await ai_strategy_suite.analyze_patterns(
            request.ticker,
            request.context
        )

        return AnalysisResponse(
            analysis_type=result.analysis_type,
            ticker=result.ticker,
            timestamp=result.timestamp.isoformat(),
            recommendation=result.recommendation,
            confidence=result.confidence,
            summary=result.summary,
            data=result.data,
            from_cache=result.from_cache,
            processing_time_ms=result.processing_time_ms
        )
    except Exception as e:
        logger.error(f"Pattern analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/macro", response_model=AnalysisResponse)
async def analyze_macro(request: AnalysisRequest):
    """
    McKinsey-Level Macro Impact Assessment

    Analyzes interest rate impact, inflation effects, GDP outlook,
    USD strength, Fed policy, global risks, and sector rotation.
    """
    try:
        result = await ai_strategy_suite.analyze_macro(
            request.ticker,
            request.context
        )

        return AnalysisResponse(
            analysis_type=result.analysis_type,
            ticker=result.ticker,
            timestamp=result.timestamp.isoformat(),
            recommendation=result.recommendation,
            confidence=result.confidence,
            summary=result.summary,
            data=result.data,
            from_cache=result.from_cache,
            processing_time_ms=result.processing_time_ms
        )
    except Exception as e:
        logger.error(f"Macro analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/competitive", response_model=AnalysisResponse)
async def analyze_competitive(request: AnalysisRequest):
    """
    Bain-Style Competitive Advantage Analysis

    Analyzes competitors, market share, competitive moat,
    management quality, innovation, SWOT, and catalysts.
    """
    try:
        result = await ai_strategy_suite.analyze_competitive(
            request.ticker,
            request.context
        )

        return AnalysisResponse(
            analysis_type=result.analysis_type,
            ticker=result.ticker,
            timestamp=result.timestamp.isoformat(),
            recommendation=result.recommendation,
            confidence=result.confidence,
            summary=result.summary,
            data=result.data,
            from_cache=result.from_cache,
            processing_time_ms=result.processing_time_ms
        )
    except Exception as e:
        logger.error(f"Competitive analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# COMPOSITE ANALYSIS ENDPOINTS
# ==========================================

@router.post("/full-analysis", response_model=CompositeAnalysisResponse)
async def run_full_analysis(request: MultiAnalysisRequest):
    """
    Run Multiple Analyses and Get Composite Score

    Runs selected analyses in parallel and computes a composite
    recommendation with agreement level and signal strength.
    """
    try:
        # Parse analysis types
        analysis_types = None
        if request.analyses:
            analysis_types = []
            for a in request.analyses:
                try:
                    analysis_types.append(AnalysisType(a))
                except ValueError:
                    logger.warning(f"Unknown analysis type: {a}")

        # Run analyses
        results = await ai_strategy_suite.run_full_analysis(
            request.ticker,
            analysis_types,
            request.context
        )

        # Compute composite score
        composite = ai_strategy_suite.compute_composite_score(results)

        # Format response
        analyses_response = {}
        for analysis_type, result in results.items():
            analyses_response[analysis_type] = AnalysisResponse(
                analysis_type=result.analysis_type,
                ticker=result.ticker,
                timestamp=result.timestamp.isoformat(),
                recommendation=result.recommendation,
                confidence=result.confidence,
                summary=result.summary,
                data=result.data,
                from_cache=result.from_cache,
                processing_time_ms=result.processing_time_ms
            )

        return CompositeAnalysisResponse(
            ticker=request.ticker,
            analyses=analyses_response,
            composite=composite,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Full analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-signal", response_model=QuickSignalResponse)
async def get_quick_signal_enhancement(request: AnalysisRequest):
    """
    Quick Signal Enhancement for SmartFlow

    Runs fast analyses (technical, patterns) and returns
    a confidence boost factor for SmartFlow signals.
    """
    try:
        # Run fast analyses only
        fast_analyses = [
            AnalysisType.TECHNICAL_ANALYSIS,
            AnalysisType.PATTERN_FINDER,
        ]

        results = await ai_strategy_suite.run_full_analysis(
            request.ticker,
            fast_analyses,
            request.context
        )

        composite = ai_strategy_suite.compute_composite_score(results)

        # Calculate confidence boost for SmartFlow
        # High agreement + strong signal = higher boost
        base_boost = 0
        if composite["agreement_level"] == "high":
            base_boost = 15
        elif composite["agreement_level"] == "medium":
            base_boost = 8

        # Adjust based on recommendation alignment
        rec = composite["composite_recommendation"]
        context_direction = request.context.get("signal_direction") if request.context else None

        if context_direction:
            if (context_direction == "buy" and rec in ["strong_buy", "buy"]) or \
               (context_direction == "sell" and rec in ["strong_sell", "sell"]):
                base_boost += 10  # Aligned
            elif (context_direction == "buy" and rec in ["strong_sell", "sell"]) or \
                 (context_direction == "sell" and rec in ["strong_buy", "buy"]):
                base_boost -= 20  # Conflicting - reduce confidence

        supporting = [
            analysis_type for analysis_type, result in results.items()
            if result.recommendation in ["strong_buy", "buy"] and context_direction == "buy" or
               result.recommendation in ["strong_sell", "sell"] and context_direction == "sell"
        ]

        return QuickSignalResponse(
            ticker=request.ticker,
            smartflow_enhancement={
                "confidence_boost": base_boost,
                "composite_recommendation": rec,
                "agreement_level": composite["agreement_level"],
                "analyses_run": list(results.keys())
            },
            recommendation=rec,
            confidence_boost=base_boost,
            signal_strength=composite["signal_strength"],
            supporting_analyses=supporting
        )

    except Exception as e:
        logger.error(f"Quick signal enhancement failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# STATUS & UTILITIES
# ==========================================

@router.get("/available-analyses")
async def list_available_analyses():
    """List all available analysis types"""
    return {
        "analyses": [
            {
                "type": AnalysisType.TECHNICAL_ANALYSIS.value,
                "name": "Citadel Technical Analysis",
                "description": "Technical indicators, patterns, support/resistance",
                "cache_ttl_minutes": 15
            },
            {
                "type": AnalysisType.DCF_VALUATION.value,
                "name": "Morgan Stanley DCF Valuation",
                "description": "Discounted cash flow fair value analysis",
                "cache_ttl_minutes": 1440  # 24 hours
            },
            {
                "type": AnalysisType.RISK_ANALYSIS.value,
                "name": "Bridgewater Risk Analysis",
                "description": "Portfolio risk assessment and stress tests",
                "cache_ttl_minutes": 120
            },
            {
                "type": AnalysisType.EARNINGS_BREAKDOWN.value,
                "name": "JPMorgan Earnings Breakdown",
                "description": "Earnings preview and post-earnings analysis",
                "cache_ttl_minutes": 720  # 12 hours
            },
            {
                "type": AnalysisType.PATTERN_FINDER.value,
                "name": "RenTech Pattern Finder",
                "description": "Statistical patterns and edges",
                "cache_ttl_minutes": 30
            },
            {
                "type": AnalysisType.MACRO_IMPACT.value,
                "name": "McKinsey Macro Impact",
                "description": "Macroeconomic analysis and sector rotation",
                "cache_ttl_minutes": 240
            },
            {
                "type": AnalysisType.COMPETITIVE_ADVANTAGE.value,
                "name": "Bain Competitive Advantage",
                "description": "Competitive moat and market position analysis",
                "cache_ttl_minutes": 1440
            },
        ]
    }


@router.get("/status")
async def get_status():
    """Get AI Strategy Suite status"""
    return {
        "status": "operational" if ai_strategy_suite.client else "no_api_key",
        "model": ai_strategy_suite.model,
        "analyses_available": len(AnalysisType),
        "cache_enabled": True
    }
