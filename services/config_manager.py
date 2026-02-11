"""
Configuration Manager Service

Handles loading and managing application configuration:
- Loads app config and vendor mappings from bundled resources
- Validates configuration completeness
"""

import os
import sys
import json
from pathlib import Path
from typing import Any


class ConfigManager:
    """Manages application configuration"""

    def __init__(self):
        # When running as a PyInstaller bundle, data files are extracted to sys._MEIPASS
        if getattr(sys, 'frozen', False):
            self.project_root = Path(sys._MEIPASS)
        else:
            self.project_root = Path(__file__).parent.parent

        self.config = None
        self.vendor_mappings = None

        # Load configurations from bundled resources
        self._load_configurations()

    def _load_configurations(self):
        """Load all configuration files from bundled resources"""
        config_dir = self.project_root / 'config'

        # Load app config
        app_config_path = config_dir / 'app_config.json'
        if app_config_path.exists():
            with open(app_config_path, 'r') as f:
                self.config = json.load(f)
        else:
            raise FileNotFoundError(f"app_config.json not found at {app_config_path}")

        # Load vendor mappings
        vendor_mappings_path = config_dir / 'vendor_mappings.json'
        if vendor_mappings_path.exists():
            with open(vendor_mappings_path, 'r') as f:
                self.vendor_mappings = json.load(f)
        else:
            self.vendor_mappings = {"mappings": []}

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation path
        Example: config_manager.get('microsoft.tenant_id')
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def get_vendor_mappings(self) -> list:
        """Get all vendor mappings"""
        return self.vendor_mappings.get('mappings', [])

    def get_enabled_vendors(self) -> list:
        """Get only enabled vendor mappings"""
        return [v for v in self.get_vendor_mappings() if v.get('enabled', True)]

    def get_disabled_vendors(self) -> list:
        """Get only disabled vendor mappings"""
        return [v for v in self.get_vendor_mappings() if not v.get('enabled', True)]

    def validate_configuration(self) -> tuple[bool, list]:
        """
        Validate configuration completeness
        Returns: (is_valid, list_of_errors)
        """
        errors = []

        # Check Microsoft configuration
        tenant_id = self.get('microsoft.tenant_id')
        client_id = self.get('microsoft.client_id')

        if not tenant_id or tenant_id == 'REPLACE_WITH_YOUR_TENANT_ID':
            errors.append("Microsoft Tenant ID not configured")

        if not client_id or client_id == 'REPLACE_WITH_YOUR_CLIENT_ID':
            errors.append("Microsoft Client ID not configured")

        # Check Key Vault configuration
        vault_url = self.get('azure_keyvault.vault_url')
        if not vault_url:
            errors.append("Azure Key Vault URL not configured")

        return (len(errors) == 0, errors)

    def __repr__(self):
        return f"<ConfigManager project_root={self.project_root}>"
