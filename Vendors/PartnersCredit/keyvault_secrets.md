# Partners Credit Azure Key Vault Secrets

## Required Secrets

1. **partnerscredit-login-url**
   - Value: `https://www.partnerscredit.com/login.aspx`
   - Description: Partners Credit login page URL

2. **partnerscredit-admin-username**
   - Value: Your Partners Credit admin username
   - Description: Admin account username for logging in

3. **partnerscredit-admin-password**
   - Value: Your Partners Credit admin password
   - Description: Admin account password for logging in
   - Note: Do NOT use "#" or "@" in passwords (causes issues)

## Notes

- Partners Credit does NOT use a default password system - they generate passwords and send them via encrypted PDF email
- The automation will submit user requests, but Partners Credit generates the actual credentials
- Users receive their credentials via email from Partners Credit
