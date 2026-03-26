"""
Agentic Monitor & AI Supervisor API Endpoints
==============================================

Provides API access to the trading monitor status, alerts, controls,
and AI-powered trading supervision.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter(prefix="/api/v1/monitor", tags=["monitor"])


@router.get("/status")
async def get_monitor_status():
    """Get current monitor status including alerts and trading state."""
    try:
        from app.services.agentic_monitor import get_agentic_monitor
        monitor = get_agentic_monitor()
        return monitor.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(severity: Optional[str] = None, limit: int = 50):
    """Get recent alerts, optionally filtered by severity."""
    try:
        from app.services.agentic_monitor import get_agentic_monitor, AlertSeverity
        monitor = get_agentic_monitor()

        sev = None
        if severity:
            try:
                sev = AlertSeverity(severity.lower())
            except ValueError:
                pass

        return {"alerts": monitor.get_alerts(severity=sev, limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause")
async def pause_trading(reason: str = "Manual pause"):
    """Manually pause all trading."""
    try:
        from app.services.agentic_monitor import get_agentic_monitor
        monitor = get_agentic_monitor()
        monitor.pause_trading(reason)
        return {"status": "paused", "reason": reason}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume")
async def resume_trading():
    """Resume trading after pause."""
    try:
        from app.services.agentic_monitor import get_agentic_monitor
        monitor = get_agentic_monitor()
        monitor.resume_trading()
        return {"status": "resumed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_session(starting_balance: float = 0.0):
    """Reset session stats."""
    try:
        from app.services.agentic_monitor import get_agentic_monitor
        monitor = get_agentic_monitor()
        monitor.reset_session(starting_balance)
        return {"status": "reset", "starting_balance": starting_balance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AI SUPERVISOR ENDPOINTS
# =============================================================================

@router.get("/supervisor/status")
async def get_supervisor_status():
    """Get AI supervisor status including learning insights."""
    try:
        from app.services.ai_trading_supervisor import get_ai_supervisor
        supervisor = get_ai_supervisor()
        return supervisor.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supervisor/flow-health")
async def check_flow_health():
    """Check health of all flow data sources."""
    try:
        from app.services.ai_trading_supervisor import get_ai_supervisor
        supervisor = get_ai_supervisor()
        status = await supervisor.check_flow_health()
        return {
            "unusual_whales": status.unusual_whales,
            "flowalgo": status.flowalgo,
            "polygon": status.polygon,
            "sources_active": status.sources_active,
            "is_market_hours": status.is_market_hours,
            "last_check": status.last_check.isoformat() if status.last_check else None,
            "error": status.error
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supervisor/insights")
async def get_pattern_insights():
    """Get AI-powered trading pattern insights."""
    try:
        from app.services.ai_trading_supervisor import get_ai_supervisor
        supervisor = get_ai_supervisor()
        return await supervisor.get_pattern_insights()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supervisor/session")
async def get_market_session():
    """Get current market session and active asset classes."""
    try:
        from app.services.ai_trading_supervisor import get_ai_supervisor
        supervisor = get_ai_supervisor()
        return {
            "session": supervisor.get_market_session().value,
            "active_asset_classes": [a.value for a in supervisor.get_active_asset_classes()]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
