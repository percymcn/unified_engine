"""
Admin Router for Owner-Only Admin Dashboard
Protected by email allowlist and authentication
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import os

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User
from app.core.config import settings
from app.services.stripe_service import PRICING_TIERS, get_all_tiers

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def redact_secret(value: Optional[str]) -> str:
    """Redact secret value (show first 6 + last 4 chars)"""
    if not value:
        return "(empty)"
    if len(value) <= 10:
        return "***REDACTED***"
    return f"{value[:6]}...{value[-4:]}"


def check_broker_config(broker_name: str, required_vars: List[str]) -> Dict[str, Any]:
    """Check broker configuration status"""
    missing = []
    present = []
    values = {}
    
    for var in required_vars:
        value = getattr(settings, var, None) or os.getenv(var)
        if not value or value in ("", "None", f"your-{var.lower()}"):
            missing.append(var)
        else:
            present.append(var)
            values[var] = redact_secret(str(value))
    
    if len(missing) == len(required_vars):
        status = "DISABLED"
    elif len(missing) == 0:
        status = "CONFIGURED"
    else:
        status = "PARTIAL"
    
    return {
        "status": status,
        "missing_vars": missing,
        "present_vars": present,
        "values": values
    }

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/overview")
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get admin dashboard overview (owner-only)"""
    check_owner_access(current_user)
    
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    verified_users = db.query(User).filter(User.is_verified == True).count()
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "verified": verified_users,
        },
        "plans_configured": len(PRICING_TIERS),
        "stripe_configured": bool(settings.STRIPE_SECRET_KEY),
    }


def check_owner_access(current_user: User) -> None:
    """Check if user is in owner admin allowlist"""
    owner_emails = settings.OWNER_ADMIN_EMAILS
    if not owner_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access not configured"
        )
    
    allowed_emails = [email.strip().lower() for email in owner_emails.split(",") if email.strip()]
    if current_user.email.lower() not in allowed_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Owner-only area."
        )


class UserInfo(BaseModel):
    id: int
    email: str
    username: str
    full_name: str | None
    subscription_tier: str
    subscription_status: str | None
    is_active: bool
    is_verified: bool
    created_at: str
    last_login: str | None


class PlanConfig(BaseModel):
    tier_id: str
    name: str
    monthly_price: int
    price_display: str
    brokers: int
    stripe_price_id: str | None
    features: List[str]


@router.get("/users")
async def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> Dict[str, Any]:
    """List all users (owner-only)"""
    check_owner_access(current_user)
    
    users = db.query(User).offset(skip).limit(limit).all()
    total = db.query(User).count()
    
    return {
        "users": [
            UserInfo(
                id=u.id,
                email=u.email,
                username=u.username,
                full_name=u.full_name,
                subscription_tier=u.subscription_tier.value if hasattr(u.subscription_tier, 'value') else (u.subscription_tier or "free"),
                subscription_status=u.subscription_status,
                is_active=u.is_active,
                is_verified=u.is_verified,
                created_at=u.created_at.isoformat() if u.created_at else "",
                last_login=u.last_login.isoformat() if u.last_login else None,
            ).model_dump()
            for u in users
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserInfo:
    """Get user details (owner-only)"""
    check_owner_access(current_user)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserInfo(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        subscription_tier=user.subscription_tier.value if hasattr(user.subscription_tier, 'value') else (user.subscription_tier or "free"),
        subscription_status=user.subscription_status,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat() if user.created_at else "",
        last_login=user.last_login.isoformat() if user.last_login else None,
    )


@router.patch("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Toggle user active status (owner-only)"""
    check_owner_access(current_user)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "message": f"User {'activated' if user.is_active else 'deactivated'}"
    }


@router.patch("/users/{user_id}/set-tier")
async def set_user_tier(
    user_id: int,
    tier: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Set user subscription tier (owner-only)"""
    check_owner_access(current_user)
    
    from app.models.enhanced_models import SubscriptionTier
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        tier_enum = SubscriptionTier(tier)
        user.subscription_tier = tier_enum
        db.commit()
        db.refresh(user)
        
        return {
            "id": user.id,
            "email": user.email,
            "subscription_tier": tier,
            "message": f"User tier set to {tier}"
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}")


@router.post("/users/{user_id}/reset-password-link")
async def generate_reset_password_link(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Generate password reset link for user (owner-only)"""
    check_owner_access(current_user)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate reset token (simplified - in production, use proper token generation)
    from app.routers.auth import create_access_token
    from datetime import timedelta
    
    reset_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "type": "password_reset"},
        expires_delta=timedelta(hours=24)
    )
    
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    
    return {
        "user_id": user.id,
        "email": user.email,
        "reset_url": reset_url,
        "message": "Password reset link generated (valid for 24 hours)"
    }


@router.get("/plans")
async def get_plan_config(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get pricing plan configuration (owner-only)"""
    check_owner_access(current_user)
    
    tiers = get_all_tiers()
    
    plans = []
    for tier in tiers:
        tier_id = tier.get("tier_id", "free")
        plans.append(PlanConfig(
            tier_id=tier_id,
            name=tier["name"],
            monthly_price=tier["price"],
            price_display=f"${tier['price']/100:.2f}/month",
            brokers=tier["brokers"],
            stripe_price_id=tier.get("stripe_price_id"),
            features=tier["features"],
        ).model_dump())
    
    return {
        "plans": plans,
        "source": "backend PRICING_TIERS",
        "stripe_configured": bool(settings.STRIPE_SECRET_KEY),
    }


@router.get("/system/env-doctor")
async def get_env_doctor(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get ENV doctor diagnostics (owner-only)"""
    check_owner_access(current_user)
    
    # Check database
    db_info = {}
    if settings.DATABASE_URL:
        if "sqlite" in settings.DATABASE_URL.lower():
            db_file = settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
            import os
            if os.path.exists(db_file):
                import os.path
                size = os.path.getsize(db_file)
                db_info = {
                    "type": "SQLite",
                    "path": db_file,
                    "size_bytes": size,
                    "exists": True
                }
            else:
                db_info = {
                    "type": "SQLite",
                    "path": db_file,
                    "exists": False
                }
        else:
            # PostgreSQL
            db_info = {
                "type": "PostgreSQL",
                "url": settings.DATABASE_URL.split("@")[-1].split("/")[0] if "@" in settings.DATABASE_URL else "unknown",
                "exists": True
            }
    
    # Check brokers
    brokers = {}
    
    # MT4/MT5 MetaAPI SDK
    brokers["mt4_sdk"] = check_broker_config("mt4_sdk", ["METAAPI_TOKEN", "METAAPI_ACCOUNT_ID"])
    brokers["mt4_manager"] = check_broker_config("mt4_manager", [
        "MT4_MANAGER_LOGIN", "MT4_MANAGER_PASSWORD", "MT4_MANAGER_HOST", "MT4_MANAGER_PORT"
    ])
    brokers["mt5_sdk"] = check_broker_config("mt5_sdk", ["METAAPI_TOKEN", "METAAPI_ACCOUNT_ID"])
    brokers["mt5_manager"] = check_broker_config("mt5_manager", [
        "MT5_MANAGER_LOGIN", "MT5_MANAGER_PASSWORD", "MT5_MANAGER_HOST", "MT5_MANAGER_PORT"
    ])
    
    # TradeLocker
    brokers["tradelocker_sdk"] = check_broker_config("tradelocker_sdk", [
        "TRADELOCKER_USERNAME", "TRADELOCKER_PASSWORD", "TRADELOCKER_SERVER"
    ])
    brokers["tradelocker_brand"] = check_broker_config("tradelocker_brand", ["TRADELOCKER_API_KEY"])
    
    # Tradovate
    brokers["tradovate_oauth"] = check_broker_config("tradovate_oauth", [
        "TRADOVATE_CLIENT_ID", "TRADOVATE_CLIENT_SECRET"
    ])
    brokers["tradovate_password"] = check_broker_config("tradovate_password", [
        "TRADOVATE_USER_ID", "TRADOVATE_PASSWORD"
    ])
    
    # ProjectX
    brokers["projectx_sdk"] = check_broker_config("projectx_sdk", [
        "PROJECT_X_USERNAME", "PROJECT_X_API_KEY"
    ])
    brokers["projectx_legacy"] = check_broker_config("projectx_legacy", ["PROJECTX_API_TOKEN"])
    
    # OAuth
    oauth_status = {
        "google": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_ID != "your-google-client-id"),
        "github": bool(settings.GITHUB_CLIENT_ID),
        "microsoft": bool(settings.MICROSOFT_CLIENT_ID)
    }
    
    return {
        "database": db_info,
        "brokers": brokers,
        "oauth": oauth_status,
        "backend_port": settings.PORT,
        "backend_host": settings.HOST
    }


@router.get("/system/pipeline-status")
async def get_pipeline_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get full system pipeline status - see the veins of the system (owner-only)"""
    check_owner_access(current_user)

    import asyncio
    import aiohttp
    from datetime import datetime, timedelta
    from app.models.models import Signal, Trade
    from app.models.database_models import TradingAccount, WebhookConfig

    # Pipeline components status
    components = {}

    # 1. Database status
    try:
        user_count = db.query(User).count()
        components["database"] = {
            "status": "healthy",
            "latency_ms": 5,  # Simplified
            "connections": user_count > 0,
            "message": f"PostgreSQL online, {user_count} users"
        }
    except Exception as e:
        components["database"] = {
            "status": "error",
            "latency_ms": -1,
            "message": str(e)
        }

    # 2. Redis status
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL or "redis://localhost:6379/0")
        r.ping()
        components["redis"] = {
            "status": "healthy",
            "latency_ms": 2,
            "message": "Redis connected"
        }
    except Exception as e:
        components["redis"] = {
            "status": "warning",
            "latency_ms": -1,
            "message": f"Redis unavailable: {str(e)[:50]}"
        }

    # 3. Webhook ingestion
    try:
        active_webhooks = db.query(WebhookConfig).filter(WebhookConfig.is_active == True).count()
        recent_signals = db.query(Signal).filter(
            Signal.created_at >= datetime.utcnow() - timedelta(hours=1)
        ).count()
        components["webhook_ingestion"] = {
            "status": "healthy" if active_webhooks > 0 else "idle",
            "active_webhooks": active_webhooks,
            "signals_last_hour": recent_signals,
            "message": f"{active_webhooks} active webhooks, {recent_signals} signals/hr"
        }
    except Exception as e:
        components["webhook_ingestion"] = {
            "status": "error",
            "message": str(e)[:50]
        }

    # 4. Signal processing
    try:
        from sqlalchemy import func
        pending_signals = db.query(Signal).filter(Signal.status == "pending").count()
        processed_24h = db.query(Signal).filter(
            Signal.processed_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        components["signal_processor"] = {
            "status": "healthy" if pending_signals < 10 else "busy",
            "pending": pending_signals,
            "processed_24h": processed_24h,
            "message": f"{pending_signals} pending, {processed_24h} processed today"
        }
    except Exception as e:
        components["signal_processor"] = {
            "status": "warning",
            "message": str(e)[:50]
        }

    # 5. Broker connections
    broker_stats = {}
    try:
        accounts = db.query(TradingAccount).filter(TradingAccount.is_active == True).all()
        for account in accounts:
            broker = account.broker.value if account.broker else "unknown"
            if broker not in broker_stats:
                broker_stats[broker] = {"count": 0, "accounts": []}
            broker_stats[broker]["count"] += 1
            broker_stats[broker]["accounts"].append(account.account_number or account.account_name or str(account.id))

        components["broker_connections"] = {
            "status": "healthy" if len(accounts) > 0 else "idle",
            "active_accounts": len(accounts),
            "brokers": broker_stats,
            "message": f"{len(accounts)} active accounts across {len(broker_stats)} brokers"
        }
    except Exception as e:
        components["broker_connections"] = {
            "status": "error",
            "message": str(e)[:50]
        }

    # 6. Trade execution
    try:
        trades_24h = db.query(Trade).filter(
            Trade.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        failed_trades = db.query(Trade).filter(
            Trade.status == "failed",
            Trade.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        components["trade_execution"] = {
            "status": "healthy" if failed_trades == 0 else "warning",
            "trades_24h": trades_24h,
            "failed_24h": failed_trades,
            "success_rate": f"{((trades_24h - failed_trades) / max(trades_24h, 1)) * 100:.1f}%" if trades_24h > 0 else "N/A",
            "message": f"{trades_24h} trades, {failed_trades} failed"
        }
    except Exception as e:
        components["trade_execution"] = {
            "status": "warning",
            "message": str(e)[:50]
        }

    # 7. Recent activity feed
    recent_activity = []
    try:
        recent_signals_list = db.query(Signal).order_by(Signal.received_at.desc()).limit(5).all()
        for sig in recent_signals_list:
            recent_activity.append({
                "type": "signal",
                "action": sig.action,
                "symbol": sig.symbol,
                "status": sig.status,
                "time": sig.received_at.isoformat() if sig.received_at else None
            })

        recent_trades_list = db.query(Trade).order_by(Trade.created_at.desc()).limit(5).all()
        for trade in recent_trades_list:
            recent_activity.append({
                "type": "trade",
                "action": trade.action,
                "symbol": trade.symbol,
                "status": trade.status,
                "time": trade.created_at.isoformat() if trade.created_at else None
            })

        # Sort by time
        recent_activity.sort(key=lambda x: x.get("time") or "", reverse=True)
        recent_activity = recent_activity[:10]
    except Exception as e:
        recent_activity = [{"error": str(e)[:50]}]

    # Calculate overall health
    statuses = [c.get("status", "unknown") for c in components.values()]
    if "error" in statuses:
        overall = "degraded"
    elif "warning" in statuses:
        overall = "warning"
    else:
        overall = "healthy"

    return {
        "overall_health": overall,
        "timestamp": datetime.utcnow().isoformat(),
        "components": components,
        "recent_activity": recent_activity,
        "pipeline_flow": [
            {"id": "webhook", "name": "Webhook Ingestion", "connects_to": "signal_processor"},
            {"id": "signal_processor", "name": "Signal Processor", "connects_to": "broker_connections"},
            {"id": "broker_connections", "name": "Broker Connections", "connects_to": "trade_execution"},
            {"id": "trade_execution", "name": "Trade Execution", "connects_to": "database"},
            {"id": "database", "name": "Database", "connects_to": None},
            {"id": "redis", "name": "Redis Cache", "connects_to": "signal_processor"},
        ]
    }
