"""
Automation Result Models

Data classes for storing automation results with timestamps for PDF reporting.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

from models.user import EntraUser


@dataclass
class VendorResult:
    """Result of a single vendor automation"""
    vendor_name: str
    display_name: str
    success: bool
    start_time: datetime
    end_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    screenshot_path: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


@dataclass
class AutomationSummary:
    """Complete automation session summary"""
    user: EntraUser
    vendor_results: List[VendorResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    @property
    def success_count(self) -> int:
        """Count of successful vendor automations"""
        return sum(1 for v in self.vendor_results if v.success)

    @property
    def failure_count(self) -> int:
        """Count of failed vendor automations"""
        return sum(1 for v in self.vendor_results if not v.success)

    @property
    def total_duration_seconds(self) -> float:
        """Total duration in seconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
