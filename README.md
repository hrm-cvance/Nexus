# Nexus - Automated Vendor Account Provisioning

Nexus automates the creation of user accounts across multiple vendor platforms used by Highland Mortgage Services. It integrates with Azure Active Directory (Entra ID) for user lookup, Azure Key Vault for secure credential management, and Playwright for browser-based automation.

## Features

- **Azure AD Integration**: Search and retrieve user information from Entra ID
- **Group-Based Provisioning**: Automatically detect which vendors need accounts based on AD group membership
- **Secure Credential Management**: All vendor credentials stored in Azure Key Vault
- **AI-Powered Matching**: Intelligent role and branch assignment using Claude AI
- **Browser Automation**: Playwright-based automation for vendor account creation
- **Duplicate Detection**: Prompts for resolution when usernames or emails already exist
- **PDF Summaries**: Generate provisioning summary reports
- **User-Friendly GUI**: CustomTkinter interface with tabbed workflow

## Supported Vendors

| Vendor | Entra Group | Automation | Status |
|--------|-------------|------------|--------|
| **AccountChek** | `AccountChek_Users` | `accountchek.py` | Active |
| **BankVOD** | `BankVOD_Users` | `bankvod.py` | Active |
| **Clear Capital** | `ClearCapital_Users` | `clearcapital.py` | Active |
| **DataVerify** | `DataVerify_Users` | `dataverify.py` | Active |
| **Certified Credit** | `CertifiedCredit_Users` | `certifiedcredit.py` | Active |
| **Partners Credit** | `PartnersCredit_Users` | `partnerscredit.py` | Active |
| **The Work Number** | `TheWorkNumber_Users` | `theworknumber.py` | Active |
| **MMI** | `MMI_Users` | `mmi.py` | Active |
| **Experience.com** | `Experience_Users` | `experience.py` | Disabled |

## Architecture

```
Nexus Application
├── Microsoft Entra ID ─── User data & group membership (Graph API)
├── Azure Key Vault ────── Vendor credentials (admin logins, URLs)
├── Playwright ─────────── Browser automation (Chromium, non-headless)
├── Claude AI ──────────── Role/branch matching
└── CustomTkinter GUI ──── Tabbed workflow interface
```

## Prerequisites

- **Python 3.8+**
- **Node.js & npm** (for Playwright)
- **Azure Subscription** with:
  - App Registration (delegated permissions)
  - Azure Key Vault
  - Entra ID access
- **Anthropic API Key** (for AI matching - optional)

## Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd Nexus
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Playwright Browsers
```bash
playwright install chromium
```

### 4. Configure Azure

Follow the detailed setup guide in [docs/AZURE_KEYVAULT_SETUP.md](docs/AZURE_KEYVAULT_SETUP.md).

1. Create App Registration in Azure AD
2. Create Azure Key Vault
3. Add vendor credentials as secrets
4. Grant "Key Vault Secrets User" role to users

### 5. Configure Application

On first run, Nexus creates configuration in `%APPDATA%\Nexus\`:
- `config\app_config.json` - Azure tenant, client ID, Key Vault URL
- `config\vendor_mappings.json` - Vendor-to-group mappings
- `logs\` - Application logs

Edit `app_config.json` with your Azure details:
```json
{
  "microsoft": {
    "tenant_id": "your-tenant-id",
    "client_id": "your-client-id",
    "scopes": [
      "User.Read.All",
      "GroupMember.Read.All",
      "Group.Read.All",
      "https://vault.azure.net/user_impersonation"
    ]
  },
  "azure_keyvault": {
    "vault_url": "https://your-keyvault.vault.azure.net/"
  }
}
```

## Usage

```bash
python main.py
```

### Workflow

1. **Sign In** - Authenticate with your Microsoft account
2. **Search User** - Search Entra ID by name, email, or employee ID
3. **Select Vendors** - Review detected vendor access based on group membership
4. **Run Automation** - Provision accounts across selected vendors
5. **Review Results** - Check status, view logs, export PDF summary

### GUI Tabs

| Tab | Purpose |
|-----|---------|
| **Search** | Search Entra ID for users |
| **Provisioning** | Review user details, select vendors to provision |
| **Automation** | Monitor automation progress, handle prompts (MFA, duplicates) |
| **Summary** | View results, export PDF report |

### Duplicate User Handling

When a vendor reports that a username or email already exists, Nexus prompts you with options:
- **Provide an alternative** username/email to retry
- **Skip** the vendor entirely

## Adding a New Vendor

See [VENDOR_ONBOARDING_TEMPLATE.md](VENDOR_ONBOARDING_TEMPLATE.md) for the full guide.

Quick steps:
1. Create `vendors/{VendorName}/config.json` with vendor details
2. Create automation module `automation/vendors/{vendorname}.py`
3. Implement `provision_user()` async function
4. Add mapping to `config/vendor_mappings.json`
5. Store credentials in Azure Key Vault

### Key Vault Secret Naming

Each vendor needs secrets following the pattern `{vendorname}-{key}`:
```
{vendorname}-login-url
{vendorname}-admin-username (or login-email)
{vendorname}-admin-password (or login-password)
{vendorname}-newuser-password (if applicable)
```

## Project Structure

```
Nexus/
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── package.json                     # Playwright dependencies
├── gui/                             # GUI components
│   ├── main_window.py               # Main CustomTkinter window
│   ├── tab_search.py                # User search tab
│   ├── tab_provisioning.py          # Vendor selection tab
│   ├── tab_automation.py            # Automation runner & status
│   └── tab_summary.py              # Results summary & PDF export
├── services/                        # Core services
│   ├── auth_service.py              # MSAL authentication
│   ├── graph_api.py                 # Microsoft Graph API client
│   ├── keyvault_service.py          # Azure Key Vault integration
│   ├── config_manager.py            # Configuration management
│   ├── ai_matcher.py                # AI role/branch matching
│   ├── pdf_generator.py             # PDF summary generation
│   └── msal_credential_adapter.py   # MSAL to Azure Identity adapter
├── automation/vendors/              # Vendor automation modules
│   ├── accountchek.py
│   ├── bankvod.py
│   ├── clearcapital.py
│   ├── dataverify.py
│   ├── certifiedcredit.py
│   ├── partnerscredit.py
│   ├── theworknumber.py
│   ├── mmi.py
│   └── experience.py
├── models/                          # Data models
│   ├── user.py                      # EntraUser model
│   ├── vendor.py                    # Vendor config models
│   └── automation_result.py         # Result models
├── vendors/                         # Vendor-specific configs
│   ├── AccountChek/
│   ├── BankVOD/
│   ├── ClearCapital/
│   ├── DataVerify/
│   ├── CertifiedCredit/
│   ├── PartnersCredit/
│   ├── TheWorkNumber/
│   ├── MMI/
│   └── Experience/
├── config/                          # Application configuration
│   ├── app_config.json
│   └── vendor_mappings.json
└── docs/                            # Documentation
    ├── AZURE_KEYVAULT_SETUP.md
    ├── AUTHENTICATION_GUIDE.md
    └── vendor_automation_checklist.md
```

## Logging

Logs are stored in `%APPDATA%\Nexus\logs\`:
- Format: `nexus_YYYYMMDD.log`
- Includes: Authentication, API calls, automation steps, errors
- Automation screenshots saved to project root during runs (gitignored)

## Troubleshooting

### Authentication Issues
- Ensure app registration has correct API permissions
- Check tenant ID and client ID in config
- Verify user has required roles

### Key Vault Access Denied
- User must have "Key Vault Secrets User" role
- Check Key Vault's tenant ID matches app registration
- Verify vault URL is correct

### Automation Failures
- Check logs in `%APPDATA%\Nexus\logs\`
- Review screenshots saved during automation
- Verify vendor credentials in Key Vault
- Ensure Playwright browsers are installed (`playwright install chromium`)

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Invalid issuer (AKV10032)` | Key Vault tenant mismatch | Update Key Vault tenant ID |
| `403 Forbidden` | Insufficient KV permissions | Grant "Key Vault Secrets User" role |
| `Secret not found` | Missing KV secret | Add required secrets to vault |
| `Could not find Add User button` | Tour/modal blocking UI | Check `_dismiss_tour()` selectors |

## Security

- All credentials stored in Azure Key Vault (never in code)
- Azure AD authentication with delegated permissions (no service principals)
- RBAC-based access control via Key Vault policies
- `.gitignore` prevents committing secrets, screenshots, and logs
- Automation runs non-headless so users can monitor and intervene

## Credits

Built by Chris Vance @ Highland Mortgage Services

Technologies: Python, Playwright, MSAL, Azure SDK, Anthropic Claude, CustomTkinter, ReportLab

## License

Internal use only - Highland Mortgage Services
