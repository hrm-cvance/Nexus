"""
Vendor Data Models

Represents vendor configuration and credentials
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class FieldType(Enum):
    """Field types for vendor configuration"""
    TEXT = "text"
    EMAIL = "email"
    PASSWORD = "password"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    READONLY = "readonly"


@dataclass
class VendorField:
    """Represents a configurable field for a vendor"""
    name: str
    label: str
    field_type: FieldType
    required: bool = True
    default_value: Optional[str] = None
    options: List[str] = field(default_factory=list)
    entra_attribute: Optional[str] = None
    read_only: bool = False
    tooltip: Optional[str] = None
    depends_on: Optional[str] = None  # For cascading dropdowns
    validation_pattern: Optional[str] = None

    @classmethod
    def from_config(cls, config: Dict) -> 'VendorField':
        """Create VendorField from configuration dictionary"""
        field_type_str = config.get('type', 'text')
        field_type = FieldType(field_type_str)

        return cls(
            name=config['name'],
            label=config['label'],
            field_type=field_type,
            required=config.get('required', True),
            default_value=config.get('default_value'),
            options=config.get('options', []),
            entra_attribute=config.get('entra_attribute'),
            read_only=config.get('read_only', False),
            tooltip=config.get('tooltip'),
            depends_on=config.get('depends_on'),
            validation_pattern=config.get('validation_pattern')
        )


@dataclass
class PasswordRules:
    """Password complexity rules for vendor"""
    length: int = 16
    max_length: int = 128
    min_uppercase: int = 2
    min_lowercase: int = 2
    min_digits: int = 2
    min_special: int = 2
    allowed_special: str = "!@#$%^&*-_=+"
    excluded_chars: Optional[str] = None
    notes: Optional[str] = None

    @classmethod
    def from_config(cls, config: Dict) -> 'PasswordRules':
        """Create PasswordRules from configuration dictionary"""
        return cls(
            length=config.get('length', 16),
            max_length=config.get('max_length', 128),
            min_uppercase=config.get('min_uppercase', 2),
            min_lowercase=config.get('min_lowercase', 2),
            min_digits=config.get('min_digits', 2),
            min_special=config.get('min_special', 2),
            allowed_special=config.get('allowed_special', "!@#$%^&*-_=+"),
            excluded_chars=config.get('excluded_chars'),
            notes=config.get('notes')
        )


@dataclass
class VendorConfig:
    """Configuration for a vendor system"""
    name: str
    display_name: str
    logo_path: Optional[str] = None
    entra_group_name: Optional[str] = None
    entra_group_id: Optional[str] = None
    fields: List[VendorField] = field(default_factory=list)
    password_rules: Optional[PasswordRules] = None
    automation_module: Optional[str] = None
    enabled: bool = True

    # UI state
    is_selected: bool = False
    is_auto_detected: bool = False

    def __repr__(self):
        return f"<VendorConfig {self.display_name} (enabled={self.enabled})>"
