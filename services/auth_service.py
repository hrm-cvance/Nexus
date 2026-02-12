"""
Authentication Service

Handles Microsoft authentication using MSAL with delegated permissions:
- Interactive browser sign-in (no client secrets)
- Token management and refresh
- Single token for both Graph API and Key Vault
- Persistent token cache for remembering sign-in between sessions
"""

import os
import msal
from typing import List, Optional, Dict
from utils.logger import get_logger

logger = get_logger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class AuthService:
    """Microsoft authentication service using delegated permissions (PublicClientApplication)"""

    def __init__(self, tenant_id: str, client_id: str, redirect_uri: str = "http://localhost:8400"):
        """
        Initialize authentication service

        Args:
            tenant_id: Azure AD tenant ID
            client_id: Application (client) ID
            redirect_uri: Redirect URI for authentication flow
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"

        # Set up persistent token cache
        self._cache_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Nexus")
        self._cache_path = os.path.join(self._cache_dir, "token_cache.bin")
        self.token_cache = msal.SerializableTokenCache()
        self._load_cache()

        # Create MSAL PublicClientApplication with persistent cache
        self.msal_app = msal.PublicClientApplication(
            client_id=client_id,
            authority=self.authority,
            token_cache=self.token_cache
        )

        # Restore current account from cache if available
        accounts = self.msal_app.get_accounts()
        self.current_account = accounts[0] if accounts else None

        logger.info(f"AuthService initialized for tenant {tenant_id}")

    def _load_cache(self):
        """Load token cache from disk if it exists"""
        if os.path.exists(self._cache_path):
            try:
                with open(self._cache_path, "r") as f:
                    self.token_cache.deserialize(f.read())
                logger.info("Token cache loaded from disk")
            except Exception as e:
                logger.warning(f"Failed to load token cache: {e}")

    def _save_cache(self):
        """Save token cache to disk if it has changed"""
        if self.token_cache.has_state_changed:
            try:
                os.makedirs(self._cache_dir, exist_ok=True)
                with open(self._cache_path, "w") as f:
                    f.write(self.token_cache.serialize())
                logger.info("Token cache saved to disk")
            except Exception as e:
                logger.warning(f"Failed to save token cache: {e}")

    def sign_in_interactive(self, scopes: List[str]) -> Dict:
        """
        Interactive browser sign-in for user
        Opens system browser for Microsoft authentication

        Args:
            scopes: List of permission scopes to request

        Returns:
            Token response dictionary with access_token, refresh_token, etc.

        Raises:
            AuthenticationError: If sign-in fails
        """
        logger.info("Starting interactive sign-in")
        logger.debug(f"Requested scopes: {scopes}")

        try:
            # Try silent authentication first (if cached token exists)
            accounts = self.msal_app.get_accounts()
            if accounts:
                logger.info(f"Found {len(accounts)} cached account(s)")
                result = self.msal_app.acquire_token_silent(scopes=scopes, account=accounts[0])
                if result and "access_token" in result:
                    logger.info("Successfully acquired token silently from cache")
                    self.current_account = accounts[0]
                    return result

            # No cached token, perform interactive sign-in
            logger.info("No cached token found, opening browser for authentication")
            result = self.msal_app.acquire_token_interactive(
                scopes=scopes,
                prompt="select_account"  # Allow user to select account
            )

            if "access_token" in result:
                logger.info("Interactive sign-in successful")
                self._save_cache()
                accounts = self.msal_app.get_accounts()
                if accounts:
                    self.current_account = accounts[0]
                    logger.info(f"Signed in as: {self.current_account.get('username', 'Unknown')}")
                return result
            else:
                error_desc = result.get("error_description", "Unknown error")
                logger.error(f"Sign-in failed: {error_desc}")
                raise AuthenticationError(f"Sign-in failed: {error_desc}")

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise AuthenticationError(f"Authentication failed: {str(e)}")

    def get_token_silent(self, scopes: List[str]) -> Optional[str]:
        """
        Get access token silently (from cache or refresh)

        Args:
            scopes: List of permission scopes

        Returns:
            Access token string, or None if not available
        """
        accounts = self.msal_app.get_accounts()
        if not accounts:
            logger.warning("No accounts in cache")
            return None

        result = self.msal_app.acquire_token_silent(scopes=scopes, account=accounts[0])

        if result and "access_token" in result:
            logger.debug("Token acquired silently")
            return result["access_token"]

        logger.warning("Could not acquire token silently")
        return None

    def sign_out(self):
        """Sign out and clear cached tokens"""
        logger.info("Signing out")
        accounts = self.msal_app.get_accounts()

        for account in accounts:
            logger.debug(f"Removing account: {account.get('username', 'Unknown')}")
            self.msal_app.remove_account(account)

        self.current_account = None

        # Delete the cache file entirely so no tokens persist on disk
        if os.path.exists(self._cache_path):
            try:
                os.remove(self._cache_path)
                logger.info("Token cache file deleted from disk")
            except Exception as e:
                logger.warning(f"Failed to delete token cache file: {e}")

        logger.info("Sign-out complete")

    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        accounts = self.msal_app.get_accounts()
        return len(accounts) > 0

    def get_current_user(self) -> Optional[Dict]:
        """Get current signed-in user account info"""
        if self.current_account:
            return {
                "username": self.current_account.get("username"),
                "name": self.current_account.get("name"),
                "environment": self.current_account.get("environment")
            }
        return None

    def get_current_username(self) -> Optional[str]:
        """Get username of current signed-in user"""
        if self.current_account:
            return self.current_account.get("username")
        return None

    def __repr__(self):
        username = self.get_current_username() or "Not signed in"
        return f"<AuthService {username}>"
