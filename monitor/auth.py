"""
Nexus Monitor Authentication

Uses MSAL ConfidentialClientApplication for unattended client credentials flow.
Provides two adapters:
- token_provider callable for GraphAPIClient
- ServiceCredentialAdapter (TokenCredential) for KeyVaultService
"""

import msal
from azure.core.credentials import AccessToken, TokenCredential
from datetime import datetime, timezone
from typing import List, Optional
import logging

logger = logging.getLogger('NexusMonitor.auth')


class MonitorAuth:
    """MSAL ConfidentialClientApplication wrapper for client credentials flow"""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=self.authority
        )
        logger.info(f"MonitorAuth initialized for tenant {tenant_id}")

    def get_token(self, scopes: List[str]) -> Optional[str]:
        """Acquire token for the given scopes via client credentials flow"""
        result = self.app.acquire_token_for_client(scopes=scopes)
        if result and "access_token" in result:
            logger.debug("Token acquired via client credentials")
            return result["access_token"]

        error = result.get("error_description", result.get("error", "Unknown error"))
        logger.error(f"Failed to acquire token: {error}")
        return None

    def get_graph_token_provider(self):
        """Return a callable suitable for GraphAPIClient(token_provider=...)"""
        # Client credentials always uses .default scope regardless of what's passed
        def provider(scopes):
            return self.get_token(["https://graph.microsoft.com/.default"])
        return provider

    def get_keyvault_credential(self) -> 'ServiceCredentialAdapter':
        """Return a TokenCredential suitable for KeyVaultService"""
        return ServiceCredentialAdapter(self)


class ServiceCredentialAdapter(TokenCredential):
    """Adapts MonitorAuth to Azure Identity TokenCredential interface for Key Vault"""

    def __init__(self, monitor_auth: MonitorAuth):
        self.monitor_auth = monitor_auth

    def get_token(self, *scopes, **kwargs) -> AccessToken:
        requested_scopes = list(scopes) if scopes else ["https://vault.azure.net/.default"]
        token_str = self.monitor_auth.get_token(requested_scopes)

        if not token_str:
            raise Exception("Failed to acquire service token for Key Vault")

        expires_on = int(datetime.now(timezone.utc).timestamp()) + 3600
        return AccessToken(token_str, expires_on)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
