"""
Provisioning Job Service

Handles async MetaApi account provisioning jobs.
Uses FastAPI BackgroundTasks for non-blocking provisioning.
"""
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.models.database_models import (
    ProvisioningJob,
    ProvisioningJobStatus,
    TradingAccount,
    Credential,
)
from app.core.config import settings
from app.core.encryption import get_encryption_service

logger = logging.getLogger(__name__)


class ProvisioningJobService:
    """Service for managing async MetaApi provisioning jobs"""

    def __init__(self, db: Session):
        self.db = db

    def create_job(
        self,
        user_id: int,
        trading_account_id: int,
        platform: str,
        login: str,
        password: str,
        server: str,
        account_name: str,
    ) -> ProvisioningJob:
        """Create a new provisioning job (does not start execution)"""
        job_id = str(uuid.uuid4())

        job = ProvisioningJob(
            id=job_id,
            user_id=user_id,
            trading_account_id=trading_account_id,
            platform=platform.lower(),
            login=login,
            server=server,
            account_name=account_name,
            status=ProvisioningJobStatus.PENDING,
            status_message="Job created, waiting to start",
            progress_percent=0,
        )

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        # Store password encrypted separately (not in job table)
        self._store_temp_password(job_id, password)

        logger.info(f"Created provisioning job {job_id} for user {user_id}, account {trading_account_id}")
        return job

    def _store_temp_password(self, job_id: str, password: str):
        """Store password in Redis with short TTL for job execution"""
        from app.cache.redis_client import redis_client
        if redis_client:
            # Store for 10 minutes (job should complete by then)
            redis_client.setex(f"provision_pwd:{job_id}", 600, password)

    def _get_temp_password(self, job_id: str) -> Optional[str]:
        """Retrieve password from Redis"""
        from app.cache.redis_client import redis_client
        if redis_client:
            pwd = redis_client.get(f"provision_pwd:{job_id}")
            return pwd.decode() if pwd else None
        return None

    def _clear_temp_password(self, job_id: str):
        """Clear password from Redis after use"""
        from app.cache.redis_client import redis_client
        if redis_client:
            redis_client.delete(f"provision_pwd:{job_id}")

    def get_job(self, job_id: str) -> Optional[ProvisioningJob]:
        """Get job by ID"""
        return self.db.query(ProvisioningJob).filter(ProvisioningJob.id == job_id).first()

    def get_jobs_for_account(self, trading_account_id: int) -> list:
        """Get all jobs for a trading account"""
        return (
            self.db.query(ProvisioningJob)
            .filter(ProvisioningJob.trading_account_id == trading_account_id)
            .order_by(ProvisioningJob.created_at.desc())
            .all()
        )

    def get_pending_jobs(self) -> list:
        """Get all pending jobs that need execution"""
        return (
            self.db.query(ProvisioningJob)
            .filter(ProvisioningJob.status == ProvisioningJobStatus.PENDING)
            .all()
        )

    def update_job_status(
        self,
        job_id: str,
        status: ProvisioningJobStatus,
        message: str = None,
        progress: int = None,
        metaapi_account_id: str = None,
        error_message: str = None,
    ):
        """Update job status"""
        job = self.get_job(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found for status update")
            return

        job.status = status
        if message:
            job.status_message = message
        if progress is not None:
            job.progress_percent = progress
        if metaapi_account_id:
            job.metaapi_account_id = metaapi_account_id
        if error_message:
            job.error_message = error_message

        if status == ProvisioningJobStatus.CREATING and not job.started_at:
            job.started_at = datetime.utcnow()
        if status in (ProvisioningJobStatus.COMPLETED, ProvisioningJobStatus.FAILED):
            job.completed_at = datetime.utcnow()

        self.db.commit()
        logger.info(f"Job {job_id} status updated to {status.value}: {message}")


async def execute_provisioning_job(job_id: str, db_url: str = None):
    """
    Execute a provisioning job asynchronously.
    This is the background task that does the actual MetaApi provisioning.
    """
    from app.db.database import SessionLocal
    from app.services.metaapi_provisioning_service import get_provisioning_service

    db = SessionLocal()
    try:
        service = ProvisioningJobService(db)
        job = service.get_job(job_id)

        if not job:
            logger.error(f"Job {job_id} not found")
            return

        if job.status != ProvisioningJobStatus.PENDING:
            logger.warning(f"Job {job_id} is not pending (status: {job.status})")
            return

        # Get password from Redis
        password = service._get_temp_password(job_id)
        if not password:
            service.update_job_status(
                job_id,
                ProvisioningJobStatus.FAILED,
                "Password not found or expired",
                error_message="Provisioning password expired. Please try again.",
            )
            return

        # Get provisioning service
        provisioning_service = get_provisioning_service()
        if not provisioning_service:
            service.update_job_status(
                job_id,
                ProvisioningJobStatus.FAILED,
                "MetaApi not configured",
                error_message="METAAPI_TOKEN not configured on server",
            )
            return

        # Update status: Creating
        service.update_job_status(
            job_id,
            ProvisioningJobStatus.CREATING,
            "Creating MetaApi account...",
            progress=10,
        )

        try:
            # Call the provisioning service with status callbacks
            result = await _provision_with_status_updates(
                provisioning_service,
                service,
                job_id,
                login=job.login,
                password=password,
                server=job.server,
                platform=job.platform,
                name=job.account_name,
            )

            # Success! Update credential with metaapi_account_id
            if result and result.get("account_id"):
                metaapi_account_id = result["account_id"]

                # Update the credential record
                await _update_credential_with_metaapi_id(
                    db, job.user_id, job.trading_account_id, metaapi_account_id
                )

                service.update_job_status(
                    job_id,
                    ProvisioningJobStatus.COMPLETED,
                    "MetaApi account provisioned successfully",
                    progress=100,
                    metaapi_account_id=metaapi_account_id,
                )

                logger.info(f"Provisioning job {job_id} completed: {metaapi_account_id}")
            else:
                service.update_job_status(
                    job_id,
                    ProvisioningJobStatus.FAILED,
                    "Provisioning returned no account ID",
                    error_message="MetaApi did not return an account ID",
                )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Provisioning job {job_id} failed: {error_msg}")
            service.update_job_status(
                job_id,
                ProvisioningJobStatus.FAILED,
                f"Provisioning failed: {error_msg[:100]}",
                error_message=error_msg,
            )

        finally:
            # Always clear the temp password
            service._clear_temp_password(job_id)

    finally:
        db.close()


async def _provision_with_status_updates(
    provisioning_service,
    job_service: ProvisioningJobService,
    job_id: str,
    login: str,
    password: str,
    server: str,
    platform: str,
    name: str,
) -> Dict[str, Any]:
    """
    Run provisioning with status updates at each stage.
    This wraps the provisioning service to provide progress feedback.
    """
    # Stage 1: Create account (10-30%)
    job_service.update_job_status(
        job_id,
        ProvisioningJobStatus.CREATING,
        "Registering account with MetaApi...",
        progress=15,
    )

    # The actual provisioning call - this does create, deploy, connect, sync
    result = await provisioning_service.provision_account(
        login=login,
        password=password,
        server=server,
        platform=platform,
        name=name,
    )

    # If we get here, provisioning succeeded
    job_service.update_job_status(
        job_id,
        ProvisioningJobStatus.COMPLETED,
        "Account fully provisioned and connected",
        progress=100,
    )

    return result


async def _update_credential_with_metaapi_id(
    db: Session,
    user_id: int,
    trading_account_id: int,
    metaapi_account_id: str,
):
    """Update the credential record with the provisioned MetaApi account ID"""
    from app.core.encryption import get_encryption_service

    encryption = get_encryption_service()

    # Get the trading account to find the broker type
    account = db.query(TradingAccount).filter(TradingAccount.id == trading_account_id).first()
    if not account:
        logger.warning(f"Trading account {trading_account_id} not found")
        return

    broker_value = account.broker.value

    # Find the credential for this account
    credential = (
        db.query(Credential)
        .filter(
            Credential.user_id == user_id,
            Credential.service == broker_value,
            Credential.is_active == True,
        )
        .order_by(Credential.created_at.desc())
        .first()
    )

    if credential:
        # Decrypt, update, re-encrypt
        try:
            data = encryption.decrypt_dict(credential.encrypted_data)
            data["metaapi_account_id"] = metaapi_account_id
            credential.encrypted_data = encryption.encrypt_dict(data)
            db.commit()
            logger.info(f"Updated credential {credential.id} with metaapi_account_id")
        except Exception as e:
            logger.error(f"Failed to update credential: {e}")
    else:
        logger.warning(f"No credential found for user {user_id}, broker {broker_value}")
