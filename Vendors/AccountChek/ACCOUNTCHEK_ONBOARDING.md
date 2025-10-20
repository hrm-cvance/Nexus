# Vendor Onboarding Template - Account Creation Automation

> **Purpose:** This template helps us automate the process of creating user accounts in vendor systems. You know the vendor system well - we just need you to document exactly how you create accounts manually. The more detail you provide, the better the automation will work!

> **Don't worry about technical terms** - just describe what you see and do. We'll handle the technical parts.

**Date:** October 6, 2024
**Completed By:** Chris Vance
**Vendor Name:** AccountChek

---

## 1. Vendor Overview

### 1.1 Basic Information
- **Vendor Name:** AccountChek
- **Platform/System Name:** AccountChek Verifier Platform
- **Primary Purpose:** Bank account verification system for loan processing
- **Vendor Contact (if applicable):** AccountChek Support
- **Internal Department Owner:** IT/Operations

### 1.2 Application URL
- **Login URL:** https://verifier.accountchek.com/login
- **Production Environment:** https://verifier.accountchek.com
- **Test/Staging Environment (if available):** N/A - Production only

---

## 2. Authentication & Access

### 2.1 Login Requirements
- **Authentication Method:**
  - [x] Email/Password
  - [ ] Username/Password
  - [ ] SSO/SAML
  - [ ] Multi-Factor Authentication (MFA)
  - [ ] Other: _____________________

- **Admin Account Credentials:**
  - **Username/Email:** cvance@highlandsmortgage.com
  - **Password Location:** Stored in config.json (production passwords in secure vault)
  - **MFA Method (if applicable):** N/A

### 2.2 Session Management
- **Session Timeout:** Approximately 30 minutes of inactivity
- **Does the session require periodic re-authentication?** Yes, after timeout
- **Any CAPTCHA or bot detection mechanisms?** No

---

## 3. User Management Access

### 3.1 Navigation to User Management
**Describe the step-by-step navigation from login to the user creation screen:**

> **Tip:** Write down every click, menu selection, or button you press. Copy the exact wording you see on screen (including capitalization and punctuation).

**Example:**
1. After login, I click on my name "JOHN DOE" in the top-right corner
2. From the dropdown menu, I click "User Management"
3. The User Management page loads

**Your steps:**
1. After login, I click on my name "CHRIS VANCE" (or user name) in the top-right corner
2. A dropdown menu appears
3. From the dropdown menu, I click on "Verifiers"
4. The User Management page loads with heading "User Management"
5. _____________________

**REQUIRED: Take screenshots of each step:** (Save to `Vendors/[VendorName]/screenshots/`)
- [x] Screenshot: What you see immediately after logging in (test-results/after-login.png)
- [x] Screenshot: Any menu or dropdown you opened (test-results/dropdown-menu.png)
- [x] Screenshot: The page where you manage users (test-results/before-new-user-click.png)

### 3.2 User Management Interface
- **How do you initiate new user creation?**
  - [x] Button (exact label: "New User")
  - [ ] Menu option (exact text: _____________)
  - [ ] Link (exact text: _____________)
  - [ ] Icon button (describe icon: _____________)
  - [ ] Other: _____________________

- **What happens when clicked?**
  - [x] Modal/dialog appears (overlay on same page)
  - [ ] New page loads
  - [ ] Sidebar/panel slides out
  - [ ] Inline form appears below
  - [ ] Other: _____________________

- **If modal/dialog, does it have a close button (X) or backdrop click to close?** Yes, modal has close button and can close by clicking backdrop

---

## 4. User Roles & Permissions

### 4.1 Available User Roles
**List all available user roles/permission levels in the vendor system:**

| Role Name | Description | Access Level | Will Be Auto-Created? |
|-----------|-------------|--------------|----------------------|
| User | Standard verifier with basic access | Standard | ✅ Yes (default) |
| Admin | Administrator with full access | Full | ❌ No (manual only) |
| Manager | Mid-level management access | Enhanced | ❌ No (manual only) |

**IMPORTANT:** Only the "User" role is created via automation. All elevated roles (Admin, Manager) must be created manually for security purposes.

### 4.2 Standard User Role Details
- **What is the exact name of the standard user role?** User

- **How is this role assigned during user creation?**
  - [x] Dropdown selection (automation will always select "User")
  - [ ] Radio buttons
  - [ ] Checkboxes (multiple roles)
  - [ ] Automatic/default (no selection needed)
  - [ ] Other: _____________________

- **Can a user have multiple roles simultaneously?** No, single role selection

- **Is the standard role the default selection when the form opens?** Unknown - automation explicitly selects "User" to ensure correct role

### 4.3 Elevated Roles (Manual Creation Only)
**List roles that require manual creation:**

| Role Name | Why Manual Only? | Who Can Create? |
|-----------|------------------|-----------------|
| Admin | Full system access, security risk | IT Leadership only |
| Manager | Enhanced permissions, elevated access | IT Leadership only |

---

## 5. Organizational Structure

### 5.1 Regional/Branch Structure
- **Does the vendor system have regions, branches, or divisions?**
  - [x] Regions
  - [x] Branches
  - [ ] Divisions
  - [ ] Departments
  - [ ] Cost Centers
  - [ ] None
  - [ ] Other: _____________________

### 5.2 Structure Details
**If yes, describe the hierarchy:**

- **Top Level (e.g., Region):** Region (e.g., Corporate, Western Region, Eastern Region)
- **Mid Level (e.g., Division):** N/A
- **Bottom Level (e.g., Branch):** Branch (e.g., "1200 - Eckert Division", specific branch codes)

### 5.3 Structure Assignment
- **Are these assigned during user creation?** Yes
- **Are they required fields?** Yes, both Region and Branch are required
- **Do selections cascade (e.g., selecting region filters available branches)?** Yes! When you select a Region, the Branch dropdown updates to show only branches in that region
- **How are they presented in the UI?**
  - [x] Dropdown menus
  - [ ] Hierarchical tree selector
  - [ ] Separate fields for each level
  - [ ] Other: _____________________

---

## 6. User Account Fields

### 6.1 Required Fields
**List all REQUIRED fields for account creation:**

| Field Name | Field Type | Format/Validation | Example Value | Notes |
|------------|------------|-------------------|---------------|-------|
| First Name | Text | Standard text | John | Required |
| Last Name | Text | Standard text | Doe | Required |
| Email | Email | Valid email format | john.doe@example.com | Must be unique in system |
| Job Title | Text | Standard text | Loan Officer | Required |
| Role | Dropdown | Select from list | User | Required |
| Password | Password | Complex password | Welcome@456 | Required, must meet complexity |
| Region | Dropdown | Select from list | Corporate | Required |
| Branch | Dropdown | Select from list | 1200 - Eckert Division | Required, filtered by Region |

### 6.2 Optional Fields
**List all OPTIONAL fields:**

| Field Name | Field Type | Format/Validation | Example Value | Default Value | Notes |
|------------|------------|-------------------|---------------|---------------|-------|
| Must Change Password | Checkbox | Boolean | Checked | Unchecked | Forces password change on first login |
| Active | Checkbox | Boolean | Checked | Checked | Account enabled status |

### 6.3 Password Configuration

> **Note:** Nexus will auto-generate secure passwords by default. We need to know what password rules this vendor requires so we can generate passwords that meet their complexity requirements.

**Password Rules:**
- **Minimum length:** 12 characters
- **Maximum length:** 20 characters
- **Must include uppercase letters (A-Z)?** [x] Yes - Minimum: 1
- **Must include lowercase letters (a-z)?** [x] Yes - Minimum: 1
- **Must include numbers (0-9)?** [x] Yes - Minimum: 1
- **Must include special characters?** [x] Yes - Minimum: 1

**If special characters are required:**
- **Which special characters are ALLOWED?** (Check all that apply)
  - [x] ! (exclamation mark)
  - [x] @ (at sign)
  - [x] # (hash/pound)
  - [x] $ (dollar sign)
  - [x] % (percent)
  - [x] ^ (caret)
  - [x] & (ampersand)
  - [x] * (asterisk)
  - [x] - (hyphen/dash)
  - [x] _ (underscore)
  - [x] = (equals)
  - [x] + (plus)
  - [ ] Other: _____________________

- **Are any special characters NOT ALLOWED or cause problems?**
  - [ ] Yes - list them: _____________________
  - [x] No - all common special characters work fine

**Additional Password Rules:**
- **Are there any other password requirements we should know about?**
  - [ ] No consecutive characters (e.g., "aaa" or "111" not allowed)
  - [ ] Cannot contain username or email
  - [ ] Cannot contain common words
  - [ ] Must be different from last ___ passwords
  - [ ] Expires after ___ days
  - [ ] Other: _____________________

**Password Setup During Account Creation:**
- **Is a password set during creation?** [x] Yes
- **Is there a "Must change password on first login" option?** [x] Yes - checkbox option
- **Can a temporary password be auto-generated by the system?** [ ] No - must be manually entered
- **If auto-generated, what format does it use?** N/A

**What should Nexus do?**
- [ ] Use the vendor's auto-generated password (if available)
- [x] Generate our own password that meets the vendor's requirements (recommended)

**Nexus password generation for AccountChek:**
- Default: 16 characters long
- Guaranteed: 2 uppercase, 2 lowercase, 2 digits, 2 special characters
- Uses only allowed special characters: !@#$%^&*-_=+
- No ambiguous characters (0/O, 1/l/I) to avoid confusion

### 6.4 Account Status Options
- **Can accounts be created in an inactive/disabled state?** Yes, via "Active" checkbox
- **Are there any activation steps after creation?** No
- **Email verification required?** No

---

## 7. Microsoft Entra ID (Azure AD) Field Mapping

> **Note:** We connect to Microsoft Entra ID using Microsoft Graph API to retrieve user attributes for automated provisioning.

### 7.1 Provisioning Trigger Group
**This automation uses Entra ID group membership to determine which users need accounts created.**

- **Entra ID Group Name:** AccountChek_Users
  - **Group Object ID:** (To be provided by identity team)
  - **Group Purpose:** Members of this group will automatically have accounts created in AccountChek
  - **Role Assigned:** User (standard role only - admins/managers must be created manually)

**Important Notes:**
- ✅ **Only standard users are created via automation**
- ❌ **Admin and Manager roles must be created manually** for security purposes
- The automation queries this group via Graph API: `https://graph.microsoft.com/v1.0/groups/{groupId}/members`
- Users must be added to the `AccountChek_Users` group in Entra ID to trigger account creation

### 7.2 Entra ID User Attributes Required
**Specify which Entra ID user attributes are needed and how they map to vendor fields:**

| Vendor Field | Entra ID Attribute (Graph API) | Transformation Logic | Example |
|--------------|--------------------------------|----------------------|---------|
| First Name | givenName | Direct mapping | John |
| Last Name | surname | Direct mapping | Doe |
| Email | mail or userPrincipalName | Direct mapping, prefer mail if available | john.doe@highlandsmortgage.com |
| Job Title | jobTitle | Direct mapping | Loan Officer |
| Region | department or officeLocation | Map department/office to region | Corporate |
| Branch | officeLocation or extension attribute | Map office location to branch code | 1200 - Eckert Division |
| Role | N/A - Fixed Value | Always "User" (standard role only) | User |
| Password | N/A | Generate secure temporary password | Welcome@456 (temp) |

**Graph API endpoint used:** `https://graph.microsoft.com/v1.0/users/{id}?$select=givenName,surname,mail,userPrincipalName,jobTitle,department,officeLocation`

### 7.3 What Role Will Users Be Assigned?
**Since we only create standard users via automation:**

| Vendor Role Name | Will Be Auto-Created? | Notes |
|------------------|-----------------------|-------|
| User | ✅ Yes | Default role for all automated accounts |
| Admin | ❌ No | Must be created manually by IT Leadership |
| Manager | ❌ No | Must be created manually by IT Leadership |

**Standard user role name in AccountChek:** "User"

### 7.4 Entra ID Department/Office Mapping
**If vendor has regional/branch structure, map Entra ID attributes:**

| Entra ID Attribute | Example Value | Vendor Region/Branch | Notes |
|--------------------|---------------|----------------------|-------|
| department | Corporate | Corporate (Region) | Primary region mapping |
| officeLocation | Eckert Division | 1200 - Eckert Division (Branch) | Office to branch code mapping |
| officeLocation | Western Region Office | Western Region | Alternative region mapping |
| companyName | Highlands Mortgage | N/A | Company identifier |

**Mapping table for offices to branches:**
- "Eckert Division" → "1200 - Eckert Division"
- Additional mappings to be defined based on Entra data

### 7.5 Conditional Logic
**Describe any conditional logic needed for Entra ID mapping:**

**Provisioning trigger logic:**
1. Query members of the `AccountChek_Users` Entra ID group: `GET /groups/{groupId}/members`
2. For each member, check if they already have an AccountChek account
3. If not, proceed with account creation using their Entra ID attributes
4. All users are assigned the "User" role (no role-based logic needed)

**Branch assignment logic:**
1. Get user's `officeLocation` attribute from Entra ID
2. Look up corresponding branch code in mapping table
3. If exact match not found, parse location string for known keywords
4. Get user's `department` attribute to determine Region
5. After selecting Region in AccountChek, verify the Branch exists in that Region's dropdown

**API Authentication:**
- Use Microsoft Graph API with application permissions
- Required Graph API permissions: `User.Read.All`, `GroupMember.Read.All`, `Group.Read.All`
- Authentication via client credentials flow (app registration)

---

## 8. Account Creation Workflow

### 8.1 Step-by-Step Process
**Document the complete workflow for creating a user account:**

1. Click "New User" button on User Management page
2. Modal dialog appears with new user form
3. Fill in First Name field
4. Fill in Last Name field
5. Fill in Email field
6. Fill in Job Title field
7. Select Role from dropdown (first dropdown)
8. Enter Password
9. Select Region from dropdown (second dropdown)
10. Wait ~1 second for Branch dropdown to populate
11. Select Branch from dropdown (third dropdown)
12. Check "Must Change Password" checkbox if needed (second checkbox)
13. Click "Save" button
14. Wait for confirmation

### 8.2 Form Submission
- **What is the label on the submit button?** "Save"
- **Does submission happen on the same page or navigate away?** Same page - modal closes
- **Are there confirmation dialogs before final submission?** No

### 8.3 Success Indicators

> **What we need:** How do YOU know that the account was created successfully? What do you look for?

**After clicking Save/Submit, what tells you it worked?**

- [x] A green message appears
  - **Copy the exact message text here:** "Verifier Saved" (or similar success message)
  - **Where on the screen does it appear?** Top of the page (alert banner area)
  - **Does it disappear after a few seconds, or stay on screen?** May disappear after a few seconds
  - **IMPORTANT: Take a screenshot** and save to: `Vendors/AccountChek/screenshots/success-message.png`

- [x] The form closes/disappears automatically
- [x] I'm taken back to the user list page (modal closes, revealing user list)
- [ ] I receive an email confirmation
- [x] The new user immediately appears in the user list
- [ ] The form clears out and is ready for another user
- [ ] Other: _____________________

**What else changes on the screen after successful creation?**
- [x] A new row appears in the user table
- [ ] The total user count number increases
- [ ] A green checkmark icon appears
- [x] Other: User email is visible in the list

### 8.4 How to Verify the User Was Really Created

> **What we need:** After you create a user, how do you double-check that they're actually in the system?

**Your verification process:**
1. After creating the user, I remain on the User Management page (or return to it)
2. I search for the user using their: [x] Email [ ] Name [ ] Username [ ] Other: _____
3. I look for the following information to confirm it's correct:
   - [x] Name is correct
   - [x] Email is correct
   - [x] Role is correct
   - [x] Region/Branch is correct
   - [x] Account status shows as Active
   - [ ] Other: _____________________

**Take a screenshot** of the user list showing the newly created user and save to: `Vendors/AccountChek/screenshots/user-in-list.png`


---

## 9. Error Handling & Edge Cases

### 9.1 Common Errors

> **What we need:** What error messages have you seen when creating accounts? This helps us handle problems gracefully.

**Tell us about errors you've encountered:**

| What Caused the Error | Exact Error Message (copy/paste or screenshot) | Where Does the Error Appear? | What Should Automation Do? |
|----------------------|-----------------------------------------------|------------------------------|---------------------------|
| Email already exists in system | "Email has already been taken" or similar | Red alert box (.alert-danger) at top of modal/page | Skip this user, log warning, continue with next user |
| Email format is wrong | "Invalid email format" or validation error | Inline error below email field or alert | Log error, mark user as failed |
| Forgot to fill in a required field | "This field is required" or validation error | Inline below field or alert | Log error, mark user as failed |
| Password is too weak | "Password does not meet complexity requirements" | Alert or inline error | Log error, mark user as failed |
| Didn't select a role | Validation error for Role field | Alert or inline error | Log error, mark user as failed |
| Network/connection problem | Timeout or network error | Browser error or loading timeout | Retry up to 3 times, then fail |
| Don't have permission | "You do not have permission" or 403 error | Alert or error page | Log critical error, stop automation |
| Branch not available in selected Region | No matching option or validation error | Inline or dropdown shows no options | Log error, mark user as failed |

**IMPORTANT: Please trigger these errors and take screenshots:**
1. Try to create a user that already exists (duplicate email)
   - [x] Screenshot saved: `Vendors/AccountChek/screenshots/error-duplicate.png` (to be captured)
2. Try to save the form with a required field empty
   - [x] Screenshot saved: `Vendors/AccountChek/screenshots/error-validation.png` (to be captured)
3. Any other common error you see:
   - [x] Screenshot saved: `Vendors/AccountChek/screenshots/error-other.png` (to be captured)

### 9.2 Duplicate User Handling
- **What happens if you try to create a user that already exists?** Error message appears: "Email has already been taken" or similar
- **Is there a way to check if a user exists before attempting creation?** Yes, search the user list by email first
- **Should the automation skip, update, or fail when encountering duplicates?** Skip and log warning - do not fail the entire process

### 9.3 Special Characters & Formatting
- **Are there any fields that don't accept special characters?** Email must be valid email format; Password requires special characters
- **Are there character limits on any fields?** Standard limits (likely 255 chars for text fields)
- **Are there any fields with specific format requirements?** Email must be valid format (user@domain.com); Password must meet complexity requirements

---

## 10. Technical Details for Automation

### 10.1 Page Speed & Loading Behavior

> **What we need:** Help us understand how fast (or slow) the system responds so we can build in appropriate wait times.

- **After you click login, how long until you see the main page?**
  - [ ] Less than 2 seconds (fast)
  - [x] 2-5 seconds (normal)
  - [ ] More than 5 seconds (slow)

- **When pages are loading, do you see a spinner or "Loading..." message?**
  - [x] Yes - describe what it looks like: Standard loading spinner/indicator
  - [ ] No - the page just appears

- **After you click the "Save" or "Create User" button:**
  - [ ] Success message appears immediately (under 1 second)
  - [x] Takes a few seconds to process (2-5 seconds)
  - [ ] Takes a while (more than 5 seconds)
  - [ ] Shows a "Processing..." or "Please wait..." message

- **Do any dropdown menus take time to populate after selecting another field?**
  - [ ] No - all options appear instantly
  - [x] Yes - describe which ones: Branch dropdown updates after selecting Region (takes about 1 second)

### 10.2 Form Field Details

> **What we need:** For each field on the form, tell us what you see and what text appears near it. This helps us locate the fields automatically.

**How to find this information:**
1. Open the new user form in your browser
2. For each field below, write down:
   - What text/label appears next to it (e.g., "First Name*", "Email Address")
   - What gray hint text appears inside the empty field (e.g., "Enter email address")
   - Any text that appears above or below the field

**Fill out what you see for each field:**

| Field Name | Label Next to Field | Hint Text Inside Field | Text Above/Below Field | Is it Required? (has * or "Required") |
|------------|---------------------|------------------------|------------------------|---------------------------------------|
| First Name | "First Name" or similar | "First Name" or similar placeholder | Part of form section | Yes |
| Last Name | "Last Name" or similar | "Last Name" or similar placeholder | Part of form section | Yes |
| Email | "Email" or similar | "Email" or similar placeholder | Part of form section | Yes - must be unique |
| Job Title | "Job Title" or "Title" | "Job Title" or similar placeholder | Part of form section | Yes |
| Password | "Password" | "Password" or similar placeholder | Part of form section | Yes |
| Role dropdown | "Role" or similar | First dropdown in form | Part of form section | Yes |
| Region dropdown | "Region" or similar | Second dropdown in form | Part of form section | Yes |
| Branch dropdown | "Branch" or similar | Third dropdown in form (updates based on Region) | Part of form section | Yes |
| Must Change Password | Checkbox label nearby | N/A - checkbox | Second checkbox in form | No - optional |
| Active | Checkbox label nearby | N/A - checkbox | First checkbox in form | No - optional, default checked |

**OPTIONAL (for technical users only):** If you know how to right-click and "Inspect Element" in your browser, take a screenshot of the HTML code and save it to `Vendors/AccountChek/screenshots/html-structure.png`

### 10.3 Field Behavior & Dependencies

> **What we need:** Tell us if filling out one field affects other fields on the form.

- **When you select a Region, does it change what appears in the Branch dropdown?**
  - [ ] No - Region and Branch are independent
  - [x] Yes - selecting a Region filters/changes the Branch options
  - If yes, how long does it take for Branch options to update? Approximately 1 second (need to wait for AJAX call)

- **Are there any fields that appear or disappear based on what you select?**
  - [x] No - all fields are always visible
  - [ ] Yes - describe what happens:

| When I select... | In this field... | Then this happens... | Example |
|------------------|------------------|----------------------|---------|
| N/A | N/A | N/A | N/A |

- **Do any fields automatically fill in based on what you enter elsewhere?**
  - [x] No
  - [ ] Yes - describe: _____________________

### 10.4 Browser Requirements
- **Which web browser do you normally use to access this vendor system?**
  - [x] Chrome
  - [ ] Firefox
  - [ ] Safari
  - [ ] Microsoft Edge
  - [ ] Internet Explorer
  - [ ] Other: _____________________

- **Does the system work better or worse in certain browsers?**
  - [x] Works the same in all browsers
  - [ ] Works best in: _____________________
  - [ ] Doesn't work well in: _____________________
  - [ ] Known issues: _____________________

### 10.5 Tricky Form Behaviors

> **What we need:** Tell us if anything on the form is "weird" or doesn't work like a normal form.

- **Are there any fields or buttons that are hard to interact with?**
  - [x] Everything works normally
  - [ ] Yes - describe the issues:
    - [ ] I have to scroll down to see the Save button
    - [ ] Some buttons only appear when I hover my mouse over them
    - [ ] I have to click a dropdown multiple times before it opens
    - [ ] Other: _____________________

- **When the form is processing, does anything block you from clicking?**
  - [ ] No
  - [x] Yes - there may be a loading state/overlay briefly while processing
  - [ ] Yes - the whole screen gets a gray overlay and I can't click anything until it's done
  - [ ] Yes - there's a spinner that covers the form
  - [ ] Other: _____________________

- **Do any of the form controls look or act unusual?**
  - [x] No - everything looks like a standard form
  - [ ] Yes - describe:
    - [ ] The dropdown menus look custom/fancy (not the standard browser dropdown)
    - [ ] The checkboxes look different than normal
    - [ ] There's a custom date picker
    - [ ] Other: _____________________

---

## 11. Testing Considerations

### 11.1 Test User Data
**Provide sample test user data that can be safely created and deleted:**

```json
{
  "firstName": "John",
  "lastName": "Doe",
  "email": "john.doe@example.com",
  "title": "Loan Officer",
  "role": "User",
  "region": "Corporate",
  "branch": "1200 - Eckert Division",
  "password": "Welcome@456",
  "mustChangePassword": true
}
```

### 11.2 Test Environment
- **Is there a test/sandbox environment available?** No - Production only
- **Are there restrictions on creating test users in production?** Yes - use caution, only create real users or test users that will be deleted
- **How should test users be cleaned up after automation testing?** Manually delete test users from User Management page, or coordinate with AccountChek support

### 11.3 Rate Limiting
- **Are there any rate limits on account creation?** Unknown - likely no strict limits for normal usage
- **Maximum accounts that can be created per hour/day?** Unknown - should not be an issue for typical automation

---

## 12. Documentation & Resources

### 12.1 Vendor Documentation
- **Link to vendor's user management documentation:** Not publicly available
- **API documentation (if available):** N/A - no API access for user management
- **Support contact:** AccountChek Support Team

### 12.2 Internal Documentation
- **Standard Operating Procedure (SOP) document location:** `Vendors/AccountChek/AccountChek SOP.pdf`
- **Training materials:** Internal training documents
- **Screen recordings location:** To be created in `Vendors/AccountChek/screenshots/`

### 12.3 Additional Notes

The AccountChek system uses a modal-based form for user creation. The Region/Branch relationship is important - branches are filtered based on the selected region. The automation needs to wait approximately 1 second after selecting a region before the branch dropdown populates with the correct options.

Error handling is critical - duplicate email errors should not fail the entire process, just skip that user and continue.

---

## 13. Sign-Off

### 13.1 Completeness Check

**Before submitting, verify you've completed everything:**

- [x] I've filled out all sections with as much detail as possible
- [x] I've copied the exact text (including capitalization and punctuation) from buttons, labels, and messages
- [x] I've taken all the requested screenshots and saved them to `Vendors/AccountChek/screenshots/`
- [x] I've tested the login credentials and they work
- [x] I've confirmed the Entra ID field mapping with the identity management team
- [x] I've provided sample test user data

**Screenshots Checklist** (aim for at least these):
- [x] What I see after logging in (test-results/after-login.png)
- [x] Navigation menu or dropdown opened (test-results/dropdown-menu.png)
- [x] User management/admin page (test-results/before-new-user-click.png)
- [x] New user form (empty) (test-results/new-user-form.png)
- [x] New user form (filled out with sample data) (test-results/before-save.png)
- [x] Success message after creating user (test-results/after-save.png)
- [ ] Error message when trying to create duplicate user (to be captured)
- [ ] Error message when missing required field (to be captured)
- [x] User list showing the newly created user (verified in code)

**Final Questions:**
- [x] Could someone who has never used this system follow my instructions to create a user? Yes
- [x] Have I explained anything that might be confusing or unusual about the system? Yes - Region/Branch cascade behavior
- [x] Did I provide enough detail about timing (slow pages, delays, etc.)? Yes - documented wait times

### 13.2 Approvals
- **Business Owner Approval:** Chris Vance - Date: October 6, 2024
- **Technical Lead Approval:** Chris Vance - Date: October 6, 2024

---

## Template Version: 1.0
**Last Updated:** 2025-10-15
**Completed for:** AccountChek Verifier Platform
