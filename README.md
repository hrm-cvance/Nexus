<div align="center">

# Nexus

**Automated Vendor Account Provisioning**

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/playwright-automation-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev/python/)
[![Azure](https://img.shields.io/badge/azure-integrated-0078D4?logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/)
[![License](https://img.shields.io/badge/license-proprietary-gray)]()

Nexus streamlines employee onboarding by automatically provisioning user accounts across vendor platforms. It integrates with Microsoft Entra ID for identity lookup, Azure Key Vault for credential management, and Playwright for browser automation.

</div>

---

## Table of Contents

- [Overview](#overview)
- [Supported Vendors](#supported-vendors)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Deployment](#deployment)
- [Usage](#usage)
- [Adding a New Vendor](#adding-a-new-vendor)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Contributing](#contributing)

## Overview

When a new employee joins, IT must create accounts on multiple third-party vendor platforms. Nexus reduces this from a manual, error-prone process to a guided, automated workflow:

1. **Look up** the employee in Microsoft Entra ID
2. **Detect** which vendor accounts are needed based on AD group membership
3. **Provision** accounts automatically via browser automation
4. **Generate** a PDF summary of all provisioned accounts

### Key Capabilities

| Capability | Description |
|---|---|
| **Identity Integration** | Pulls user data and group membership from Microsoft Entra ID via Graph API |
| **Secure Credentials** | All vendor admin credentials stored in Azure Key Vault — never in code or config files |
| **Intelligent Matching** | Uses Claude AI to map job titles to vendor-specific roles and branch codes |
| **Duplicate Detection** | Detects existing accounts and prompts for resolution (skip or provide alternate) |
| **MFA Handling** | Automatically reads OTP codes from email and enters them; falls back to manual entry if needed |
| **PDF Reports** | Generates provisioning summary reports for audit and record-keeping |

## Supported Vendors

| Vendor | Automation Module | Status |
|---|---|---|
| AccountChek | `accountchek.py` | Active |
| BankVOD | `bankvod.py` | Active |
| Certified Credit | `certifiedcredit.py` | Disabled |
| Clear Capital | `clearcapital.py` | Active |
| DataVerify | `dataverify.py` | Active |
| MMI | `mmi.py` | Active |
| Partners Credit | `partnerscredit.py` | Active |
| The Work Number (Equifax) | `theworknumber.py` | Active |
| Experience.com | `experience.py` | Disabled |

Each vendor is mapped to an Entra ID security group. When a user is a member of a vendor's group, Nexus flags that vendor for provisioning.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Nexus GUI                            │
│  ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌───────────┐  │
│  │  Search   │ │ Provisioning │ │Automation│ │  Summary  │  │
│  └────┬─────┘ └──────┬───────┘ └────┬─────┘ └─────┬─────┘  │
└───────┼──────────────┼──────────────┼─────────────┼─────────┘
        │              │              │             │
   ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐  ┌────▼────┐
   │ Graph   │   │   Claude   │  │Playwright│  │ReportLab│
   │  API    │   │     AI     │  │(Chromium)│  │  (PDF)  │
   └────┬────┘   └───────────┘  └────┬─────┘  └─────────┘
        │                            │
   ┌────▼────┐                  ┌────▼─────┐
   │ Entra   │                  │  Azure   │
   │   ID    │                  │ Key Vault│
   └─────────┘                  └──────────┘
```

| Component | Purpose |
|---|---|
| **Microsoft Entra ID** | Employee identity, group membership, profile attributes |
| **Azure Key Vault** | Vendor admin credentials, login URLs, default passwords |
| **Playwright** | Chromium browser automation (non-headless for observability) |
| **Claude AI** | Maps job titles to vendor-specific roles and branch codes |
| **CustomTkinter** | Desktop GUI with tabbed workflow |
| **ReportLab** | PDF provisioning summary generation |
| **MSAL** | OAuth 2.0 authentication with delegated permissions and persistent token cache |
| **Win32 API** | Native icon loading (WM_SETICON) for crisp title bar and taskbar icons at all DPI scales |

## Getting Started

### Prerequisites

- Python 3.8+
- Azure subscription with Entra ID, Key Vault, and an App Registration
- Anthropic API key *(optional — for AI-powered role matching)*

### Installation

```bash
# Clone the repository
git clone https://github.com/hrm-cvance/Nexus.git
cd Nexus

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright Chromium browser
playwright install chromium
```

### Configuration

1. Copy the example config and fill in your Azure details:

```bash
cp config/app_config.example.json config/app_config.json
```

2. Edit `config/app_config.json`:

```json
{
  "microsoft": {
    "tenant_id": "YOUR_AZURE_TENANT_ID",
    "client_id": "YOUR_AZURE_CLIENT_ID",
    "redirect_uri": "http://localhost:8400",
    "scopes": ["User.Read.All", "GroupMember.Read.All", "Group.Read.All", "Mail.Read.Shared"]
  },
  "azure_keyvault": {
    "vault_url": "https://YOUR-KEYVAULT-NAME.vault.azure.net/"
  }
}
```

3. Populate Azure Key Vault with vendor credentials. See [docs/AZURE_KEYVAULT_SETUP.md](docs/AZURE_KEYVAULT_SETUP.md) for the full setup guide.

### Run

```bash
python main.py
```

## Deployment

Nexus supports enterprise deployment via Microsoft Intune.

### Build

The included build script packages the application into a single executable and creates the Intune deployment package in one step:

```bash
build.bat
```

This produces:
- `dist/Nexus.exe` (~113 MB) — standalone executable with all Python dependencies bundled
- `dist/intune_output/install.intunewin` — ready-to-upload Intune Win32 app package

The 8-step build pipeline:

1. Pre-flight checks (Python, PyInstaller)
2. Cleans previous builds
3. Resolves package paths (customtkinter)
4. Generates Windows version metadata from `APP_VERSION` in `main.py`
5. Runs PyInstaller with icon, version info, and all hidden imports
6. Verifies build output
7. Assembles Intune source folder (`dist/intune_source/` with Nexus.exe + install.ps1 + uninstall.ps1)
8. Runs `C:\PrepTool\IntuneWinAppUtil.exe` to create the `.intunewin` package

The exe embeds Windows file properties (right-click → Properties → Details): version number, company name, and product description. Version is maintained in one place (`APP_VERSION` in `main.py`) and flows to the window title bar, exe metadata, and Intune detection rules.

> **Note:** If `IntuneWinAppUtil.exe` is not found at `C:\PrepTool\`, the build still succeeds — it just skips the `.intunewin` packaging step and prints the manual command.

### Intune Deployment

The `deploy/` directory contains PowerShell scripts for Win32 app deployment:

| Script | Purpose |
|---|---|
| `deploy/install.ps1` | Installs `Nexus.exe`, sets up shared Playwright browser path (skips if already installed), creates Start Menu shortcut |
| `deploy/uninstall.ps1` | Removes application, browsers, environment variables, and shortcuts |

**Intune Win32 app configuration:**

| Setting | Value |
|---|---|
| Install command | `powershell.exe -ExecutionPolicy Bypass -File install.ps1` |
| Uninstall command | `powershell.exe -ExecutionPolicy Bypass -File uninstall.ps1` |
| Install behavior | System |
| Max install time | 60 minutes |
| Detection rule | File exists: `C:\Program Files\Nexus\Nexus.exe` |

The install script sets a machine-wide `PLAYWRIGHT_BROWSERS_PATH` environment variable so all users share a single Chromium installation at `C:\ProgramData\Nexus\browsers`. On reinstall/update, Playwright browser installation is skipped if a `chromium-*` directory already exists.

> **Encoding:** The PowerShell scripts in `deploy/` must be saved with **UTF-8 BOM** encoding and **CRLF** line endings. Windows PowerShell 5.1 (used by Intune in SYSTEM context) requires the BOM to correctly parse the files.

## Usage

For a detailed walkthrough, see the [User Guide](docs/USER_GUIDE.md).

### Workflow

1. **Sign In** — Authenticate with your Microsoft account (remembered between sessions)
2. **Search** — Find the employee in Entra ID by name, email, or employee ID
3. **Select Vendors** — Review detected vendors and confirm which to provision
4. **Automate** — Watch as accounts are created; respond to MFA or duplicate prompts as needed
5. **Review** — Check results and export a PDF summary

### Duplicate User Handling

When a vendor reports that a username or email already exists, Nexus displays a dialog with options:

- **Provide an alternative** email or username to retry
- **Skip** the vendor and continue with the remaining vendors

### MFA Handling

Some vendor portals require two-factor authentication. When MFA is detected, Nexus:

1. Automatically clicks "Send Verification Code" (if applicable)
2. Reads the OTP code from the `nexus@highlandsmortgage.com` inbox via Microsoft Graph API
3. Enters the code and clicks Submit automatically
4. Falls back to manual entry if auto-read fails (permissions, timeout, or unrecognized email format)

Auto-MFA is supported for **TheWorkNumber** (Equifax) and **Partners Credit**. Other vendors with MFA (e.g., MMI) still require manual code entry.

## Nexus Monitor

Nexus Monitor is a standalone headless service that runs background automation tasks on a server. It is built and deployed separately from the main Nexus GUI app.

### Overview

| | Nexus App | Nexus Monitor |
|---|---|---|
| **Runs on** | Tech's workstation | Server |
| **UI** | CustomTkinter GUI | Headless (console) |
| **Auth** | Delegated (user sign-in) | Client credentials (client secret) |
| **Deploy** | Intune (`Nexus.exe`) | Task Scheduler (`NexusMonitor.exe`) |

### Current Jobs

| Job | Interval | Description |
|---|---|---|
| Partners User List | 5 min | Fetches password-protected PDF from Partners Credit email, unlocks it, posts to Teams via Power Automate webhook |

### Build & Deploy

```bash
# Build
build_monitor.bat

# Deploy (on server, as admin)
powershell -ExecutionPolicy Bypass -File install_monitor.ps1
```

Files on the server (`C:\Scripts\NexusMonitor\`):
- `NexusMonitor.exe` — the service
- `monitor_config.json` — client secret, webhook URL, mailbox (not in source control)
- `state.json` — tracks processed items (auto-created)
- `logs/` — rotating log files

### Configuration

Copy `config/monitor_config.example.json` to `monitor_config.json` alongside the exe:

```json
{
  "client_secret": "YOUR_CLIENT_SECRET",
  "polling_interval_minutes": 5,
  "teams_webhook_url": "YOUR_POWER_AUTOMATE_WEBHOOK_URL",
  "monitor_mailbox": "nexus@highlandsmortgage.com"
}
```

**Prerequisites:**
- Client secret added to the Nexus app registration in Entra
- `Mail.Read` application permission (admin consented)
- Power Automate flow configured with HTTP trigger

## Adding a New Vendor

See [VENDOR_ONBOARDING_TEMPLATE.md](docs/VENDOR_ONBOARDING_TEMPLATE.md) for the complete guide.

**Summary:**

1. Create `Vendors/{VendorName}/config.json` with vendor-specific configuration
2. Create `automation/vendors/{vendorname}.py` implementing the `provision_user()` async entry point
3. Add a mapping entry in `config/vendor_mappings.json` linking an Entra group to the automation module
4. Store admin credentials in Azure Key Vault using the naming convention `{vendorname}-{key}`

### Key Vault Secret Naming Convention

Each vendor requires secrets following this pattern:

```
{vendorname}-login-url
{vendorname}-login-email        (or login-username)
{vendorname}-login-password     (or admin-password)
{vendorname}-newuser-password   (if applicable)
```

## Project Structure

```
Nexus/
├── main.py                            # Entry point (supports --install-browsers for deployment)
├── monitor.py                         # Nexus Monitor entry point (standalone polling service)
├── requirements.txt                   # Python dependencies
├── build.bat                          # Build + Intune packaging (8-step: preflight → build → .intunewin)
├── build_monitor.bat                  # Build NexusMonitor.exe
├── version_info.py                    # Generates Windows exe version metadata from APP_VERSION
├── deploy/                            # Deployment scripts
│   ├── install.ps1                    # Nexus GUI — Intune install
│   ├── uninstall.ps1                  # Nexus GUI — Intune uninstall
│   ├── install_monitor.ps1            # Nexus Monitor — Task Scheduler install
│   └── uninstall_monitor.ps1          # Nexus Monitor — Task Scheduler uninstall
├── assets/                            # Application assets
│   ├── nexus.ico                      # Multi-size icon (16–256px, font-hinted N)
│   ├── nexus.png                      # 256px reference PNG
│   ├── nexus.svg                      # SVG source (reference only)
│   └── generate_icon.py               # Icon generation script (Segoe UI Bold + manual ICO binary)
├── config/                            # Application configuration
│   ├── app_config.example.json        # Template (copy to app_config.json)
│   ├── monitor_config.example.json    # Template for Nexus Monitor (copy to monitor_config.json)
│   └── vendor_mappings.json           # Entra group → vendor automation mappings
├── monitor/                           # Nexus Monitor service
│   ├── auth.py                        # Client credentials authentication
│   ├── runner.py                      # Job runner with interval polling
│   ├── state.py                       # JSON state tracking
│   └── jobs/
│       └── partners_user_list.py      # Partners Credit PDF job
├── gui/                               # CustomTkinter GUI
│   ├── main_window.py                 # Main window and tab container
│   ├── tab_search.py                  # Entra ID user search
│   ├── tab_provisioning.py            # Vendor selection and user details
│   ├── tab_automation.py              # Automation runner and status display
│   └── tab_summary.py                 # Results and PDF export
├── services/                          # Core services
│   ├── auth_service.py                # MSAL authentication (delegated, persistent token cache)
│   ├── graph_api.py                   # Microsoft Graph API client
│   ├── keyvault_service.py            # Azure Key Vault integration
│   ├── config_manager.py              # Configuration loader
│   ├── ai_matcher.py                  # Claude AI role/branch matching
│   ├── pdf_generator.py               # PDF report generation
│   └── msal_credential_adapter.py     # MSAL → Azure Identity bridge
├── automation/vendors/                # Vendor automation modules
│   ├── accountchek.py
│   ├── bankvod.py
│   ├── certifiedcredit.py
│   ├── clearcapital.py
│   ├── dataverify.py
│   ├── experience.py
│   ├── mmi.py
│   ├── partnerscredit.py
│   └── theworknumber.py
├── models/                            # Data models
│   ├── user.py                        # EntraUser model
│   ├── vendor.py                      # VendorConfig model
│   └── automation_result.py           # Provisioning result model
├── Vendors/                           # Per-vendor configuration
│   ├── {VendorName}/
│   │   ├── config.json                # Vendor-specific settings (org, roles, URLs)
│   │   └── roles.json                 # Role mappings (if applicable)
├── docs/                              # Documentation
│   ├── ANNOUNCEMENT.md                # Rollout announcement for IT operations
│   ├── AUTHENTICATION_GUIDE.md        # Authentication architecture and setup
│   ├── AZURE_KEYVAULT_SETUP.md        # Key Vault provisioning guide (32 secrets)
│   ├── USER_GUIDE.md                  # End-user step-by-step guide
│   ├── VENDOR_ONBOARDING_TEMPLATE.md  # Template for documenting new vendor workflows
│   └── VENDOR_AUTOMATION_CHECKLIST.md # Vendor readiness matrix
└── utils/
    ├── logger.py                      # Logging configuration
    └── screenshot.py                  # Safe screenshot and debug file saving (%LOCALAPPDATA%\Nexus\screenshots\)
```

## Troubleshooting

### Authentication Issues

| Symptom | Cause | Resolution |
|---|---|---|
| Sign-in fails | Incorrect tenant or client ID | Verify values in `config/app_config.json` |
| `Insufficient privileges` | Missing API permissions | Ensure app registration has `User.Read.All`, `GroupMember.Read.All`, `Group.Read.All` |
| Token refresh errors | Expired consent | Re-authenticate or have an admin re-grant permissions |
| Sign-in not remembered | Cache file missing | Ensure `%LOCALAPPDATA%\Nexus\` is writable; signing out deletes the cache |

### Key Vault Issues

| Symptom | Cause | Resolution |
|---|---|---|
| `Invalid issuer (AKV10032)` | Tenant mismatch | Ensure Key Vault tenant matches app registration |
| `403 Forbidden` | Insufficient permissions | Grant user the **Key Vault Secrets User** RBAC role |
| `Secret not found` | Missing credential | Add the required secret to Key Vault ([naming convention](#key-vault-secret-naming-convention)) |

### Automation Issues

| Symptom | Cause | Resolution |
|---|---|---|
| `Executable doesn't exist` | Chromium not installed | Run `playwright install chromium` or contact IT support |
| Modal/tour blocking form | Vendor UI overlay | Check `_dismiss_tour()` selectors in the automation module |
| Timeout during MFA | User didn't complete MFA in time | Re-run the automation; MFA timeout is 10 minutes |

### Logs

Automation logs are written to `%APPDATA%\Nexus\logs\` with the format `nexus_YYYYMMDD.log`. Screenshots are captured at each automation step and saved to `%LOCALAPPDATA%\Nexus\screenshots\`.

## Security

| Measure | Detail |
|---|---|
| **Credential Storage** | All vendor credentials stored in Azure Key Vault — never in source code or config files |
| **Authentication** | GUI: Microsoft Entra ID with delegated permissions via MSAL; persistent token cache at `%LOCALAPPDATA%\Nexus\`. Monitor: client credentials flow (no user context) |
| **Access Control** | RBAC-based Key Vault policies; users must hold **Key Vault Secrets User** role |
| **Source Control** | `.gitignore` excludes secrets, screenshots, logs, and environment files |
| **Observability** | Automation runs in non-headless Chromium so operators can monitor and intervene |
| **Audit Trail** | PDF summary reports and timestamped logs for every provisioning run |

## Documentation

| Document | Audience | Description |
|---|---|---|
| [User Guide](docs/USER_GUIDE.md) | End users | Step-by-step walkthrough of the provisioning workflow |
| [Announcement](docs/ANNOUNCEMENT.md) | IT operations | Rollout announcement with before/after comparison |
| [Authentication Guide](docs/AUTHENTICATION_GUIDE.md) | Developers / IT admins | MSAL delegated auth architecture, App Registration setup |
| [Key Vault Setup](docs/AZURE_KEYVAULT_SETUP.md) | IT admins | Complete secret inventory (32 secrets), RBAC configuration |
| [Vendor Checklist](docs/VENDOR_AUTOMATION_CHECKLIST.md) | Developers | Readiness matrix for all vendor automation modules |
| [Onboarding Template](docs/VENDOR_ONBOARDING_TEMPLATE.md) | Subject matter experts | Fill-in template for documenting new vendor workflows |

## Contributing

Nexus is an internal tool. To contribute:

1. Create a feature branch from `main`
2. Follow existing patterns in `automation/vendors/` for new vendor modules
3. Ensure all vendor credentials are stored in Key Vault — never hardcode URLs or passwords
4. Test with a non-production user account before submitting a pull request
5. Open a PR against `main` for review

---

<div align="center">

**Nexus** is developed and maintained by the IT department at **Highland Mortgage Services**.

</div>
