# Vendor Onboarding Template - Account Creation Automation

> **Purpose:** This template helps us automate the process of creating user accounts in vendor systems. You know the vendor system well - we just need you to document exactly how you create accounts manually. The more detail you provide, the better the automation will work!

> **Don't worry about technical terms** - just describe what you see and do. We'll handle the technical parts.

**Date:** _____________________
**Completed By:** _____________________
**Vendor Name:** _____________________

---

## 1. Vendor Overview

### 1.1 Basic Information
- **Vendor Name:**
- **Platform/System Name:**
- **Primary Purpose:**
- **Vendor Contact (if applicable):**
- **Internal Department Owner:**

### 1.2 Application URL
- **Login URL:**
- **Production Environment:**
- **Test/Staging Environment (if available):**

---

## 2. Authentication & Access

### 2.1 Login Requirements
- **Authentication Method:**
  - [ ] Username/Password
  - [ ] Email/Password
  - [ ] SSO/SAML
  - [ ] Multi-Factor Authentication (MFA)
  - [ ] Other: _____________________

- **Admin Account Credentials:**
  - **Username/Email:**
  - **Password Location:** (e.g., password manager, vault)
  - **MFA Method (if applicable):**

### 2.2 Session Management
- **Session Timeout:**
- **Does the session require periodic re-authentication?**
- **Any CAPTCHA or bot detection mechanisms?**

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
1. After login, navigate to: _____________________
2. Click on: _____________________
3. Additional steps: _____________________
4. _____________________
5. _____________________

**REQUIRED: Take screenshots of each step:** (Save to `Vendors/[VendorName]/screenshots/`)
- [ ] Screenshot: What you see immediately after logging in
- [ ] Screenshot: Any menu or dropdown you opened
- [ ] Screenshot: The page where you manage users

### 3.2 User Management Interface
- **How do you initiate new user creation?**
  - [ ] Button (exact label: _____________)
  - [ ] Menu option (exact text: _____________)
  - [ ] Link (exact text: _____________)
  - [ ] Icon button (describe icon: _____________)
  - [ ] Other: _____________________

- **What happens when clicked?**
  - [ ] Modal/dialog appears (overlay on same page)
  - [ ] New page loads
  - [ ] Sidebar/panel slides out
  - [ ] Inline form appears below
  - [ ] Other: _____________________

- **If modal/dialog, does it have a close button (X) or backdrop click to close?**

---

## 4. User Roles & Permissions

### 4.1 Available User Roles
**List all available user roles/permission levels in the vendor system:**

| Role Name | Description | Access Level | Will Be Auto-Created? |
|-----------|-------------|--------------|----------------------|
| | | Standard | ✅ Yes (default) |
| | | Admin/Manager | ❌ No (manual only) |
| | | Admin/Manager | ❌ No (manual only) |
| | | | |

**IMPORTANT:** Only the standard/basic user role should be marked as "Will Be Auto-Created". All elevated roles (Admin, Manager, Supervisor, etc.) must be created manually for security purposes.

### 4.2 Standard User Role Details
- **What is the exact name of the standard user role?** (e.g., "User", "Standard User", "Employee")
  - Role name: _____________________

- **How is this role assigned during user creation?**
  - [ ] Dropdown selection (we'll always select the standard role)
  - [ ] Radio buttons (we'll select the standard role option)
  - [ ] Checkboxes (we'll check only the standard role)
  - [ ] Automatic/default (no selection needed)
  - [ ] Other: _____________________

- **Can a user have multiple roles simultaneously?**
  - If yes: We will only assign the standard role

- **Is the standard role the default selection when the form opens?**
  - [ ] Yes - already selected
  - [ ] No - we need to select it

### 4.3 Elevated Roles (Manual Creation Only)
**List roles that require manual creation:**

| Role Name | Why Manual Only? | Who Can Create? |
|-----------|------------------|-----------------|
| Admin | Full system access, security risk | IT Leadership only |
| Manager | Elevated permissions | Department managers |
| | | |


---

## 5. Organizational Structure

### 5.1 Regional/Branch Structure
- **Does the vendor system have regions, branches, or divisions?**
  - [ ] Regions
  - [ ] Branches
  - [ ] Divisions
  - [ ] Departments
  - [ ] Cost Centers
  - [ ] None
  - [ ] Other: _____________________

### 5.2 Structure Details
**If yes, describe the hierarchy:**

- **Top Level (e.g., Region):**
- **Mid Level (e.g., Division):**
- **Bottom Level (e.g., Branch):**

### 5.3 Structure Assignment
- **Are these assigned during user creation?**
- **Are they required fields?**
- **Do selections cascade (e.g., selecting region filters available branches)?**
- **How are they presented in the UI?**
  - [ ] Dropdown menus
  - [ ] Hierarchical tree selector
  - [ ] Separate fields for each level
  - [ ] Other: _____________________

---

## 6. User Account Fields

### 6.1 Required Fields
**List all REQUIRED fields for account creation:**

| Field Name | Field Type | Format/Validation | Example Value | Notes |
|------------|------------|-------------------|---------------|-------|
| First Name | Text | | John | |
| Last Name | Text | | Doe | |
| Email | Email | | john.doe@company.com | Must be unique |
| | | | | |
| | | | | |
| | | | | |

### 6.2 Optional Fields
**List all OPTIONAL fields:**

| Field Name | Field Type | Format/Validation | Example Value | Default Value | Notes |
|------------|------------|-------------------|---------------|---------------|-------|
| Phone | Text | (555) 555-5555 | | | |
| | | | | | |
| | | | | | |

### 6.3 Password Configuration

> **Note:** Nexus will auto-generate secure passwords by default. We need to know what password rules this vendor requires so we can generate passwords that meet their complexity requirements.

**Password Rules:**
- **Minimum length:** _____ characters
- **Maximum length:** _____ characters (if any)
- **Must include uppercase letters (A-Z)?** [ ] Yes [ ] No - Minimum: _____
- **Must include lowercase letters (a-z)?** [ ] Yes [ ] No - Minimum: _____
- **Must include numbers (0-9)?** [ ] Yes [ ] No - Minimum: _____
- **Must include special characters?** [ ] Yes [ ] No - Minimum: _____

**If special characters are required:**
- **Which special characters are ALLOWED?** (Check all that apply)
  - [ ] ! (exclamation mark)
  - [ ] @ (at sign)
  - [ ] # (hash/pound)
  - [ ] $ (dollar sign)
  - [ ] % (percent)
  - [ ] ^ (caret)
  - [ ] & (ampersand)
  - [ ] * (asterisk)
  - [ ] - (hyphen/dash)
  - [ ] _ (underscore)
  - [ ] = (equals)
  - [ ] + (plus)
  - [ ] Other: _____________________

- **Are any special characters NOT ALLOWED or cause problems?**
  - [ ] Yes - list them: _____________________
  - [ ] No - all special characters work fine
  - Example: "The system doesn't allow curly braces { } or angle brackets < >"

**Additional Password Rules:**
- **Are there any other password requirements we should know about?**
  - [ ] No consecutive characters (e.g., "aaa" or "111" not allowed)
  - [ ] Cannot contain username or email
  - [ ] Cannot contain common words
  - [ ] Must be different from last ___ passwords
  - [ ] Expires after ___ days
  - [ ] Other: _____________________

**Password Setup During Account Creation:**
- **Is a password set during creation?** [ ] Yes [ ] No
- **Is there a "Must change password on first login" option?** [ ] Yes [ ] No
- **Can a temporary password be auto-generated by the system?** [ ] Yes [ ] No
- **If auto-generated, what format does it use?** _____________________

**What should Nexus do?**
- [ ] Use the vendor's auto-generated password (if available)
- [ ] Generate our own password that meets the vendor's requirements (recommended)

### 6.4 Account Status Options
- **Can accounts be created in an inactive/disabled state?**
- **Are there any activation steps after creation?**
- **Email verification required?**

---

## 7. Microsoft Entra ID (Azure AD) Field Mapping

> **Note:** We connect to Microsoft Entra ID using Microsoft Graph API to retrieve user attributes for automated provisioning.

### 7.1 Provisioning Trigger Group
**This automation uses Entra ID group membership to determine which users need accounts created.**

- **Entra ID Group Name:** [VendorName]_Users
  - **Example:** `AccountChek_Users`, `VendorXYZ_Users`
  - **Group Object ID:** _____________________ (to be provided by identity team)
  - **Group Purpose:** Members of this group will automatically have accounts created in the vendor system
  - **Role Assigned:** Standard User (default role only - admins/managers must be created manually)

**Important Notes:**
- ✅ **Only standard/basic users are created via automation**
- ❌ **Admin and Manager roles must be created manually** for security purposes
- The automation queries this group via Graph API: `https://graph.microsoft.com/v1.0/groups/{groupId}/members`
- Users must be added to this group in Entra ID to trigger account creation

### 7.2 Entra ID User Attributes Required
**Specify which Entra ID user attributes are needed and how they map to vendor fields:**

| Vendor Field | Entra ID Attribute (Graph API) | Transformation Logic | Example |
|--------------|--------------------------------|----------------------|---------|
| First Name | givenName | Direct mapping | John |
| Last Name | surname | Direct mapping | Doe |
| Email | mail or userPrincipalName | Direct mapping | john.doe@company.com |
| Role | N/A - Fixed Value | Always "User" (standard role) | User |
| | | | |
| | | | |
| | | | |

**Graph API endpoint used:** `https://graph.microsoft.com/v1.0/users/{id}`

### 7.3 What Role Will Users Be Assigned?
**Since we only create standard users via automation:**

| Vendor Role Name | Will Be Auto-Created? | Notes |
|------------------|-----------------------|-------|
| User (or Standard User) | ✅ Yes | Default role for all automated accounts |
| Admin | ❌ No | Must be created manually |
| Manager | ❌ No | Must be created manually |
| Power User | ❌ No | Must be created manually |
| [Other elevated roles] | ❌ No | Must be created manually |

**What is the exact role name/label for standard users in this vendor system?** _____________________
- Example: "User", "Standard User", "Basic User", "Employee", etc.

### 7.4 Entra ID Department/Office Mapping
**If vendor has regional/branch structure, map Entra ID attributes:**

| Entra ID Attribute | Example Value | Vendor Region/Branch | Notes |
|--------------------|---------------|----------------------|-------|
| department | Sales | | |
| officeLocation | New York Office | | |
| companyName | | | |
| | | | |

### 7.5 Conditional Logic
**Describe any conditional logic needed for Entra ID mapping:**

Example: "If officeLocation contains 'Western', assign to 'Western Region'; if officeLocation is 'HQ', assign to 'Corporate' region"

**Note:** Role assignment is NOT conditional - all automated accounts receive the standard user role only.

---

## 8. Account Creation Workflow

### 8.1 Step-by-Step Process
**Document the complete workflow for creating a user account:**

1.
2.
3.
4.
5.

### 8.2 Form Submission
- **What is the label on the submit button?** (e.g., "Save", "Create User", "Submit")
- **Does submission happen on the same page or navigate away?**
- **Are there confirmation dialogs before final submission?**

### 8.3 Success Indicators

> **What we need:** How do YOU know that the account was created successfully? What do you look for?

**After clicking Save/Submit, what tells you it worked?**

- [ ] A green message appears
  - **Copy the exact message text here:** _____________________
  - **Where on the screen does it appear?** (top of page, center popup, corner notification, etc.): _____________________
  - **Does it disappear after a few seconds, or stay on screen?** _____________________
  - **IMPORTANT: Take a screenshot** and save to: `Vendors/[VendorName]/screenshots/success-message.png`

- [ ] The form closes/disappears automatically
- [ ] I'm taken back to the user list page
- [ ] I receive an email confirmation
- [ ] The new user immediately appears in the user list
- [ ] The form clears out and is ready for another user
- [ ] Other: _____________________

**What else changes on the screen after successful creation?**
- [ ] The total user count number increases
- [ ] A new row appears in the user table
- [ ] A green checkmark icon appears
- [ ] Other: _____________________

### 8.4 How to Verify the User Was Really Created

> **What we need:** After you create a user, how do you double-check that they're actually in the system?

**Your verification process:**
1. After creating the user, I go to: _____________________
2. I search for the user using their: [ ] Email [ ] Name [ ] Username [ ] Other: _____
3. I look for the following information to confirm it's correct:
   - [ ] Name is correct
   - [ ] Email is correct
   - [ ] Role is correct
   - [ ] Region/Branch is correct
   - [ ] Account status shows as Active
   - [ ] Other: _____________________

**Take a screenshot** of the user list showing the newly created user and save to: `Vendors/[VendorName]/screenshots/user-in-list.png`


---

## 9. Error Handling & Edge Cases

### 9.1 Common Errors

> **What we need:** What error messages have you seen when creating accounts? This helps us handle problems gracefully.

**Tell us about errors you've encountered:**

| What Caused the Error | Exact Error Message (copy/paste or screenshot) | Where Does the Error Appear? | What Should Automation Do? |
|----------------------|-----------------------------------------------|------------------------------|---------------------------|
| Email already exists in system | "Email already in use" | Red alert box at top of form | Skip this user and continue with next one |
| Email format is wrong | | | |
| Forgot to fill in a required field | | | |
| Password is too weak | | | |
| Didn't select a role | | | |
| Network/connection problem | | | |
| Don't have permission | | | |
| Other: _____________ | | | |

**IMPORTANT: Please trigger these errors and take screenshots:**
1. Try to create a user that already exists (duplicate email)
   - [ ] Screenshot saved: `Vendors/[VendorName]/screenshots/error-duplicate.png`
2. Try to save the form with a required field empty
   - [ ] Screenshot saved: `Vendors/[VendorName]/screenshots/error-validation.png`
3. Any other common error you see:
   - [ ] Screenshot saved: `Vendors/[VendorName]/screenshots/error-other.png`

### 9.2 Duplicate User Handling
- **What happens if you try to create a user that already exists?**
- **Is there a way to check if a user exists before attempting creation?**
- **Should the automation skip, update, or fail when encountering duplicates?**

### 9.3 Special Characters & Formatting
- **Are there any fields that don't accept special characters?**
- **Are there character limits on any fields?**
- **Are there any fields with specific format requirements?** (e.g., phone numbers)

---

## 10. Technical Details for Automation

### 10.1 Page Speed & Loading Behavior

> **What we need:** Help us understand how fast (or slow) the system responds so we can build in appropriate wait times.

- **After you click login, how long until you see the main page?**
  - [ ] Less than 2 seconds (fast)
  - [ ] 2-5 seconds (normal)
  - [ ] More than 5 seconds (slow)

- **When pages are loading, do you see a spinner or "Loading..." message?**
  - [ ] Yes - describe what it looks like: _____________________
  - [ ] No - the page just appears

- **After you click the "Save" or "Create User" button:**
  - [ ] Success message appears immediately (under 1 second)
  - [ ] Takes a few seconds to process (2-5 seconds)
  - [ ] Takes a while (more than 5 seconds)
  - [ ] Shows a "Processing..." or "Please wait..." message

- **Do any dropdown menus take time to populate after selecting another field?**
  - [ ] No - all options appear instantly
  - [ ] Yes - describe which ones: _____________________

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
| First Name | "First Name*" | "First Name" | "User Information" appears above | Yes - has * |
| Last Name | | | | |
| Email | | | | |
| Password | | | | |
| Job Title | | | | |
| Role dropdown | | | | |
| Region dropdown | | | | |
| Branch dropdown | | | | |
| Other: _______ | | | | |
| Other: _______ | | | | |

**OPTIONAL (for technical users only):** If you know how to right-click and "Inspect Element" in your browser, take a screenshot of the HTML code and save it to `Vendors/[VendorName]/screenshots/html-structure.png`

### 10.3 Field Behavior & Dependencies

> **What we need:** Tell us if filling out one field affects other fields on the form.

- **When you select a Region, does it change what appears in the Branch dropdown?**
  - [ ] No - Region and Branch are independent
  - [ ] Yes - selecting a Region filters/changes the Branch options
  - If yes, how long does it take for Branch options to update? _____________________

- **Are there any fields that appear or disappear based on what you select?**
  - [ ] No - all fields are always visible
  - [ ] Yes - describe what happens:

| When I select... | In this field... | Then this happens... | Example |
|------------------|------------------|----------------------|---------|
| "Manager" | Role dropdown | A "Team Size" field appears below | If Manager is selected, I need to enter team size |
| | | | |
| | | | |

- **Do any fields automatically fill in based on what you enter elsewhere?**
  - [ ] No
  - [ ] Yes - describe: _____________________
  - Example: "When I select 'Western Region', the email domain automatically changes to '@west.company.com'"

### 10.4 Browser Requirements
- **Which web browser do you normally use to access this vendor system?**
  - [ ] Chrome
  - [ ] Firefox
  - [ ] Safari
  - [ ] Microsoft Edge
  - [ ] Internet Explorer
  - [ ] Other: _____________________

- **Does the system work better or worse in certain browsers?**
  - [ ] Works the same in all browsers
  - [ ] Works best in: _____________________
  - [ ] Doesn't work well in: _____________________
  - [ ] Known issues: _____________________

### 10.5 Tricky Form Behaviors

> **What we need:** Tell us if anything on the form is "weird" or doesn't work like a normal form.

- **Are there any fields or buttons that are hard to interact with?**
  - [ ] Everything works normally
  - [ ] Yes - describe the issues:
    - [ ] I have to scroll down to see the Save button
    - [ ] Some buttons only appear when I hover my mouse over them
    - [ ] I have to click a dropdown multiple times before it opens
    - [ ] Other: _____________________

- **When the form is processing, does anything block you from clicking?**
  - [ ] No
  - [ ] Yes - the whole screen gets a gray overlay and I can't click anything until it's done
  - [ ] Yes - there's a spinner that covers the form
  - [ ] Other: _____________________

- **Do any of the form controls look or act unusual?**
  - [ ] No - everything looks like a standard form
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
  "firstName": "",
  "lastName": "",
  "email": "",
  "role": "",
  "region": "",
  "branch": ""
}
```

### 11.2 Test Environment
- **Is there a test/sandbox environment available?**
- **Are there restrictions on creating test users in production?**
- **How should test users be cleaned up after automation testing?**

### 11.3 Rate Limiting
- **Are there any rate limits on account creation?**
- **Maximum accounts that can be created per hour/day?**

---

## 12. Documentation & Resources

### 12.1 Vendor Documentation
- **Link to vendor's user management documentation:**
- **API documentation (if available):**
- **Support contact:**

### 12.2 Internal Documentation
- **Standard Operating Procedure (SOP) document location:**
- **Training materials:**
- **Screen recordings location:**

### 12.3 Additional Notes


---

## 13. Sign-Off

### 13.1 Completeness Check

**Before submitting, verify you've completed everything:**

- [ ] I've filled out all sections with as much detail as possible
- [ ] I've copied the exact text (including capitalization and punctuation) from buttons, labels, and messages
- [ ] I've taken all the requested screenshots and saved them to `Vendors/[VendorName]/screenshots/`
- [ ] I've tested the login credentials and they work
- [ ] I've confirmed the Entra ID field mapping with the identity management team
- [ ] I've provided sample test user data

**Screenshots Checklist** (aim for at least these):
- [ ] What I see after logging in
- [ ] Navigation menu or dropdown opened
- [ ] User management/admin page
- [ ] New user form (empty)
- [ ] New user form (filled out with sample data)
- [ ] Success message after creating user
- [ ] Error message when trying to create duplicate user
- [ ] Error message when missing required field
- [ ] User list showing the newly created user

**Final Questions:**
- [ ] Could someone who has never used this system follow my instructions to create a user?
- [ ] Have I explained anything that might be confusing or unusual about the system?
- [ ] Did I provide enough detail about timing (slow pages, delays, etc.)?

### 13.2 Approvals
- **Business Owner Approval:** _____________________ Date: _____
- **Technical Lead Approval:** _____________________ Date: _____

---

## Template Version: 1.0
**Last Updated:** 2025-10-15
