# ClearCapital - Azure Key Vault Secrets

This document lists the secrets required for ClearCapital automation.

## Required Secrets

### Login Credentials

1. **clearcapital-login-url**
   - **Description**: The ClearCapital secure portal URL
   - **Value**: `https://secure.clearcapital.com`
   - **Type**: URL

2. **clearcapital-admin-username**
   - **Description**: Admin username for logging into ClearCapital to manage users
   - **Value**: Your ClearCapital admin account username
   - **Type**: String

3. **clearcapital-admin-password**
   - **Description**: Admin password for logging into ClearCapital
   - **Value**: Your ClearCapital admin account password
   - **Type**: Secret/Password

## How to Add Secrets to Azure Key Vault

Using Azure CLI:
```bash
# Set your Key Vault name
VAULT_NAME="hrm-nexus-credentials"

# Add ClearCapital secrets
az keyvault secret set --vault-name $VAULT_NAME --name "clearcapital-login-url" --value "https://secure.clearcapital.com"
az keyvault secret set --vault-name $VAULT_NAME --name "clearcapital-admin-username" --value "YOUR_ADMIN_USERNAME"
az keyvault secret set --vault-name $VAULT_NAME --name "clearcapital-admin-password" --value "YOUR_ADMIN_PASSWORD"
```

Using Azure Portal:
1. Navigate to your Key Vault: `hrm-nexus-credentials`
2. Click "Secrets" in the left menu
3. Click "+ Generate/Import"
4. For each secret:
   - Name: Use the exact name from above (e.g., `clearcapital-admin-username`)
   - Value: Enter the corresponding value
   - Click "Create"

## Notes

- User-specific data (name, email, phone) comes from Entra ID user attributes
- Username format is `Firstname.Lastname` (e.g., `John.Smith`)
- If username exists, append `1` (e.g., `John.Smith1`)
- Default roles can be configured in `config.json`
