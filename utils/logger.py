"""
Logging Utility

Sets up application-wide logging with:
- File logging to AppData/logs
- Console logging for development
- Colored output for better readability
- Rotating log files
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logger(app_name: str, log_level: str = "INFO") -> logging.Logger:
    """
    Set up application logger with file and console handlers

    Args:
        app_name: Name of the application
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Create formatters
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)8s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = logging.Formatter(
        '[%(levelname)s] %(message)s'
    )

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if logs directory exists)
    try:
        # Determine log directory
        if sys.platform == 'win32':
            import os
            appdata = os.environ.get('APPDATA', '')
            if appdata:
                log_dir = Path(appdata) / 'Nexus' / 'logs'
            else:
                log_dir = Path.home() / 'AppData' / 'Roaming' / 'Nexus' / 'logs'
        else:
            log_dir = Path.home() / '.nexus' / 'logs'

        # Create log directory if it doesn't exist
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create log file with date
        log_file = log_dir / f"nexus_{datetime.now().strftime('%Y%m%d')}.log"

        # Rotating file handler (10 MB max, keep 5 backups)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

        logger.info(f"Logging to: {log_file}")

    except Exception as e:
        logger.warning(f"Could not set up file logging: {str(e)}")

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module

    Returns a child logger of 'Nexus' to ensure all logs
    go to the same file handler
    """
    # Return a child logger of the main Nexus logger
    # This ensures all module logs use the same handlers
    if name == 'Nexus':
        return logging.getLogger('Nexus')
    else:
        return logging.getLogger(f'Nexus.{name}')
