"""
Nexus Monitor - Standalone Polling Service

A headless background service that runs registered jobs on configurable intervals.
Uses MSAL client credentials for unattended authentication (no user sign-in required).

Usage:
    python monitor.py              # Run as polling service
    python monitor.py --once       # Run all jobs once and exit (testing)
"""

import sys
import json
import logging
from pathlib import Path

# Add project root to path
if getattr(sys, 'frozen', False):
    project_root = Path(sys._MEIPASS)
else:
    project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger('NexusMonitor')


def setup_monitor_logging():
    """Set up logging for the monitor service"""
    import os
    from datetime import datetime
    from logging.handlers import RotatingFileHandler

    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)8s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    logger.addHandler(console)

    # File handler
    try:
        # Log alongside the exe (or project root in dev)
        if getattr(sys, 'frozen', False):
            log_dir = Path(sys.executable).parent / 'logs'
        else:
            log_dir = Path(__file__).parent / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"nexus_monitor_{datetime.now().strftime('%Y%m%d')}.log"

        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"Logging to: {log_file}")
    except Exception as e:
        logger.warning(f"Could not set up file logging: {e}")

    return logger


def load_monitor_config(root: Path) -> dict:
    """Load monitor_config.json from config directory or alongside exe"""
    config_paths = [
        root / 'config' / 'monitor_config.json',
        Path(sys.executable).parent / 'monitor_config.json',
    ]

    for path in config_paths:
        if path.exists():
            with open(path, 'r') as f:
                config = json.load(f)
            logger.info(f"Monitor config loaded from: {path}")
            return config

    logger.error("monitor_config.json not found. Checked paths:")
    for path in config_paths:
        logger.error(f"  - {path}")
    sys.exit(1)


def main():
    """Monitor entry point"""
    setup_monitor_logging()
    logger.info("Starting Nexus Monitor")

    # Load configs
    from services.config_manager import ConfigManager
    app_config = ConfigManager()
    tenant_id = app_config.get('microsoft.tenant_id')
    client_id = app_config.get('microsoft.client_id')
    vault_url = app_config.get('azure_keyvault.vault_url')

    monitor_config = load_monitor_config(project_root)
    client_secret = monitor_config.get('client_secret')

    if not client_secret:
        logger.error("client_secret not found in monitor_config.json")
        sys.exit(1)

    # Initialize auth
    from monitor.auth import MonitorAuth
    auth = MonitorAuth(tenant_id, client_id, client_secret)

    # Test auth immediately - fail fast if credentials are bad
    test_token = auth.get_token(["https://graph.microsoft.com/.default"])
    if not test_token:
        logger.error("Failed to acquire initial token - check client_secret and app registration")
        sys.exit(1)
    logger.info("Authentication successful")

    # Initialize services
    from services.graph_api import GraphAPIClient
    from services.keyvault_service import KeyVaultService

    graph_client = GraphAPIClient(token_provider=auth.get_graph_token_provider())

    KeyVaultService.reset()
    keyvault = KeyVaultService(
        vault_url=vault_url,
        credential=auth.get_keyvault_credential(),
        skip_connection_test=True
    )

    # Initialize state
    from monitor.state import StateManager
    state = StateManager()

    # Load jobs and start runner
    from monitor.jobs import ALL_JOBS
    from monitor.runner import JobRunner, JobContext

    context = JobContext(
        graph_client=graph_client,
        keyvault=keyvault,
        state=state,
        config=monitor_config
    )

    runner = JobRunner(
        jobs=ALL_JOBS,
        context=context,
        default_interval=monitor_config.get('polling_interval_minutes', 5)
    )

    if '--once' in sys.argv:
        runner.run_once()
    else:
        runner.run_forever()


if __name__ == "__main__":
    main()
