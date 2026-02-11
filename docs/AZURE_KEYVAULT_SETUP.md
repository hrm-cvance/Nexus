# Azure Key Vault Setup Guide

This guide covers provisioning and configuring Azure Key Vault for Nexus. All vendor admin credentials (login URLs, usernames, passwords) are stored in Key Vault and retrieved at runtime using the signed-in user's Microsoft identity.

## Table of Contents

- [How Nexus Authenticates](#how-nexus-authenticates)
- [Prerequisites](#prerequisites)
- [Step 1: Create the Key Vault](#step-1-create-the-key-vault)
- [Step 2: Grant User Access](#step-2-grant-user-access)
- [Step 3: Add Vendor Secrets](#step-3-add-vendor-secrets)
- [Step 4: Configure Nexus](#step-4-configure-nexus)
- [Step 5: Verify Setup](#step-5-verify-setup)
- [Complete Secret Reference](#complete-secret-reference)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)

## How Nexus Authenticates

Nexus uses **delegated permissions** — no service principals or stored client secrets.

```
User signs in via Microsoft (MSAL)
        │
        ▼
┌─────────────────┐
│  MSAL Token     │──► Microsoft Graph API (user lookup, groups)
│  (delegated)    │
│                 │──► Azure Key Vault (vendor credentials)
│                 │    via MSALCredentialAdapter
└─────────────────┘
```

1. The user signs in through a Microsoft browser authentication prompt
2. MSAL acquires a token with delegated scopes
3. An `MSALCredentialAdapter` bridges the MSAL token to the Azure SDK credential interface
4. The `KeyVaultService` uses that credential to call Key Vault as the signed-in user

This means **each user who runs Nexus must have Key Vault access** — there is no shared service account.

## Prerequisites

- **Azure subscription** with permissions to create a Key Vault
- **Azure AD App Registration** with delegated permissions (see [AUTHENTICATION_GUIDE.md](AUTHENTICATION_GUIDE.md))
- **Azure CLI** installed ([download](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)) — used for initial setup only

## Step 1: Create the Key Vault

### Option A: Azure Portal

1. Navigate to [portal.azure.com](https://portal.azure.com)
2. **Create a resource** > search for **Key Vault** > **Create**
3. Configure:
   - **Subscription**: Your Azure subscription
   - **Resource Group**: Create new or select existing
   - **Key Vault Name**: Must be globally unique (e.g., `hrm-nexus-credentials`)
   - **Region**: Select your region
   - **Pricing Tier**: Standard
   - **Permission model**: Azure role-based access control (RBAC)
4. Click **Review + Create** > **Create**

### Option B: Azure CLI

```bash
az login

RESOURCE_GROUP="nexus-rg"
VAULT_NAME="hrm-nexus-credentials"   # must be globally unique
LOCATION="eastus"

# Create resource group (if needed)
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Key Vault with RBAC authorization
az keyvault create \
  --name $VAULT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --enable-rbac-authorization true
```

## Step 2: Grant User Access

Every user who runs Nexus needs the **Key Vault Secrets User** role on the vault. This grants read-only access to secret values.

### Grant access to a single user

```bash
VAULT_NAME="hrm-nexus-credentials"

# Get the Key Vault resource ID
VAULT_ID=$(az keyvault show --name $VAULT_NAME --query id -o tsv)

# Get the user's object ID
USER_ID=$(az ad user show --id "user@yourcompany.com" --query id -o tsv)

# Assign the role
az role assignment create \
  --assignee $USER_ID \
  --role "Key Vault Secrets User" \
  --scope $VAULT_ID
```

### Grant access to an Azure AD group (recommended)

For easier management, create a security group (e.g., `Nexus_Users`) and assign the role to the group:

```bash
GROUP_ID=$(az ad group show --group "Nexus_Users" --query id -o tsv)

az role assignment create \
  --assignee $GROUP_ID \
  --role "Key Vault Secrets User" \
  --scope $VAULT_ID
```

Then add users to the `Nexus_Users` group in Entra ID as needed.

### Grant admin access (for managing secrets)

The IT admin who adds/updates vendor credentials needs the **Key Vault Secrets Officer** role:

```bash
ADMIN_ID=$(az ad user show --id "admin@yourcompany.com" --query id -o tsv)

az role assignment create \
  --assignee $ADMIN_ID \
  --role "Key Vault Secrets Officer" \
  --scope $VAULT_ID
```

## Step 3: Add Vendor Secrets

All secrets follow the naming convention: `{vendorname}-{credential-type}`

Secret names may only contain alphanumeric characters and hyphens.

### Add secrets via Azure CLI

```bash
VAULT_NAME="hrm-nexus-credentials"

# Example: AccountChek
az keyvault secret set --vault-name $VAULT_NAME --name "accountchek-login-url"       --value "https://verifier.accountchek.com/login"
az keyvault secret set --vault-name $VAULT_NAME --name "accountchek-login-email"      --value "admin@yourcompany.com"
az keyvault secret set --vault-name $VAULT_NAME --name "accountchek-login-password"   --value "<password>"
az keyvault secret set --vault-name $VAULT_NAME --name "accountchek-newuser-password"  --value "<default-password>"
```

Repeat for each vendor. See [Complete Secret Reference](#complete-secret-reference) below for the full list.

### Add secrets via Azure Portal

1. Navigate to your Key Vault in the Azure Portal
2. Click **Secrets** in the left menu
3. Click **+ Generate/Import**
4. Enter the secret **Name** and **Value**
5. Click **Create**

## Step 4: Configure Nexus

The Key Vault URL is set in the application configuration file.

1. Copy the example config if you haven't already:

```bash
cp config/app_config.example.json config/app_config.json
```

2. Set the `vault_url` in `config/app_config.json`:

```json
{
  "azure_keyvault": {
    "vault_url": "https://hrm-nexus-credentials.vault.azure.net/",
    "secret_naming_convention": "{vendor}-{field}"
  }
}
```

> **Fallback**: If `vault_url` is not set in the config, the `KeyVaultService` will check for the `AZURE_KEYVAULT_URL` environment variable.

## Step 5: Verify Setup

1. Launch Nexus:
   ```bash
   python main.py
   ```
2. Sign in with your Microsoft account
3. Search for a test user and start a provisioning run
4. Check the logs for Key Vault initialization messages:
   ```
   ✓ KeyVaultService initialized for https://hrm-nexus-credentials.vault.azure.net/
   ✓ Retrieved secret 'accountchek-login-url' from Key Vault
   ```

Log files are located at `%APPDATA%\Nexus\logs\nexus_YYYYMMDD.log`.

## Complete Secret Reference

Below is the full inventory of Key Vault secrets required for each vendor.

### AccountChek

| Secret Name | Description |
|---|---|
| `accountchek-login-url` | Admin portal login URL |
| `accountchek-login-email` | Admin login email |
| `accountchek-login-password` | Admin login password |
| `accountchek-newuser-password` | Default password for new users |

### BankVOD

| Secret Name | Description |
|---|---|
| `bankvod-login-url` | Admin portal login URL |
| `bankvod-login-account-id` | Account identifier |
| `bankvod-login-email` | Admin login email |
| `bankvod-login-password` | Admin login password |
| `bankvod-newuser-password` | Default password for new users |

### Certified Credit

| Secret Name | Description |
|---|---|
| `certifiedcredit-login-url` | Admin portal login URL |
| `certifiedcredit-admin-username` | Admin login username |
| `certifiedcredit-admin-password` | Admin login password |
| `certifiedcredit-default-password` | Default password for new users |

### Clear Capital

| Secret Name | Description |
|---|---|
| `clearcapital-login-url` | Admin portal login URL |
| `clearcapital-admin-username` | Admin login username |
| `clearcapital-admin-password` | Admin login password |

### DataVerify

| Secret Name | Description |
|---|---|
| `dataverify-login-url` | Admin portal login URL |
| `dataverify-admin-username` | Admin login username |
| `dataverify-admin-password` | Admin login password |

### MMI

| Secret Name | Description |
|---|---|
| `mmi-login-url` | Admin portal login URL |
| `mmi-admin-username` | Admin login username |
| `mmi-admin-password` | Admin login password |

### Partners Credit

| Secret Name | Description |
|---|---|
| `partnerscredit-login-url` | Admin portal login URL |
| `partnerscredit-admin-username` | Admin login username |
| `partnerscredit-admin-password` | Admin login password |

### The Work Number (Equifax)

| Secret Name | Description |
|---|---|
| `theworknumber-login-url` | Admin portal login URL |
| `theworknumber-admin-username` | Admin login username |
| `theworknumber-admin-password` | Admin login password |

### Experience.com

| Secret Name | Description |
|---|---|
| `experience-login-url` | Admin portal login URL |
| `experience-admin-email` | Admin login email |
| `experience-admin-password` | Admin login password |

### Summary

| Vendor | Secrets | Notes |
|---|---|---|
| AccountChek | 4 | Uses `login-email`; has `newuser-password` |
| BankVOD | 5 | Has unique `login-account-id` field |
| Certified Credit | 4 | Uses `admin-username`; has `default-password` |
| Clear Capital | 3 | Standard |
| DataVerify | 3 | Standard |
| MMI | 3 | Standard |
| Partners Credit | 3 | Standard |
| The Work Number | 3 | Standard |
| Experience.com | 3 | Uses `admin-email`; currently disabled |
| **Total** | **31** | |

## Troubleshooting

### "Azure Key Vault URL not configured"

The `vault_url` is missing from both `config/app_config.json` and the `AZURE_KEYVAULT_URL` environment variable.

**Fix**: Set the URL in `config/app_config.json` under `azure_keyvault.vault_url`.

### "Invalid issuer" (AKV10032)

Your Azure account's tenant does not match the Key Vault's tenant.

**Fix**: Ensure the Key Vault is in the same Azure tenant as the Nexus App Registration. Check `microsoft.tenant_id` in `config/app_config.json`.

### "403 Forbidden" / "Access Denied"

The signed-in user does not have permission to read secrets.

**Fix**: Grant the user (or their group) the **Key Vault Secrets User** RBAC role. See [Step 2](#step-2-grant-user-access).

### "Secret not found"

The requested secret name does not exist in the vault.

**Fix**: Verify the secret exists:
```bash
az keyvault secret list --vault-name $VAULT_NAME --query "[].name" -o tsv
```

Compare against the [Complete Secret Reference](#complete-secret-reference) above.

### Authentication prompt not appearing

MSAL may have a cached token. Close Nexus, clear the MSAL token cache, and relaunch.

The MSAL cache is stored in `%APPDATA%\Nexus\` or the system token broker (WAM) on Windows.

## Security Best Practices

| Practice | Detail |
|---|---|
| **Use RBAC** | Prefer Azure RBAC over legacy Access Policies for granular, auditable control |
| **Least privilege** | Grant **Secrets User** (read-only) to operators; **Secrets Officer** only to admins who manage credentials |
| **Group-based access** | Assign roles to an Entra ID group rather than individual users |
| **Enable soft-delete** | Protects against accidental deletion (enabled by default on new vaults) |
| **Enable purge protection** | Prevents permanent deletion during the retention period |
| **Rotate credentials** | Use Key Vault secret versioning to rotate vendor passwords without downtime |
| **Audit logging** | Enable Azure Monitor diagnostic settings to track all secret access |
| **Network restrictions** | Consider Key Vault firewall rules if your network topology supports it |

## Additional Resources

- [Azure Key Vault documentation](https://learn.microsoft.com/en-us/azure/key-vault/)
- [Azure RBAC for Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/rbac-guide)
- [MSAL for Python](https://learn.microsoft.com/en-us/entra/msal/python/)
- [Nexus Authentication Guide](AUTHENTICATION_GUIDE.md)
