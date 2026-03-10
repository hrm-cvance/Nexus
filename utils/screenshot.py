"""
Screenshot & Debug File Utility

Provides safe screenshot and HTML debug file saving that:
- Routes files to a writable directory (%LOCALAPPDATA%\\Nexus\\screenshots\\)
- Never raises exceptions — screenshot failures won't crash automation
- Creates the output directory automatically on first use
"""

import os
import logging
from pathlib import Path
from typing import Union

logger = logging.getLogger('Nexus.utils.screenshot')

# Cache the resolved directory so we only compute it once
_screenshot_dir = None


def get_screenshot_dir() -> Path:
    """
    Get the writable screenshot directory, creating it if needed.

    Returns:
        Path to %LOCALAPPDATA%\\Nexus\\screenshots\\
    """
    global _screenshot_dir
    if _screenshot_dir is not None:
        return _screenshot_dir

    local_appdata = os.environ.get('LOCALAPPDATA', '')
    if local_appdata:
        base = Path(local_appdata) / 'Nexus' / 'screenshots'
    else:
        base = Path.home() / 'AppData' / 'Local' / 'Nexus' / 'screenshots'

    try:
        base.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create screenshot directory {base}: {e}")
        # Fall back to temp directory
        import tempfile
        base = Path(tempfile.gettempdir()) / 'Nexus' / 'screenshots'
        base.mkdir(parents=True, exist_ok=True)

    _screenshot_dir = base
    return _screenshot_dir


def get_screenshot_path(filename: str) -> Path:
    """
    Get the full path for a screenshot file.

    Args:
        filename: Screenshot filename (e.g., 'certifiedcredit_login_page.png')

    Returns:
        Full path in the writable screenshot directory
    """
    return get_screenshot_dir() / filename


async def safe_screenshot(page, filename: str) -> bool:
    """
    Take a screenshot safely — never raises, always uses writable directory.

    Args:
        page: Playwright Page or popup object
        filename: Screenshot filename (e.g., 'certifiedcredit_login_page.png')

    Returns:
        True if screenshot was saved, False if it failed
    """
    try:
        path = get_screenshot_path(filename)
        await page.screenshot(path=str(path))
        logger.debug(f"Screenshot saved: {path}")
        return True
    except Exception as e:
        logger.debug(f"Screenshot failed ({filename}): {e}")
        return False


def safe_save_debug_html(content: str, filename: str) -> bool:
    """
    Save an HTML debug file safely — never raises, always uses writable directory.

    Args:
        content: HTML content to save
        filename: Debug filename (e.g., 'certifiedcredit_login_page.html')

    Returns:
        True if file was saved, False if it failed
    """
    try:
        path = get_screenshot_path(filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.debug(f"Debug file saved: {path}")
        return True
    except Exception as e:
        logger.debug(f"Debug file save failed ({filename}): {e}")
        return False
