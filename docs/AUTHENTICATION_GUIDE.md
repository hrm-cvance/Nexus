# Nexus Authentication Guide

## Overview

Nexus uses **unified delegated authentication** — users sign in once with their Microsoft account and gain access to both Microsoft Graph API and Azure Key Vault automatically. No service principals, client secrets, or CLI tools are involved.

## For End Users

1. Launch **Nexus**
2. If you've signed in before, you're **already connected** — no action needed
3. If this is your first time (or you previously signed out), click **Sign In**
4. A browser window opens — sign in with your Highland Mortgage Microsoft account
5. Done. The application now has access to:
   - **Microsoft Graph API** — to search employees in Entra ID
   - **Azure Key Vault** — to retrieve vendor admin credentials

Your sign-in is remembered between sessions. You only need to sign in again if you explicitly sign out or after approximately 90 days of inactivity.

## Technical Architecture

```
User clicks "Sign In"
        │
        ▼
┌──────────────────────────────────┐
│  MSAL PublicClientApplication    │
│  (interactive browser auth)      │
└──────────┬───────────────────────┘
           │
           ├──► Microsoft Graph API
           │    Scopes: User.Read.All, GroupMember.Read.All, Group.Read.All
           │    Used for: employee search, group membership lookup
           │
           └──► Azure Key Vault
                Scope: https://vault.azure.net/.default
                Bridge: MSALCredentialAdapter → Azure SDK TokenCredential
                Used for: retrieving vendor admin credentials
```

The key innovation is the `MSALCredentialAdapter` class, which bridges MSAL's token format (used by Graph API) to the Azure Identity SDK's `TokenCredential` interface (used by Key Vault). This allows **one sign-in for both services** without requiring separate authentication flows.

## Authentication Flow

### 1. User Signs In

When the user clicks "Sign In" in the User Search tab:

```python
# AuthService wraps MSAL PublicClientApplication
auth_service.sign_in_interactive(scopes=[
    "User.Read.All",
    "GroupMember.Read.All",
    "Group.Read.All"
])
```

- Opens the system browser for Microsoft authentication
- User signs in with their Microsoft account
- MSAL caches the token to disk at `%LOCALAPPDATA%\Nexus\token_cache.bin`
- Access token is valid for ~1 hour and auto-refreshes
- On next app launch, the cached token is loaded automatically (no browser sign-in needed)

### 2. Graph API Access

The `GraphAPIClient` uses the `AuthService` to acquire tokens for Graph API calls:

```python
graph_client = GraphAPIClient(auth_service=auth_service, scopes=scopes)
users = graph_client.search_users("Jane Smith")
groups = graph_client.get_user_groups(user_id)
```

### 3. Key Vault Access

The `MSALCredentialAdapter` converts MSAL tokens into the format the Azure Key Vault SDK expects:

```python
# Created in main_window.py during initialization
msal_credential = MSALCredentialAdapter(
    auth_service=auth_service,
    scopes=["https://vault.azure.net/.default"]
)

keyvault = KeyVaultService(vault_url=vault_url, credential=msal_credential)
password = keyvault.get_vendor_credential("accountchek", "login-password")
```

## Required Azure Configuration

### App Registration

The Azure AD App Registration must be configured as a **public client** (no client secret) with the following **delegated** permissions:

| API | Permission | Type | Purpose |
|---|---|---|---|
| Microsoft Graph | `User.Read.All` | Delegated | Search and read employee profiles |
| Microsoft Graph | `GroupMember.Read.All` | Delegated | Read group memberships for vendor detection |
| Microsoft Graph | `Group.Read.All` | Delegated | List and query security groups |

The App Registration must also have:
- **Redirect URI**: `http://localhost:8400` (for the interactive browser flow)
- **Allow public client flows**: Enabled

### Key Vault RBAC

Key Vault access is granted via Azure RBAC, not through the App Registration's API permissions.

Each Nexus user (or their security group) must hold the **Key Vault Secrets User** role on the vault. See [AZURE_KEYVAULT_SETUP.md](AZURE_KEYVAULT_SETUP.md) for details.

## Token Lifecycle

```
1. User clicks Sign In → browser opens
2. Token acquired (access token expires in ~1 hour)
3. Token cached to disk at %LOCALAPPDATA%\Nexus\token_cache.bin
4. App restarted → cache loaded from disk → user auto-authenticated (no browser)
5. Access token expires → MSAL refreshes silently using refresh token
6. Refresh token expires (~90 days of inactivity) → user must sign in again
7. User clicks Sign Out → cache file deleted from disk → next launch requires sign-in
```

### What This Means in Practice

- Users sign in once and don't need to again for approximately 90 days
- If the app is restarted, the cached token is loaded automatically — no sign-in prompt
- Signing out fully clears the cache from disk, requiring a fresh sign-in next time
- No Azure CLI, PowerShell modules, or manual token management required

## Troubleshooting

### "User has not consented to permissions"

The user hasn't approved the app's requested permissions.

**Fix:** An Azure AD admin can grant tenant-wide consent in the Azure Portal under **App Registrations > [Nexus] > API permissions > Grant admin consent**. Alternatively, the user consents during their first sign-in.

### "Key Vault access denied"

The signed-in user doesn't have permission to read Key Vault secrets.

**Fix:**
1. Add the user to the `Nexus_Users` security group in Entra ID
2. Ensure the group has the **Key Vault Secrets User** role on the vault
3. Wait 5–15 minutes for group membership to propagate

### "DefaultAzureCredential failed to retrieve a token"

The app is falling back to `DefaultAzureCredential` instead of using the MSAL adapter.

**Fix:** This indicates a code issue. Ensure `main_window.py` creates an `MSALCredentialAdapter` and passes it to `KeyVaultService` during initialization.

### Token Expired / "Sign in required"

The refresh token has expired after extended inactivity (approximately 90 days).

**Fix:** Click **Sign In** again.

## Security

| Aspect | Detail |
|---|---|
| **Client type** | Public client (no client secret stored anywhere) |
| **Token storage** | MSAL `SerializableTokenCache` persisted to `%LOCALAPPDATA%\Nexus\token_cache.bin`; deleted on sign-out |
| **Transport** | All communication over HTTPS |
| **Endpoints** | `login.microsoftonline.com`, `graph.microsoft.com`, `*.vault.azure.net` |
| **Permissions** | Delegated only — the app acts as the signed-in user, not as itself |
| **Scope** | Users can only access Key Vault secrets they've been granted access to via RBAC |

## For Developers

### Adding Authentication for New Azure Services

The `MSALCredentialAdapter` can be reused for any Azure SDK service that accepts a `TokenCredential`:

```python
# Example: Azure Storage
storage_credential = MSALCredentialAdapter(
    auth_service=auth_service,
    scopes=["https://storage.azure.com/.default"]
)
```

### Testing Authentication Locally

```python
from services.auth_service import AuthService
from services.msal_credential_adapter import MSALCredentialAdapter

auth = AuthService(tenant_id="...", client_id="...", redirect_uri="http://localhost:8400")
auth.sign_in_interactive(["User.Read.All", "GroupMember.Read.All", "Group.Read.All"])

credential = MSALCredentialAdapter(auth, scopes=["https://vault.azure.net/.default"])
token = credential.get_token("https://vault.azure.net/.default")
print(f"Token acquired: {token.token[:20]}...")
```
