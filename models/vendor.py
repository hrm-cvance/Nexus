"""
Vendor Data Models

Represents vendor configuration and credentials
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class VendorConfig:
    """Configuration for a vendor system"""
    name: str
    display_name: str
    entra_group_name: Optional[str] = None

    # UI state
    is_selected: bool = False
    is_auto_detected: bool = False

    def __repr__(self):
        return f"<VendorConfig {self.display_name}>"
