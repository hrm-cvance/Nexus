# BankVOD Vendor Integration

This directory contains configuration and documentation for the BankVOD vendor automation.

## Overview

**BankVOD** is a verification of deposit (VOD) service platform. The Nexus automation creates authorized user accounts in the BankVOD system.

## Process Flow

The automation follows this workflow based on the BankVOD Account Setup SOP:

1. **Login** to BankVOD admin portal
2. **Navigate** to Main Menu → Authorized Users
3. **Click** "Add New Authorized User" button
4. **Fill form** with user details:
   - First Name
   - Last Name
   - Email
   - Password (auto-generated, shown to user)
   - Cost Center/Account Code (from Entra ID)
   - Comments (optional)
5. **Submit** form to create user
6. **Search** for newly created user
7. **Update** user record to change password to HRM default
8. **Submit** updated user

## Files

- `config.json` - Vendor configuration and Key Vault secret mappings
- `keyvault_secrets.md` - Documentation for required Azure Key Vault secrets
- `README.md` - This file

## Configuration

### Entra ID Group
- **Group Name**: `BankVOD_Users`
- Users in this group will automatically be detected for BankVOD provisioning

### Required Fields
- **First Name** - From Entra ID `givenName`
- **Last Name** - From Entra ID `surname`
- **Email** - From Entra ID `mail`
- **Cost Center/Account Code** - Extracted from Entra ID `officeLocation` or `department`
- **Password** - Auto-generated initially, then changed to HRM default

### Default Settings
- **Password Change Required**: No (password is set to HRM default by admin)

## Azure Key Vault Secrets

See [keyvault_secrets.md](keyvault_secrets.md) for the complete list of required secrets:

- `bankvod-login-url`
- `bankvod-login-email`
- `bankvod-login-password`
- `bankvod-newuser-password`

## Automation Module

The Playwright automation is implemented in:
- **Module**: `automation/vendors/bankvod.py`
- **Entry Point**: `provision_user(user, config_path, api_key)`

## Testing

To test BankVOD automation:

1. Ensure all Key Vault secrets are configured
2. Add test user to `BankVOD_Users` group in Entra ID
3. Run Nexus application
4. Search for test user
5. Click "Start Automation" for BankVOD
6. Verify account creation in BankVOD portal
7. Check logs in `%APPDATA%\Nexus\logs\`

## Known Issues / Notes

- The two-step process (create + update password) is required because BankVOD doesn't allow setting custom passwords during initial creation
- Auto-generated password is shown to user, then immediately changed to HRM default
- Cost Center field is required - extracted from office location or department in Entra ID

## Support

For issues with BankVOD automation:
1. Check Nexus logs: `%APPDATA%\Nexus\logs\nexus_YYYYMMDD.log`
2. Verify Key Vault secrets are correct
3. Ensure user has Cost Center information in Entra ID
4. Check screenshots saved to Desktop on errors
