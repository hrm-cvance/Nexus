# Partners Credit Setup Instructions

## Overview
Partners Credit automation has been fully integrated into Nexus. Follow these steps to complete the setup.

## 1. Azure Key Vault Secrets

You need to manually create these 3 secrets in Azure Key Vault:

### Secret Names and Values

1. **partnerscredit-login-url**
   - Value: `https://www.partnerscredit.com/login.aspx`

2. **partnerscredit-admin-username**
   - Value: Your Partners Credit admin username

3. **partnerscredit-admin-password**
   - Value: Your Partners Credit admin password
   - Note: Avoid using "#" or "@" characters

## 2. Entra ID Group

Create or verify the Entra ID group exists:
- **Group Name**: `PartnersCredit_Users`
- Add users to this group who need Partners Credit accounts

## 3. Testing the Automation

Once secrets are created, you can test the automation:

### Via Test Script
```bash
python test_partnerscredit.py
```

### Via Nexus GUI
1. Launch Nexus: `python main.py`
2. Go to the Automation tab
3. Select a user who is in the `PartnersCredit_Users` group
4. Click "Run Automation"
5. Partners Credit should appear in the vendor list and run automatically

## 4. Manual Steps Required

The automation handles everything except:
- **MFA**: You will manually select public/private computer and enter the text code
- **Email Follow-up**: Partners Credit sends credentials via encrypted PDF email
  - Check your email after automation completes
  - Use your Partners Credit admin password to decrypt the PDF
  - Forward the credentials to the new user

## 5. How It Works

1. **Login**: Logs into Partners Credit with admin credentials
2. **MFA**: Waits for you to manually complete MFA
3. **Navigation**: Goes to Admin → User Admin → New User Requests
4. **User Count**: Inputs "1" user and clicks Next
5. **Form Filling**: Fills user information from Entra ID:
   - First Name, Last Name
   - Phone (cell phone, digits only)
   - Email
   - Job Title
   - Report Access Level (AI-matched based on job title)
   - Department (based on cost center)
   - Comments (default text about eliminating credit pulling)
6. **Submit**: Submits the request
7. **Completion**: Partners Credit generates credentials and emails them

## 6. AI Title Matching

The automation uses AI to match job titles to Report Access Levels:

- **User**: Loan Officers, MLOs, Originators
- **Company**: Loan Processors
- **Department** (default): Most other roles
- **No Access**: Closers, specific restricted roles

The mappings are defined in `title_mapping.json` and use the AccountChek AI matching pattern.

## 7. Department Logic

- **Default**: "Plano Division"
- **East Region**: Cost centers 8000+
- **Special Comments**: Cost centers 7003, 7074, 7075 get additional instructions about report formatting

## 8. Troubleshooting

### Screenshots
The automation saves screenshots at each step:
- `partnerscredit_login_page.png`
- `partnerscredit_after_login.png`
- `partnerscredit_mfa_page.png`
- `partnerscredit_new_user_requests.png`
- `partnerscredit_user_form.png`
- `partnerscredit_form_filled.png`
- `partnerscredit_request_submitted.png`

### Logs
Check the Nexus logs for detailed information about each step.

### Common Issues
- **Login fails**: Verify Key Vault secrets are correct
- **MFA timeout**: Complete MFA within 5 minutes
- **Form fields not filled**: Check screenshots to see what happened

## 9. Configuration Files

All configuration is in `Vendors/PartnersCredit/`:
- `config.json`: Workflow settings, department mapping, default values
- `title_mapping.json`: Job title to Report Access Level mappings
- `keyvault_secrets.md`: Key Vault secret documentation

## 10. Status

✅ Automation code complete
✅ Integration with Nexus GUI complete
✅ Title mapping with AI matching complete
✅ Form selectors verified and working
⏳ Azure Key Vault secrets need to be created (manual step)
⏳ Testing with real user data pending

## Next Steps

1. Create the 3 Azure Key Vault secrets
2. Test with a real user account
3. Verify the encrypted PDF email arrives
4. Document any edge cases or issues
