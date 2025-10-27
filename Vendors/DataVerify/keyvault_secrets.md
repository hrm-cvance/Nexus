# DataVerify Azure Key Vault Secrets

The following secrets need to be added to Azure Key Vault for DataVerify automation:

## Required Secrets

1. **dataverify-login-url**
   - Value: `https://www.dataverify.com/dvweb/user/login.aspx`
   - Description: DataVerify login page URL

2. **dataverify-admin-username**
   - Value: Your DataVerify admin username
   - Description: Admin account username for automation

3. **dataverify-admin-password**
   - Value: Your DataVerify admin password
   - Description: Admin account password for automation

## How to Add Secrets

### Using Azure CLI:
```bash
az keyvault secret set --vault-name hrm-nexus-credentials --name dataverify-login-url --value "https://www.dataverify.com/dvweb/user/login.aspx"
az keyvault secret set --vault-name hrm-nexus-credentials --name dataverify-admin-username --value "your-username"
az keyvault secret set --vault-name hrm-nexus-credentials --name dataverify-admin-password --value "your-password"
```

### Using Azure Portal:
1. Navigate to Azure Key Vault: `hrm-nexus-credentials`
2. Go to "Secrets" in the left menu
3. Click "+ Generate/Import"
4. Enter the secret name and value
5. Click "Create"

## Notes
- Username format: First initial + Last name (e.g., "THurley")
- System auto-generates passwords and emails them to users
- Only Processors and Underwriters receive accounts unless approved by NPS
