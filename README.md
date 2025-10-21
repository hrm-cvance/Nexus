# Nexus - Automated Vendor Account Provisioning

Nexus is an automated system for provisioning user accounts across multiple vendor platforms. It integrates with Azure Active Directory (Entra ID) and Azure Key Vault to securely manage credentials and automate account creation based on group membership.

## Features

- **Azure AD Integration**: Search and retrieve user information from Entra ID
- **Group-Based Provisioning**: Automatically detect which vendors need accounts based on AD group membership
- **Secure Credential Management**: All vendor credentials stored in Azure Key Vault
- **AI-Powered Matching**: Intelligent role and branch assignment using Claude AI
- **Browser Automation**: Playwright-based automation for vendor account creation
- **User-Friendly GUI**: Tkinter-based interface for non-technical users
- **Comprehensive Logging**: Detailed logs for troubleshooting and audit trails

## Supported Vendors

| Vendor | Entra Group | Status |
|--------|-------------|--------|
| **AccountChek** | `AccountChek_Users` | ✅ Active |
| **BankVOD** | `BankVOD_Users` | ✅ Active |

## Architecture

```
Nexus Application
├── Azure AD (Entra ID) - User data & group membership
├── Azure Key Vault - Secure credential storage
├── Microsoft Graph API - User search & details
├── Playwright Browser Automation - Vendor account creation
└── Claude AI - Role/branch matching
```

## Prerequisites

- **Python 3.8+**
- **Node.js & npm** (for Playwright)
- **Azure Subscription** with:
  - App Registration (for authentication)
  - Azure Key Vault (for credentials)
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

Follow the detailed setup guide in [docs/AZURE_KEYVAULT_SETUP.md](docs/AZURE_KEYVAULT_SETUP.md)

**Quick Summary:**
1. Create App Registration in Azure AD
2. Create Azure Key Vault
3. Add vendor credentials as secrets
4. Grant permissions to Nexus app and users

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

### Running Nexus

```bash
python main.py
```

### Workflow

1. **Sign In**: Sign in with your Microsoft account (must have Graph API permissions)
2. **Search User**: Search for user by name, email, or employee ID
3. **Select User**: View user details and detected vendor access
4. **Provision Accounts**: Start automation to create vendor accounts
5. **Review Results**: Check logs and screenshots for success/errors

### User Interface

- **Tab 1: User Search** - Search Entra ID for users
- **Tab 2: Account Provisioning** - Review user details and select vendors
- **Tab 3: Automation Status** - Monitor automation progress and view results

## Adding a New Vendor

Follow the [VENDOR_ONBOARDING_TEMPLATE.md](VENDOR_ONBOARDING_TEMPLATE.md) guide:

1. Create vendor directory: `Vendors/{VendorName}/`
2. Add configuration: `config.json`, `roles.json`
3. Create automation module: `automation/vendors/{vendorname}.py`
4. Add to vendor mappings: `config/vendor_mappings.json`
5. Store credentials in Azure Key Vault
6. Test automation

## Key Vault Secrets

Each vendor requires secrets stored in Azure Key Vault:

### AccountChek Secrets
- `accountchek-login-url` - Login page URL
- `accountchek-login-email` - Admin email
- `accountchek-login-password` - Admin password
- `accountchek-newuser-password` - Default password for new users

### BankVOD Secrets
- `bankvod-login-url` - Login page URL
- `bankvod-login-account-id` - Company/Account ID (if required)
- `bankvod-login-email` - Admin email
- `bankvod-login-password` - Admin password
- `bankvod-newuser-password` - Default password for new users

## Configuration Files

### Vendor Config (`Vendors/{VendorName}/config.json`)
```json
{
  "vendor": {
    "name": "VendorName",
    "display_name": "Vendor Display Name",
    "keyvault_secrets": {
      "login_url": "vendor-login-url",
      "login_email": "vendor-login-email",
      "login_password": "vendor-login-password",
      "newuser_password": "vendor-newuser-password"
    }
  }
}
```

### Vendor Mappings (`config/vendor_mappings.json`)
```json
{
  "mappings": [
    {
      "entra_group_name": "VendorName_Users",
      "vendor_name": "VendorName",
      "automation_module": "automation.vendors.vendorname",
      "enabled": true
    }
  ]
}
```

## Project Structure

```
c:\Scripts\Nexus\
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── package.json                     # Playwright dependencies
├── gui/                            # GUI components
│   ├── main_window.py              # Main application window
│   ├── tab_search.py               # User search tab
│   ├── tab_provisioning.py         # Account provisioning tab
│   └── tab_automation.py           # Automation status tab
├── services/                       # Core services
│   ├── auth_service.py             # MSAL authentication
│   ├── graph_api.py                # Microsoft Graph API client
│   ├── keyvault_service.py         # Azure Key Vault integration
│   ├── config_manager.py           # Configuration management
│   ├── msal_credential_adapter.py  # MSAL to Azure Identity adapter
│   └── ai_matcher.py               # AI role/branch matching
├── automation/vendors/             # Vendor automation modules
│   ├── accountchek.py              # AccountChek automation
│   └── bankvod.py                  # BankVOD automation
├── models/                         # Data models
│   ├── user.py                     # User and group models
│   └── vendor.py                   # Vendor configuration models
├── utils/                          # Utilities
│   └── logger.py                   # Logging configuration
├── Vendors/                        # Vendor-specific configs
│   ├── AccountChek/
│   │   ├── config.json
│   │   ├── roles.json
│   │   └── README.md
│   └── BankVOD/
│       ├── config.json
│       └── README.md
├── config/                         # Application configuration
│   ├── app_config.json             # Azure & app settings
│   └── vendor_mappings.json        # Vendor-to-group mappings
└── docs/                           # Documentation
    ├── AZURE_KEYVAULT_SETUP.md
    └── AUTHENTICATION_GUIDE.md
```

## Logging

Logs are stored in `%APPDATA%\Nexus\logs\`:
- Format: `nexus_YYYYMMDD.log`
- Includes: Authentication, API calls, automation steps, errors
- Log level: INFO (configurable in `logger.py`)

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
- Review screenshots (saved to Desktop on error)
- Verify vendor credentials in Key Vault
- Ensure Playwright browsers are installed

### Common Errors

**"Invalid issuer" (AKV10032)**
- Key Vault tenant mismatch - update Key Vault tenant ID or grant cross-tenant access

**"403 Forbidden"**
- Insufficient Key Vault permissions - grant "Key Vault Secrets User" role

**"Secret not found"**
- Missing Key Vault secret - add required secrets to vault

## Security

- ✅ All credentials stored in Azure Key Vault (never in code)
- ✅ Uses Azure AD authentication (no hardcoded passwords)
- ✅ RBAC-based access control via Key Vault policies
- ✅ Audit logs for all automation activities
- ✅ `.gitignore` prevents committing sensitive data

## Development

### Adding a New Vendor Automation

1. Copy `Vendors/AccountChek/` as template
2. Update `config.json` with vendor details
3. Create automation module in `automation/vendors/`
4. Implement `provision_user()` function
5. Add vendor mapping to `config/vendor_mappings.json`
6. Add secrets to Azure Key Vault
7. Test thoroughly before production use

### Running Tests
```bash
# Test Graph API connection
python -c "from services.graph_api import GraphAPIClient; print('Test')"

# Test Key Vault connection
python -c "from services.keyvault_service import get_keyvault_service; kv = get_keyvault_service(); print(kv.test_connection())"
```

## Version History

- **v1.0.0** (2025-10-20)
  - Initial release
  - AccountChek automation
  - BankVOD automation
  - Azure Key Vault integration
  - AI-powered role matching
  - Interactive browser authentication

## Credits

Built by Chris Vance @ Highland Mortgage Services

Technologies:
- Python 3.x
- Playwright (browser automation)
- Microsoft Authentication Library (MSAL)
- Azure SDK for Python
- Anthropic Claude AI
- Tkinter (GUI)

## License

Internal use only - Highland Mortgage Services

## Support

For issues or questions:
1. Check logs in `%APPDATA%\Nexus\logs\`
2. Review documentation in `docs/`
3. Contact IT administrator
