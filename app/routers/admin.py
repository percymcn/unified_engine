"""
Admin Router for Owner-Only Admin Dashboard
Protected by email allowlist and authentication
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Body
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


class SetTierRequest(BaseModel):
    tier: str

@router.patch("/users/{user_id}/set-tier")
async def set_user_tier(
    user_id: int,
    request: SetTierRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Set user subscription tier (owner-only)"""
    check_owner_access(current_user)

    # Valid tiers: free, starter/tier_1, trader/tier_2, pro/tier_3, enterprise/tier_4
    VALID_TIERS = {"free", "starter", "trader", "pro", "enterprise", "tier_1", "tier_2", "tier_3", "tier_4"}

    tier = request.tier.lower()
    if tier not in VALID_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {request.tier}. Valid tiers: {', '.join(sorted(VALID_TIERS))}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.subscription_tier = tier
    db.commit()
    db.refresh(user)

    logger.info(f"Admin {current_user.id} set user {user_id} tier to {tier}")

    return {
        "id": user.id,
        "email": user.email,
        "subscription_tier": tier,
        "message": f"User tier set to {tier}"
    }


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


@router.get("/system/connected-accounts")
async def get_connected_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get all connected accounts grouped by broker type (owner-only)"""
    check_owner_access(current_user)

    from app.models.database_models import TradingAccount
    from collections import defaultdict

    accounts = db.query(TradingAccount).all()

    # Group by broker type
    broker_groups = defaultdict(list)
    for account in accounts:
        broker_name = account.broker.value if account.broker else "unknown"
        user = db.query(User).filter(User.id == account.user_id).first()
        broker_groups[broker_name].append({
            "id": account.id,
            "account_number": account.account_number,
            "account_name": account.account_name,
            "user_id": account.user_id,
            "user_email": user.email if user else "Unknown",
            "is_active": account.is_active,
            "is_connected": account.is_connected,
            "balance": float(account.balance) if account.balance else 0,
            "equity": float(account.equity) if account.equity else 0,
            "created_at": account.created_at.isoformat() if account.created_at else None,
            "last_sync": account.last_sync.isoformat() if account.last_sync else None,
        })

    # Summary stats
    total_accounts = len(accounts)
    active_accounts = sum(1 for a in accounts if a.is_active)
    connected_accounts = sum(1 for a in accounts if a.is_connected)

    return {
        "summary": {
            "total": total_accounts,
            "active": active_accounts,
            "connected": connected_accounts,
        },
        "brokers": {
            broker: {
                "count": len(accts),
                "active": sum(1 for a in accts if a["is_active"]),
                "connected": sum(1 for a in accts if a["is_connected"]),
                "accounts": accts,
            }
            for broker, accts in broker_groups.items()
        }
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
            "status": "healthy" if pending_signals < 50 else "busy",
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
        recent_signals_list = db.query(Signal).order_by(Signal.created_at.desc()).limit(5).all()
        for sig in recent_signals_list:
            recent_activity.append({
                "type": "signal",
                "action": sig.action,
                "symbol": sig.symbol,
                "status": sig.status,
                "time": sig.created_at.isoformat() if sig.created_at else None
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


# =============================================================================
# System Configuration Management (Database-backed settings)
# =============================================================================

class ConfigCreate(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    is_secret: bool = False


class ConfigUpdate(BaseModel):
    value: str
    description: Optional[str] = None


# Config categories for organization
CONFIG_CATEGORIES = {
    "stripe": {
        "name": "Stripe Payment",
        "icon": "credit-card",
        "keys": ["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PRO_PRICE_ID"]
    },
    "database": {
        "name": "Database",
        "icon": "database",
        "keys": ["DATABASE_URL", "DATABASE_POOL_SIZE"]
    },
    "redis": {
        "name": "Redis Cache",
        "icon": "zap",
        "keys": ["REDIS_URL"]
    },
    "auth": {
        "name": "Authentication",
        "icon": "shield",
        "keys": ["JWT_SECRET_KEY", "JWT_ALGORITHM", "ACCESS_TOKEN_EXPIRE_MINUTES"]
    },
    "oauth": {
        "name": "OAuth Providers",
        "icon": "key",
        "keys": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"]
    },
    "email": {
        "name": "Email Service",
        "icon": "mail",
        "keys": ["SENDGRID_API_KEY", "EMAIL_FROM_ADDRESS"]
    },
    "brokers": {
        "name": "Broker APIs",
        "icon": "server",
        "keys": ["METAAPI_TOKEN", "TRADELOCKER_CLIENT_ID", "TRADELOCKER_CLIENT_SECRET", "TRADOVATE_APP_ID"]
    },
}

# Keys that should never be fully revealed
SECRET_KEYS = {
    "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET",
    "JWT_SECRET_KEY", "DATABASE_URL",
    "GOOGLE_CLIENT_SECRET", "GITHUB_CLIENT_SECRET", "MICROSOFT_CLIENT_SECRET",
    "SENDGRID_API_KEY", "METAAPI_TOKEN",
    "TRADELOCKER_CLIENT_SECRET", "TRADOVATE_APP_SECRET",
}


@router.get("/system/configs")
async def list_system_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """List all system configurations from database"""
    check_owner_access(current_user)

    from app.models.models import SystemConfig

    configs = db.query(SystemConfig).filter(SystemConfig.is_active == True).all()

    return {
        "configs": [
            {
                "id": c.id,
                "key": c.key,
                "value": redact_secret(c.value) if c.key in SECRET_KEYS else c.value,
                "description": c.description,
                "is_secret": c.key in SECRET_KEYS,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in configs
        ]
    }


@router.post("/system/configs")
async def create_system_config(
    config: ConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new system configuration"""
    check_owner_access(current_user)

    from app.models.models import SystemConfig

    # Check if key already exists
    existing = db.query(SystemConfig).filter(SystemConfig.key == config.key).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Config key '{config.key}' already exists"
        )

    new_config = SystemConfig(
        key=config.key,
        value=config.value,
        description=config.description,
        is_active=True,
    )
    db.add(new_config)
    db.commit()
    db.refresh(new_config)

    return {
        "message": "Config created successfully",
        "config": {
            "id": new_config.id,
            "key": new_config.key,
            "value": redact_secret(new_config.value) if config.is_secret else new_config.value,
        }
    }


@router.put("/system/configs/{key}")
async def update_system_config(
    key: str,
    config: ConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update a system configuration"""
    check_owner_access(current_user)

    from app.models.models import SystemConfig

    existing = db.query(SystemConfig).filter(SystemConfig.key == key).first()

    if existing:
        existing.value = config.value
        if config.description is not None:
            existing.description = config.description
        db.commit()
        db.refresh(existing)
    else:
        # Create new if doesn't exist
        new_config = SystemConfig(
            key=key,
            value=config.value,
            description=config.description,
            is_active=True,
        )
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        existing = new_config

    return {
        "message": "Config updated successfully",
        "config": {
            "id": existing.id,
            "key": existing.key,
            "value": redact_secret(existing.value) if key in SECRET_KEYS else existing.value,
        }
    }


@router.delete("/system/configs/{key}")
async def delete_system_config(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Delete a system configuration"""
    check_owner_access(current_user)

    from app.models.models import SystemConfig

    existing = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config key '{key}' not found"
        )

    db.delete(existing)
    db.commit()

    return {"message": f"Config '{key}' deleted successfully"}


@router.get("/system/all-env-vars")
async def get_all_env_vars(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get all environment variables organized by category"""
    check_owner_access(current_user)

    from app.models.models import SystemConfig

    # Get database overrides
    db_configs = db.query(SystemConfig).filter(SystemConfig.is_active == True).all()
    db_overrides = {c.key: c.value for c in db_configs}

    result = {}
    for category_id, category_info in CONFIG_CATEGORIES.items():
        variables = {}
        for key in category_info["keys"]:
            # Check database first, then env, then settings
            db_value = db_overrides.get(key)
            env_value = os.getenv(key)
            settings_value = getattr(settings, key, None)

            actual_value = db_value or env_value or settings_value
            source = "database" if db_value else ("env" if env_value else ("settings" if settings_value else "not_set"))

            is_secret = key in SECRET_KEYS
            display_value = "[NOT SET]" if not actual_value else (
                redact_secret(str(actual_value)) if is_secret else str(actual_value)
            )

            variables[key] = {
                "value": display_value,
                "source": source,
                "configured": bool(actual_value),
                "is_secret": is_secret,
            }

        result[category_id] = {
            "name": category_info["name"],
            "icon": category_info["icon"],
            "variables": variables,
        }

    return {
        "categories": result,
    }


@router.post("/system/restart")
async def restart_backend(
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Trigger a graceful backend restart.
    The server will restart after responding to this request.
    """
    check_owner_access(current_user)

    import subprocess
    import sys

    def do_restart():
        import time
        time.sleep(1)  # Give time for response to be sent
        # Restart the uvicorn process
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765"],
            start_new_session=True
        )
        os._exit(0)  # Exit current process

    if background_tasks:
        background_tasks.add_task(do_restart)
    else:
        import threading
        threading.Thread(target=do_restart, daemon=True).start()

    return {
        "message": "Backend restart initiated. Please wait a few seconds and refresh.",
        "status": "restarting"
    }


@router.get("/system/logs")
async def get_system_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    log_type: str = "all",  # all, signals, trades, webhooks, errors
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """Get system logs - signals, trades, webhook activity (owner-only)"""
    check_owner_access(current_user)

    from datetime import datetime, timedelta
    from app.models.models import Signal, Trade
    from app.models.database_models import WebhookConfig

    logs = []

    try:
        # Get recent signals
        if log_type in ["all", "signals"]:
            signals = db.query(Signal).order_by(Signal.created_at.desc()).offset(offset).limit(limit).all()
            for sig in signals:
                user = db.query(User).filter(User.id == sig.user_id).first() if sig.user_id else None
                logs.append({
                    "id": sig.id,
                    "type": "signal",
                    "timestamp": sig.created_at.isoformat() if sig.created_at else None,
                    "user_email": user.email if user else "System",
                    "action": sig.action,
                    "symbol": sig.symbol,
                    "status": sig.status,
                    "message": sig.message or f"Signal {sig.action} {sig.symbol}",
                    "details": {
                        "quantity": sig.quantity,
                        "strategy": sig.strategy_id,
                        "source": sig.source,
                    }
                })

        # Get recent trades
        if log_type in ["all", "trades"]:
            trades = db.query(Trade).order_by(Trade.created_at.desc()).offset(offset).limit(limit).all()
            for trade in trades:
                user = db.query(User).filter(User.id == trade.user_id).first() if trade.user_id else None
                logs.append({
                    "id": trade.id,
                    "type": "trade",
                    "timestamp": trade.created_at.isoformat() if trade.created_at else None,
                    "user_email": user.email if user else "System",
                    "action": trade.action,
                    "symbol": trade.symbol,
                    "status": trade.status,
                    "message": f"Trade {trade.action} {trade.symbol} @ {trade.price}" if trade.price else f"Trade {trade.action} {trade.symbol}",
                    "details": {
                        "quantity": trade.quantity,
                        "price": float(trade.price) if trade.price else None,
                        "pnl": float(trade.pnl) if trade.pnl else None,
                        "broker": trade.broker_type.value if trade.broker_type else None,
                    }
                })

        # Get webhook configs activity
        if log_type in ["all", "webhooks"]:
            webhooks = db.query(WebhookConfig).order_by(WebhookConfig.updated_at.desc()).offset(offset).limit(limit).all()
            for wh in webhooks:
                user = db.query(User).filter(User.id == wh.user_id).first() if wh.user_id else None
                logs.append({
                    "id": wh.id,
                    "type": "webhook",
                    "timestamp": wh.updated_at.isoformat() if wh.updated_at else (wh.created_at.isoformat() if wh.created_at else None),
                    "user_email": user.email if user else "System",
                    "action": "active" if wh.is_active else "inactive",
                    "symbol": wh.symbol_filter or "All",
                    "status": "active" if wh.is_active else "inactive",
                    "message": f"Webhook config '{wh.name}' - {wh.symbol_filter or 'all symbols'}",
                    "details": {
                        "name": wh.name,
                        "broker_type": wh.broker_type.value if wh.broker_type else None,
                        "is_active": wh.is_active,
                    }
                })

        # Sort all logs by timestamp descending
        logs.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
        logs = logs[:limit]

    except Exception as e:
        return {
            "logs": [],
            "total": 0,
            "error": str(e)[:100],
        }

    return {
        "logs": logs,
        "total": len(logs),
        "limit": limit,
        "offset": offset,
        "log_type": log_type,
    }


@router.get("/users/{user_id}/logs")
async def get_user_logs(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
) -> Dict[str, Any]:
    """Get logs for a specific user (owner-only)"""
    check_owner_access(current_user)

    from datetime import datetime
    from app.models.models import Signal, Trade

    # Get target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    logs = []

    try:
        # Get user's signals
        signals = db.query(Signal).filter(Signal.user_id == user_id).order_by(Signal.created_at.desc()).limit(limit).all()
        for sig in signals:
            logs.append({
                "id": sig.id,
                "type": "signal",
                "timestamp": sig.created_at.isoformat() if sig.created_at else None,
                "action": sig.action,
                "symbol": sig.symbol,
                "status": sig.status,
                "message": sig.message or f"Signal {sig.action} {sig.symbol}",
                "details": {
                    "quantity": sig.quantity,
                    "strategy": sig.strategy_id,
                    "source": sig.source,
                }
            })

        # Get user's trades
        trades = db.query(Trade).filter(Trade.user_id == user_id).order_by(Trade.created_at.desc()).limit(limit).all()
        for trade in trades:
            logs.append({
                "id": trade.id,
                "type": "trade",
                "timestamp": trade.created_at.isoformat() if trade.created_at else None,
                "action": trade.action,
                "symbol": trade.symbol,
                "status": trade.status,
                "message": f"Trade {trade.action} {trade.symbol} @ {trade.price}" if trade.price else f"Trade {trade.action} {trade.symbol}",
                "details": {
                    "quantity": trade.quantity,
                    "price": float(trade.price) if trade.price else None,
                    "pnl": float(trade.pnl) if trade.pnl else None,
                    "broker": trade.broker_type.value if trade.broker_type else None,
                }
            })

        # Sort all logs by timestamp descending
        logs.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
        logs = logs[:limit]

    except Exception as e:
        return {
            "user_id": user_id,
            "user_email": target_user.email,
            "logs": [],
            "total": 0,
            "error": str(e)[:100],
        }

    return {
        "user_id": user_id,
        "user_email": target_user.email,
        "logs": logs,
        "total": len(logs),
    }


@router.get("/system/webhook-retention")
async def get_webhook_retention_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get webhook log retention statistics (owner-only)"""
    check_owner_access(current_user)

    from app.services.webhook_retention_service import get_retention_stats

    try:
        stats = await get_retention_stats(db)
        return {
            "success": True,
            **stats
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/system/webhook-retention/cleanup")
async def trigger_webhook_cleanup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Manually trigger webhook log cleanup (owner-only)"""
    check_owner_access(current_user)

    from app.services.webhook_retention_service import cleanup_all_webhook_logs

    try:
        summary = await cleanup_all_webhook_logs(db)
        return {
            "success": True,
            "message": "Webhook log cleanup completed",
            **summary
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.put("/system/env-var/{key}")
async def update_env_var(
    key: str,
    body: ConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update an environment variable by storing in database.
    Note: Some changes may require server restart to take effect.
    """
    check_owner_access(current_user)

    from app.models.models import SystemConfig

    # Store/update in database
    existing = db.query(SystemConfig).filter(SystemConfig.key == key).first()

    if existing:
        existing.value = body.value
        if body.description:
            existing.description = body.description
    else:
        new_config = SystemConfig(
            key=key,
            value=body.value,
            description=body.description or f"Config for {key}",
            is_active=True,
        )
        db.add(new_config)

    db.commit()

    # Try to apply immediately for supported settings
    runtime_applied = False
    try:
        # For some settings, we can update at runtime
        if hasattr(settings, key):
            setattr(settings, key, body.value)
            runtime_applied = True
    except Exception:
        pass

    return {
        "message": f"Config '{key}' saved to database",
        "runtime_applied": runtime_applied,
        "requires_restart": not runtime_applied,
        "key": key,
        "value": redact_secret(body.value) if key in SECRET_KEYS else body.value,
    }


# ============================================================
# Admin Mass Broadcast (Email to all users)
# ============================================================

class BroadcastEmailRequest(BaseModel):
    """Request model for admin broadcast email"""
    subject: str
    message: str
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    tier_filter: Optional[str] = None  # Optional: only send to specific tier

    class Config:
        json_schema_extra = {
            "example": {
                "subject": "Scheduled Maintenance - Jan 30",
                "message": "We will be performing scheduled maintenance on January 30 from 2:00 AM to 4:00 AM UTC. Trading will be temporarily unavailable during this period.",
                "cta_text": "View Status Page",
                "cta_url": "https://status.mytradeflow.app",
            }
        }


@router.post("/broadcast/email")
async def send_broadcast_email(
    request: BroadcastEmailRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Send broadcast email to all users (owner-only).
    Use for maintenance announcements, feature updates, etc.
    """
    check_owner_access(current_user)

    from app.services.resend_email_service import send_broadcast_email as send_broadcast

    # Get all active users
    query = db.query(User).filter(User.is_active == True)

    # Filter by tier if specified
    if request.tier_filter:
        query = query.filter(User.subscription_tier == request.tier_filter)

    users = query.all()
    emails = [u.email for u in users if u.email]

    if not emails:
        return {
            "success": False,
            "message": "No active users found",
            "sent": 0,
            "failed": 0,
        }

    # Send broadcast
    results = await send_broadcast(
        to_emails=emails,
        subject=request.subject,
        message=request.message,
        cta_text=request.cta_text,
        cta_url=request.cta_url,
    )

    return {
        "success": True,
        "message": f"Broadcast sent to {results['sent']} users",
        "total_users": len(emails),
        "sent": results["sent"],
        "failed": results["failed"],
        "errors": results.get("errors", [])[:10],  # Limit errors in response
    }


@router.post("/broadcast/telegram")
async def send_broadcast_telegram(
    message: str = Body(..., embed=True),
    min_tier: str = Body("free", embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Send broadcast Telegram message to all users with Telegram enabled (owner-only).
    """
    check_owner_access(current_user)

    from app.services.telegram_service import broadcast_telegram_message
    from app.models.enhanced_models import NotificationPreference

    # Get all users with Telegram enabled
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.telegram_enabled == True,
        NotificationPreference.telegram_chat_id != None,
    ).all()

    if not prefs:
        return {
            "success": False,
            "message": "No users with Telegram enabled",
            "sent": 0,
            "failed": 0,
        }

    # Build chat_ids and user_tiers for tier gating
    chat_ids = []
    user_tiers = {}
    for pref in prefs:
        user = db.query(User).filter(User.id == pref.user_id).first()
        if user and user.is_active:
            chat_id = pref.telegram_chat_id
            chat_ids.append(chat_id)
            user_tiers[chat_id] = user.subscription_tier

    results = await broadcast_telegram_message(
        chat_ids=chat_ids,
        message=message,
        min_tier=min_tier,
        user_tiers=user_tiers,
    )

    return {
        "success": True,
        "message": f"Telegram broadcast sent to {results['sent']} users",
        "total_eligible": len(chat_ids),
        **results,
    }
