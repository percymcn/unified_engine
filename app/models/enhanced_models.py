"""
Enhanced Models for Enterprise Premium SaaS Platform
Adds: RBAC, Subscriptions, Multi-tenancy, OAuth, Notifications
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON, Enum as SQLEnum, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum

# Enums for enhanced features
class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    PREMIUM_USER = "premium_user"
    FREE_USER = "free_user"

class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"

class OAuthProvider(str, enum.Enum):
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"

class NotificationType(str, enum.Enum):
    TRADE = "trade"
    SIGNAL = "signal"
    ALERT = "alert"
    SYSTEM = "system"
    BILLING = "billing"

class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"

# Association table for many-to-many relationship between users and organizations
user_organization_table = Table(
    'user_organizations',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('organization_id', Integer, ForeignKey('organizations.id'), primary_key=True),
    Column('role', String, default='member'),
    Column('joined_at', DateTime(timezone=True), server_default=func.now())
)

# Association table for permissions
permission_role_table = Table(
    'permission_roles',
    Base.metadata,
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)

class Organization(Base):
    """Multi-tenancy: Organizations/Workspaces"""
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Subscription
    subscription_tier = Column(SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE)
    subscription_status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.INCOMPLETE)
    stripe_customer_id = Column(String, index=True)
    stripe_subscription_id = Column(String, index=True)
    subscription_start_date = Column(DateTime(timezone=True))
    subscription_end_date = Column(DateTime(timezone=True))
    
    # Limits based on subscription tier
    max_accounts = Column(Integer, default=1)
    max_users = Column(Integer, default=1)
    max_api_calls_per_month = Column(Integer, default=1000)
    max_signals_per_month = Column(Integer, default=100)
    
    # Usage tracking
    current_accounts = Column(Integer, default=0)
    current_users = Column(Integer, default=1)
    api_calls_this_month = Column(Integer, default=0)
    signals_this_month = Column(Integer, default=0)
    
    # Settings
    settings = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], backref="owned_organizations")
    members = relationship("User", secondary=user_organization_table, back_populates="organizations")
    accounts = relationship("Account", back_populates="organization")

class Role(Base):
    """RBAC: Roles"""
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text)
    is_system_role = Column(Boolean, default=False)  # System roles cannot be deleted
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    permissions = relationship("Permission", secondary=permission_role_table, back_populates="roles")
    users = relationship("User", back_populates="role_obj")

class Permission(Base):
    """RBAC: Permissions"""
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    resource = Column(String, nullable=False)  # accounts, users, signals, etc.
    action = Column(String, nullable=False)  # read, write, delete, manage
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    roles = relationship("Role", secondary=permission_role_table, back_populates="permissions")

class UserSubscription(Base):
    """User-level subscription tracking"""
    __tablename__ = "user_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tier = Column(SQLEnum(SubscriptionTier), nullable=False)
    status = Column(SQLEnum(SubscriptionStatus), nullable=False)
    
    # Stripe integration
    stripe_customer_id = Column(String, index=True)
    stripe_subscription_id = Column(String, index=True)
    stripe_price_id = Column(String)
    
    # Dates
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True))
    trial_end_date = Column(DateTime(timezone=True))
    cancelled_at = Column(DateTime(timezone=True))
    
    # Usage limits
    max_accounts = Column(Integer, default=1)
    max_api_calls_per_month = Column(Integer, default=1000)
    max_signals_per_month = Column(Integer, default=100)
    
    # Current usage
    current_accounts = Column(Integer, default=0)
    api_calls_this_month = Column(Integer, default=0)
    signals_this_month = Column(Integer, default=0)
    
    # Metadata (renamed to avoid conflict with SQLAlchemy metadata)
    subscription_metadata = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="subscription")

class OAuthAccount(Base):
    """OAuth provider accounts"""
    __tablename__ = "oauth_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(SQLEnum(OAuthProvider), nullable=False)
    provider_user_id = Column(String, nullable=False, index=True)
    provider_email = Column(String)
    access_token = Column(Text)  # Encrypted
    refresh_token = Column(Text)  # Encrypted
    expires_at = Column(DateTime(timezone=True))
    provider_data = Column(JSON)  # Additional provider-specific data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="oauth_accounts")
    
    __table_args__ = (
        {'mysql_engine': 'InnoDB'},
    )

class Notification(Base):
    """Enhanced notification system"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    
    # Notification details
    type = Column(SQLEnum(NotificationType), nullable=False)
    channel = Column(SQLEnum(NotificationChannel), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    # Status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True))
    
    # Action/URL
    action_url = Column(String)
    action_label = Column(String)
    
    # Metadata (renamed to avoid conflict)
    notification_metadata = Column(JSON, default={})
    priority = Column(String, default="normal")  # low, normal, high, urgent
    
    # Delivery tracking
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    failure_reason = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    organization = relationship("Organization", backref="notifications")

class NotificationPreference(Base):
    """User notification preferences"""
    __tablename__ = "notification_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Channel preferences
    email_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=False)
    push_enabled = Column(Boolean, default=True)
    in_app_enabled = Column(Boolean, default=True)
    
    # Type preferences
    trade_notifications = Column(Boolean, default=True)
    signal_notifications = Column(Boolean, default=True)
    alert_notifications = Column(Boolean, default=True)
    system_notifications = Column(Boolean, default=True)
    billing_notifications = Column(Boolean, default=True)
    
    # Quiet hours
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_hours_start = Column(String, default="22:00")  # HH:MM format
    quiet_hours_end = Column(String, default="08:00")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="notification_preferences", uselist=False)

class AuditLog(Base):
    """Audit logging for compliance and security"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    
    # Action details
    action = Column(String, nullable=False, index=True)  # create, update, delete, login, etc.
    resource_type = Column(String, nullable=False)  # user, account, signal, etc.
    resource_id = Column(String, index=True)
    
    # Request details
    ip_address = Column(String)
    user_agent = Column(Text)
    request_method = Column(String)
    request_path = Column(String)
    
    # Changes
    old_values = Column(JSON)
    new_values = Column(JSON)
    
    # Status
    status = Column(String, default="success")  # success, failure
    error_message = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", backref="audit_logs")
    organization = relationship("Organization", backref="audit_logs")

class UsageMetric(Base):
    """Track usage metrics for billing and analytics"""
    __tablename__ = "usage_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    
    # Metric details
    metric_type = Column(String, nullable=False, index=True)  # api_call, signal, account, etc.
    metric_value = Column(Float, default=1.0)
    
    # Time tracking
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    hour = Column(Integer)  # 0-23 for hourly aggregation
    
    # Metadata (renamed to avoid conflict)
    metric_metadata = Column(JSON, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", backref="usage_metrics")
    organization = relationship("Organization", backref="usage_metrics")
