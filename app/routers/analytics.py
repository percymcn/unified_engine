"""
Analytics Dashboard Router
Provides aggregated metrics and statistics for admin/premium users
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case, and_, or_
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.core.rbac import require_permission, require_role
from app.models.models import User, Account, Trade, Signal, Position
from app.models.enhanced_models import (
    UserSubscription, SubscriptionTier, UsageMetric,
    Organization, AuditLog, Notification
)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

# Response models
class UserSignupStats(BaseModel):
    date: str
    count: int
    cumulative: int

class SubscriptionDistribution(BaseModel):
    tier: str
    count: int
    percentage: float

class RevenueStats(BaseModel):
    period: str
    revenue: float
    subscriptions: int
    churn: int

class APIUsageStats(BaseModel):
    period: str
    api_calls: int
    signals: int
    accounts: int

class OrganizationStats(BaseModel):
    total: int
    active: int
    by_tier: Dict[str, int]

class DashboardStats(BaseModel):
    total_users: int
    active_users: int
    total_organizations: int
    active_organizations: int
    total_subscriptions: int
    revenue_this_month: float
    api_calls_today: int
    signals_today: int

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(require_permission("admin:read")),
    db: Session = Depends(get_db)
):
    """Get overall dashboard statistics"""
    # Total users
    total_users = db.query(func.count(User.id)).scalar() or 0
    
    # Active users (logged in last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users = db.query(func.count(User.id)).filter(
        User.last_login >= thirty_days_ago
    ).scalar() or 0
    
    # Total organizations
    total_orgs = db.query(func.count(Organization.id)).scalar() or 0
    
    # Active organizations
    active_orgs = db.query(func.count(Organization.id)).filter(
        Organization.is_active == True
    ).scalar() or 0
    
    # Total subscriptions
    total_subs = db.query(func.count(UserSubscription.id)).filter(
        UserSubscription.status == "active"
    ).scalar() or 0
    
    # Revenue this month (mock - replace with actual Stripe data)
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
    premium_subs = db.query(func.count(UserSubscription.id)).filter(
        UserSubscription.tier == SubscriptionTier.PREMIUM,
        UserSubscription.status == "active",
        UserSubscription.start_date >= start_of_month
    ).scalar() or 0
    enterprise_subs = db.query(func.count(UserSubscription.id)).filter(
        UserSubscription.tier == SubscriptionTier.ENTERPRISE,
        UserSubscription.status == "active",
        UserSubscription.start_date >= start_of_month
    ).scalar() or 0
    revenue_this_month = (premium_subs * 29.0) + (enterprise_subs * 99.0)  # Mock pricing
    
    # API calls today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    api_calls_today = db.query(func.count(UsageMetric.id)).filter(
        UsageMetric.metric_type == "api_call",
        UsageMetric.date >= today_start
    ).scalar() or 0
    
    # Signals today
    signals_today = db.query(func.count(Signal.id)).filter(
        Signal.created_at >= today_start
    ).scalar() or 0
    
    return DashboardStats(
        total_users=total_users,
        active_users=active_users,
        total_organizations=total_orgs,
        active_organizations=active_orgs,
        total_subscriptions=total_subs,
        revenue_this_month=revenue_this_month,
        api_calls_today=api_calls_today,
        signals_today=signals_today
    )

@router.get("/user-signups", response_model=List[UserSignupStats])
async def get_user_signups(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(require_permission("admin:read")),
    db: Session = Depends(get_db)
):
    """Get user signup statistics over time"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get daily signups
    daily_signups = db.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date
    ).group_by(
        func.date(User.created_at)
    ).order_by(
        func.date(User.created_at)
    ).all()
    
    # Calculate cumulative
    result = []
    cumulative = 0
    for date, count in daily_signups:
        cumulative += count
        result.append(UserSignupStats(
            date=date.isoformat(),
            count=count,
            cumulative=cumulative
        ))
    
    return result

@router.get("/subscription-distribution", response_model=List[SubscriptionDistribution])
async def get_subscription_distribution(
    current_user: User = Depends(require_permission("admin:read")),
    db: Session = Depends(get_db)
):
    """Get subscription tier distribution"""
    total = db.query(func.count(UserSubscription.id)).filter(
        UserSubscription.status == "active"
    ).scalar() or 1
    
    tiers = db.query(
        UserSubscription.tier,
        func.count(UserSubscription.id).label('count')
    ).filter(
        UserSubscription.status == "active"
    ).group_by(
        UserSubscription.tier
    ).all()
    
    result = []
    for tier, count in tiers:
        result.append(SubscriptionDistribution(
            tier=tier.value if hasattr(tier, 'value') else str(tier),
            count=count,
            percentage=round((count / total) * 100, 2)
        ))
    
    return result

@router.get("/revenue", response_model=List[RevenueStats])
async def get_revenue_stats(
    period: str = Query("month", pattern="^(day|week|month)$"),
    months: int = Query(6, ge=1, le=12),
    current_user: User = Depends(require_permission("admin:read")),
    db: Session = Depends(get_db)
):
    """Get revenue statistics (mock data - replace with Stripe integration)"""
    result = []
    now = datetime.utcnow()
    
    for i in range(months):
        if period == "month":
            period_start = (now - timedelta(days=30 * (months - i))).replace(day=1, hour=0, minute=0, second=0)
            period_end = period_start + timedelta(days=30)
            period_label = period_start.strftime("%Y-%m")
        elif period == "week":
            period_start = now - timedelta(weeks=months - i)
            period_end = period_start + timedelta(weeks=1)
            period_label = period_start.strftime("%Y-W%W")
        else:  # day
            period_start = (now - timedelta(days=months - i)).replace(hour=0, minute=0, second=0)
            period_end = period_start + timedelta(days=1)
            period_label = period_start.strftime("%Y-%m-%d")
        
        # Count subscriptions
        premium_count = db.query(func.count(UserSubscription.id)).filter(
            UserSubscription.tier == SubscriptionTier.PREMIUM,
            UserSubscription.status == "active",
            UserSubscription.start_date >= period_start,
            UserSubscription.start_date < period_end
        ).scalar() or 0
        
        enterprise_count = db.query(func.count(UserSubscription.id)).filter(
            UserSubscription.tier == SubscriptionTier.ENTERPRISE,
            UserSubscription.status == "active",
            UserSubscription.start_date >= period_start,
            UserSubscription.start_date < period_end
        ).scalar() or 0
        
        # Mock revenue calculation
        revenue = (premium_count * 29.0) + (enterprise_count * 99.0)
        subscriptions = premium_count + enterprise_count
        
        # Mock churn (cancelled subscriptions)
        churn = db.query(func.count(UserSubscription.id)).filter(
            UserSubscription.status == "cancelled",
            UserSubscription.cancelled_at >= period_start,
            UserSubscription.cancelled_at < period_end
        ).scalar() or 0
        
        result.append(RevenueStats(
            period=period_label,
            revenue=revenue,
            subscriptions=subscriptions,
            churn=churn
        ))
    
    return result

@router.get("/api-usage", response_model=List[APIUsageStats])
async def get_api_usage_stats(
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(require_permission("admin:read")),
    db: Session = Depends(get_db)
):
    """Get API usage statistics"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Group by date
    daily_usage = db.query(
        func.date(UsageMetric.date).label('date'),
        func.sum(case((UsageMetric.metric_type == "api_call", UsageMetric.metric_value), else_=0)).label('api_calls'),
        func.sum(case((UsageMetric.metric_type == "signal", UsageMetric.metric_value), else_=0)).label('signals'),
        func.count(func.distinct(UsageMetric.user_id)).label('accounts')
    ).filter(
        UsageMetric.date >= start_date
    ).group_by(
        func.date(UsageMetric.date)
    ).order_by(
        func.date(UsageMetric.date)
    ).all()
    
    result = []
    for date, api_calls, signals, accounts in daily_usage:
        result.append(APIUsageStats(
            period=date.isoformat(),
            api_calls=int(api_calls or 0),
            signals=int(signals or 0),
            accounts=int(accounts or 0)
        ))
    
    return result

@router.get("/organizations", response_model=OrganizationStats)
async def get_organization_stats(
    current_user: User = Depends(require_permission("admin:read")),
    db: Session = Depends(get_db)
):
    """Get organization statistics"""
    total = db.query(func.count(Organization.id)).scalar() or 0
    active = db.query(func.count(Organization.id)).filter(
        Organization.is_active == True
    ).scalar() or 0
    
    # By tier
    by_tier = {}
    tier_counts = db.query(
        Organization.subscription_tier,
        func.count(Organization.id).label('count')
    ).group_by(
        Organization.subscription_tier
    ).all()
    
    for tier, count in tier_counts:
        tier_key = tier.value if hasattr(tier, 'value') else str(tier)
        by_tier[tier_key] = count
    
    return OrganizationStats(
        total=total,
        active=active,
        by_tier=by_tier
    )

@router.get("/usage-by-tier")
async def get_usage_by_tier(
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(require_permission("admin:read")),
    db: Session = Depends(get_db)
):
    """Get usage statistics grouped by subscription tier"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Join UsageMetric with UserSubscription to get tier
    usage_by_tier = db.query(
        UserSubscription.tier,
        func.sum(case((UsageMetric.metric_type == "api_call", UsageMetric.metric_value), else_=0)).label('api_calls'),
        func.sum(case((UsageMetric.metric_type == "signal", UsageMetric.metric_value), else_=0)).label('signals'),
        func.count(func.distinct(UsageMetric.user_id)).label('users')
    ).join(
        UsageMetric, UsageMetric.user_id == UserSubscription.user_id
    ).filter(
        UsageMetric.date >= start_date,
        UserSubscription.status == "active"
    ).group_by(
        UserSubscription.tier
    ).all()
    
    result = []
    for tier, api_calls, signals, users in usage_by_tier:
        result.append({
            "tier": tier.value if hasattr(tier, 'value') else str(tier),
            "api_calls": int(api_calls or 0),
            "signals": int(signals or 0),
            "users": int(users or 0)
        })
    
    return {"usage_by_tier": result}
