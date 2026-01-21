"""
Tradovate Token Service

Handles secure storage and automatic refresh of Tradovate OAuth tokens.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.core.encryption import encrypt, decrypt
from app.models.database_models import TradingAccount, BrokerType

logger = logging.getLogger(__name__)

# Refresh tokens 5 minutes before expiry
REFRESH_BUFFER_SECONDS = 300


class TradovateTokenService:
    """Manages Tradovate OAuth token lifecycle."""

    def __init__(self, db: Session):
        self.db = db

    def store_tokens(
        self,
        account: TradingAccount,
        access_token: str,
        refresh_token: Optional[str],
        expires_in: int,
        environment: str,
    ) -> None:
        """
        Store OAuth tokens with encryption.

        Args:
            account: TradingAccount to update
            access_token: OAuth access token
            refresh_token: OAuth refresh token (optional)
            expires_in: Token lifetime in seconds
            environment: "demo" or "live"
        """
        account.access_token = encrypt(access_token)
        if refresh_token:
            account.refresh_token = encrypt(refresh_token)
        account.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        account.oauth_environment = environment
        self.db.commit()
        logger.info(f"Stored tokens for account {account.id}, expires at {account.token_expires_at}")

    def get_access_token(self, account: TradingAccount) -> Optional[str]:
        """
        Get decrypted access token, refreshing if necessary.

        Args:
            account: TradingAccount to get token for

        Returns:
            Decrypted access token, or None if refresh failed
        """
        if not account.access_token:
            return None

        # Check if refresh needed
        if self._needs_refresh(account):
            if not self._refresh_token(account):
                return None

        return decrypt(account.access_token)

    def _needs_refresh(self, account: TradingAccount) -> bool:
        """Check if token needs refreshing."""
        if not account.token_expires_at:
            return False  # No expiry tracked, assume valid

        refresh_threshold = datetime.utcnow() + timedelta(seconds=REFRESH_BUFFER_SECONDS)
        return account.token_expires_at <= refresh_threshold

    def _refresh_token(self, account: TradingAccount) -> bool:
        """
        Refresh the access token using the refresh token.

        Returns:
            True if refresh successful, False otherwise
        """
        if not account.refresh_token:
            logger.warning(f"No refresh token for account {account.id}")
            return False

        try:
            refresh_token = decrypt(account.refresh_token)
            environment = account.oauth_environment or "demo"

            api_base = (
                "https://live.tradovateapi.com/v1"
                if environment == "live"
                else "https://demo.tradovateapi.com/v1"
            )

            # Synchronous request (use httpx sync client)
            with httpx.Client() as client:
                response = client.post(
                    f"{api_base}/auth/renewaccesstoken",
                    json={"refreshToken": refresh_token},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    logger.error(f"Token refresh failed: {response.text}")
                    return False

                data = response.json()

            # Store new tokens
            new_access = data.get("accessToken")
            new_refresh = data.get("refreshToken")  # May or may not be provided
            expires_in = data.get("expiresIn", 3600)

            if new_access:
                account.access_token = encrypt(new_access)
                account.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                if new_refresh:
                    account.refresh_token = encrypt(new_refresh)
                self.db.commit()
                logger.info(f"Refreshed token for account {account.id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Token refresh error for account {account.id}: {e}")
            return False

    async def refresh_token_async(self, account: TradingAccount) -> bool:
        """
        Async version of token refresh.

        Returns:
            True if refresh successful, False otherwise
        """
        if not account.refresh_token:
            logger.warning(f"No refresh token for account {account.id}")
            return False

        try:
            refresh_token = decrypt(account.refresh_token)
            environment = account.oauth_environment or "demo"

            api_base = (
                "https://live.tradovateapi.com/v1"
                if environment == "live"
                else "https://demo.tradovateapi.com/v1"
            )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{api_base}/auth/renewaccesstoken",
                    json={"refreshToken": refresh_token},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    logger.error(f"Token refresh failed: {response.text}")
                    return False

                data = response.json()

            # Store new tokens
            new_access = data.get("accessToken")
            new_refresh = data.get("refreshToken")
            expires_in = data.get("expiresIn", 3600)

            if new_access:
                account.access_token = encrypt(new_access)
                account.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                if new_refresh:
                    account.refresh_token = encrypt(new_refresh)
                self.db.commit()
                logger.info(f"Refreshed token for account {account.id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Token refresh error for account {account.id}: {e}")
            return False


def get_tradovate_token_service(db: Session) -> TradovateTokenService:
    """Factory function for dependency injection."""
    return TradovateTokenService(db)
