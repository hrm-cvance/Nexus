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
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.logger import setup_logger
from services.config_manager import ConfigManager
from gui.main_window import NexusMainWindow

# Application metadata
APP_NAME = "Nexus"
APP_VERSION = "1.0.0"
APP_AUTHOR = "IT Department"


def setup_application():
    """
    Initialize application environment
    - Set up logging
    - Load configuration
    - Check for first run
    - Validate dependencies

    Note: Azure Key Vault is initialized in main_window.py after user signs in
    """
    # Set up logging
    logger = setup_logger(APP_NAME)
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")

    # Load configuration
    config_manager = ConfigManager()

    # Check if this is first run
    if config_manager.is_first_run():
        logger.info("First run detected - initializing application data")
        config_manager.initialize_first_run()

    # Note: Key Vault initialization happens in GUI after user authentication
    logger.info("Key Vault will be initialized when user signs in")

    return logger, config_manager


def main():
    """Main application entry point"""
    try:
        # Set up application
        logger, config_manager = setup_application()

        # Create and run GUI
        logger.info("Launching GUI")
        app = NexusMainWindow(config_manager)
        app.run()

    except Exception as e:
        print(f"Fatal error starting application: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
