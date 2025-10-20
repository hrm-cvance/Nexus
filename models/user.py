"""
User Data Model

Represents a user from Microsoft Entra ID
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class EntraGroup:
    """Represents an Entra ID group"""
    id: str
    display_name: str
    description: Optional[str] = None
    mail: Optional[str] = None


@dataclass
class EntraUser:
    """Represents a user from Microsoft Entra ID"""

    # Required fields
    id: str
    display_name: str
    user_principal_name: str

    # Optional fields
    given_name: Optional[str] = None
    surname: Optional[str] = None
    mail: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    office_location: Optional[str] = None
    employee_id: Optional[str] = None
    mobile_phone: Optional[str] = None
    business_phones: List[str] = field(default_factory=list)
    photo_url: Optional[str] = None
    photo_data: Optional[bytes] = None

    # Group memberships
    groups: List[EntraGroup] = field(default_factory=list)

    # Metadata
    created_datetime: Optional[datetime] = None
    last_sign_in: Optional[datetime] = None

    @classmethod
    def from_graph_api(cls, graph_data: dict) -> 'EntraUser':
        """
        Create EntraUser from Microsoft Graph API response

        Args:
            graph_data: User data from Graph API

        Returns:
            EntraUser instance
        """
        return cls(
            id=graph_data.get('id', ''),
            display_name=graph_data.get('displayName', ''),
            user_principal_name=graph_data.get('userPrincipalName', ''),
            given_name=graph_data.get('givenName'),
            surname=graph_data.get('surname'),
            mail=graph_data.get('mail'),
            job_title=graph_data.get('jobTitle'),
            department=graph_data.get('department'),
            office_location=graph_data.get('officeLocation'),
            employee_id=graph_data.get('employeeId'),
            mobile_phone=graph_data.get('mobilePhone'),
            business_phones=graph_data.get('businessPhones', [])
        )

    @property
    def full_name(self) -> str:
        """Get full name from given name and surname"""
        if self.given_name and self.surname:
            return f"{self.given_name} {self.surname}"
        return self.display_name

    @property
    def email(self) -> str:
        """Get email address (prefer mail over userPrincipalName)"""
        return self.mail or self.user_principal_name

    @property
    def group_names(self) -> List[str]:
        """Get list of group display names"""
        return [group.display_name for group in self.groups]

    def is_member_of(self, group_name: str) -> bool:
        """Check if user is member of a specific group"""
        return group_name in self.group_names

    def __repr__(self):
        return f"<EntraUser {self.display_name} ({self.email})>"
