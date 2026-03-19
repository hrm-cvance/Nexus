# Nexus Monitor

## Problem

Partners Credit sends a password-protected PDF ("Partners User List") via email to `nexus@highlandsmortgage.com`. Today, someone must manually check the inbox, download the PDF, unlock it, and share it. This should be automated. Additionally, there will be future background tasks that need a framework to run in.

## Solution

Nexus Monitor — a standalone headless service that runs on a server, polls for events, and executes registered jobs. The first job fetches Partners Credit PDFs, strips the password, and posts the unlocked PDF to a Teams channel via Power Automate webhook.

## Architecture

Nexus Monitor is fully separate from the Nexus GUI app:

| | Nexus App | Nexus Monitor |
|---|---|---|
| **Runs on** | Tech's workstation | Server |
| **UI** | CustomTkinter GUI | Headless service |
| **Auth** | Delegated (user sign-in) | Client credentials (client secret) |
| **Deploy** | Intune (Nexus.exe) | Separate build (NexusMonitor.exe) |
| **Entry point** | `main.py` | `monitor.py` |

Both live in the same repo and share service code (`keyvault_service.py`, `graph_api.py`), but are built and deployed independently.

## Prerequisites (Manual)

1. **Entra App Registration**: Add a client secret to the existing Nexus app registration
2. **Entra App Registration**: Add `Mail.Read` application permission (not delegated), admin consent
3. **Server**: Create `config/monitor_config.json` with client secret and webhook URL (gitignored, server-only)
4. **Server**: Restrict file ACLs on `monitor_config.json` to only the service account (contains client secret and webhook signature)
5. **Server**: Install NexusMonitor.exe as a Windows service (via `nssm` or Task Scheduler)

## Design

### Config — `config/monitor_config.json`

Server-only config (gitignored). Contains secrets and monitor-specific settings:

```json
{
  "client_secret": "YOUR_CLIENT_SECRET",
  "polling_interval_minutes": 5,
  "teams_webhook_url": "YOUR_POWER_AUTOMATE_WEBHOOK_URL",
  "monitor_mailbox": "nexus@highlandsmortgage.com"
}
```

Reads `app_config.json` for shared settings: `tenant_id`, `client_id`, `vault_url`.

An example template (`config/monitor_config.example.json`) is checked into the repo.

**Note:** The `monitor_config.json` contains both the client secret and the webhook URL (which includes an API signature). Both are sensitive — file ACLs should restrict access to the service account only.

### Project Structure

```
monitor.py                          # Entry point — init auth, start runner
monitor/
  __init__.py                       # Package init
  runner.py                         # Poll loop — runs jobs on their intervals
  state.py                          # JSON state file — tracks processed items
  auth.py                           # ConfidentialClientApplication wrapper + TokenCredential
  jobs/
    __init__.py                     # Job registry — explicit registration (not filesystem discovery)
    partners_user_list.py           # Job 1: fetch PDF, unlock, push to Teams
```

### Component: `monitor/auth.py` — Service Authentication

Wraps MSAL `ConfidentialClientApplication` for client credentials flow:
- Authenticates as the application (no user context)
- Uses client secret from `monitor_config.json`
- Acquires token via `acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])`
- No token expiry concerns — client credentials tokens are short-lived but auto-refreshed by MSAL

**Two interfaces provided:**

1. **`ServiceTokenProvider`** — provides a `get_token(scopes) -> str` method for `GraphAPIClient` to use. This abstracts token acquisition so `GraphAPIClient` can work with either delegated auth (`AuthService`) or client credentials (`ServiceTokenProvider`).

2. **`ServiceCredentialAdapter`** — implements Azure Identity SDK's `TokenCredential` protocol (`get_token(*scopes) -> AccessToken`) for `KeyVaultService`. Similar to the existing `MSALCredentialAdapter` but using `acquire_token_for_client()` instead of `acquire_token_silent()`.

### Refactor: `services/graph_api.py` — Abstract Token Acquisition

`GraphAPIClient` currently takes an `AuthService` and calls `auth_service.get_token_silent(scopes)` in `_get_headers()`. This couples it to delegated auth.

**Change:** Refactor the constructor to accept either an `AuthService` or any object with a `get_token_silent(scopes) -> Optional[str]` method. The `ServiceTokenProvider` in `monitor/auth.py` will implement this same interface. This keeps backward compatibility — the GUI still passes `AuthService`, the monitor passes `ServiceTokenProvider`.

Alternatively, accept a simple callable `token_provider: Callable[[List[str]], Optional[str]]` — whichever is cleaner during implementation.

### Component: `monitor/state.py` — State Tracking

JSON file at `C:\ProgramData\NexusMonitor\state.json` (fixed path, not `%APPDATA%`, since the service runs under SYSTEM which has a different AppData path):

```json
{
  "partners_user_list": {
    "processed_ids": ["AAMkAGQ...", "AAMkAGR..."],
    "last_run": "2026-03-18T12:00:00Z"
  }
}
```

Interface:
- `is_processed(job_name, item_id) -> bool`
- `mark_processed(job_name, item_id)`
- `get_last_run(job_name) -> Optional[str]`
- Auto-saves on every write
- **Pruning:** `processed_ids` is capped at 500 entries per job. When the cap is reached, the oldest entries are discarded. This prevents unbounded growth over months of operation.

### Component: `monitor/runner.py` — Job Runner

- Loads jobs from the explicit registry in `monitor/jobs/__init__.py` (no filesystem discovery — PyInstaller bundles don't have scannable directories)
- Main loop: iterates jobs sequentially, checks if each job's interval has elapsed since `last_run`
- Calls `job.run(context)` where context contains: `graph_client`, `keyvault`, `state`, `config`
- **Per-job timeout:** 5 minutes default. If a job exceeds its timeout, it is interrupted and logged as failed.
- Jobs run sequentially — no overlap possible within a single runner loop
- Job failures are caught and logged — never crash the runner
- `Ctrl+C` / service stop triggers graceful shutdown
- Logs job results: success, failure, skip (interval not elapsed)

### Component: `monitor/jobs/__init__.py` — Job Registry

Explicit registration — each job is imported and listed:

```python
from monitor.jobs.partners_user_list import PartnersUserListJob

ALL_JOBS = [
    PartnersUserListJob,
]
```

Each job class exposes:
- `JOB_NAME: str` — identifier for state tracking and logging
- `INTERVAL_MINUTES: int` — polling interval
- `run(context) -> None` — job logic, raises on failure

### Job 1: `monitor/jobs/partners_user_list.py`

**Flow:**
1. Call `graph_client.read_recent_emails()` to fetch emails from `nexus@highlandsmortgage.com`
   - Server-side filter: subject contains "Partners User List"
   - Time window: emails from the last 24 hours (wider window since we track state)
   - Client-side filter: sender is `support@partnerscredit.com`
2. For each email not in state (`is_processed` check):
   a. Fetch attachments via Graph API: `GET /users/{mailbox}/messages/{id}/attachments`
   b. Find the first PDF attachment (filter by `contentType` containing `pdf`). If multiple PDFs exist, process only the first.
   c. Decode base64 content (`contentBytes`)
   d. Unlock PDF with `pikepdf` using password from Key Vault (`partnerscredit-admin-password`), save in memory with `encryption=False`
   e. POST the unlocked PDF to the Power Automate webhook (base64-encoded in JSON body)
   f. Mark message ID as processed in state
3. Log summary: how many emails processed, any failures

**Graph API for attachments:**
```
GET /users/{mailbox}/messages/{messageId}/attachments
$select=id,name,contentType,contentBytes
```
Returns base64-encoded file content in `contentBytes`.

**Webhook POST format:**
```json
{
  "filename": "Partners User List 20260318.pdf",
  "content": "<base64-encoded unlocked PDF>",
  "timestamp": "2026-03-18T12:00:00Z"
}
```
The exact schema may need adjustment based on the Power Automate trigger's expected input. This will be finalized during implementation by inspecting the trigger schema.

**Webhook response handling:** HTTP 200-202 is treated as success. Any other status code is treated as failure (don't mark processed, retry next cycle). Response body is logged for debugging.

### Component: `monitor.py` — Entry Point

1. Load `app_config.json` (via `ConfigManager` — reads `tenant_id`, `client_id`, `vault_url`; the vendor_mappings load is harmless and ignored)
2. Load `monitor_config.json` (separate JSON read — not via ConfigManager)
3. Initialize `ConfidentialClientApplication` auth via `monitor/auth.py`
4. Initialize `KeyVaultService` with `ServiceCredentialAdapter` (call `KeyVaultService.reset()` first to ensure clean singleton state)
5. Initialize `GraphAPIClient` with `ServiceTokenProvider`
6. Initialize state manager
7. Start runner with all registered jobs
8. Supports `--once` flag: run all jobs once and exit (useful for testing)

### Logging

Logs to `C:\ProgramData\NexusMonitor\logs\nexus_monitor_YYYYMMDD.log` (fixed path, not `%APPDATA%`, since SYSTEM context resolves `%APPDATA%` differently). Console output also enabled for debugging when run interactively.

Uses the existing `utils/logger.py` pattern but with a different app name and log directory.

### Build — `build_monitor.bat`

Separate PyInstaller build producing `dist/NexusMonitor.exe`:
- Bundles `monitor.py` + `monitor/` + `services/` + `utils/` + `config/app_config.json`
- Includes `--hidden-import` flags for `pikepdf` and `msal` (PyInstaller often misses native dependencies)
- Does NOT bundle `config/monitor_config.json` (deployed separately on server)
- Does NOT bundle GUI code (`gui/`, `customtkinter`)
- Does NOT bundle Playwright (no browser automation needed)
- Significantly smaller exe than the main Nexus build

### Deployment

- `NexusMonitor.exe` installed on the server (e.g., `C:\Program Files\NexusMonitor\`)
- `monitor_config.json` placed alongside the exe
- Data directory: `C:\ProgramData\NexusMonitor\` (logs, state)
- Registered as a Windows service via `nssm`:
  ```
  nssm install NexusMonitor "C:\Program Files\NexusMonitor\NexusMonitor.exe"
  ```

## Error Handling

| Failure | Behavior |
|---|---|
| Auth failure (bad client secret) | Log error, retry on next poll cycle |
| Key Vault inaccessible | Log error, skip job, retry next cycle |
| No new emails | Normal — log "no new emails", continue |
| PDF attachment not found | Log warning, mark email processed (avoid retry loop) |
| Wrong PDF password | Log error, skip email (don't mark processed so it retries) |
| Webhook POST fails (non-2xx) | Log error + response body, don't mark processed (retry next cycle) |
| State file corrupt | Log warning, recreate empty state |
| Job exceeds timeout (5 min) | Log error, move to next job |

## Files Changed/Created

**New files:**
- `monitor.py` — entry point
- `monitor/__init__.py` — package init
- `monitor/runner.py` — job runner
- `monitor/state.py` — state tracking
- `monitor/auth.py` — client credentials auth + credential adapters
- `monitor/jobs/__init__.py` — job registry (explicit imports)
- `monitor/jobs/partners_user_list.py` — first job
- `config/monitor_config.example.json` — config template (placeholder values only)
- `build_monitor.bat` — build script

**Modified files:**
- `.gitignore` — add `config/monitor_config.json`
- `services/graph_api.py` — refactor `__init__`/`_get_headers` to accept abstract token provider; add `get_message_attachments()` method

**Shared (no changes needed):**
- `services/keyvault_service.py` — used as-is (singleton reset called by monitor.py)
- `services/config_manager.py` — used as-is (vendor_mappings load is harmless)
- `config/app_config.json` — read-only

## Out of Scope

- GUI integration (monitor is headless)
- Intune deployment (server is managed separately)
- Additional jobs beyond Partners User List (framework supports them, built later)
- Power Automate flow configuration (assumed already set up)
- Managed identity or certificate-based auth (client secret is pragmatic for on-prem)
