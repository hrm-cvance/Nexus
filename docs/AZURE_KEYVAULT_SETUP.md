# Azure Key Vault Setup Guide

This guide explains how to set up Azure Key Vault for the Nexus application to securely store and retrieve vendor credentials.

## Overview

Nexus uses Azure Key Vault to:
- **Eliminate plaintext passwords** from config files
- **Centralize credential management** in Azure
- **Leverage Azure AD authentication** for secure access
- **Enable credential rotation** without code changes
- **Provide audit trails** for credential access

## Prerequisites

1. **Azure Subscription** with permissions to create Key Vault
2. **Azure CLI** installed ([Download](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli))
3. **Appropriate Azure AD permissions** (or use service principal)

## Step 1: Create Azure Key Vault

### Option A: Using Azure Portal

1. Navigate to [Azure Portal](https://portal.azure.com)
2. Click **Create a resource** → Search for "Key Vault"
3. Click **Create**
4. Fill in the details:
   - **Subscription**: Your Azure subscription
   - **Resource Group**: Create new or select existing
   - **Key Vault Name**: `nexus-credentials` (must be globally unique)
   - **Region**: Select your region
   - **Pricing Tier**: Standard
5. Click **Review + Create** → **Create**

### Option B: Using Azure CLI

```bash
# Login to Azure
az login

# Set variables
RESOURCE_GROUP="nexus-rg"
VAULT_NAME="nexus-credentials"  # Must be globally unique
LOCATION="eastus"

# Create resource group (if needed)
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Key Vault
az keyvault create \
  --name $VAULT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --enabled-for-deployment true \
  --enabled-for-template-deployment true
```

## Step 2: Add Vendor Credentials to Key Vault

### AccountChek Secrets

```bash
# Set your Key Vault name
VAULT_NAME="nexus-credentials"

# Add AccountChek secrets
az keyvault secret set --vault-name $VAULT_NAME \
  --name "accountchek-login-url" \
  --value "https://verifier.accountchek.com/login"

az keyvault secret set --vault-name $VAULT_NAME \
  --name "accountchek-login-email" \
  --value "your-admin@email.com"

az keyvault secret set --vault-name $VAULT_NAME \
  --name "accountchek-login-password" \
  --value "YourSecurePassword123!"

az keyvault secret set --vault-name $VAULT_NAME \
  --name "accountchek-newuser-password" \
  --value "Welcome@123"
```

### Secret Naming Convention

All secrets follow the pattern: `{vendor-name}-{credential-type}`

Examples:
- `accountchek-login-url`
- `accountchek-login-email`
- `accountchek-login-password`
- `accountchek-newuser-password`

## Step 3: Configure Access Permissions

### Option A: Using Access Policy (Classic)

```bash
# Grant your user account access
USER_PRINCIPAL_NAME="user@yourcompany.com"

az keyvault set-policy \
  --name $VAULT_NAME \
  --upn $USER_PRINCIPAL_NAME \
  --secret-permissions get list
```

### Option B: Using RBAC (Recommended)

```bash
# Enable RBAC on Key Vault
az keyvault update --name $VAULT_NAME --enable-rbac-authorization true

# Get your user object ID
USER_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)

# Get Key Vault resource ID
VAULT_ID=$(az keyvault show --name $VAULT_NAME --query id -o tsv)

# Assign "Key Vault Secrets User" role
az role assignment create \
  --assignee $USER_OBJECT_ID \
  --role "Key Vault Secrets User" \
  --scope $VAULT_ID
```

## Step 4: Configure Nexus Application

### Set Environment Variable

**Windows (PowerShell):**
```powershell
# Set for current session
$env:AZURE_KEYVAULT_URL = "https://nexus-credentials.vault.azure.net/"

# Set permanently (user-level)
[System.Environment]::SetEnvironmentVariable("AZURE_KEYVAULT_URL", "https://nexus-credentials.vault.azure.net/", "User")

# Set permanently (system-level - requires admin)
[System.Environment]::SetEnvironmentVariable("AZURE_KEYVAULT_URL", "https://nexus-credentials.vault.azure.net/", "Machine")
```

**Windows (Command Prompt):**
```cmd
set AZURE_KEYVAULT_URL=https://nexus-credentials.vault.azure.net/
```

**Linux/Mac:**
```bash
export AZURE_KEYVAULT_URL=https://nexus-credentials.vault.azure.net/

# Add to ~/.bashrc or ~/.zshrc for persistence
echo 'export AZURE_KEYVAULT_URL=https://nexus-credentials.vault.azure.net/' >> ~/.bashrc
```

## Step 5: Authenticate to Azure

Nexus supports multiple authentication methods:

### 1. Azure CLI (Recommended for Development)

```bash
az login
```

This is the easiest method for local development. Nexus will automatically use your Azure CLI credentials.

### 2. Managed Identity (Recommended for Production)

When running on Azure VMs, App Services, or Azure Functions:
- Enable System-Assigned Managed Identity on the resource
- Grant the managed identity access to the Key Vault
- No code changes needed - authentication is automatic

### 3. Service Principal (CI/CD Pipelines)

```bash
# Create service principal
SP_OUTPUT=$(az ad sp create-for-rbac --name "nexus-sp" --skip-assignment)

# Extract credentials
CLIENT_ID=$(echo $SP_OUTPUT | jq -r '.appId')
CLIENT_SECRET=$(echo $SP_OUTPUT | jq -r '.password')
TENANT_ID=$(echo $SP_OUTPUT | jq -r '.tenant')

# Grant access to Key Vault
az keyvault set-policy \
  --name $VAULT_NAME \
  --spn $CLIENT_ID \
  --secret-permissions get list

# Set environment variables
export AZURE_CLIENT_ID=$CLIENT_ID
export AZURE_CLIENT_SECRET=$CLIENT_SECRET
export AZURE_TENANT_ID=$TENANT_ID
```

## Step 6: Verify Setup

### Test Key Vault Connection

```python
# Test script
from services.keyvault_service import get_keyvault_service

try:
    kv = get_keyvault_service()
    print(f"✓ Connected to: {kv.vault_url}")

    # Test getting a secret
    secret = kv.get_secret("accountchek-login-url")
    print(f"✓ Retrieved secret: accountchek-login-url")

    # Get status
    status = kv.get_status()
    print(f"✓ Auth method: {status['auth_method']}")
    print(f"✓ Cached secrets: {status['cached_secrets']}")

except Exception as e:
    print(f"✗ Error: {e}")
```

### Check Logs

After running Nexus, check the logs for Key Vault initialization:

```
%APPDATA%\Nexus\logs\nexus_YYYYMMDD.log
```

Look for:
- `✓ KeyVaultService initialized and connected to https://...`
- `Using Azure CLI authentication for Key Vault`

## Troubleshooting

### Error: "AZURE_KEYVAULT_URL not configured"

**Solution**: Set the environment variable:
```bash
export AZURE_KEYVAULT_URL=https://your-vault.vault.azure.net/
```

### Error: "Permission denied" or "403 Forbidden"

**Solution**: Grant your user access to the Key Vault:
```bash
az keyvault set-policy --name $VAULT_NAME --upn user@company.com --secret-permissions get list
```

### Error: "Azure CLI authentication failed"

**Solution**: Login to Azure CLI:
```bash
az login
az account show  # Verify you're logged in
```

### Error: "Secret not found"

**Solution**: Verify secret exists and name is correct:
```bash
az keyvault secret list --vault-name $VAULT_NAME --query "[].name"
```

## Security Best Practices

1. **Use RBAC** instead of Access Policies for better granular control
2. **Enable soft-delete** and purge protection on Key Vault
3. **Rotate credentials regularly** using Key Vault secret versions
4. **Monitor access** using Azure Monitor and Log Analytics
5. **Use Managed Identity** in production (no stored credentials)
6. **Restrict network access** using Key Vault firewalls
7. **Enable audit logging** to track secret access

## Adding New Vendors

When adding a new vendor, follow this pattern:

```bash
# Example: Adding "VendorX" credentials
VAULT_NAME="nexus-credentials"

az keyvault secret set --vault-name $VAULT_NAME \
  --name "vendorx-login-url" \
  --value "https://vendorx.com/login"

az keyvault secret set --vault-name $VAULT_NAME \
  --name "vendorx-login-email" \
  --value "admin@company.com"

az keyvault secret set --vault-name $VAULT_NAME \
  --name "vendorx-login-password" \
  --value "SecurePassword123!"
```

## Next Steps

1. ✓ Create Azure Key Vault
2. ✓ Add vendor secrets
3. ✓ Configure access permissions
4. ✓ Set AZURE_KEYVAULT_URL environment variable
5. ✓ Authenticate to Azure (az login)
6. ✓ Run Nexus and verify logs
7. ✓ Test automation with real credentials

## Additional Resources

- [Azure Key Vault Documentation](https://learn.microsoft.com/en-us/azure/key-vault/)
- [Azure CLI Reference](https://learn.microsoft.com/en-us/cli/azure/keyvault)
- [Python Azure SDK](https://learn.microsoft.com/en-us/python/api/overview/azure/keyvault-secrets-readme)
- [Managed Identity Overview](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview)
