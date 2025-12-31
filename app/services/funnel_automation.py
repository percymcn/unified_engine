"""
Funnel Automation Service
Background service for handling funnel automation workflows
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import aiohttp
import aioredis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import engine, SessionLocal
from app.models.models import User

logger = logging.getLogger(__name__)

class FunnelAutomationService:
    """Handles automated funnel processes and lead nurturing"""
    
    def __init__(self):
        self.redis_client = None
        self.email_service_url = "https://api.sendgrid.com/v3/mail/send"
        self.webhook_urls = {
            'n8n': 'http://n8n:5678/webhook/funnel-automation',
            'slack': 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK',
        }
        
    async def initialize(self):
        """Initialize the service"""
        try:
            # Connect to Redis
            self.redis_client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("✅ Funnel Automation Service connected to Redis")
            
            # Start background tasks
            asyncio.create_task(self.process_lead_nurturing())
            asyncio.create_task(self.process_application_reviews())
            asyncio.create_task(self.process_payment_followups())
            asyncio.create_task(self.process_vsl_engagement())
            asyncio.create_task(self.monitor_funnel_health())
            
            logger.info("🚀 Funnel Automation Service started successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Funnel Automation Service: {e}")
            raise
    
    async def process_lead_nurturing(self):
        """Process lead nurturing sequences"""
        while True:
            try:
                # Get leads that need nurturing
                leads_to_nurture = await self.get_leads_for_nurturing()
                
                for lead in leads_to_nurture:
                    await self.send_nurturing_email(lead)
                    await self.update_lead_status(lead['id'], 'nurtured')
                
                # Wait before next check
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Error in lead nurturing: {e}")
                await asyncio.sleep(60)
    
    async def process_application_reviews(self):
        """Process application reviews and approvals"""
        while True:
            try:
                # Get pending applications
                pending_apps = await self.get_pending_applications()
                
                for app in pending_apps:
                    # Auto-approve based on criteria
                    if await self.should_auto_approve(app):
                        await self.approve_application(app)
                    else:
                        await self.flag_for_manual_review(app)
                
                # Wait before next check
                await asyncio.sleep(600)  # 10 minutes
                
            except Exception as e:
                logger.error(f"Error in application processing: {e}")
                await asyncio.sleep(60)
    
    async def process_payment_followups(self):
        """Process payment follow-ups and failed payments"""
        while True:
            try:
                # Get recent payments that need follow-up
                payments_to_followup = await self.get_payments_for_followup()
                
                for payment in payments_to_followup:
                    await self.send_payment_followup(payment)
                
                # Wait before next check
                await asyncio.sleep(1800)  # 30 minutes
                
            except Exception as e:
                logger.error(f"Error in payment follow-up: {e}")
                await asyncio.sleep(60)
    
    async def process_vsl_engagement(self):
        """Process VSL engagement and trigger follow-ups"""
        while True:
            try:
                # Get VSL engagement data
                vsl_data = await self.get_vsl_engagement_data()
                
                for engagement in vsl_data:
                    if engagement['completed']:
                        await self.send_vsl_completion_email(engagement)
                    elif engagement['watch_time_seconds'] > 600:  # 10 minutes
                        await self.send_vsl_midpoint_email(engagement)
                
                # Wait before next check
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Error in VSL engagement processing: {e}")
                await asyncio.sleep(60)
    
    async def monitor_funnel_health(self):
        """Monitor funnel health and send alerts"""
        while True:
            try:
                # Calculate funnel metrics
                metrics = await self.calculate_funnel_metrics()
                
                # Check for issues
                issues = []
                
                if metrics['conversion_rate'] < 0.05:  # Less than 5%
                    issues.append("Low conversion rate detected")
                
                if metrics['lead_dropoff'] > 0.5:  # More than 50% dropoff
                    issues.append("High lead dropoff detected")
                
                if metrics['vsl_completion_rate'] < 0.3:  # Less than 30%
                    issues.append("Low VSL completion rate")
                
                # Send alerts if issues found
                if issues:
                    await self.send_funnel_alert(issues, metrics)
                
                # Wait before next check
                await asyncio.sleep(3600)  # 1 hour
                
            except Exception as e:
                logger.error(f"Error in funnel health monitoring: {e}")
                await asyncio.sleep(300)
    
    async def get_leads_for_nurturing(self) -> List[Dict]:
        """Get leads that need nurturing"""
        try:
            # Query leads from database or cache
            leads_json = await self.redis_client.get("leads_pending_nurturing")
            
            if leads_json:
                return json.loads(leads_json)
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting leads for nurturing: {e}")
            return []
    
    async def send_nurturing_email(self, lead: Dict):
        """Send nurturing email to lead"""
        try:
            email_data = {
                "personalizations": [{
                    "to": [{"email": lead["email"]}],
                    "subject": "Your Free Trading Guide is Ready!",
                }],
                "from": {"email": "noreply@fluxeo-trading.com"},
                "content": [{
                    "type": "text/plain",
                    "value": f"Hi {lead.get('name', 'Trader')},\n\nYour free trading guide is ready for download.\n\nBest regards,\nFluxeo Trading Team"
                }]
            }
            
            # Send email (implementation depends on your email service)
            await self.send_email(email_data)
            
            logger.info(f"Nurturing email sent to lead {lead['id']}")
            
        except Exception as e:
            logger.error(f"Error sending nurturing email: {e}")
    
    async def get_pending_applications(self) -> List[Dict]:
        """Get pending applications"""
        try:
            apps_json = await self.redis_client.get("applications_pending")
            
            if apps_json:
                return json.loads(apps_json)
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting pending applications: {e}")
            return []
    
    async def should_auto_approve(self, application: Dict) -> bool:
        """Determine if application should be auto-approved"""
        try:
            # Auto-approval criteria
            criteria = {
                'experience_level': ['intermediate', 'advanced'],
                'initial_capital': ['1k-5k', '5k-10k', '10k-25k', '25k-50k', 'over-50k'],
                'time_commitment': ['2-4-hours', '4-6-hours', '6-plus-hours'],
            }
            
            # Check if application meets criteria
            if application.get('experience_level') not in criteria['experience_level']:
                return False
            
            if application.get('initial_capital') not in criteria['initial_capital']:
                return False
            
            if application.get('time_commitment') not in criteria['time_commitment']:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking auto-approval: {e}")
            return False
    
    async def approve_application(self, application: Dict):
        """Approve application and grant launchpad access"""
        try:
            # Grant launchpad access
            access_data = {
                "user_id": application.get('user_id'),
                "lead_id": application.get('lead_id'),
                "access_level": "basic",
                "features_enabled": ["foundations", "risk-management"]
            }
            
            # Call launchpad access endpoint
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://api:8000/api/v1/funnel/launchpad/grant",
                    json=access_data,
                    headers={"X-API-Key": "funnel-api-key-2024"}
                ) as response:
                    if response.status == 200:
                        logger.info(f"Application {application['id']} auto-approved")
                        await self.send_approval_email(application)
                    else:
                        logger.error(f"Failed to approve application {application['id']}")
            
        except Exception as e:
            logger.error(f"Error approving application: {e}")
    
    async def send_approval_email(self, application: Dict):
        """Send approval email"""
        try:
            email_data = {
                "personalizations": [{
                    "to": [{"email": application["email"]}],
                    "subject": "Congratulations! Your Application Has Been Approved",
                }],
                "from": {"email": "noreply@fluxeo-trading.com"},
                "content": [{
                    "type": "text/plain",
                    "value": f"Hi {application.get('full_name', 'Trader')},\n\nCongratulations! Your application has been approved.\n\nYou now have access to the Launchpad program.\n\nBest regards,\nFluxeo Trading Team"
                }]
            }
            
            await self.send_email(email_data)
            
        except Exception as e:
            logger.error(f"Error sending approval email: {e}")
    
    async def get_vsl_engagement_data(self) -> List[Dict]:
        """Get VSL engagement data"""
        try:
            vsl_json = await self.redis_client.get("vsl_engagement_data")
            
            if vsl_json:
                return json.loads(vsl_json)
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting VSL engagement data: {e}")
            return []
    
    async def send_vsl_completion_email(self, engagement: Dict):
        """Send email to users who completed VSL"""
        try:
            # Get lead email
            lead_email = await self.get_lead_email(engagement['lead_id'])
            
            if not lead_email:
                return
            
            email_data = {
                "personalizations": [{
                    "to": [{"email": lead_email}],
                    "subject": "Ready to Take the Next Step?",
                }],
                "from": {"email": "noreply@fluxeo-trading.com"},
                "content": [{
                    "type": "text/plain",
                    "value": "Great job completing the video! Ready to apply for our Launchpad program?\n\nBest regards,\nFluxeo Trading Team"
                }]
            }
            
            await self.send_email(email_data)
            
        except Exception as e:
            logger.error(f"Error sending VSL completion email: {e}")
    
    async def calculate_funnel_metrics(self) -> Dict:
        """Calculate funnel health metrics"""
        try:
            # Get metrics from funnel router
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://api:8000/api/v1/funnel/metrics",
                    headers={"Authorization": f"Bearer {settings.SECRET_KEY}"}
                ) as response:
                    if response.status == 200:
                        metrics = await response.json()
                        
                        return {
                            'conversion_rate': metrics.get('conversion_rates', {}).get('lead_to_application', 0),
                            'lead_dropoff': 0.3,  # Calculate from actual data
                            'vsl_completion_rate': 0.7,  # Calculate from actual data
                            'total_leads': metrics.get('total_leads', 0),
                            'total_applications': metrics.get('total_applications', 0),
                        }
            
            return {
                'conversion_rate': 0,
                'lead_dropoff': 0,
                'vsl_completion_rate': 0,
                'total_leads': 0,
                'total_applications': 0,
            }
            
        except Exception as e:
            logger.error(f"Error calculating funnel metrics: {e}")
            return {}
    
    async def send_funnel_alert(self, issues: List[str], metrics: Dict):
        """Send funnel health alert"""
        try:
            alert_data = {
                "text": f"🚨 Funnel Health Alert\n\nIssues:\n" + "\n".join(f"• {issue}" for issue in issues),
                "attachments": [{
                    "color": "danger",
                    "fields": [
                        {"title": "Conversion Rate", "value": f"{metrics.get('conversion_rate', 0):.2%}", "short": True},
                        {"title": "Total Leads", "value": metrics.get('total_leads', 0), "short": True},
                        {"title": "Total Applications", "value": metrics.get('total_applications', 0), "short": True},
                    ]
                }]
            }
            
            # Send to Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_urls['slack'],
                    json=alert_data
                ) as response:
                    if response.status == 200:
                        logger.info("Funnel alert sent to Slack")
            
        except Exception as e:
            logger.error(f"Error sending funnel alert: {e}")
    
    async def send_email(self, email_data: Dict):
        """Send email using email service"""
        try:
            # Implementation depends on your email service
            # This is a placeholder for SendGrid, Mailgun, etc.
            logger.info(f"Email would be sent: {email_data['personalizations'][0]['to']}")
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
    
    async def update_lead_status(self, lead_id: str, status: str):
        """Update lead status in cache/database"""
        try:
            await self.redis_client.set(f"lead_status_{lead_id}", status, ex=86400)
            
        except Exception as e:
            logger.error(f"Error updating lead status: {e}")
    
    async def get_lead_email(self, lead_id: str) -> str:
        """Get lead email from cache/database"""
        try:
            email = await self.redis_client.get(f"lead_email_{lead_id}")
            return email or ""
            
        except Exception as e:
            logger.error(f"Error getting lead email: {e}")
            return ""

# Main execution
async def main():
    """Main function to run the funnel automation service"""
    service = FunnelAutomationService()
    
    try:
        await service.initialize()
        
        # Keep the service running
        while True:
            await asyncio.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("🛑 Funnel Automation Service shutting down...")
    except Exception as e:
        logger.error(f"❌ Fatal error in Funnel Automation Service: {e}")

if __name__ == "__main__":
    asyncio.run(main())