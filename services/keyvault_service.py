"""
Azure Key Vault Service

Retrieves vendor credentials from Azure Key Vault:
- Uses user's Microsoft token (delegated permissions)
- No secrets stored locally
- Centralized credential management
- NO FALLBACK - All credentials must be in Key Vault
"""

import os
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential, AzureCliCredential
from azure.core.exceptions import AzureError
from typing import Dict, Optional, List

from utils.logger import get_logger

logger = get_logger(__name__)


class KeyVaultError(Exception):
    """Raised when Key Vault operation fails"""
    pass


class KeyVaultService:
    """Service for retrieving vendor credentials from Azure Key Vault - NO FALLBACK"""

    _instance = None
    _cache: Dict[str, str] = {}

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to reuse client connection"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, vault_url: Optional[str] = None, credential=None, skip_connection_test: bool = False):
        """
        Initialize Key Vault service

        Args:
            vault_url: Key Vault URL (e.g., https://hrm-nexus-credentials.vault.azure.net/)
                      If None, will try to get from environment variable AZURE_KEYVAULT_URL
            credential: Azure credential object (optional, uses DefaultAzureCredential if not provided)
            skip_connection_test: Skip initial connection test (useful when credential requires user sign-in)

        Raises:
            KeyVaultError: If vault URL is not provided
        """
        # Skip if already initialized
        if self._initialized:
            return

        self.vault_url = vault_url or os.environ.get('AZURE_KEYVAULT_URL')

        if not self.vault_url:
            error_msg = (
                "Azure Key Vault URL not configured. Please set AZURE_KEYVAULT_URL environment variable "
                "or provide vault_url parameter. All credentials must be stored in Azure Key Vault."
            )
            logger.error(error_msg)
            raise KeyVaultError(error_msg)

        try:
            # Use provided credential or fall back to automatic detection
            if credential:
                self.credential = credential
                logger.info("Using provided credential for Key Vault (interactive browser auth)")
            else:
                # Try Azure CLI first, then fall back to DefaultAzureCredential
                try:
                    self.credential = AzureCliCredential()
                    # Test the credential
                    self.credential.get_token("https://vault.azure.net/.default")
                    logger.info("Using Azure CLI authentication for Key Vault")
                except Exception as cli_error:
                    logger.debug(f"Azure CLI auth failed: {cli_error}")
                    # Fall back to DefaultAzureCredential (managed identity, environment vars, etc.)
                    self.credential = DefaultAzureCredential()
                    logger.info("Using DefaultAzureCredential for Key Vault")

            # Create Key Vault client
            self.client = SecretClient(vault_url=self.vault_url, credential=self.credential)

            # Test connection (unless skipped - e.g., when credential requires user interaction)
            if not skip_connection_test:
                if not self.test_connection():
                    logger.warning("Key Vault connection test failed. Connection will be attempted when secrets are accessed.")
            else:
                logger.info("Key Vault connection test skipped (will authenticate when needed)")

            logger.info(f"✓ KeyVaultService initialized for {self.vault_url}")

        except KeyVaultError:
            raise
        except Exception as e:
            error_msg = f"Failed to initialize Azure Key Vault client: {e}"
            logger.error(error_msg)
            raise KeyVaultError(error_msg)

        self._initialized = True

    def get_secret(self, secret_name: str) -> str:
        """
        Get a single secret value from Key Vault

        Args:
            secret_name: Name of the secret

        Returns:
            Secret value

        Raises:
            KeyVaultError: If secret cannot be retrieved
        """
        # Check cache first
        if secret_name in self._cache:
            logger.debug(f"Retrieved secret '{secret_name}' from cache")
            return self._cache[secret_name]

        try:
            logger.debug(f"Getting secret: {secret_name}")
            secret = self.client.get_secret(secret_name)

            # Cache the secret
            self._cache[secret_name] = secret.value

            logger.info(f"✓ Retrieved secret '{secret_name}' from Key Vault")
            return secret.value

        except AzureError as e:
            error_str = str(e)

            # Provide user-friendly error messages based on the error type
            if "Invalid issuer" in error_str or "AKV10032" in error_str:
                user_msg = (
                    f"❌ Key Vault Access Denied - Tenant Mismatch\n\n"
                    f"Your Azure account's tenant is not authorized to access this Key Vault.\n"
                    f"The Key Vault may be in a different Azure tenant.\n\n"
                    f"Action Required:\n"
                    f"• Contact your administrator to verify the Key Vault configuration\n"
                    f"• Ensure the Key Vault is in the same tenant as your Nexus app registration\n"
                    f"• Or grant cross-tenant access if needed\n\n"
                    f"Secret: '{secret_name}'"
                )
            elif "Forbidden" in error_str or "403" in error_str:
                user_msg = (
                    f"❌ Key Vault Access Denied - Insufficient Permissions\n\n"
                    f"You don't have permission to read secrets from this Key Vault.\n\n"
                    f"Action Required:\n"
                    f"• Contact your administrator to grant you 'Key Vault Secrets User' role\n"
                    f"• Verify you are a member of the Nexus_Users group\n\n"
                    f"Secret: '{secret_name}'"
                )
            elif "not found" in error_str.lower() or "404" in error_str:
                user_msg = (
                    f"❌ Secret Not Found\n\n"
                    f"The secret '{secret_name}' does not exist in the Key Vault.\n\n"
                    f"Action Required:\n"
                    f"• Ask your administrator to create the secret in Azure Key Vault\n"
                    f"• Verify the secret name is correct: '{secret_name}'"
                )
            else:
                user_msg = f"❌ Key Vault Error: Failed to retrieve secret '{secret_name}'\n\nDetails: {error_str}"

            logger.error(user_msg)
            raise KeyVaultError(user_msg)
        except Exception as e:
            error_msg = f"❌ Unexpected Error: Failed to get secret '{secret_name}'\n\nDetails: {str(e)}"
            logger.error(error_msg)
            raise KeyVaultError(error_msg)

    def get_vendor_credential(self, vendor_name: str, credential_type: str) -> str:
        """
        Get a vendor credential using standardized naming convention

        Args:
            vendor_name: Vendor name (e.g., 'accountchek')
            credential_type: Type of credential (e.g., 'login-email', 'login-password', 'newuser-password')

        Returns:
            Credential value

        Raises:
            KeyVaultError: If credential cannot be retrieved
        """
        # Build secret name: {vendor}-{credential-type}
        # Azure Key Vault secret names can only contain alphanumeric characters and hyphens
        secret_name = f"{vendor_name.lower()}-{credential_type}".replace('_', '-')

        logger.debug(f"Getting vendor credential: {secret_name}")
        return self.get_secret(secret_name)

    def get_vendor_credentials(self, vendor_name: str) -> Dict[str, str]:
        """
        Retrieve vendor credentials from Key Vault

        Args:
            vendor_name: Name of vendor (e.g., "accountchek")

        Returns:
            Dictionary with login_email, login_password, login_url, newuser_password

        Raises:
            KeyVaultError: If credentials cannot be retrieved
        """
        logger.info(f"Retrieving credentials for vendor: {vendor_name}")

        try:
            # Retrieve secrets with naming convention: {vendor}-{credential-type}
            credentials = {
                'login_email': self.get_vendor_credential(vendor_name, 'login-email'),
                'login_password': self.get_vendor_credential(vendor_name, 'login-password'),
                'login_url': self.get_vendor_credential(vendor_name, 'login-url'),
                'newuser_password': self.get_vendor_credential(vendor_name, 'newuser-password')
            }

            logger.info(f"✓ Successfully retrieved all credentials for {vendor_name}")
            return credentials

        except KeyVaultError:
            raise
        except Exception as e:
            error_msg = f"Failed to retrieve credentials for {vendor_name}: {str(e)}"
            logger.error(error_msg)
            raise KeyVaultError(error_msg)

    def test_connection(self) -> bool:
        """
        Test connection to Key Vault

        Returns:
            True if connection successful, False otherwise
        """
        logger.info("Testing Key Vault connection")

        try:
            # Try to list properties (doesn't retrieve actual values)
            secret_properties = self.client.list_properties_of_secrets()
            # Just check if we can iterate (don't need to fetch all)
            next(secret_properties, None)
            logger.info("Key Vault connection test successful")
            return True
        except Exception as e:
            logger.error(f"Key Vault connection test failed: {e}")
            return False

    def __repr__(self):
        return f"<KeyVaultService {self.vault_url}>"


# Global instance (lazy initialization)
_keyvault_service: Optional[KeyVaultService] = None


def get_keyvault_service(vault_url: Optional[str] = None) -> KeyVaultService:
    """
    Get or create the global KeyVault service instance

    Args:
        vault_url: Key Vault URL (only used on first call)

    Returns:
        KeyVaultService instance

    Raises:
        KeyVaultError: If initialization fails
    """
    global _keyvault_service
    if _keyvault_service is None:
        _keyvault_service = KeyVaultService(vault_url=vault_url)
    return _keyvault_service
