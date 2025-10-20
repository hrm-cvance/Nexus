"""
Automation Result Data Model

Represents the result of a vendor automation run
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class AutomationStatus(Enum):
    """Status of automation execution"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"
    DUPLICATE = "duplicate"


class ErrorType(Enum):
    """Types of errors that can occur"""
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    DUPLICATE_ACCOUNT = "duplicate_account"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class LogEntry:
    """Single log entry from automation"""
    timestamp: datetime
    level: str  # DEBUG, INFO, WARNING, ERROR, SUCCESS
    message: str
    vendor_name: str

    def __repr__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] [{self.level}] {self.message}"


@dataclass
class AutomationResult:
    """Result of a vendor automation run"""
    vendor_name: str
    status: AutomationStatus = AutomationStatus.NOT_STARTED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    error_type: Optional[ErrorType] = None
    screenshots: List[str] = field(default_factory=list)
    log_entries: List[LogEntry] = field(default_factory=list)
    progress_percent: int = 0
    current_step: str = ""

    # Account details
    created_account_email: Optional[str] = None
    created_account_username: Optional[str] = None
    temporary_password: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        """Get duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def is_complete(self) -> bool:
        """Check if automation is complete (success or error)"""
        return self.status in [AutomationStatus.SUCCESS, AutomationStatus.ERROR, AutomationStatus.SKIPPED]

    @property
    def is_successful(self) -> bool:
        """Check if automation completed successfully"""
        return self.status == AutomationStatus.SUCCESS

    @property
    def is_error(self) -> bool:
        """Check if automation ended in error"""
        return self.status == AutomationStatus.ERROR

    @property
    def status_emoji(self) -> str:
        """Get emoji for current status"""
        emoji_map = {
            AutomationStatus.NOT_STARTED: "🔴",
            AutomationStatus.IN_PROGRESS: "🟡",
            AutomationStatus.SUCCESS: "🟢",
            AutomationStatus.ERROR: "🟠",
            AutomationStatus.SKIPPED: "⚪",
            AutomationStatus.DUPLICATE: "🟠"
        }
        return emoji_map.get(self.status, "⚪")

    def add_log(self, level: str, message: str):
        """Add a log entry"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            vendor_name=self.vendor_name
        )
        self.log_entries.append(entry)

    def add_screenshot(self, screenshot_path: str):
        """Add a screenshot path"""
        self.screenshots.append(screenshot_path)

    def update_progress(self, percent: int, step: str):
        """Update progress"""
        self.progress_percent = min(100, max(0, percent))
        self.current_step = step

    def mark_started(self):
        """Mark automation as started"""
        self.status = AutomationStatus.IN_PROGRESS
        self.start_time = datetime.now()

    def mark_success(self, account_email: str = None):
        """Mark automation as successful"""
        self.status = AutomationStatus.SUCCESS
        self.end_time = datetime.now()
        self.progress_percent = 100
        if account_email:
            self.created_account_email = account_email

    def mark_error(self, error_message: str, error_type: ErrorType = ErrorType.UNKNOWN_ERROR):
        """Mark automation as failed"""
        self.status = AutomationStatus.ERROR
        self.end_time = datetime.now()
        self.error_message = error_message
        self.error_type = error_type

    def mark_duplicate(self, email: str):
        """Mark as duplicate account"""
        self.status = AutomationStatus.ERROR
        self.end_time = datetime.now()
        self.error_type = ErrorType.DUPLICATE_ACCOUNT
        self.error_message = f"Account already exists for {email}"

    def get_summary(self) -> dict:
        """Get summary dictionary for reporting"""
        return {
            "vendor": self.vendor_name,
            "status": self.status.value,
            "duration": self.duration,
            "error": self.error_message,
            "account_created": self.created_account_email,
            "screenshots_count": len(self.screenshots),
            "log_entries_count": len(self.log_entries)
        }

    def __repr__(self):
        return f"<AutomationResult {self.vendor_name} {self.status.value}>"
