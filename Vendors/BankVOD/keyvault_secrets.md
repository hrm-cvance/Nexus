# BankVOD - Azure Key Vault Secrets

This document lists the required secrets for BankVOD automation.

## Required Secrets

Add these secrets to your Azure Key Vault:

### 1. Login URL
- **Secret Name**: `bankvod-login-url`
- **Value**: `https://www.bankvod.com/MyAccount/#b`
- **Description**: BankVOD login page URL

### 2. Login Account ID
- **Secret Name**: `bankvod-login-account-id`
- **Value**: `<your-company-account-id>`
- **Description**: Company/Account ID for logging into BankVOD (if required by login page)

### 3. Login Email
- **Secret Name**: `bankvod-login-email`
- **Value**: `<your-admin-email>`
- **Description**: Admin account email for logging into BankVOD

### 4. Login Password
- **Secret Name**: `bankvod-login-password`
- **Value**: `<your-admin-password>`
- **Description**: Admin account password for logging into BankVOD

### 5. New User Password
- **Secret Name**: `bankvod-newuser-password`
- **Value**: `<default-password-for-new-users>`
- **Description**: Default password assigned to newly created users (HRM default)

## Adding Secrets to Key Vault

### Via Azure Portal
1. Navigate to your Key Vault in Azure Portal
2. Go to "Secrets" in the left menu
3. Click "+ Generate/Import"
4. Enter the secret name and value
5. Click "Create"

### Via Azure CLI
```bash
az keyvault secret set --vault-name <your-vault-name> --name bankvod-login-url --value "https://www.bankvod.com/MyAccount/#b"
az keyvault secret set --vault-name <your-vault-name> --name bankvod-login-account-id --value "<company-account-id>"
az keyvault secret set --vault-name <your-vault-name> --name bankvod-login-email --value "<admin-email>"
az keyvault secret set --vault-name <your-vault-name> --name bankvod-login-password --value "<admin-password>"
az keyvault secret set --vault-name <your-vault-name> --name bankvod-newuser-password --value "<default-password>"
```

### Via PowerShell
```powershell
$vaultName = "<your-vault-name>"
Set-AzKeyVaultSecret -VaultName $vaultName -Name "bankvod-login-url" -SecretValue (ConvertTo-SecureString "https://www.bankvod.com/MyAccount/#b" -AsPlainText -Force)
Set-AzKeyVaultSecret -VaultName $vaultName -Name "bankvod-login-account-id" -SecretValue (ConvertTo-SecureString "<company-account-id>" -AsPlainText -Force)
Set-AzKeyVaultSecret -VaultName $vaultName -Name "bankvod-login-email" -SecretValue (ConvertTo-SecureString "<admin-email>" -AsPlainText -Force)
Set-AzKeyVaultSecret -VaultName $vaultName -Name "bankvod-login-password" -SecretValue (ConvertTo-SecureString "<admin-password>" -AsPlainText -Force)
Set-AzKeyVaultSecret -VaultName $vaultName -Name "bankvod-newuser-password" -SecretValue (ConvertTo-SecureString "<default-password>" -AsPlainText -Force)
```

## Permissions

Users running Nexus automation need the **Key Vault Secrets User** role to read these secrets.

## Security Notes

- ✅ Never commit actual passwords to Git
- ✅ Rotate credentials regularly
- ✅ Use strong passwords for admin accounts
- ✅ Limit Key Vault access to authorized personnel only
