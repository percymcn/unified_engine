"""
SmartFlow Integrity API Router
===============================

API endpoints for SmartFlow integrity monitoring and baseline management.

Endpoints:
- GET /api/v1/smartflow/integrity/status - Full integrity status
- GET /api/v1/smartflow/integrity/topology - Runtime topology for visualization
- GET /api/v1/smartflow/integrity/drift - Current drift findings
- GET /api/v1/smartflow/integrity/baseline - Current baseline info
- POST /api/v1/smartflow/integrity/freeze-baseline - Create new baseline
- POST /api/v1/smartflow/integrity/run-check - Force integrity check
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import User
from app.routers.auth import get_current_user
from app.services.smartflow_integrity_monitor import (
    integrity_monitor,
    IntegrityReport,
    DriftFinding,
    to_dict,
    BASELINE_DIR,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/smartflow/integrity", tags=["SmartFlow Integrity"])


# ============================================================================
# Request/Response Models
# ============================================================================

class IntegrityStatusResponse(BaseModel):
    """Response for integrity status endpoint."""
    timestamp: str
    overall_status: str
    health_score: float
    category_scores: Dict[str, float]
    components: List[Dict[str, Any]]
    drift_count: int
    critical_drift_count: int
    baseline_version: Optional[str]
    notes: List[str]


class TopologyResponse(BaseModel):
    """Response for topology endpoint."""
    timestamp: str
    overall_status: str
    health_score: float
    nodes: List[Dict[str, Any]]
    drift_count: int
    baseline_version: Optional[str]


class DriftResponse(BaseModel):
    """Response for drift findings endpoint."""
    timestamp: str
    total_findings: int
    critical: List[Dict[str, Any]]
    warning: List[Dict[str, Any]]
    info: List[Dict[str, Any]]


class BaselineResponse(BaseModel):
    """Response for baseline info endpoint."""
    loaded: bool
    version: Optional[str]
    created_at: Optional[str]
    path: str
    summary: Optional[Dict[str, Any]]


class FreezeBaselineRequest(BaseModel):
    """Request to freeze a new baseline."""
    version: str = Field(..., description="Version tag for the new baseline")
    reason: str = Field(default="", description="Reason for freezing")


class FreezeBaselineResponse(BaseModel):
    """Response for freeze baseline endpoint."""
    success: bool
    version: str
    path: str
    message: str


# ============================================================================
# Admin Check Dependency
# ============================================================================

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin user for sensitive operations."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/status", response_model=IntegrityStatusResponse)
async def get_integrity_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get full SmartFlow integrity status.

    Returns overall health score, component statuses, and drift summary.
    """
    try:
        report = integrity_monitor.run_full_check(db)

        critical_count = sum(
            1 for d in report.drift_findings
            if d.severity.value == 'critical'
        )

        return IntegrityStatusResponse(
            timestamp=report.timestamp.isoformat(),
            overall_status=report.overall_status.value,
            health_score=report.health_score,
            category_scores=report.category_scores,
            components=[to_dict(c) for c in report.components],
            drift_count=len(report.drift_findings),
            critical_drift_count=critical_count,
            baseline_version=report.baseline_version,
            notes=report.notes
        )
    except Exception as e:
        logger.error(f"Integrity check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Integrity check failed: {str(e)}"
        )


@router.get("/topology", response_model=TopologyResponse)
async def get_topology(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get SmartFlow runtime topology for visualization.

    Returns nodes representing pipeline stages with their status.
    """
    try:
        topology = integrity_monitor.get_topology(db)

        return TopologyResponse(
            timestamp=topology['timestamp'],
            overall_status=topology['overall_status'],
            health_score=topology['health_score'],
            nodes=topology['nodes'],
            drift_count=topology['drift_count'],
            baseline_version=topology['baseline_version']
        )
    except Exception as e:
        logger.error(f"Topology check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Topology check failed: {str(e)}"
        )


@router.get("/drift", response_model=DriftResponse)
async def get_drift_findings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current drift findings grouped by severity.
    """
    try:
        report = integrity_monitor.run_full_check(db)

        findings = report.drift_findings
        critical = [to_dict(f) for f in findings if f.severity.value == 'critical']
        warning = [to_dict(f) for f in findings if f.severity.value == 'warning']
        info = [to_dict(f) for f in findings if f.severity.value == 'info']

        return DriftResponse(
            timestamp=report.timestamp.isoformat(),
            total_findings=len(findings),
            critical=critical,
            warning=warning,
            info=info
        )
    except Exception as e:
        logger.error(f"Drift check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Drift check failed: {str(e)}"
        )


@router.get("/baseline", response_model=BaselineResponse)
async def get_baseline_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get information about the current golden baseline.
    """
    baseline = integrity_monitor.get_baseline()

    if baseline:
        summary = {
            "code_identity": baseline.get("code_identity", {}),
            "alembic_version": baseline.get("database_schema", {}).get("alembic_version"),
            "strategy_count": len(baseline.get("strategy_registry", {}).get("strategies", [])),
            "runtime_stages": len(baseline.get("runtime_chain", {}).get("stages", [])),
            "validation_status": baseline.get("validation_status", {})
        }

        return BaselineResponse(
            loaded=True,
            version=baseline.get("baseline_version"),
            created_at=baseline.get("created_at"),
            path=integrity_monitor.baseline_path,
            summary=summary
        )
    else:
        return BaselineResponse(
            loaded=False,
            version=None,
            created_at=None,
            path=integrity_monitor.baseline_path,
            summary=None
        )


@router.post("/freeze-baseline", response_model=FreezeBaselineResponse)
async def freeze_baseline(
    request: FreezeBaselineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create a new golden baseline from current system state.

    Admin only. Captures current code identity, database state,
    strategy registry, and runtime configuration.
    """
    try:
        from sqlalchemy import text

        # Build new baseline
        baseline = {
            "baseline_version": request.version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": current_user.email,
            "freeze_reason": request.reason or "Manual freeze",
        }

        # Code identity (placeholder - actual git info from env/build)
        baseline["code_identity"] = {
            "git_commit": os.getenv("GIT_COMMIT", "unknown"),
            "app_version": os.getenv("APP_VERSION", "1.2.1"),
            "image_tag": os.getenv("IMAGE_TAG", "latest"),
        }

        # Database schema
        result = db.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        alembic_version = result[0] if result else "unknown"

        # Get table list
        tables_result = db.execute(text("""
            SELECT tablename FROM pg_tables
            WHERE schemaname='public'
            AND tablename SIMILAR TO '(smartflow|strategy)%'
            ORDER BY tablename
        """)).fetchall()

        baseline["database_schema"] = {
            "alembic_version": alembic_version,
            "smartflow_tables": [r[0] for r in tables_result if r[0].startswith('smartflow')],
            "strategy_tables": [r[0] for r in tables_result if r[0].startswith('strategy')],
        }

        # Strategy registry
        strategies_result = db.execute(text("""
            SELECT strategy_id, strategy_type, status, health_status,
                   sharpe_ratio, win_rate, is_paused
            FROM smartflow_strategies
        """)).fetchall()

        baseline["strategy_registry"] = {
            "strategies": [
                {
                    "strategy_id": r[0],
                    "strategy_type": r[1],
                    "status": r[2],
                    "health_status": r[3],
                    "sharpe_ratio": r[4],
                    "win_rate": r[5],
                    "is_paused": r[6]
                }
                for r in strategies_result
            ]
        }

        # Runtime chain (from existing baseline or default)
        existing = integrity_monitor.get_baseline()
        if existing and "runtime_chain" in existing:
            baseline["runtime_chain"] = existing["runtime_chain"]

        # Save baseline
        os.makedirs(BASELINE_DIR, exist_ok=True)
        filename = f"SMARTFLOW_GOLDEN_BASELINE_{request.version}.json"
        filepath = os.path.join(BASELINE_DIR, filename)

        with open(filepath, 'w') as f:
            json.dump(baseline, f, indent=2, default=str)

        # Reload monitor
        integrity_monitor._baseline = baseline
        integrity_monitor.baseline_path = filepath

        logger.info(f"Baseline frozen: {filename} by {current_user.email}")

        return FreezeBaselineResponse(
            success=True,
            version=request.version,
            path=filepath,
            message=f"Baseline {request.version} created successfully"
        )

    except Exception as e:
        logger.error(f"Failed to freeze baseline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to freeze baseline: {str(e)}"
        )


@router.post("/run-check")
async def run_integrity_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Force a fresh integrity check.

    Returns full report including all components and drift findings.
    """
    try:
        report = integrity_monitor.run_full_check(db)
        return to_dict(report)
    except Exception as e:
        logger.error(f"Integrity check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Integrity check failed: {str(e)}"
        )
