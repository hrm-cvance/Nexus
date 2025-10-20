"""
Microsoft Graph API Client

Handles queries to Microsoft Entra ID (Azure AD):
- User search
- User details retrieval
- Group membership queries
"""

import requests
from typing import List, Optional, Dict
from enum import Enum

from services.auth_service import AuthService
from models.user import EntraUser, EntraGroup
from utils.logger import get_logger

logger = get_logger(__name__)


class SearchType(Enum):
    """Types of user search"""
    EMAIL = "mail"
    FIRST_NAME = "givenName"
    LAST_NAME = "surname"
    DISPLAY_NAME = "displayName"
    EMPLOYEE_ID = "employeeId"
    USER_PRINCIPAL_NAME = "userPrincipalName"


class GraphAPIError(Exception):
    """Raised when Graph API request fails"""
    pass


class GraphAPIClient:
    """Microsoft Graph API client for Entra ID queries"""

    BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self, auth_service: AuthService, scopes: List[str]):
        """
        Initialize Graph API client

        Args:
            auth_service: Authenticated AuthService instance
            scopes: Required API scopes
        """
        self.auth_service = auth_service
        self.scopes = scopes
        logger.info("GraphAPIClient initialized")

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers with current token"""
        token = self.auth_service.get_token_silent(self.scopes)
        if not token:
            raise GraphAPIError("No access token available. Please sign in.")

        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def _make_request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        """
        Make authenticated request to Graph API

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., /users)
            params: Query parameters

        Returns:
            Response JSON

        Raises:
            GraphAPIError: If request fails
        """
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()

        # Check if ConsistencyLevel is needed (for advanced queries like $search)
        if params and "ConsistencyLevel" in params:
            headers["ConsistencyLevel"] = params["ConsistencyLevel"]
            del params["ConsistencyLevel"]  # Remove from params, it's a header

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"Graph API HTTP error: {e}")
            if e.response.status_code == 401:
                raise GraphAPIError("Authentication failed. Please sign in again.")
            elif e.response.status_code == 403:
                raise GraphAPIError("Insufficient permissions to access this resource.")
            else:
                raise GraphAPIError(f"API request failed: {e}")

        except requests.exceptions.ConnectionError:
            logger.error("Connection error to Graph API")
            raise GraphAPIError("Unable to connect to Microsoft Graph API. Check your internet connection.")

        except requests.exceptions.Timeout:
            logger.error("Graph API request timeout")
            raise GraphAPIError("Request timed out. Please try again.")

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise GraphAPIError(f"Unexpected error: {str(e)}")

    def test_connection(self) -> bool:
        """Test connection to Graph API"""
        try:
            self._make_request("GET", "/me")
            logger.info("Graph API connection test successful")
            return True
        except Exception as e:
            logger.error(f"Graph API connection test failed: {e}")
            return False

    def search_users(self, query: str, search_type: SearchType = SearchType.DISPLAY_NAME) -> List[EntraUser]:
        """
        Search for users in Entra ID

        Args:
            query: Search query string
            search_type: Type of search (email, name, etc.)

        Returns:
            List of EntraUser objects matching search
        """
        logger.info(f"Searching users: {search_type.value} = '{query}'")

        # Select fields to retrieve
        select_fields = "id,displayName,givenName,surname,mail,userPrincipalName,jobTitle,department,officeLocation,employeeId,mobilePhone,businessPhones"

        # Build query parameters
        params = {
            "$select": select_fields,
            "$top": 50  # Limit results
        }

        # Use $search for display name (better fuzzy matching)
        # Use $filter for exact matches (email, employee ID)
        if search_type == SearchType.DISPLAY_NAME:
            # $search provides better partial matching (searches displayName and mail)
            params["$search"] = f'"displayName:{query}" OR "mail:{query}"'
            params["$count"] = "true"
            params["$orderby"] = "displayName"
            # Add ConsistencyLevel header for advanced query
            params["ConsistencyLevel"] = "eventual"
        elif search_type == SearchType.EMAIL:
            params["$filter"] = f"startswith(mail,'{query}') or startswith(userPrincipalName,'{query}')"
        elif search_type == SearchType.FIRST_NAME:
            params["$filter"] = f"startswith(givenName,'{query}')"
        elif search_type == SearchType.LAST_NAME:
            params["$filter"] = f"startswith(surname,'{query}')"
        else:
            params["$filter"] = f"{search_type.value} eq '{query}'"

        try:
            response = self._make_request("GET", "/users", params=params)
            users_data = response.get("value", [])

            logger.info(f"Found {len(users_data)} user(s)")

            # Convert to EntraUser objects
            users = [EntraUser.from_graph_api(user_data) for user_data in users_data]
            return users

        except Exception as e:
            logger.error(f"User search failed: {e}")
            raise

    def get_user_details(self, user_id: str) -> EntraUser:
        """
        Get full details for a specific user

        Args:
            user_id: User's object ID or userPrincipalName

        Returns:
            EntraUser object with full details
        """
        logger.info(f"Getting details for user: {user_id}")

        select_fields = "id,displayName,givenName,surname,mail,userPrincipalName,jobTitle,department,officeLocation,employeeId,mobilePhone,businessPhones"

        params = {"$select": select_fields}

        try:
            response = self._make_request("GET", f"/users/{user_id}", params=params)
            user = EntraUser.from_graph_api(response)

            # Get group memberships
            user.groups = self.get_user_groups(user_id)

            logger.info(f"Retrieved details for {user.display_name} ({len(user.groups)} groups)")
            return user

        except Exception as e:
            logger.error(f"Failed to get user details: {e}")
            raise

    def get_user_groups(self, user_id: str) -> List[EntraGroup]:
        """
        Get group memberships for a user

        Args:
            user_id: User's object ID

        Returns:
            List of EntraGroup objects
        """
        logger.debug(f"Getting groups for user: {user_id}")

        params = {"$select": "id,displayName,description,mail"}

        try:
            response = self._make_request("GET", f"/users/{user_id}/memberOf", params=params)
            groups_data = response.get("value", [])

            # Filter to only security groups (not other object types)
            groups = []
            for group_data in groups_data:
                if group_data.get("@odata.type") == "#microsoft.graph.group":
                    group = EntraGroup(
                        id=group_data.get("id"),
                        display_name=group_data.get("displayName", ""),
                        description=group_data.get("description"),
                        mail=group_data.get("mail")
                    )
                    groups.append(group)

            logger.debug(f"User is member of {len(groups)} group(s)")
            return groups

        except Exception as e:
            logger.error(f"Failed to get user groups: {e}")
            return []

    def get_user_photo(self, user_id: str) -> Optional[bytes]:
        """
        Get user's profile photo

        Args:
            user_id: User's object ID

        Returns:
            Photo data as bytes, or None if no photo
        """
        logger.debug(f"Getting photo for user: {user_id}")

        try:
            url = f"{self.BASE_URL}/users/{user_id}/photo/$value"
            headers = self._get_headers()

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                logger.debug("Photo retrieved successfully")
                return response.content
            else:
                logger.debug("No photo available for user")
                return None

        except Exception as e:
            logger.debug(f"Could not retrieve photo: {e}")
            return None

    def __repr__(self):
        return f"<GraphAPIClient connected={self.auth_service.is_authenticated()}>"
