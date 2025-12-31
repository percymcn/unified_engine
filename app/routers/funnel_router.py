"""
Funnel Router
Complete funnel management system for lead generation and conversion
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import json
import uuid

from app.db.database import get_db
from app.routers.auth import get_current_user, verify_api_key
from app.models.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/funnel", tags=["funnel"])

# Pydantic Models
class LeadCapture(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    phone: Optional[str] = None
    source: str
    funnel_stage: str
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None

class ApplicationData(BaseModel):
    lead_id: str
    full_name: str
    email: EmailStr
    phone: str
    experience_level: str
    trading_goals: List[str]
    initial_capital: str
    time_commitment: str
    risk_tolerance: str

class LaunchpadAccess(BaseModel):
    user_id: str
    lead_id: str
    access_level: str = "basic"
    features_enabled: List[str] = []

class PremiumPurchase(BaseModel):
    user_id: str
    lead_id: str
    plan_type: str
    payment_method: str
    amount: float
    currency: str = "USD"

class VSLTracking(BaseModel):
    lead_id: str
    video_id: str
    watch_time_seconds: int
    completed: bool
    timestamp: datetime

# In-memory storage (replace with database in production)
leads_db = {}
applications_db = {}
launchpad_access_db = {}
premium_purchases_db = {}
vsl_tracking_db = {}

class FunnelManager:
    """Manages the complete funnel flow"""
    
    def __init__(self):
        self.conversion_rates = {
            "free_guide": 0.15,
            "application": 0.08,
            "launchpad": 0.12,
            "premium": 0.05
        }
        self.funnel_stages = ["visitor", "lead", "applicant", "launchpad_user", "premium_customer"]
    
    async def capture_lead(self, lead_data: LeadCapture) -> Dict[str, Any]:
        """Capture new lead from funnel entry point"""
        lead_id = str(uuid.uuid4())
        
        lead = {
            "id": lead_id,
            "email": lead_data.email,
            "name": lead_data.name,
            "phone": lead_data.phone,
            "source": lead_data.source,
            "funnel_stage": lead_data.funnel_stage,
            "utm_source": lead_data.utm_source,
            "utm_medium": lead_data.utm_medium,
            "utm_campaign": lead_data.utm_campaign,
            "captured_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        leads_db[lead_id] = lead
        
        # Trigger automation workflows
        await self.trigger_automation("lead_captured", lead)
        
        logger.info(f"Lead captured: {lead_id} from {lead_data.source}")
        return lead
    
    async def process_application(self, app_data: ApplicationData) -> Dict[str, Any]:
        """Process launchpad application"""
        app_id = str(uuid.uuid4())
        
        application = {
            "id": app_id,
            "lead_id": app_data.lead_id,
            "full_name": app_data.full_name,
            "email": app_data.email,
            "phone": app_data.phone,
            "experience_level": app_data.experience_level,
            "trading_goals": app_data.trading_goals,
            "initial_capital": app_data.initial_capital,
            "time_commitment": app_data.time_commitment,
            "risk_tolerance": app_data.risk_tolerance,
            "submitted_at": datetime.now().isoformat(),
            "status": "pending_review"
        }
        
        applications_db[app_id] = application
        
        # Update lead stage
        if app_data.lead_id in leads_db:
            leads_db[app_data.lead_id]["funnel_stage"] = "applicant"
            leads_db[app_data.lead_id]["status"] = "application_submitted"
        
        # Trigger automation workflows
        await self.trigger_automation("application_submitted", application)
        
        logger.info(f"Application submitted: {app_id} for lead {app_data.lead_id}")
        return application
    
    async def grant_launchpad_access(self, access_data: LaunchpadAccess) -> Dict[str, Any]:
        """Grant access to launchpad"""
        access_id = str(uuid.uuid4())
        
        access = {
            "id": access_id,
            "user_id": access_data.user_id,
            "lead_id": access_data.lead_id,
            "access_level": access_data.access_level,
            "features_enabled": access_data.features_enabled,
            "granted_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
            "status": "active"
        }
        
        launchpad_access_db[access_id] = access
        
        # Update lead stage
        if access_data.lead_id in leads_db:
            leads_db[access_data.lead_id]["funnel_stage"] = "launchpad_user"
            leads_db[access_data.lead_id]["status"] = "launchpad_access_granted"
        
        # Trigger automation workflows
        await self.trigger_automation("launchpad_access_granted", access)
        
        logger.info(f"Launchpad access granted: {access_id} to user {access_data.user_id}")
        return access
    
    async def process_premium_purchase(self, purchase_data: PremiumPurchase) -> Dict[str, Any]:
        """Process premium subscription purchase"""
        purchase_id = str(uuid.uuid4())
        
        purchase = {
            "id": purchase_id,
            "user_id": purchase_data.user_id,
            "lead_id": purchase_data.lead_id,
            "plan_type": purchase_data.plan_type,
            "payment_method": purchase_data.payment_method,
            "amount": purchase_data.amount,
            "currency": purchase_data.currency,
            "purchased_at": datetime.now().isoformat(),
            "status": "active",
            "next_billing_date": (datetime.now() + timedelta(days=30)).isoformat()
        }
        
        premium_purchases_db[purchase_id] = purchase
        
        # Update lead stage
        if purchase_data.lead_id in leads_db:
            leads_db[purchase_data.lead_id]["funnel_stage"] = "premium_customer"
            leads_db[purchase_data.lead_id]["status"] = "premium_subscriber"
        
        # Trigger automation workflows
        await self.trigger_automation("premium_purchase_completed", purchase)
        
        logger.info(f"Premium purchase completed: {purchase_id} for user {purchase_data.user_id}")
        return purchase
    
    async def track_vsl_engagement(self, tracking_data: VSLTracking) -> Dict[str, Any]:
        """Track VSL (Video Sales Letter) engagement"""
        tracking_id = str(uuid.uuid4())
        
        tracking = {
            "id": tracking_id,
            "lead_id": tracking_data.lead_id,
            "video_id": tracking_data.video_id,
            "watch_time_seconds": tracking_data.watch_time_seconds,
            "completed": tracking_data.completed,
            "timestamp": tracking_data.timestamp.isoformat() if isinstance(tracking_data.timestamp, datetime) else tracking_data.timestamp
        }
        
        if tracking_data.lead_id not in vsl_tracking_db:
            vsl_tracking_db[tracking_data.lead_id] = []
        
        vsl_tracking_db[tracking_data.lead_id].append(tracking)
        
        # Update lead engagement score
        if tracking_data.lead_id in leads_db:
            current_score = leads_db[tracking_data.lead_id].get("engagement_score", 0)
            leads_db[tracking_data.lead_id]["engagement_score"] = current_score + (10 if tracking_data.completed else 5)
            leads_db[tracking_data.lead_id]["last_engagement"] = datetime.now().isoformat()
        
        # Trigger automation if video completed
        if tracking_data.completed:
            await self.trigger_automation("vsl_completed", tracking)
        
        logger.info(f"VSL tracking recorded: {tracking_id} for lead {tracking_data.lead_id}")
        return tracking
    
    async def trigger_automation(self, event_type: str, data: Dict[str, Any]):
        """Trigger automation workflows via NATS"""
        try:
            # This would integrate with NATS for workflow automation
            event = {
                "event_type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat(),
                "source": "funnel_system"
            }
            
            # TODO: Send to NATS
            # await nats_client.publish("funnel.events", json.dumps(event))
            
            logger.info(f"Automation triggered: {event_type}")
            
        except Exception as e:
            logger.error(f"Failed to trigger automation for {event_type}: {e}")
    
    async def get_funnel_metrics(self) -> Dict[str, Any]:
        """Get comprehensive funnel metrics"""
        total_leads = len(leads_db)
        total_applications = len(applications_db)
        total_launchpad_users = len(launchpad_access_db)
        total_premium_customers = len(premium_purchases_db)
        
        # Stage breakdown
        stage_counts = {}
        for stage in self.funnel_stages:
            stage_counts[stage] = sum(1 for lead in leads_db.values() if lead.get("funnel_stage") == stage)
        
        # Conversion rates
        conversion_rates = {}
        if total_leads > 0:
            conversion_rates["lead_to_application"] = total_applications / total_leads
            conversion_rates["application_to_launchpad"] = total_launchpad_users / total_applications if total_applications > 0 else 0
            conversion_rates["launchpad_to_premium"] = total_premium_customers / total_launchpad_users if total_launchpad_users > 0 else 0
        
        # Revenue metrics
        total_revenue = sum(purchase["amount"] for purchase in premium_purchases_db.values())
        
        return {
            "total_leads": total_leads,
            "total_applications": total_applications,
            "total_launchpad_users": total_launchpad_users,
            "total_premium_customers": total_premium_customers,
            "stage_breakdown": stage_counts,
            "conversion_rates": conversion_rates,
            "total_revenue": total_revenue,
            "average_revenue_per_customer": total_revenue / total_premium_customers if total_premium_customers > 0 else 0,
            "timestamp": datetime.now().isoformat()
        }

# Global funnel manager instance
funnel_manager = FunnelManager()

# API Endpoints

@router.post("/lead/capture")
async def capture_lead(
    lead_data: LeadCapture,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Capture new lead from any funnel entry point"""
    try:
        lead = await funnel_manager.capture_lead(lead_data)
        
        # Background tasks for lead nurturing
        background_tasks.add_task(send_welcome_email, lead["email"], lead["name"])
        
        return {
            "success": True,
            "lead_id": lead["id"],
            "message": "Lead captured successfully",
            "next_steps": ["welcome_email_sent", "lead_nurturing_started"]
        }
        
    except Exception as e:
        logger.error(f"Error capturing lead: {e}")
        raise HTTPException(status_code=500, detail="Failed to capture lead")

@router.post("/application/submit")
async def submit_application(
    app_data: ApplicationData,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Submit launchpad application"""
    try:
        application = await funnel_manager.process_application(app_data)
        
        # Background tasks for application processing
        background_tasks.add_task(send_application_confirmation, application["email"])
        background_tasks.add_task(notify_review_team, application["id"])
        
        return {
            "success": True,
            "application_id": application["id"],
            "message": "Application submitted successfully",
            "status": "pending_review"
        }
        
    except Exception as e:
        logger.error(f"Error processing application: {e}")
        raise HTTPException(status_code=500, detail="Failed to process application")

@router.post("/launchpad/grant")
async def grant_launchpad(
    access_data: LaunchpadAccess,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Grant launchpad access to user"""
    try:
        access = await funnel_manager.grant_launchpad_access(access_data)
        
        # Background tasks for onboarding
        background_tasks.add_task(send_launchpad_welcome, access_data.user_id)
        background_tasks.add_task(create_onboarding_schedule, access_data.user_id)
        
        return {
            "success": True,
            "access_id": access["id"],
            "access_level": access["access_level"],
            "expires_at": access["expires_at"],
            "message": "Launchpad access granted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error granting launchpad access: {e}")
        raise HTTPException(status_code=500, detail="Failed to grant launchpad access")

@router.post("/premium/purchase")
async def process_premium_purchase(
    purchase_data: PremiumPurchase,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Process premium subscription purchase"""
    try:
        purchase = await funnel_manager.process_premium_purchase(purchase_data)
        
        # Background tasks for purchase fulfillment
        background_tasks.add_task(send_purchase_confirmation, purchase_data.user_id, purchase["id"])
        background_tasks.add_task(activate_premium_features, purchase_data.user_id, purchase_data.plan_type)
        
        return {
            "success": True,
            "purchase_id": purchase["id"],
            "plan_type": purchase["plan_type"],
            "amount": purchase["amount"],
            "next_billing_date": purchase["next_billing_date"],
            "message": "Premium purchase completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error processing premium purchase: {e}")
        raise HTTPException(status_code=500, detail="Failed to process premium purchase")

@router.post("/vsl/track")
async def track_vsl(
    tracking_data: VSLTracking,
    api_key: str = Depends(verify_api_key)
):
    """Track VSL engagement"""
    try:
        tracking = await funnel_manager.track_vsl_engagement(tracking_data)
        
        return {
            "success": True,
            "tracking_id": tracking["id"],
            "watch_time_seconds": tracking["watch_time_seconds"],
            "completed": tracking["completed"],
            "message": "VSL engagement tracked successfully"
        }
        
    except Exception as e:
        logger.error(f"Error tracking VSL engagement: {e}")
        raise HTTPException(status_code=500, detail="Failed to track VSL engagement")

@router.get("/metrics")
async def get_funnel_metrics(
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive funnel metrics"""
    try:
        metrics = await funnel_manager.get_funnel_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting funnel metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get funnel metrics")

@router.get("/leads")
async def get_leads(
    limit: int = 100,
    stage: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get leads with optional filtering"""
    try:
        leads = list(leads_db.values())
        
        if stage:
            leads = [lead for lead in leads if lead.get("funnel_stage") == stage]
        
        # Sort by captured_at descending
        leads.sort(key=lambda x: x.get("captured_at", ""), reverse=True)
        
        return {
            "leads": leads[:limit],
            "total": len(leads),
            "filtered": len(leads[:limit])
        }
        
    except Exception as e:
        logger.error(f"Error getting leads: {e}")
        raise HTTPException(status_code=500, detail="Failed to get leads")

@router.get("/applications")
async def get_applications(
    limit: int = 100,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get applications with optional filtering"""
    try:
        applications = list(applications_db.values())
        
        if status:
            applications = [app for app in applications if app.get("status") == status]
        
        # Sort by submitted_at descending
        applications.sort(key=lambda x: x.get("submitted_at", ""), reverse=True)
        
        return {
            "applications": applications[:limit],
            "total": len(applications),
            "filtered": len(applications[:limit])
        }
        
    except Exception as e:
        logger.error(f"Error getting applications: {e}")
        raise HTTPException(status_code=500, detail="Failed to get applications")

# Background task functions (placeholders)
async def send_welcome_email(email: str, name: Optional[str]):
    """Send welcome email to new lead"""
    logger.info(f"Welcome email sent to {email}")
    # TODO: Integrate with email service

async def send_application_confirmation(email: str):
    """Send application confirmation email"""
    logger.info(f"Application confirmation sent to {email}")
    # TODO: Integrate with email service

async def notify_review_team(application_id: str):
    """Notify review team about new application"""
    logger.info(f"Review team notified about application {application_id}")
    # TODO: Integrate with notification system

async def send_launchpad_welcome(user_id: str):
    """Send launchpad welcome message"""
    logger.info(f"Launchpad welcome sent to user {user_id}")
    # TODO: Integrate with messaging system

async def create_onboarding_schedule(user_id: str):
    """Create onboarding schedule for new user"""
    logger.info(f"Onboarding schedule created for user {user_id}")
    # TODO: Integrate with scheduling system

async def send_purchase_confirmation(user_id: str, purchase_id: str):
    """Send purchase confirmation"""
    logger.info(f"Purchase confirmation sent to user {user_id} for purchase {purchase_id}")
    # TODO: Integrate with email service

async def activate_premium_features(user_id: str, plan_type: str):
    """Activate premium features for user"""
    logger.info(f"Premium features activated for user {user_id} with plan {plan_type}")
    # TODO: Integrate with user management system