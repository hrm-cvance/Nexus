# Nexus Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone headless polling service ("Nexus Monitor") that fetches password-protected PDFs from the nexus@ inbox, unlocks them, and posts them to Teams via a Power Automate webhook.

**Architecture:** Separate entry point (`monitor.py`) with a job framework. Uses MSAL client credentials for unattended auth. Reuses existing `services/` for Key Vault and Graph API (with a refactor to abstract token acquisition). First job: Partners Credit User List PDF processing.

**Tech Stack:** Python, MSAL ConfidentialClientApplication, Microsoft Graph API (Mail + Attachments), pikepdf, Power Automate webhook

**Spec:** `docs/superpowers/specs/2026-03-18-nexus-monitor-design.md`

**Note:** This project has no test suite. Steps focus on implementation and manual verification via `--once` flag.

---

### Task 1: Refactor GraphAPIClient to accept abstract token provider

**Files:**
- Modify: `services/graph_api.py:40-61` (constructor, `_get_headers`, `__repr__`)

This refactor allows the monitor to use `GraphAPIClient` with client credentials instead of `AuthService`.

- [ ] **Step 1: Refactor constructor to accept a callable token provider**

In `services/graph_api.py`, replace the constructor and `_get_headers`:

```python
def __init__(self, auth_service=None, scopes: List[str] = None, token_provider=None):
    """
    Initialize Graph API client

    Args:
        auth_service: AuthService instance (delegated auth — used by GUI)
        scopes: Required API scopes (used with auth_service)
        token_provider: Callable(scopes) -> token_string (used by monitor)
                        If provided, auth_service and scopes are ignored.
    """
    if token_provider:
        self._token_provider = token_provider
    elif auth_service and scopes:
        self._token_provider = lambda s: auth_service.get_token_silent(s)
        self._scopes = scopes
    else:
        raise ValueError("Either token_provider or (auth_service + scopes) must be provided")

    # Store scopes for the auth_service path
    self._scopes = scopes or []
    logger.info("GraphAPIClient initialized")

def _get_headers(self) -> Dict[str, str]:
    """Get authorization headers with current token"""
    token = self._token_provider(self._scopes)
    if not token:
        raise GraphAPIError("No access token available. Please sign in.")

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
```

- [ ] **Step 2: Update `__repr__`**

Replace the `__repr__` at line 312:

```python
def __repr__(self):
    return "<GraphAPIClient>"
```

- [ ] **Step 3: Verify GUI still works**

The GUI passes `GraphAPIClient(auth_service=self.auth_service, scopes=scopes)` at `gui/main_window.py:111`. This still works because the constructor wraps `auth_service.get_token_silent` into `_token_provider`. No changes needed in `main_window.py`.

Run syntax check:
```bash
.venv/Scripts/python -c "import py_compile; py_compile.compile('services/graph_api.py', doraise=True); print('OK')"
```

- [ ] **Step 4: Add `get_message_attachments()` method**

Add this method after `read_recent_emails()`, before `__repr__`:

```python
def get_message_attachments(self, mailbox: str, message_id: str) -> List[Dict]:
    """
    Get attachments for a specific email message.

    Args:
        mailbox: UPN of the mailbox (e.g., nexus@highlandsmortgage.com)
        message_id: The message ID from read_recent_emails()

    Returns:
        List of attachment dicts with id, name, contentType, contentBytes
    """
    logger.info(f"Getting attachments for message {message_id[:20]}...")

    params = {
        "$select": "id,name,contentType,contentBytes"
    }

    try:
        response = self._make_request(
            "GET", f"/users/{mailbox}/messages/{message_id}/attachments",
            params=params
        )
        attachments = response.get("value", [])
        logger.info(f"Found {len(attachments)} attachment(s)")
        return attachments

    except GraphAPIError as e:
        logger.warning(f"Failed to get attachments: {e}")
        return []
```

- [ ] **Step 5: Commit**

```bash
git add services/graph_api.py
git commit -m "refactor: abstract token provider in GraphAPIClient, add get_message_attachments"
```

---

### Task 2: Create monitor auth module

**Files:**
- Create: `monitor/__init__.py`
- Create: `monitor/auth.py`

- [ ] **Step 1: Create `monitor/__init__.py`**

```python
"""Nexus Monitor — standalone polling service for background jobs"""
```

- [ ] **Step 2: Create `monitor/auth.py`**

```python
"""
Nexus Monitor Authentication

Uses MSAL ConfidentialClientApplication for unattended client credentials flow.
Provides two adapters:
- token_provider callable for GraphAPIClient
- ServiceCredentialAdapter (TokenCredential) for KeyVaultService
"""

import msal
from azure.core.credentials import AccessToken, TokenCredential
from datetime import datetime, timezone
from typing import List, Optional
import logging

logger = logging.getLogger('NexusMonitor.auth')


class MonitorAuth:
    """MSAL ConfidentialClientApplication wrapper for client credentials flow"""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=self.authority
        )
        logger.info(f"MonitorAuth initialized for tenant {tenant_id}")

    def get_token(self, scopes: List[str]) -> Optional[str]:
        """Acquire token for the given scopes via client credentials flow"""
        result = self.app.acquire_token_for_client(scopes=scopes)
        if result and "access_token" in result:
            logger.debug("Token acquired via client credentials")
            return result["access_token"]

        error = result.get("error_description", result.get("error", "Unknown error"))
        logger.error(f"Failed to acquire token: {error}")
        return None

    def get_graph_token_provider(self):
        """Return a callable suitable for GraphAPIClient(token_provider=...)"""
        def provider(scopes):
            # Client credentials always uses .default scope
            return self.get_token(["https://graph.microsoft.com/.default"])
        return provider

    def get_keyvault_credential(self) -> 'ServiceCredentialAdapter':
        """Return a TokenCredential suitable for KeyVaultService"""
        return ServiceCredentialAdapter(self)


class ServiceCredentialAdapter(TokenCredential):
    """Adapts MonitorAuth to Azure Identity TokenCredential interface for Key Vault"""

    def __init__(self, monitor_auth: MonitorAuth):
        self.monitor_auth = monitor_auth

    def get_token(self, *scopes, **kwargs) -> AccessToken:
        requested_scopes = list(scopes) if scopes else ["https://vault.azure.net/.default"]
        token_str = self.monitor_auth.get_token(requested_scopes)

        if not token_str:
            raise Exception("Failed to acquire service token for Key Vault")

        expires_on = int(datetime.now(timezone.utc).timestamp()) + 3600
        return AccessToken(token_str, expires_on)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
```

- [ ] **Step 3: Syntax check**

```bash
.venv/Scripts/python -c "import py_compile; py_compile.compile('monitor/__init__.py', doraise=True); py_compile.compile('monitor/auth.py', doraise=True); print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add monitor/__init__.py monitor/auth.py
git commit -m "feat: add monitor auth module with client credentials flow"
```

---

### Task 3: Create state tracking module

**Files:**
- Create: `monitor/state.py`

- [ ] **Step 1: Create `monitor/state.py`**

```python
"""
Nexus Monitor State Tracking

Tracks which items (email IDs, etc.) have been processed by each job.
Persists to a JSON file. Caps processed IDs at 500 per job to prevent unbounded growth.
"""

import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger('NexusMonitor.state')

MAX_PROCESSED_IDS = 500


class StateManager:
    """Manages persistent state for monitor jobs"""

    def __init__(self, state_dir: str = None):
        if state_dir:
            self.state_dir = Path(state_dir)
        else:
            self.state_dir = Path(os.environ.get('PROGRAMDATA', 'C:\\ProgramData')) / 'NexusMonitor'

        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / 'state.json'
        self._state = self._load()
        logger.info(f"State file: {self.state_file}")

    def _load(self) -> dict:
        """Load state from disk"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"State file corrupt, recreating: {e}")
                return {}
        return {}

    def _save(self):
        """Save state to disk using write-to-temp-then-rename for safety"""
        try:
            # Write to temp file first, then rename (atomic on Windows with replace)
            fd, tmp_path = tempfile.mkstemp(dir=str(self.state_dir), suffix='.tmp')
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(self._state, f, indent=2)
                # Atomic replace
                os.replace(tmp_path, str(self.state_file))
            except Exception:
                # Clean up temp file on failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _ensure_job(self, job_name: str):
        """Ensure job entry exists in state"""
        if job_name not in self._state:
            self._state[job_name] = {"processed_ids": [], "last_run": None}

    def is_processed(self, job_name: str, item_id: str) -> bool:
        """Check if an item has already been processed"""
        self._ensure_job(job_name)
        return item_id in self._state[job_name]["processed_ids"]

    def mark_processed(self, job_name: str, item_id: str):
        """Mark an item as processed and save"""
        self._ensure_job(job_name)
        ids = self._state[job_name]["processed_ids"]
        if item_id not in ids:
            ids.append(item_id)
            # Prune oldest if over cap
            if len(ids) > MAX_PROCESSED_IDS:
                self._state[job_name]["processed_ids"] = ids[-MAX_PROCESSED_IDS:]
            self._save()

    def get_last_run(self, job_name: str) -> Optional[str]:
        """Get the last run timestamp (ISO 8601 UTC) for a job"""
        self._ensure_job(job_name)
        return self._state[job_name].get("last_run")

    def set_last_run(self, job_name: str, timestamp: str = None):
        """Set the last run timestamp for a job"""
        self._ensure_job(job_name)
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        self._state[job_name]["last_run"] = timestamp
        self._save()
```

- [ ] **Step 2: Syntax check**

```bash
.venv/Scripts/python -c "import py_compile; py_compile.compile('monitor/state.py', doraise=True); print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add monitor/state.py
git commit -m "feat: add monitor state tracking with JSON persistence"
```

---

### Task 4: Create job runner

**Files:**
- Create: `monitor/runner.py`

- [ ] **Step 1: Create `monitor/runner.py`**

```python
"""
Nexus Monitor Job Runner

Polls registered jobs on their configured intervals.
Jobs run sequentially — no overlap possible.
"""

import time
import signal
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

logger = logging.getLogger('NexusMonitor.runner')


class JobContext:
    """Context passed to each job's run() method"""

    def __init__(self, graph_client, keyvault, state, config: Dict[str, Any]):
        self.graph_client = graph_client
        self.keyvault = keyvault
        self.state = state
        self.config = config


class JobRunner:
    """Runs registered jobs on their polling intervals"""

    def __init__(self, jobs: list, context: JobContext, default_interval: int = 5):
        self.jobs = jobs
        self.context = context
        self.default_interval = default_interval
        self._running = True

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        logger.info(f"Shutdown signal received ({signum}), stopping...")
        self._running = False

    def run_once(self):
        """Run all jobs once (ignoring intervals). Used for testing."""
        logger.info(f"Running all {len(self.jobs)} job(s) once...")
        for job_cls in self.jobs:
            self._execute_job(job_cls)
        logger.info("Single run complete")

    def run_forever(self):
        """Main polling loop — runs jobs on their intervals until shutdown"""
        logger.info(f"Starting job runner with {len(self.jobs)} job(s)")
        for job_cls in self.jobs:
            logger.info(f"  - {job_cls.JOB_NAME} (every {job_cls.INTERVAL_MINUTES}m)")

        while self._running:
            for job_cls in self.jobs:
                if not self._running:
                    break

                # Check if interval has elapsed
                last_run = self.context.state.get_last_run(job_cls.JOB_NAME)
                if last_run:
                    last_run_dt = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                    interval = timedelta(minutes=job_cls.INTERVAL_MINUTES)
                    if datetime.now(timezone.utc) - last_run_dt < interval:
                        continue  # Not time yet

                self._execute_job(job_cls)

            # Sleep between poll cycles (check every 30 seconds for shutdown)
            for _ in range(6):  # 6 x 5s = 30s
                if not self._running:
                    break
                time.sleep(5)

        logger.info("Job runner stopped")

    def _execute_job(self, job_cls):
        """Execute a single job with error handling and timeout"""
        job_name = job_cls.JOB_NAME
        logger.info(f"Running job: {job_name}")
        start = time.time()

        try:
            job_cls.run(self.context)
            elapsed = time.time() - start
            logger.info(f"Job {job_name} completed in {elapsed:.1f}s")
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"Job {job_name} failed after {elapsed:.1f}s: {e}")

        # Update last_run regardless of success/failure (prevents rapid retry loops)
        self.context.state.set_last_run(job_name)
```

- [ ] **Step 2: Syntax check**

```bash
.venv/Scripts/python -c "import py_compile; py_compile.compile('monitor/runner.py', doraise=True); print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add monitor/runner.py
git commit -m "feat: add monitor job runner with interval-based polling"
```

---

### Task 5: Create Partners User List job

**Files:**
- Create: `monitor/jobs/__init__.py`
- Create: `monitor/jobs/partners_user_list.py`

- [ ] **Step 1: Create `monitor/jobs/partners_user_list.py`**

```python
"""
Partners User List Job

Fetches password-protected PDF from Partners Credit email,
unlocks it, and posts to Teams via Power Automate webhook.
"""

import base64
import io
import logging
import requests
import pikepdf

logger = logging.getLogger('NexusMonitor.jobs.partners_user_list')

JOB_NAME = "partners_user_list"
INTERVAL_MINUTES = 5

SENDER_FILTER = "support@partnerscredit.com"
SUBJECT_FILTER = "Partners User List"
KEYVAULT_PASSWORD_SECRET = "partnerscredit-admin-password"


def run(context):
    """
    Check for new Partners Credit emails, unlock PDF attachments,
    and post to Teams via webhook.
    """
    mailbox = context.config.get("monitor_mailbox", "nexus@highlandsmortgage.com")
    webhook_url = context.config.get("teams_webhook_url")

    if not webhook_url:
        logger.error("No teams_webhook_url configured — skipping job")
        return

    # Fetch recent emails with subject filter (server-side)
    messages = context.graph_client.read_recent_emails(
        mailbox=mailbox,
        subject_filter=SUBJECT_FILTER,
        minutes_ago=1440  # 24 hours
    )

    if not messages:
        logger.info("No new emails found")
        return

    # Client-side sender filter
    matching = []
    for msg in messages:
        sender = msg.get('from', {}).get('emailAddress', {}).get('address', '').lower()
        if SENDER_FILTER.lower() in sender:
            matching.append(msg)

    if not matching:
        logger.info(f"Found {len(messages)} email(s) but none from {SENDER_FILTER}")
        return

    # Get PDF password from Key Vault
    try:
        pdf_password = context.keyvault.get_vendor_credential('partnerscredit', 'admin-password')
    except Exception as e:
        logger.error(f"Failed to get PDF password from Key Vault: {e}")
        return

    processed_count = 0
    error_count = 0

    for msg in matching:
        msg_id = msg.get('id')
        subject = msg.get('subject', 'Unknown')

        if context.state.is_processed(JOB_NAME, msg_id):
            continue

        logger.info(f"Processing email: {subject}")

        try:
            # Get attachments
            attachments = context.graph_client.get_message_attachments(mailbox, msg_id)

            # Find first PDF
            pdf_attachment = None
            for att in attachments:
                content_type = (att.get('contentType') or '').lower()
                name = (att.get('name') or '').lower()
                if 'pdf' in content_type or name.endswith('.pdf'):
                    pdf_attachment = att
                    break

            if not pdf_attachment:
                logger.warning(f"No PDF attachment found in email: {subject}")
                context.state.mark_processed(JOB_NAME, msg_id)  # Don't retry
                continue

            filename = pdf_attachment.get('name', 'Partners_User_List.pdf')
            logger.info(f"Found PDF: {filename}")

            # Decode attachment
            pdf_bytes = base64.b64decode(pdf_attachment['contentBytes'])

            # Unlock PDF
            try:
                input_stream = io.BytesIO(pdf_bytes)
                output_stream = io.BytesIO()
                with pikepdf.open(input_stream, password=pdf_password) as pdf:
                    pdf.save(output_stream, encryption=False)
                unlocked_bytes = output_stream.getvalue()
                logger.info(f"PDF unlocked: {filename} ({len(unlocked_bytes)} bytes)")
            except pikepdf.PasswordError:
                logger.error(f"Wrong PDF password for: {filename} — will retry next cycle")
                error_count += 1
                continue  # Don't mark processed — retry next cycle

            # POST to Power Automate webhook
            payload = {
                "filename": filename,
                "content": base64.b64encode(unlocked_bytes).decode('utf-8')
            }

            response = requests.post(webhook_url, json=payload, timeout=60)

            if response.status_code in (200, 201, 202):
                logger.info(f"Posted to Teams: {filename} (HTTP {response.status_code})")
                context.state.mark_processed(JOB_NAME, msg_id)
                processed_count += 1
            else:
                logger.error(f"Webhook failed: HTTP {response.status_code} — {response.text[:200]}")
                error_count += 1
                # Don't mark processed — retry next cycle

        except Exception as e:
            logger.error(f"Error processing email '{subject}': {e}")
            error_count += 1

    logger.info(f"Job complete: {processed_count} processed, {error_count} errors, "
               f"{len(matching)} total emails checked")
```

- [ ] **Step 2: Create `monitor/jobs/__init__.py`**

```python
"""
Nexus Monitor Job Registry

Explicit registration — no filesystem discovery (PyInstaller bundles
don't have scannable directories).
"""

from monitor.jobs import partners_user_list

ALL_JOBS = [
    partners_user_list,
]
```

- [ ] **Step 3: Syntax check**

```bash
.venv/Scripts/python -c "import py_compile; py_compile.compile('monitor/jobs/__init__.py', doraise=True); py_compile.compile('monitor/jobs/partners_user_list.py', doraise=True); print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add monitor/jobs/__init__.py monitor/jobs/partners_user_list.py
git commit -m "feat: add Partners User List job — fetch, unlock, post PDF"
```

---

### Task 6: Create monitor entry point and config

**Files:**
- Create: `monitor.py`
- Create: `config/monitor_config.example.json`
- Modify: `.gitignore`

- [ ] **Step 1: Create `config/monitor_config.example.json`**

```json
{
  "client_secret": "YOUR_CLIENT_SECRET",
  "polling_interval_minutes": 5,
  "teams_webhook_url": "YOUR_POWER_AUTOMATE_WEBHOOK_URL",
  "monitor_mailbox": "nexus@highlandsmortgage.com"
}
```

- [ ] **Step 2: Add `config/monitor_config.json` to `.gitignore`**

Add after line 26 (`config/app_config.json`):

```
config/monitor_config.json
```

Also add the example to the negation patterns section (after line 215):

```
!config/monitor_config.example.json
```

- [ ] **Step 3: Create `monitor.py`**

```python
"""
Nexus Monitor — Standalone Polling Service

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


def setup_monitor_logging():
    """Set up logging for the monitor service"""
    import os
    from datetime import datetime
    from logging.handlers import RotatingFileHandler

    logger = logging.getLogger('NexusMonitor')
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
        log_dir = Path(os.environ.get('PROGRAMDATA', 'C:\\ProgramData')) / 'NexusMonitor' / 'logs'
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


def load_monitor_config(project_root: Path) -> dict:
    """Load monitor_config.json from config directory or alongside exe"""
    config_paths = [
        project_root / 'config' / 'monitor_config.json',  # Dev: repo/config/
        Path(sys.executable).parent / 'monitor_config.json',  # Deployed: alongside exe
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
    global logger
    logger = setup_monitor_logging()
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

    # Test auth immediately — fail fast if credentials are bad
    test_token = auth.get_token(["https://graph.microsoft.com/.default"])
    if not test_token:
        logger.error("Failed to acquire initial token — check client_secret and app registration")
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

    # Load jobs
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

    # Run
    if '--once' in sys.argv:
        runner.run_once()
    else:
        runner.run_forever()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Syntax check**

```bash
.venv/Scripts/python -c "import py_compile; py_compile.compile('monitor.py', doraise=True); print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add monitor.py config/monitor_config.example.json .gitignore
git commit -m "feat: add monitor entry point, config template, gitignore updates"
```

---

### Task 7: Add pikepdf to requirements and create build script

**Files:**
- Modify: `requirements.txt`
- Create: `build_monitor.bat`

- [ ] **Step 1: Add pikepdf to requirements.txt**

Add after the ReportLab entry:

```
# PDF Decryption (Nexus Monitor)
pikepdf>=8.0.0
```

- [ ] **Step 2: Create `build_monitor.bat`**

```batch
@echo off
REM ============================================================
REM Nexus Monitor Build Script
REM Produces: dist\NexusMonitor.exe
REM ============================================================

echo.
echo ========================================
echo   Nexus Monitor Build
echo ========================================
echo.

REM Step 1: Pre-flight checks
echo [1/4] Pre-flight checks...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    exit /b 1
)
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo ERROR: PyInstaller not installed. Run: pip install pyinstaller
    exit /b 1
)

REM Step 2: Clean previous monitor build
echo [2/4] Cleaning previous build...
if exist "dist\NexusMonitor.exe" del "dist\NexusMonitor.exe"

REM Step 3: Build
echo [3/4] Building NexusMonitor.exe...
pyinstaller ^
    --onefile ^
    --name NexusMonitor ^
    --console ^
    --add-data "config\app_config.json;config" ^
    --add-data "services;services" ^
    --add-data "utils;utils" ^
    --add-data "monitor;monitor" ^
    --hidden-import msal ^
    --hidden-import pikepdf ^
    --hidden-import azure.keyvault.secrets ^
    --hidden-import azure.identity ^
    --hidden-import azure.core ^
    monitor.py

if not exist "dist\NexusMonitor.exe" (
    echo ERROR: Build failed - NexusMonitor.exe not found
    exit /b 1
)

REM Step 4: Verify
echo [4/4] Verifying build...
echo.
echo Build successful!
echo   Output: dist\NexusMonitor.exe
for %%I in ("dist\NexusMonitor.exe") do echo   Size: %%~zI bytes
echo.
echo Deploy:
echo   1. Copy NexusMonitor.exe to server
echo   2. Place monitor_config.json alongside the exe
echo   3. Install as service: nssm install NexusMonitor "C:\path\to\NexusMonitor.exe"
echo.
```

- [ ] **Step 3: Commit**

```bash
git add requirements.txt build_monitor.bat
git commit -m "feat: add pikepdf dependency and monitor build script"
```

---

### Task 8: End-to-end test with `--once`

- [ ] **Step 1: Create a local `config/monitor_config.json` for testing**

Copy the example and fill in real values:
```bash
cp config/monitor_config.example.json config/monitor_config.json
```

Edit `config/monitor_config.json` with:
- Real client secret from Entra app registration
- Real Power Automate webhook URL
- `nexus@highlandsmortgage.com` as mailbox

- [ ] **Step 2: Install pikepdf in the dev environment**

```bash
.venv/Scripts/pip install pikepdf
```

(Already installed from our earlier test.)

- [ ] **Step 3: Run with `--once`**

```bash
.venv/Scripts/python monitor.py --once
```

Expected output:
```
[INFO] Starting Nexus Monitor
[INFO] Monitor config loaded from: ...
[INFO] MonitorAuth initialized for tenant ...
[INFO] Authentication successful
[INFO] GraphAPIClient initialized
[INFO] Running all 1 job(s) once...
[INFO] Running job: partners_user_list
[INFO] Reading recent emails from nexus@highlandsmortgage.com
[INFO] Found N email(s)...
...
[INFO] Single run complete
```

- [ ] **Step 4: Verify results**

Check:
- Logs at `C:\ProgramData\NexusMonitor\logs\`
- State file at `C:\ProgramData\NexusMonitor\state.json`
- Teams channel for the posted PDF

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: Nexus Monitor — standalone polling service with Partners User List job"
```
