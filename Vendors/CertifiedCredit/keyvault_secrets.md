# Certified Credit Azure Key Vault Secrets

## Required Secrets

1. **certifiedcredit-login-url**
   - Value: `https://certifiedcredit.meridianlink.com/custom/login.aspx`
   - Description: Login URL for Certified Credit portal

2. **certifiedcredit-admin-username**
   - Value: Your Certified Credit admin username
   - Description: Admin account username with User Setup permissions

3. **certifiedcredit-admin-password**
   - Value: Your Certified Credit admin password
   - Description: Admin account password

4. **certifiedcredit-default-password**
   - Value: HRM default password for new users
   - Description: Default password set for all new user accounts

## Notes

- The admin account must have access to Tools > User Setup
- New users will be set with manual password (HRM default)
- Users must change password on first login

## Multi-Factor Authentication (MFA)

Certified Credit requires MFA after login. The automation will:

1. Enter username and password
2. Click login button
3. **Pause and wait for MFA completion**
   - A text message will be sent to the admin's cell phone
   - User must manually enter the verification code
   - The automation will monitor the page and automatically continue when MFA is complete
4. Maximum wait time: 5 minutes (300 seconds)
5. The automation detects MFA completion by watching for the home page elements (Tools, User Setup)

**Important**: Keep the browser window visible during MFA so you can enter the code when prompted.
