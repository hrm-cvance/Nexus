# Nexus Authentication Guide

## Overview

Nexus uses **unified authentication** - users sign in once via their Microsoft account and gain access to both Microsoft Graph API and Azure Key Vault automatically.

## How It Works

### For End Users (Zero Configuration Required)

1. **Launch Nexus application**
2. **Click "Sign In"** button
3. **Browser opens** → Sign in with Microsoft account
4. **Done!** Application now has access to:
   - Microsoft Graph API (to search users)
   - Azure Key Vault (to retrieve vendor credentials)

**No Azure CLI, PowerShell modules, or command-line tools required!**

### Technical Architecture

```
┌──────────────┐
│ Nexus GUI    │
└──────┬───────┘
       │
       ├─────────> Microsoft Graph API
       │           (user search, Entra ID data)
       │           Auth: MSAL PublicClientApplication
       │
       └─────────> Azure Key Vault
                   (vendor credentials)
                   Auth: MSAL → TokenCredential Adapter
```

## Authentication Flow

### 1. User Signs In

When the user clicks "Sign In":

```python
# AuthService uses MSAL PublicClientApplication
auth_service.sign_in_interactive(scopes=[
    "User.Read",
    "User.ReadBasic.All",
    "GroupMember.Read.All"
])
```

- Opens browser for interactive authentication
- User signs in with Microsoft account
- MSAL caches the token locally
- Token is valid for ~1 hour, auto-refreshes

### 2. Graph API Access

```python
# GraphAPIClient uses AuthService tokens
graph_client = GraphAPIClient(auth_service=auth_service, scopes=scopes)
users = graph_client.search_users("John Doe")
```

### 3. Key Vault Access

```python
# MSALCredentialAdapter converts MSAL tokens to Azure Identity format
msal_credential = MSALCredentialAdapter(
    auth_service=auth_service,
    scopes=["https://vault.azure.net/.default"]
)

# KeyVaultService uses the adapted credential
keyvault = KeyVaultService(vault_url=vault_url, credential=msal_credential)
password = keyvault.get_secret("accountchek-login-password")
```

**Key Innovation:** The `MSALCredentialAdapter` bridges MSAL (used by Graph API) and Azure Identity SDK (used by Key Vault), allowing **one sign-in for both services**.

## Required Azure Permissions

### App Registration Permissions

Your Azure AD App Registration must have:

**Microsoft Graph API:**
- `User.Read` - Sign in and read user profile
- `User.ReadBasic.All` - Read basic user info
- `GroupMember.Read.All` - Read group memberships

**Azure Resource Manager (for Key Vault):**
- `user_impersonation` - Access Azure Service Management as user

### Key Vault Access Policy

The **Nexus_Users** Entra ID group must have:
- Role: **Key Vault Secrets User**
- Permissions: Get, List secrets

## Token Caching & Refresh

### Automatic Token Management

- **Tokens cached locally** by MSAL (encrypted)
- **Auto-refresh** before expiration
- **Silent authentication** on subsequent app launches
- **No re-sign-in required** unless token expires (typically 90 days)

### Token Lifecycle

```
1. User signs in → Browser opens
2. Token acquired (expires in ~1 hour)
3. Token cached to disk
4. App restarted → Token loaded from cache
5. Token expires → Auto-refreshed silently
6. Refresh token expires (90 days) → User must sign in again
```

## Deployment Scenarios

### Scenario 1: Desktop Application (Current)

**Authentication Method:** InteractiveBrowserCredential via MSAL

**User Experience:**
1. Launch Nexus.exe
2. Click "Sign In"
3. Browser opens for Microsoft login
4. Token cached - no sign-in needed for 90 days

**Requirements:**
- ✅ User has Microsoft account in your tenant
- ✅ User is member of Nexus_Users group
- ✅ No Azure CLI required
- ✅ No PowerShell modules required

### Scenario 2: Server/Shared Environment

**Authentication Method:** Service Principal (App Registration with secret)

**Setup:**
```python
from azure.identity import ClientSecretCredential

credential = ClientSecretCredential(
    tenant_id="your-tenant-id",
    client_id="your-app-id",
    client_secret="your-secret"
)

keyvault = KeyVaultService(vault_url=vault_url, credential=credential)
```

**Requirements:**
- Create App Registration
- Generate client secret
- Store secret securely (environment variable or Key Vault)

### Scenario 3: Azure VM/App Service

**Authentication Method:** Managed Identity

**Setup:**
```python
from azure.identity import ManagedIdentityCredential

credential = ManagedIdentityCredential()
keyvault = KeyVaultService(vault_url=vault_url, credential=credential)
```

**Requirements:**
- Enable System-Assigned Managed Identity on VM/App Service
- Grant managed identity "Key Vault Secrets User" role

## Troubleshooting

### Error: "DefaultAzureCredential failed to retrieve a token"

**Cause:** Application trying to use DefaultAzureCredential instead of MSAL adapter.

**Solution:** Ensure `main_window.py` creates `MSALCredentialAdapter` and passes it to `KeyVaultService`.

### Error: "User has not consented to permissions"

**Cause:** User hasn't granted app permissions yet.

**Solution:**
1. Admin grants consent in Azure Portal
2. Or user consents during first sign-in

### Error: "Key Vault access denied"

**Cause:** User not in Nexus_Users group or group doesn't have Key Vault permissions.

**Solution:**
1. Add user to Nexus_Users group in Entra ID
2. Wait 5-15 minutes for group membership to propagate
3. Grant group "Key Vault Secrets User" role on Key Vault

### Token Expired

**Cause:** Refresh token expired (after 90 days of inactivity).

**Solution:** User clicks "Sign In" again.

## Security Considerations

### Token Storage

- **MSAL tokens** encrypted and stored in user profile
- **Location:** `%LOCALAPPDATA%\\.IdentityService` (Windows)
- **Access:** Only the user account can access cached tokens

### Network Traffic

- All communication over **HTTPS**
- Microsoft OAuth endpoints: `login.microsoftonline.com`
- Graph API: `graph.microsoft.com`
- Key Vault: `*.vault.azure.net`

### Best Practices

1. **Never share tokens** between users
2. **Clear cache on shared computers** after use
3. **Use Managed Identity** in production on Azure VMs
4. **Rotate Key Vault secrets** regularly
5. **Monitor access** via Azure Monitor logs

## For Developers

### Adding New Azure Services

To add authentication for additional Azure services (e.g., Azure Storage, Cosmos DB):

```python
# In MSALCredentialAdapter
scopes = ["https://<service>.azure.net/.default"]

# Example: Azure Storage
storage_credential = MSALCredentialAdapter(
    auth_service=auth_service,
    scopes=["https://storage.azure.com/.default"]
)
```

### Testing Authentication Locally

```python
# Test script
from services.auth_service import AuthService
from services.msal_credential_adapter import MSALCredentialAdapter

# Initialize
auth = AuthService(tenant_id="...", client_id="...")

# Sign in
auth.sign_in_interactive(["User.Read"])

# Create adapter
credential = MSALCredentialAdapter(auth)

# Get token
token = credential.get_token("https://vault.azure.net/.default")
print(f"Token acquired: {token.token[:20]}...")
```

## Summary

✅ **One sign-in** for Graph API and Key Vault
✅ **No CLI tools** required for end users
✅ **Automatic token refresh** for 90 days
✅ **Secure token storage** via MSAL
✅ **Flexible deployment** (desktop, server, Azure VM)
✅ **Zero configuration** for end users

Users simply sign in with their Microsoft account and everything works!
