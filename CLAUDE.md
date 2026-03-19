# Nexus - Claude Code Project Guide

## Project Overview
Nexus is an internal tool for Highland Mortgage Services that automates vendor account provisioning. It integrates with Azure Entra ID (user lookup), Azure Key Vault (credentials), and Playwright (browser automation) to create user accounts across 9 vendor platforms.

## Tech Stack
- **Language:** Python 3.8+
- **GUI:** CustomTkinter (customtkinter)
- **Browser Automation:** Playwright (async API, Chromium)
- **Auth:** MSAL (Microsoft Authentication Library) — delegated permissions (GUI) and client credentials (Monitor)
- **Cloud:** Azure Key Vault, Microsoft Graph API (users, groups, mail, attachments)
- **AI:** Anthropic Claude (role/branch matching)
- **PDF:** ReportLab (summary generation), pikepdf (PDF decryption)

## Running the App
```bash
python main.py
```

## Project Structure
```
main.py                          # Entry point (supports --install-browsers for deployment)
monitor.py                       # Nexus Monitor entry point (standalone polling service)
build.bat                        # Build script → dist/Nexus.exe + dist/intune_output/install.intunewin
build_monitor.bat                # Build script → dist/NexusMonitor.exe
version_info.py                  # Generates Windows exe version metadata from APP_VERSION
monitor/
  __init__.py                    # Monitor package
  auth.py                        # MSAL ConfidentialClientApplication (client credentials flow)
  runner.py                      # Job runner with interval-based polling and timeouts
  state.py                       # JSON state tracking (processed items)
  jobs/
    __init__.py                  # Job registry (explicit, not filesystem discovery)
    partners_user_list.py        # Job: fetch PDF from email, unlock, post to Teams
deploy/
  install.ps1                    # Intune install script (shared Playwright browser path)
  uninstall.ps1                  # Intune uninstall script
  install_monitor.ps1            # Nexus Monitor install (Task Scheduler)
  uninstall_monitor.ps1          # Nexus Monitor uninstall
assets/
  nexus.ico                      # Multi-size icon (16–256px, font-hinted N)
  nexus.png                      # 256px reference PNG
  nexus.svg                      # SVG source (reference only — ICO is generated from font rendering)
  generate_icon.py               # Icon generation script (Segoe UI Bold + manual ICO binary)
gui/
  main_window.py                 # Main CustomTkinter window (Win32 icon loading, version in title)
  tab_search.py                  # User search tab (Entra ID lookup)
  tab_provisioning.py            # Vendor selection & provisioning tab
  tab_automation.py              # Automation runner & status display
  tab_summary.py                 # Results summary & PDF export
services/
  auth_service.py                # MSAL authentication (delegated, persistent token cache)
  graph_api.py                   # Microsoft Graph API client
  keyvault_service.py            # Azure Key Vault secret retrieval
  config_manager.py              # App configuration (loads from bundled resources)
  ai_matcher.py                  # Claude AI role/branch matching
  pdf_generator.py               # PDF summary generation
  msal_credential_adapter.py     # MSAL-to-Azure Identity adapter
automation/vendors/
  accountchek.py                 # AccountChek automation
  bankvod.py                     # BankVOD automation
  clearcapital.py                # Clear Capital automation
  dataverify.py                  # DataVerify automation
  certifiedcredit.py             # Certified Credit automation
  partnerscredit.py              # Partners Credit automation
  theworknumber.py               # The Work Number (Equifax) automation
  mmi.py                         # MMI automation
  experience.py                  # Experience.com automation (currently disabled)
models/
  user.py                        # EntraUser model
  vendor.py                      # VendorConfig model (name, display_name, entra_group_name, UI state)
  automation_result.py           # Automation result models
Vendors/{VendorName}/
  config.json                    # Vendor-specific config (org, roles, URLs)
  roles.json                     # Role mappings (if applicable)
config/
  app_config.example.json        # Template config (copy to app_config.json)
  monitor_config.example.json    # Template config for Nexus Monitor (copy to monitor_config.json)
  vendor_mappings.json           # Entra group -> vendor automation mappings
docs/                            # All documentation (auth guide, Key Vault setup, user guide, etc.)
```

## Key Patterns

### Vendor Automation Modules
Each vendor automation module in `automation/vendors/` follows this pattern:
- A class (e.g., `TheWorkNumberAutomation`) with async methods for each step
- A `provision_user()` async function as the public entry point
- Uses Playwright async API (`self.page`, `self.browser`)
- Credentials retrieved from KeyVault via `keyvault.get_vendor_credential(vendor, key)`
- Duplicate detection with callbacks: `on_username_conflict` and `on_email_conflict`
- Returns a result dict: `{'success': bool, 'messages': [], 'warnings': [], 'errors': []}`

### Duplicate User Handling
When a vendor reports a duplicate username/email, the automation calls async callbacks (`on_username_conflict`, `on_email_conflict`) that display a dialog to the user via `threading.Event` synchronization between the async automation thread and the Tkinter GUI thread. The dialog classes are `UsernameConflictDialog` and `EmailConflictDialog` in `gui/tab_automation.py`.

**Important:** Conflict callbacks run inside async functions. Never use blocking `Event.wait(timeout)` — it deadlocks the asyncio event loop. Use async polling instead:
```python
while not dialog_result_holder['ready'].wait(timeout=0.1):
    await asyncio.sleep(0.1)
```

### Vendor Config
Each vendor has a config in `Vendors/{VendorName}/config.json` and a mapping entry in `config/vendor_mappings.json` that links an Entra AD group to the automation module.

### Key Vault Secret Naming
Secrets follow the pattern: `{vendorname}-{key}` (e.g., `theworknumber-login-url`, `accountchek-admin-password`).

## Deployment
- **Build:** `build.bat` produces `dist/Nexus.exe` via PyInstaller AND `dist/intune_output/install.intunewin` via IntuneWinAppUtil (8-step pipeline)
- **Version info:** `version_info.py` reads `APP_VERSION` from `main.py` and generates `version_info.txt` for PyInstaller's `--version-file` flag (embeds File Version, Product Version, Company Name in the exe properties)
- **Intune packaging:** `build.bat` automatically assembles `dist/intune_source/` (Nexus.exe + install.ps1 + uninstall.ps1) and runs `C:\PrepTool\IntuneWinAppUtil.exe` to produce `dist/intune_output/install.intunewin`
- **Intune deployment scripts:** `deploy/install.ps1` and `deploy/uninstall.ps1` for Win32 app deployment
- **Playwright browsers:** Shared path via `PLAYWRIGHT_BROWSERS_PATH` env var at `C:\ProgramData\Nexus\browsers`; `install.ps1` skips browser install if `chromium-*` directory already exists
- **Config at runtime:** Bundled inside the exe; `config_manager.py` loads from `sys._MEIPASS` when frozen
- **IntuneWinAppUtil location:** `C:\Program Files\IntunePrepTool\IntuneWinAppUtil.exe` (Microsoft Win32 Content Prep Tool)

### Icon & Window Identity
- `assets/generate_icon.py` renders the N letterform using Segoe UI Bold font hinting at each size independently (not downscaled from SVG)
- ICO is manually constructed (Pillow's `append_images` doesn't work for ICO format) with 7 PNG frames: 16, 24, 32, 48, 64, 128, 256
- `main_window.py` uses Win32 `LoadImageW` + `SendMessageW(WM_SETICON)` for proper multi-size icon support (title bar gets ICON_SMALL, taskbar gets ICON_BIG)
- `SetCurrentProcessExplicitAppUserModelID` ensures the taskbar shows Nexus's icon instead of Python's
- Version number (`APP_VERSION` from `main.py`) is displayed in the window title bar

### Authentication & Key Vault Credential Flow
- `AuthService` uses MSAL's `SerializableTokenCache` to persist tokens to `%LOCALAPPDATA%\Nexus\token_cache.bin`
- Token cache is encrypted at rest using Windows DPAPI (`CryptProtectData`/`CryptUnprotectData` via ctypes), binding it to the current Windows user
- Plaintext caches from older versions are auto-migrated: loaded and re-encrypted on next save
- On startup, cached accounts are restored so users are auto-authenticated without a browser sign-in
- Sign-out deletes the cache file entirely (not just cleared in memory)
- Refresh tokens persist for ~90 days of inactivity; after that, a fresh browser sign-in is required
- `KeyVaultService` requires a credential object (no fallback) — always initialized with `MSALCredentialAdapter` from the GUI sign-in flow
- Vendor modules that call `KeyVaultService()` with no args get the already-initialized singleton instance
- Call `KeyVaultService.reset()` when the user signs out/re-authenticates to clear the singleton and credential cache

### Auto-MFA OTP Entry
- TheWorkNumber and Partners Credit support automatic MFA code entry via email
- `GraphAPIClient.read_recent_emails()` polls the `nexus@highlandsmortgage.com` inbox for OTP emails
- OTP codes are extracted via regex (`\b(\d{6})\b`), entered into the MFA form, and submitted
- Requires `Mail.Read.Shared` delegated permission and Full Access on the nexus@ mailbox
- Falls back to manual entry if auto-entry fails (no email found, wrong code, missing permissions)
- `graph_client` is plumbed from `MainWindow` → `AutomationStatusTab` → `provision_user()` → vendor automation class
- `GraphAPIClient` accepts either `auth_service` + `scopes` (GUI) or a `token_provider` callable (Monitor)

### Nexus Monitor
Nexus Monitor is a standalone headless polling service (`monitor.py`) that runs on a server, separate from the GUI app:
- **Auth:** MSAL `ConfidentialClientApplication` (client credentials flow, no user sign-in, no 90-day token expiry)
- **Config:** `config/monitor_config.json` (gitignored) — contains client secret, webhook URL, mailbox
- **Jobs:** Pluggable job framework in `monitor/jobs/`. Each job has `JOB_NAME`, `INTERVAL_MINUTES`, and `run(context)`
- **State:** Tracks processed item IDs in `state.json` alongside the exe (capped at 500 per job)
- **Build:** `build_monitor.bat` → `dist/NexusMonitor.exe` (separate from Nexus GUI build)
- **Deploy:** `deploy/install_monitor.ps1` registers as a Windows Scheduled Task running as SYSTEM at startup
- **First job:** `partners_user_list` — fetches password-protected PDF from email, unlocks with pikepdf + Key Vault password, POSTs to Teams via Power Automate webhook
- Never commit `config/monitor_config.json` (contains client secret and webhook URL with API signature)

### PowerShell Script Encoding
- `deploy/install.ps1` and `deploy/uninstall.ps1` MUST be saved with **UTF-8 BOM** encoding and **CRLF** line endings
- Windows PowerShell 5.1 (used by Intune/SYSTEM context) defaults to ANSI without a BOM, which causes parse errors
- Avoid Unicode characters (em dashes, smart quotes) in PS1 files — use ASCII equivalents

## Important Notes
- All automation runs in a non-headless Chromium browser so the user can observe and intervene (e.g., MFA)
- Screenshots are saved at each step for debugging (gitignored)
- Never commit credentials, `.env` files, screenshots, or `config/app_config.json` (use the example template)
- Some vendor sites use iframes (Appcues tours, MFA modals) - use `content_frame()` to access iframe content
- Toast/snackbar error messages (e.g., `#snackbar.error`) need explicit detection after form submission
- MMI uses `extensionAttribute2` from Entra ID as the NMLS number (`user.nmls_number`)
- Experience.com and Certified Credit are currently disabled in `vendor_mappings.json`
- Key Vault has 32 secrets total — see `docs/AZURE_KEYVAULT_SETUP.md` for the full inventory
- When using Playwright `page.evaluate()`, pass user data as arguments — never interpolate via f-strings (injection risk):
  ```python
  # Correct:
  await page.evaluate('(name) => { ... }', display_name)
  # Wrong:
  await page.evaluate(f'() => {{ ... "{display_name}" ... }}')
  ```
- Vendor automation `except` blocks must explicitly set `result['success'] = False`
- Browser cleanup (`browser.close()`) must be in a `finally` block to prevent browser leaks on error
