"""
Nexus - Automated Vendor Account Provisioning
Main Application Entry Point

This application automates the creation of vendor accounts by:
- Connecting to Microsoft Entra ID via Graph API
- Retrieving vendor credentials from Azure Key Vault
- Automating account creation using Playwright browser automation
"""

import sys
import os
import subprocess
from pathlib import Path

# Add project root to path (handles both normal and PyInstaller frozen state)
if getattr(sys, 'frozen', False):
    project_root = Path(sys._MEIPASS)
else:
    project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.logger import setup_logger
from services.config_manager import ConfigManager
from gui.main_window import NexusMainWindow

# Application metadata
APP_NAME = "Nexus"
APP_VERSION = "1.0.1"
APP_AUTHOR = "IT Department"


def setup_application():
    """
    Initialize application environment
    - Set up logging
    - Load configuration

    Note: Azure Key Vault is initialized in main_window.py after user signs in
    """
    logger = setup_logger(APP_NAME)
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")

    config_manager = ConfigManager()

    return logger, config_manager


def install_browsers():
    """Install Playwright Chromium browser using the bundled driver"""
    try:
        from playwright._impl._driver import compute_driver_executable, get_driver_env
        driver = compute_driver_executable()
        env = get_driver_env()
        print(f"Installing Playwright Chromium browser...")
        print(f"Driver: {driver}")
        result = subprocess.run(
            [str(driver), "install", "chromium"],
            env=env,
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return result.returncode
        print("Chromium browser installed successfully.")
        return 0
    except Exception as e:
        print(f"Failed to install browsers: {e}")
        return 1


def main():
    """Main application entry point"""
    # Handle CLI flags (used by Intune deployment scripts)
    if "--install-browsers" in sys.argv:
        sys.exit(install_browsers())

    try:
        # Set up application
        logger, config_manager = setup_application()

        # Create and run GUI
        logger.info("Launching GUI")
        app = NexusMainWindow(config_manager, version=APP_VERSION)
        app.run()

    except Exception as e:
        print(f"Fatal error starting application: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
