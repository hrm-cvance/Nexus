"""
Configuration Manager Service

Handles loading and managing application configuration:
- Detects first run and initializes AppData directory
- Extracts embedded config files to AppData
- Loads and validates configuration
- Manages user settings
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """Manages application configuration and first-run initialization"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.appdata_root = self._get_appdata_path()
        self.config = None
        self.vendor_mappings = None
        self.user_settings = None

        # Load configurations
        self._load_configurations()

    def _get_appdata_path(self) -> Path:
        """Get the AppData path for Nexus"""
        if os.name == 'nt':  # Windows
            appdata = os.environ.get('APPDATA', '')
            if not appdata:
                appdata = Path.home() / 'AppData' / 'Roaming'
            return Path(appdata) / 'Nexus'
        else:  # macOS/Linux
            return Path.home() / '.nexus'

    def is_first_run(self) -> bool:
        """Check if this is the first run of the application"""
        return not (self.appdata_root / 'config' / 'app_config.json').exists()

    def initialize_first_run(self):
        """Initialize application on first run"""
        print("Initializing Nexus for first run...")

        # Create directory structure
        directories = [
            self.appdata_root / 'config',
            self.appdata_root / 'logs',
            self.appdata_root / 'screenshots',
            self.appdata_root / 'browsers'
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {directory}")

        # Copy config files from embedded resources to AppData
        config_files = [
            'app_config.json',
            'vendor_mappings.json'
        ]

        for config_file in config_files:
            source = self.project_root / 'config' / config_file
            destination = self.appdata_root / 'config' / config_file

            if source.exists():
                shutil.copy2(source, destination)
                print(f"Copied {config_file} to AppData")
            else:
                print(f"Warning: {config_file} not found in project directory")

        # Create default user settings
        default_settings = {
            "ui": {
                "theme": "dark",
                "show_screenshots": True,
                "auto_scroll_logs": True
            },
            "automation": {
                "headless_mode": False,
                "timeout_seconds": 120,
                "auto_retry": True
            }
        }

        settings_path = self.appdata_root / 'config' / 'user_settings.json'
        with open(settings_path, 'w') as f:
            json.dump(default_settings, f, indent=2)
        print("Created default user settings")

        print("First run initialization complete!")

    def _load_configurations(self):
        """Load all configuration files"""
        # Determine config directory (AppData if exists, else project directory)
        if (self.appdata_root / 'config').exists():
            config_dir = self.appdata_root / 'config'
        else:
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

        # Load user settings
        user_settings_path = config_dir / 'user_settings.json'
        if user_settings_path.exists():
            with open(user_settings_path, 'r') as f:
                self.user_settings = json.load(f)
        else:
            self.user_settings = {}

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

    def save_user_settings(self, settings: Dict[str, Any]):
        """Save user settings to file"""
        settings_path = self.appdata_root / 'config' / 'user_settings.json'
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
        self.user_settings = settings

    def get_log_path(self) -> Path:
        """Get the logs directory path"""
        return self.appdata_root / 'logs'

    def get_screenshots_path(self) -> Path:
        """Get the screenshots directory path"""
        return self.appdata_root / 'screenshots'

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
        return f"<ConfigManager appdata={self.appdata_root}>"
