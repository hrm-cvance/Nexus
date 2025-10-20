# AccountChek - Azure Key Vault Secrets

All AccountChek credentials are stored in Azure Key Vault for security.

## Required Secrets

The following secrets must be configured in your Azure Key Vault:

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `accountchek-login-url` | AccountChek login URL | `https://verifier.accountchek.com/login` |
| `accountchek-login-email` | Admin login email | `admin@yourcompany.com` |
| `accountchek-login-password` | Admin login password | (your secure password) |
| `accountchek-newuser-password` | Default password for new users | (temporary password, must be changed on first login) |

## Secret Naming Convention

All secrets follow the pattern: `{vendor-name}-{credential-type}`

- Vendor name is lowercase
- Credential type uses hyphens
- Only alphanumeric characters and hyphens are allowed

## How to Add Secrets to Azure Key Vault

### Using Azure CLI:

```bash
# Set your Key Vault name
VAULT_NAME="your-keyvault-name"

# Add secrets
az keyvault secret set --vault-name $VAULT_NAME --name "accountchek-login-url" --value "https://verifier.accountchek.com/login"
az keyvault secret set --vault-name $VAULT_NAME --name "accountchek-login-email" --value "your-admin@email.com"
az keyvault secret set --vault-name $VAULT_NAME --name "accountchek-login-password" --value "YourSecurePassword123!"
az keyvault secret set --vault-name $VAULT_NAME --name "accountchek-newuser-password" --value "Welcome@123"
```

### Using Azure Portal:

1. Navigate to your Azure Key Vault
2. Click **Secrets** in the left menu
3. Click **+ Generate/Import**
4. Enter the secret name and value
5. Click **Create**

## Permissions Required

The Nexus application requires the following permissions on the Key Vault:

- **Secret Permissions**: Get, List

These can be granted via:
- **Access Policy** (classic)
- **RBAC Role**: "Key Vault Secrets User"

## Authentication

The application supports multiple authentication methods (in order of precedence):

1. **Azure CLI** - Best for development (requires `az login`)
2. **Managed Identity** - Best for production (Azure VMs, App Services)
3. **Environment Variables** - Service principal credentials
4. **Visual Studio Code** - For local development

## Environment Variables

Set the Key Vault URL using environment variable:

```bash
# Windows
set AZURE_KEYVAULT_URL=https://your-keyvault.vault.azure.net/

# Linux/Mac
export AZURE_KEYVAULT_URL=https://your-keyvault.vault.azure.net/
```

Or configure it in the Settings tab of the Nexus application.
