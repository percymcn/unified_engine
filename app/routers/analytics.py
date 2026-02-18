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
from app.models.models import User, Trade, Signal, Position
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


# ============================================================================
# TRADING PERFORMANCE ANALYTICS (User-level)
# ============================================================================

from app.models.database_models import (
    CircuitBreakerSettings as CBSettings,
    CircuitBreakerEvent as CBEvent,
    NewsFilterSettings as NFSettings,
    CorrelationFilterSettings as CFSettings,
    DynamicSizingSettings as DSSettings,
    StrategyPerformance,
    TimeBasedStats,
    TradeJournal,
)

# Import services
try:
    from app.services.trade_analytics_service import TradeAnalyticsService
    from app.services.news_filter_service import NewsFilterService
    from app.services.correlation_filter_service import CorrelationFilterService
    ANALYTICS_SERVICES_AVAILABLE = True
except ImportError:
    ANALYTICS_SERVICES_AVAILABLE = False


# Response models for trading analytics
class TradingPerformanceResponse(BaseModel):
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0
    gross_profit: float = 0
    gross_loss: float = 0
    net_profit: float = 0
    profit_factor: Optional[float] = None
    expectancy: float = 0
    max_drawdown: float = 0
    max_drawdown_pct: float = 0
    current_streak: int = 0
    best_hour: Optional[int] = None
    best_day: Optional[int] = None
    sharpe_ratio: Optional[float] = None


class TradeJournalResponse(BaseModel):
    id: int
    trade_uuid: str
    account_id: int
    symbol: str
    side: str
    quantity: float
    entry_price: float
    exit_price: Optional[float] = None
    entry_time: Optional[str] = None
    exit_time: Optional[str] = None
    net_pnl: Optional[float] = None
    is_winner: Optional[bool] = None
    status: str
    strategy_name: Optional[str] = None
    holding_time_seconds: Optional[int] = None


@router.get("/trading/performance", response_model=TradingPerformanceResponse)
async def get_trading_performance(
    strategy: Optional[str] = Query(None, description="Filter by strategy"),
    account_id: Optional[int] = Query(None, description="Filter by account"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get trading performance metrics for the current user."""
    if not ANALYTICS_SERVICES_AVAILABLE:
        raise HTTPException(status_code=503, detail="Analytics services not available")

    service = TradeAnalyticsService(db)
    metrics = service.calculate_performance_metrics(
        user_id=current_user.id,
        strategy_name=strategy,
        account_id=account_id
    )
    return TradingPerformanceResponse(**metrics)


@router.get("/trading/trades", response_model=List[TradeJournalResponse])
async def get_trade_journal(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="open or closed"),
    strategy: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get trade journal entries."""
    if not ANALYTICS_SERVICES_AVAILABLE:
        raise HTTPException(status_code=503, detail="Analytics services not available")

    service = TradeAnalyticsService(db)
    trades = service.get_trade_history(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        status=status,
        strategy=strategy,
        symbol=symbol
    )
    return trades


@router.get("/trading/strategies")
async def get_strategy_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get performance stats per strategy."""
    strategies = db.query(StrategyPerformance).filter(
        StrategyPerformance.user_id == current_user.id,
        StrategyPerformance.period_type == 'all_time'
    ).all()

    return [{
        'strategy_name': s.strategy_name,
        'total_trades': s.total_trades,
        'win_rate': s.win_rate,
        'net_profit': s.net_profit,
        'profit_factor': s.profit_factor,
        'expectancy': s.expectancy,
        'current_streak': s.current_streak,
        'is_active': s.is_active,
        'best_hour': s.best_hour,
        'best_day': s.best_day
    } for s in strategies]


@router.get("/trading/time-analysis")
async def get_time_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get performance by hour/day/session."""
    stats = db.query(TimeBasedStats).filter(
        TimeBasedStats.user_id == current_user.id
    ).all()

    hourly = []
    daily = []
    session = []

    for s in stats:
        entry = {
            'value': s.stat_value,
            'total_trades': s.total_trades,
            'win_rate': s.win_rate,
            'net_pnl': s.net_pnl,
            'is_recommended': s.is_recommended
        }

        if s.stat_type == 'hourly':
            hourly.append(entry)
        elif s.stat_type == 'daily':
            daily.append(entry)
        elif s.stat_type == 'session':
            session.append(entry)

    return {'hourly': hourly, 'daily': daily, 'session': session}


@router.get("/trading/circuit-breaker/status")
async def get_circuit_breaker_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check circuit breaker status."""
    if not ANALYTICS_SERVICES_AVAILABLE:
        return {'can_trade': True, 'block_reason': None, 'active_events': []}

    service = TradeAnalyticsService(db)
    can_trade, reason = service.check_circuit_breakers(current_user.id)

    active_events = db.query(CBEvent).filter(
        CBEvent.user_id == current_user.id,
        CBEvent.is_active == True
    ).all()

    return {
        'can_trade': can_trade,
        'block_reason': reason,
        'active_events': [{
            'trigger_type': e.trigger_type,
            'trigger_value': e.trigger_value,
            'triggered_at': e.triggered_at.isoformat() if e.triggered_at else None
        } for e in active_events]
    }


@router.get("/trading/circuit-breaker/settings")
async def get_circuit_breaker_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get circuit breaker settings."""
    settings = db.query(CBSettings).filter(
        CBSettings.user_id == current_user.id
    ).first()

    if not settings:
        settings = CBSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return {
        'daily_loss_limit_enabled': settings.daily_loss_limit_enabled,
        'daily_loss_limit_pct': settings.daily_loss_limit_pct,
        'weekly_loss_limit_enabled': settings.weekly_loss_limit_enabled,
        'weekly_loss_limit_pct': settings.weekly_loss_limit_pct,
        'max_drawdown_enabled': settings.max_drawdown_enabled,
        'max_drawdown_pct': settings.max_drawdown_pct,
        'consecutive_loss_enabled': settings.consecutive_loss_enabled,
        'max_consecutive_losses': settings.max_consecutive_losses,
        'auto_resume_enabled': settings.auto_resume_enabled,
        'auto_resume_after_hours': settings.auto_resume_after_hours
    }


@router.put("/trading/circuit-breaker/settings")
async def update_circuit_breaker_settings(
    settings_update: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update circuit breaker settings."""
    settings = db.query(CBSettings).filter(
        CBSettings.user_id == current_user.id
    ).first()

    if not settings:
        settings = CBSettings(user_id=current_user.id)
        db.add(settings)

    for key, value in settings_update.items():
        if hasattr(settings, key) and value is not None:
            setattr(settings, key, value)

    db.commit()
    db.refresh(settings)
    return {'status': 'updated'}


@router.post("/trading/circuit-breaker/reset")
async def reset_circuit_breakers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually reset circuit breakers."""
    import pytz

    active_events = db.query(CBEvent).filter(
        CBEvent.user_id == current_user.id,
        CBEvent.is_active == True
    ).all()

    for event in active_events:
        event.is_active = False
        event.resumed_at = datetime.now(pytz.UTC)
        event.resume_reason = 'manual'

    db.commit()
    return {'reset_count': len(active_events)}


@router.get("/trading/equity-curve")
async def get_equity_curve_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get equity curve trading status."""
    if not ANALYTICS_SERVICES_AVAILABLE:
        return {'is_trading_allowed': True, 'is_above_ma': True, 'cumulative_pnl': 0}

    service = TradeAnalyticsService(db)
    return service.get_equity_curve_status(current_user.id)


@router.get("/trading/position-multiplier")
async def get_position_multiplier(
    base_size: float = Query(..., description="Base position size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dynamic position size multiplier."""
    if not ANALYTICS_SERVICES_AVAILABLE:
        return {'multiplier': 1.0, 'adjusted_size': base_size}

    service = TradeAnalyticsService(db)
    multiplier = service.get_position_size_multiplier(current_user.id, base_size)

    return {
        'base_size': base_size,
        'multiplier': multiplier,
        'adjusted_size': base_size * multiplier
    }


@router.get("/trading/news-filter/settings")
async def get_news_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get news filter settings."""
    settings = db.query(NFSettings).filter(
        NFSettings.user_id == current_user.id
    ).first()

    if not settings:
        settings = NFSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return {
        'enabled': settings.enabled,
        'filter_high_impact': settings.filter_high_impact,
        'filter_medium_impact': settings.filter_medium_impact,
        'pause_minutes_before': settings.pause_minutes_before,
        'pause_minutes_after': settings.pause_minutes_after,
        'action_on_news': settings.action_on_news
    }


@router.put("/trading/news-filter/settings")
async def update_news_settings(
    settings_update: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update news filter settings."""
    settings = db.query(NFSettings).filter(
        NFSettings.user_id == current_user.id
    ).first()

    if not settings:
        settings = NFSettings(user_id=current_user.id)
        db.add(settings)

    for key, value in settings_update.items():
        if hasattr(settings, key) and value is not None:
            setattr(settings, key, value)

    db.commit()
    return {'status': 'updated'}


@router.get("/trading/correlation-filter/settings")
async def get_correlation_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get correlation filter settings."""
    settings = db.query(CFSettings).filter(
        CFSettings.user_id == current_user.id
    ).first()

    if not settings:
        settings = CFSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return {
        'enabled': settings.enabled,
        'max_positive_correlation': settings.max_positive_correlation,
        'max_negative_correlation': settings.max_negative_correlation,
        'action_on_correlation': settings.action_on_correlation
    }


@router.put("/trading/correlation-filter/settings")
async def update_correlation_settings(
    settings_update: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update correlation filter settings."""
    settings = db.query(CFSettings).filter(
        CFSettings.user_id == current_user.id
    ).first()

    if not settings:
        settings = CFSettings(user_id=current_user.id)
        db.add(settings)

    for key, value in settings_update.items():
        if hasattr(settings, key) and value is not None:
            setattr(settings, key, value)

    db.commit()
    return {'status': 'updated'}


@router.get("/trading/dynamic-sizing/settings")
async def get_dynamic_sizing_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dynamic position sizing settings."""
    settings = db.query(DSSettings).filter(
        DSSettings.user_id == current_user.id
    ).first()

    if not settings:
        settings = DSSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return {
        'enabled': settings.enabled,
        'method': settings.method,
        'base_risk_pct': settings.base_risk_pct,
        'increase_on_win_streak': settings.increase_on_win_streak,
        'win_streak_threshold': settings.win_streak_threshold,
        'decrease_on_loss_streak': settings.decrease_on_loss_streak,
        'loss_streak_threshold': settings.loss_streak_threshold,
        'equity_curve_enabled': settings.equity_curve_enabled,
        'pause_below_ma': settings.pause_below_ma
    }


@router.put("/trading/dynamic-sizing/settings")
async def update_dynamic_sizing_settings(
    settings_update: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update dynamic sizing settings."""
    settings = db.query(DSSettings).filter(
        DSSettings.user_id == current_user.id
    ).first()

    if not settings:
        settings = DSSettings(user_id=current_user.id)
        db.add(settings)

    for key, value in settings_update.items():
        if hasattr(settings, key) and value is not None:
            setattr(settings, key, value)

    db.commit()
    return {'status': 'updated'}
