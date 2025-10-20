"""
MSAL to Azure Identity Credential Adapter

Adapts MSAL PublicClientApplication tokens to work with Azure Identity SDK.
This allows using the same user sign-in for both Microsoft Graph API and Azure Key Vault.
"""

from azure.core.credentials import AccessToken, TokenCredential
from typing import List, Optional
from datetime import datetime, timezone
from services.auth_service import AuthService
from utils.logger import get_logger

logger = get_logger(__name__)


class MSALCredentialAdapter(TokenCredential):
    """
    Adapts MSAL authentication to Azure Identity TokenCredential interface.

    This allows using the same interactive browser sign-in for both:
    - Microsoft Graph API (via MSAL)
    - Azure Key Vault (via Azure Identity SDK)
    """

    def __init__(self, auth_service: AuthService, scopes: Optional[List[str]] = None):
        """
        Initialize the credential adapter

        Args:
            auth_service: AuthService instance (already signed in)
            scopes: Default scopes to request (defaults to Azure Resource Manager)
        """
        self.auth_service = auth_service

        # Default to Azure Resource Manager scope (works for Key Vault)
        # Key Vault scope is: https://vault.azure.net/.default
        self.default_scopes = scopes or ["https://vault.azure.net/.default"]

        logger.info("MSALCredentialAdapter initialized")

    def get_token(self, *scopes, **kwargs) -> AccessToken:
        """
        Get an access token for the specified scopes

        Args:
            *scopes: Resource scopes to request
            **kwargs: Additional keyword arguments (claims, tenant_id, etc.)

        Returns:
            AccessToken with token string and expiration time

        Raises:
            Exception: If token cannot be acquired
        """
        # Use provided scopes or fall back to defaults
        requested_scopes = list(scopes) if scopes else self.default_scopes

        logger.debug(f"Getting token for scopes: {requested_scopes}")

        try:
            # Try to get token silently first (from cache)
            token_str = self.auth_service.get_token_silent(requested_scopes)

            if not token_str:
                # Token not in cache, need to sign in interactively
                logger.info("No cached token, requesting interactive sign-in")
                result = self.auth_service.sign_in_interactive(requested_scopes)
                token_str = result.get("access_token")
                expires_on = result.get("expires_in", 3600)  # Default 1 hour

                # Convert expires_in (seconds from now) to expires_on (Unix timestamp)
                expires_on_timestamp = int(datetime.now(timezone.utc).timestamp()) + expires_on
            else:
                # We have a cached token, but we don't have expires_on
                # Request it again silently to get full token info
                accounts = self.auth_service.msal_app.get_accounts()
                if accounts:
                    result = self.auth_service.msal_app.acquire_token_silent(
                        scopes=requested_scopes,
                        account=accounts[0]
                    )
                    if result and "access_token" in result:
                        token_str = result["access_token"]
                        expires_on_timestamp = result.get("expires_on",
                            int(datetime.now(timezone.utc).timestamp()) + 3600)
                    else:
                        # Fallback: assume 1 hour expiration
                        expires_on_timestamp = int(datetime.now(timezone.utc).timestamp()) + 3600
                else:
                    # No account info, assume 1 hour
                    expires_on_timestamp = int(datetime.now(timezone.utc).timestamp()) + 3600

            if not token_str:
                raise Exception("Failed to acquire access token")

            logger.debug(f"Token acquired, expires at: {expires_on_timestamp}")

            # Return Azure Identity SDK compatible AccessToken
            return AccessToken(token_str, expires_on_timestamp)

        except Exception as e:
            logger.error(f"Failed to get token: {e}")
            raise

    def close(self):
        """Close any resources (not needed for MSAL adapter)"""
        pass

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
