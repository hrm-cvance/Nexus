# Nexus - Claude Code Project Guide

## Project Overview
Nexus is an internal tool for Highland Mortgage Services that automates vendor account provisioning. It integrates with Azure Entra ID (user lookup), Azure Key Vault (credentials), and Playwright (browser automation) to create user accounts across 9 vendor platforms.

## Tech Stack
- **Language:** Python 3.8+
- **GUI:** CustomTkinter (customtkinter)
- **Browser Automation:** Playwright (async API, Chromium)
- **Auth:** MSAL (Microsoft Authentication Library) with delegated permissions and persistent token cache
- **Cloud:** Azure Key Vault, Microsoft Graph API
- **AI:** Anthropic Claude (role/branch matching)
- **PDF:** ReportLab (summary generation)

## Running the App
```bash
python main.py
```

## Project Structure
```
main.py                          # Entry point (supports --install-browsers for deployment)
build.bat                        # PyInstaller build script → dist/Nexus.exe
deploy/
  install.ps1                    # Intune install script (shared Playwright browser path)
  uninstall.ps1                  # Intune uninstall script
gui/
  main_window.py                 # Main CustomTkinter window
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
  vendor.py                      # Vendor config models
  automation_result.py           # Automation result models
Vendors/{VendorName}/
  config.json                    # Vendor-specific config (org, roles, URLs)
  roles.json                     # Role mappings (if applicable)
config/
  app_config.example.json        # Template config (copy to app_config.json)
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

### Vendor Config
Each vendor has a config in `Vendors/{VendorName}/config.json` and a mapping entry in `config/vendor_mappings.json` that links an Entra AD group to the automation module.

### Key Vault Secret Naming
Secrets follow the pattern: `{vendorname}-{key}` (e.g., `theworknumber-login-url`, `accountchek-admin-password`).

## Deployment
- **Build:** `build.bat` produces `dist/Nexus.exe` via PyInstaller (uses `sys._MEIPASS` for bundled resources)
- **Intune:** `deploy/install.ps1` and `deploy/uninstall.ps1` for Win32 app deployment
- **Playwright browsers:** Shared path via `PLAYWRIGHT_BROWSERS_PATH` env var at `C:\ProgramData\Nexus\browsers`
- **Config at runtime:** Bundled inside the exe; `config_manager.py` loads from `sys._MEIPASS` when frozen

### Authentication & Token Cache
- `AuthService` uses MSAL's `SerializableTokenCache` to persist tokens to `%LOCALAPPDATA%\Nexus\token_cache.bin`
- On startup, cached accounts are restored so users are auto-authenticated without a browser sign-in
- Sign-out deletes the cache file entirely (not just cleared in memory)
- Refresh tokens persist for ~90 days of inactivity; after that, a fresh browser sign-in is required

## Important Notes
- All automation runs in a non-headless Chromium browser so the user can observe and intervene (e.g., MFA)
- Screenshots are saved at each step for debugging (gitignored)
- Never commit credentials, `.env` files, screenshots, or `config/app_config.json` (use the example template)
- Some vendor sites use iframes (Appcues tours, MFA modals) - use `content_frame()` to access iframe content
- Toast/snackbar error messages (e.g., `#snackbar.error`) need explicit detection after form submission
- MMI uses `extensionAttribute2` from Entra ID as the NMLS number (`user.nmls_number`)
- Experience.com is currently disabled in `vendor_mappings.json`
- Key Vault has 32 secrets total — see `docs/AZURE_KEYVAULT_SETUP.md` for the full inventory
