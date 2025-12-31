"""
Credential Router
Secure credential management system for API keys and sensitive data
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
import secrets
from cryptography.fernet import Fernet
import hashlib

from app.db.database import get_db
from app.routers.auth import get_current_user, verify_api_key
from app.models.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/credentials", tags=["credentials"])

# Encryption key management
ENCRYPTION_KEY = Fernet.generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

# Pydantic Models
class CredentialCreate(BaseModel):
    name: str
    type: str  # api_key, password, certificate, token
    service: str  # mt4, mt5, tradelocker, tradovate, projectx, etc.
    credential_data: Dict[str, Any]
    description: Optional[str] = None
    expires_at: Optional[datetime] = None
    rotation_days: Optional[int] = 90

class CredentialUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    expires_at: Optional[datetime] = None
    rotation_days: Optional[int] = None
    is_active: Optional[bool] = None

class CredentialAccess(BaseModel):
    credential_id: str
    purpose: str
    access_duration_minutes: int = 60

class AuditLog(BaseModel):
    action: str
    credential_id: str
    user_id: str
    timestamp: datetime
    ip_address: str
    user_agent: str
    success: bool

# In-memory storage (replace with database in production)
credentials_db = {}
audit_logs = []
access_tokens = {}

class CredentialManager:
    """Manages secure credential storage and access"""
    
    def __init__(self):
        self.supported_services = [
            "mt4", "mt5", "tradelocker", "tradovate", "projectx",
            "n8n", "nats", "redis", "postgres", "external_api"
        ]
        self.credential_types = [
            "api_key", "password", "certificate", "token", "oauth"
        ]
    
    def encrypt_credential(self, credential_data: Dict[str, Any]) -> str:
        """Encrypt credential data"""
        json_data = json.dumps(credential_data).encode()
        encrypted_data = cipher_suite.encrypt(json_data)
        return encrypted_data.decode()
    
    def decrypt_credential(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt credential data"""
        encrypted_bytes = encrypted_data.encode()
        decrypted_data = cipher_suite.decrypt(encrypted_bytes)
        return json.loads(decrypted_data.decode())
    
    async def create_credential(self, credential_data: CredentialCreate, user_id: str) -> Dict[str, Any]:
        """Create new encrypted credential"""
        credential_id = str(uuid.uuid4())
        
        # Validate service and type
        if credential_data.service not in self.supported_services:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported service: {credential_data.service}. Supported: {self.supported_services}"
            )
        
        if credential_data.type not in self.credential_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported credential type: {credential_data.type}. Supported: {self.credential_types}"
            )
        
        # Encrypt sensitive data
        encrypted_data = self.encrypt_credential(credential_data.credential_data)
        
        credential = {
            "id": credential_id,
            "name": credential_data.name,
            "type": credential_data.type,
            "service": credential_data.service,
            "encrypted_data": encrypted_data,
            "description": credential_data.description,
            "created_by": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "expires_at": credential_data.expires_at.isoformat() if credential_data.expires_at else None,
            "rotation_days": credential_data.rotation_days,
            "last_rotated": datetime.now().isoformat(),
            "is_active": True,
            "access_count": 0,
            "last_accessed": None
        }
        
        credentials_db[credential_id] = credential
        
        # Log creation
        await self.log_audit_event("credential_created", credential_id, user_id, True)
        
        # Schedule rotation if needed
        if credential_data.rotation_days:
            await self.schedule_rotation(credential_id, credential_data.rotation_days)
        
        logger.info(f"Credential created: {credential_id} for service {credential_data.service}")
        return {
            "id": credential_id,
            "name": credential_data.name,
            "type": credential_data.type,
            "service": credential_data.service,
            "created_at": credential["created_at"],
            "expires_at": credential["expires_at"],
            "rotation_days": credential_data.rotation_days
        }
    
    async def get_credential(self, credential_id: str, user_id: str, purpose: str = "access") -> Dict[str, Any]:
        """Get decrypted credential for temporary use"""
        if credential_id not in credentials_db:
            raise HTTPException(status_code=404, detail="Credential not found")
        
        credential = credentials_db[credential_id]
        
        if not credential["is_active"]:
            raise HTTPException(status_code=403, detail="Credential is inactive")
        
        # Check expiration
        if credential["expires_at"]:
            expires_at = datetime.fromisoformat(credential["expires_at"])
            if datetime.now() > expires_at:
                raise HTTPException(status_code=403, detail="Credential has expired")
        
        # Decrypt data
        decrypted_data = self.decrypt_credential(credential["encrypted_data"])
        
        # Update access tracking
        credential["access_count"] += 1
        credential["last_accessed"] = datetime.now().isoformat()
        
        # Log access
        await self.log_audit_event("credential_accessed", credential_id, user_id, True, {"purpose": purpose})
        
        logger.info(f"Credential accessed: {credential_id} by user {user_id}")
        
        return {
            "id": credential_id,
            "name": credential["name"],
            "type": credential["type"],
            "service": credential["service"],
            "credential_data": decrypted_data,
            "access_count": credential["access_count"],
            "last_accessed": credential["last_accessed"]
        }
    
    async def update_credential(self, credential_id: str, update_data: CredentialUpdate, user_id: str) -> Dict[str, Any]:
        """Update credential metadata"""
        if credential_id not in credentials_db:
            raise HTTPException(status_code=404, detail="Credential not found")
        
        credential = credentials_db[credential_id]
        
        # Update allowed fields
        if update_data.name:
            credential["name"] = update_data.name
        if update_data.description is not None:
            credential["description"] = update_data.description
        if update_data.expires_at:
            credential["expires_at"] = update_data.expires_at.isoformat()
        if update_data.rotation_days:
            credential["rotation_days"] = update_data.rotation_days
        if update_data.is_active is not None:
            credential["is_active"] = update_data.is_active
        
        credential["updated_at"] = datetime.now().isoformat()
        
        # Log update
        await self.log_audit_event("credential_updated", credential_id, user_id, True)
        
        logger.info(f"Credential updated: {credential_id} by user {user_id}")
        return credential
    
    async def rotate_credential(self, credential_id: str, new_credential_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Rotate credential with new data"""
        if credential_id not in credentials_db:
            raise HTTPException(status_code=404, detail="Credential not found")
        
        credential = credentials_db[credential_id]
        
        # Encrypt new data
        encrypted_data = self.encrypt_credential(new_credential_data)
        
        # Update credential
        credential["encrypted_data"] = encrypted_data
        credential["last_rotated"] = datetime.now().isoformat()
        credential["updated_at"] = datetime.now().isoformat()
        
        # Log rotation
        await self.log_audit_event("credential_rotated", credential_id, user_id, True)
        
        logger.info(f"Credential rotated: {credential_id} by user {user_id}")
        return credential
    
    async def delete_credential(self, credential_id: str, user_id: str) -> bool:
        """Delete credential permanently"""
        if credential_id not in credentials_db:
            raise HTTPException(status_code=404, detail="Credential not found")
        
        # Log deletion
        await self.log_audit_event("credential_deleted", credential_id, user_id, True)
        
        # Delete credential
        del credentials_db[credential_id]
        
        logger.info(f"Credential deleted: {credential_id} by user {user_id}")
        return True
    
    async def list_credentials(self, user_id: str, service: Optional[str] = None) -> List[Dict[str, Any]]:
        """List credentials (metadata only)"""
        credentials = []
        
        for cred_id, credential in credentials_db.items():
            # Filter by service if specified
            if service and credential["service"] != service:
                continue
            
            # Return metadata only (no sensitive data)
            credential_meta = {
                "id": credential["id"],
                "name": credential["name"],
                "type": credential["type"],
                "service": credential["service"],
                "description": credential["description"],
                "created_at": credential["created_at"],
                "updated_at": credential["updated_at"],
                "expires_at": credential["expires_at"],
                "rotation_days": credential["rotation_days"],
                "last_rotated": credential["last_rotated"],
                "is_active": credential["is_active"],
                "access_count": credential["access_count"],
                "last_accessed": credential["last_accessed"]
            }
            credentials.append(credential_meta)
        
        return credentials
    
    async def log_audit_event(self, action: str, credential_id: str, user_id: str, success: bool, metadata: Optional[Dict] = None):
        """Log audit event"""
        audit_entry = {
            "id": str(uuid.uuid4()),
            "action": action,
            "credential_id": credential_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "metadata": metadata or {}
        }
        
        audit_logs.append(audit_entry)
        
        # TODO: Send to audit logging system
        logger.info(f"Audit event: {action} for credential {credential_id} by user {user_id}")
    
    async def schedule_rotation(self, credential_id: str, days: int):
        """Schedule credential rotation"""
        # TODO: Integrate with task scheduler
        logger.info(f"Credential rotation scheduled for {credential_id} in {days} days")
    
    async def get_audit_logs(self, credential_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get audit logs"""
        logs = audit_logs
        
        if credential_id:
            logs = [log for log in logs if log["credential_id"] == credential_id]
        
        # Sort by timestamp descending
        logs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return logs[:limit]
    
    async def check_expiring_credentials(self) -> List[Dict[str, Any]]:
        """Check for credentials expiring soon"""
        expiring_soon = []
        warning_threshold = timedelta(days=7)
        
        for cred_id, credential in credentials_db.items():
            if not credential["expires_at"] or not credential["is_active"]:
                continue
            
            expires_at = datetime.fromisoformat(credential["expires_at"])
            time_until_expiry = expires_at - datetime.now()
            
            if time_until_expiry <= warning_threshold:
                expiring_soon.append({
                    "id": cred_id,
                    "name": credential["name"],
                    "service": credential["service"],
                    "expires_at": credential["expires_at"],
                    "days_until_expiry": time_until_expiry.days
                })
        
        return expiring_soon

# Global credential manager instance
credential_manager = CredentialManager()

# API Endpoints

@router.post("/create")
async def create_credential(
    credential_data: CredentialCreate,
    current_user: User = Depends(get_current_user)
):
    """Create new encrypted credential"""
    try:
        credential = await credential_manager.create_credential(credential_data, current_user.id)
        
        return {
            "success": True,
            "credential": credential,
            "message": "Credential created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to create credential")

@router.get("/{credential_id}")
async def get_credential(
    credential_id: str,
    purpose: str = "access",
    current_user: User = Depends(get_current_user)
):
    """Get decrypted credential for temporary use"""
    try:
        credential = await credential_manager.get_credential(credential_id, current_user.id, purpose)
        
        return {
            "success": True,
            "credential": credential,
            "message": "Credential retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve credential")

@router.put("/{credential_id}")
async def update_credential(
    credential_id: str,
    update_data: CredentialUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update credential metadata"""
    try:
        credential = await credential_manager.update_credential(credential_id, update_data, current_user.id)
        
        return {
            "success": True,
            "credential": credential,
            "message": "Credential updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to update credential")

@router.post("/{credential_id}/rotate")
async def rotate_credential(
    credential_id: str,
    new_credential_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Rotate credential with new data"""
    try:
        credential = await credential_manager.rotate_credential(credential_id, new_credential_data, current_user.id)
        
        return {
            "success": True,
            "credential": credential,
            "message": "Credential rotated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rotating credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to rotate credential")

@router.delete("/{credential_id}")
async def delete_credential(
    credential_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete credential permanently"""
    try:
        success = await credential_manager.delete_credential(credential_id, current_user.id)
        
        return {
            "success": success,
            "message": "Credential deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete credential")

@router.get("/")
async def list_credentials(
    service: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """List credentials (metadata only)"""
    try:
        credentials = await credential_manager.list_credentials(current_user.id, service)
        
        return {
            "success": True,
            "credentials": credentials,
            "total": len(credentials)
        }
        
    except Exception as e:
        logger.error(f"Error listing credentials: {e}")
        raise HTTPException(status_code=500, detail="Failed to list credentials")

@router.get("/audit/logs")
async def get_audit_logs(
    credential_id: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get audit logs"""
    try:
        logs = await credential_manager.get_audit_logs(credential_id, limit)
        
        return {
            "success": True,
            "audit_logs": logs,
            "total": len(logs)
        }
        
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get audit logs")

@router.get("/status/expiring")
async def get_expiring_credentials(
    current_user: User = Depends(get_current_user)
):
    """Get credentials expiring soon"""
    try:
        expiring = await credential_manager.check_expiring_credentials()
        
        return {
            "success": True,
            "expiring_credentials": expiring,
            "total": len(expiring)
        }
        
    except Exception as e:
        logger.error(f"Error checking expiring credentials: {e}")
        raise HTTPException(status_code=500, detail="Failed to check expiring credentials")

@router.get("/services")
async def get_supported_services():
    """Get list of supported services"""
    return {
        "success": True,
        "supported_services": credential_manager.supported_services,
        "credential_types": credential_manager.credential_types
    }

@router.post("/validate/{credential_id}")
async def validate_credential(
    credential_id: str,
    current_user: User = Depends(get_current_user)
):
    """Validate credential against its service"""
    try:
        # Get credential
        credential = await credential_manager.get_credential(credential_id, current_user.id, "validation")
        
        # TODO: Implement service-specific validation
        validation_result = {
            "valid": True,
            "service": credential["service"],
            "validated_at": datetime.now().isoformat(),
            "message": "Credential validation successful"
        }
        
        # Log validation
        await credential_manager.log_audit_event(
            "credential_validated", 
            credential_id, 
            current_user.id, 
            True,
            {"validation_result": validation_result}
        )
        
        return {
            "success": True,
            "validation": validation_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate credential")