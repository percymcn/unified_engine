"""
Credential Repository

SQLAlchemy implementation for persistent credential storage.
Uses centralized encryption service for all encrypt/decrypt operations.
"""
import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models import Credential
from app.core.encryption import get_encryption_service, EncryptionError

logger = logging.getLogger(__name__)


class CredentialRepository:
    """Repository for credential persistence with encryption."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._encryption = get_encryption_service()

    async def create(
        self,
        credential_id: str,
        user_id: int,
        name: str,
        credential_type: str,
        service: str,
        credential_data: dict,
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        rotation_days: Optional[int] = 90
    ) -> Credential:
        """Create new encrypted credential."""
        # Encrypt the credential data
        encrypted_data = self._encryption.encrypt_dict(credential_data)

        credential = Credential(
            id=credential_id,
            user_id=user_id,
            name=name,
            type=credential_type,
            service=service,
            encrypted_data=encrypted_data,
            description=description,
            expires_at=expires_at,
            rotation_days=rotation_days,
            last_rotated=datetime.utcnow(),
            is_active=True,
            access_count=0
        )

        self._session.add(credential)
        await self._session.flush()
        await self._session.refresh(credential)

        logger.info(f"Credential created: {credential_id} for service {service}")
        return credential

    async def get_by_id(self, credential_id: str) -> Optional[Credential]:
        """Get credential by ID."""
        result = await self._session.execute(
            select(Credential).where(Credential.id == credential_id)
        )
        return result.scalar_one_or_none()

    async def get_decrypted_data(self, credential_id: str) -> Optional[dict]:
        """Get decrypted credential data."""
        credential = await self.get_by_id(credential_id)
        if not credential:
            return None

        try:
            # Update access tracking
            credential.access_count += 1
            credential.last_accessed = datetime.utcnow()
            await self._session.flush()

            # Decrypt and return
            return self._encryption.decrypt_dict(credential.encrypted_data)
        except EncryptionError as e:
            logger.error(f"Failed to decrypt credential {credential_id}: {e}")
            raise

    async def list_by_user(
        self,
        user_id: int,
        service: Optional[str] = None,
        active_only: bool = True
    ) -> List[Credential]:
        """List credentials for a user (metadata only)."""
        conditions = [Credential.user_id == user_id]

        if service:
            conditions.append(Credential.service == service)
        if active_only:
            conditions.append(Credential.is_active == True)

        result = await self._session.execute(
            select(Credential).where(and_(*conditions))
        )
        return list(result.scalars().all())

    async def update(
        self,
        credential_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        rotation_days: Optional[int] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Credential]:
        """Update credential metadata."""
        credential = await self.get_by_id(credential_id)
        if not credential:
            return None

        if name is not None:
            credential.name = name
        if description is not None:
            credential.description = description
        if expires_at is not None:
            credential.expires_at = expires_at
        if rotation_days is not None:
            credential.rotation_days = rotation_days
        if is_active is not None:
            credential.is_active = is_active

        await self._session.flush()
        return credential

    async def rotate(
        self,
        credential_id: str,
        new_credential_data: dict
    ) -> Optional[Credential]:
        """Rotate credential with new encrypted data."""
        credential = await self.get_by_id(credential_id)
        if not credential:
            return None

        # Encrypt new data
        credential.encrypted_data = self._encryption.encrypt_dict(new_credential_data)
        credential.last_rotated = datetime.utcnow()

        await self._session.flush()
        logger.info(f"Credential rotated: {credential_id}")
        return credential

    async def delete(self, credential_id: str) -> bool:
        """Hard delete credential."""
        credential = await self.get_by_id(credential_id)
        if not credential:
            return False

        await self._session.delete(credential)
        await self._session.flush()
        logger.info(f"Credential deleted: {credential_id}")
        return True

    async def soft_delete(self, credential_id: str) -> bool:
        """Soft delete (deactivate) credential."""
        credential = await self.get_by_id(credential_id)
        if not credential:
            return False

        credential.is_active = False
        await self._session.flush()
        logger.info(f"Credential deactivated: {credential_id}")
        return True

    async def get_by_user_and_service(
        self,
        user_id: int,
        service: str,
        active_only: bool = True
    ) -> Optional[dict]:
        """
        Get decrypted credential data by user_id and service.

        Returns the first active credential found for the user/service combination.
        """
        conditions = [
            Credential.user_id == user_id,
            Credential.service == service
        ]
        if active_only:
            conditions.append(Credential.is_active == True)

        result = await self._session.execute(
            select(Credential).where(and_(*conditions)).limit(1)
        )
        credential = result.scalar_one_or_none()

        if not credential:
            return None

        try:
            # Update access tracking
            credential.access_count += 1
            credential.last_accessed = datetime.utcnow()
            await self._session.flush()

            # Decrypt and return
            return self._encryption.decrypt_dict(credential.encrypted_data)
        except EncryptionError as e:
            logger.error(f"Failed to decrypt credential for user {user_id}, service {service}: {e}")
            return None
