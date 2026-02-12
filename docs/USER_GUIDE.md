# Nexus User Guide

This guide walks you through using Nexus to provision vendor accounts for new employees.

---

## Getting Started

1. Open **Nexus** from your Start Menu
2. The application opens with the **User Search** tab active

## Step 1: Sign In

Before you can do anything, you need to be signed in with your Microsoft account.

**If you've used Nexus before**, your sign-in is remembered automatically. When you open the app, the status indicator will already be green and show **Connected as: your email**. You can skip straight to Step 2.

**If this is your first time** (or you previously signed out):

1. Click the **Sign In** button in the Microsoft Sign-In section
2. A browser window will open with the Microsoft login page
3. Sign in with your Highland Mortgage email and password
4. Once signed in, the status indicator will turn green and show **Connected**

> **Tip:** This is the same Microsoft account you use for Outlook and Teams. Your sign-in persists between sessions — you won't need to sign in again unless you click **Sign Out** or go approximately 90 days without using Nexus.

## Step 2: Search for the Employee

Once signed in, you can search for the new hire in Azure Active Directory.

1. Choose a search type from the dropdown:
   - **Display Name** — search by the person's name (e.g., "Jane Smith")
   - **Email** — search by their email address
   - **Employee ID** — search by their employee number
2. Type your search term in the text box
3. Click **Search** (or press Enter)
4. Results will appear in the table below

When you find the right person:

1. Click on their row in the results table
2. Click **Select User** to continue

This takes you to the **Account Provisioning** tab.

## Step 3: Review and Select Vendors

The Account Provisioning tab shows you:

- **Employee details** — name, email, job title, department, and office location pulled from Azure AD
- **Detected vendors** — which vendor accounts the employee needs, based on the Azure AD groups they belong to

Each vendor is shown as a card with a checkbox. Vendors are pre-selected if the employee is in the matching AD group.

**What you can do here:**

- **Uncheck** a vendor if you don't want to create an account for it right now
- **Check** an additional vendor if you want to add one that wasn't auto-detected
- Review the employee's information to make sure it looks correct

When you're ready, click **Start Automation**.

## Step 4: Watch the Automation

The Automation Status tab shows real-time progress as Nexus creates accounts on each vendor platform.

**What you'll see:**

- A progress card for each vendor showing its current status
- A live Chrome browser window where the automation is happening
- Status messages as each step completes

**Things that may require your attention:**

### Verification Codes (MFA)

Some vendor sites require a verification code sent via text message or email. When this happens:

1. Nexus will pause and display a message asking you to complete the verification
2. Check your phone or email for the code
3. Enter the code in the browser window
4. Click the verify/submit button in the browser
5. Nexus will detect that you've completed the step and resume automatically

> **Note:** You have up to 10 minutes to complete a verification step before it times out.

### Duplicate Accounts

If a vendor already has an account with the employee's email address, Nexus will show a dialog asking what to do:

- **Enter an alternate email** — type a different email address and Nexus will retry with that email
- **Skip this vendor** — move on to the next vendor without creating an account

### Errors

If something goes wrong with a vendor, Nexus will mark it as failed and continue with the remaining vendors. You can see error details in the status messages.

## Step 5: Review the Results

When all vendors have been processed, the Summary tab shows the results:

- **Success count** — how many accounts were created successfully
- **Warning count** — accounts created with notes (e.g., used an alternate email)
- **Failed count** — vendors that could not be completed

Each vendor has a result card showing what happened.

### Export a PDF Report

Click **Export PDF** to save a summary report. This creates a PDF document with:

- The employee's name and details
- Which vendors were provisioned
- The date and time
- Any warnings or errors

Save this PDF for your records.

### Start Another

Click **Start New Automation** to go back to the User Search tab and provision another employee.

---

## Quick Reference

| Task | Where | How |
|---|---|---|
| Sign in | User Search tab | Automatic if previously signed in; otherwise click **Sign In** |
| Find an employee | User Search tab | Search by name, email, or employee ID |
| Choose vendors | Account Provisioning tab | Check/uncheck vendor cards, then click **Start Automation** |
| Handle MFA | Automation Status tab | Enter the code in the browser window when prompted |
| Handle duplicates | Automation Status tab | Choose alternate email or skip the vendor |
| Save results | Summary tab | Click **Export PDF** |

## Frequently Asked Questions

**Q: Do I need to know the vendor admin passwords?**
No. Nexus retrieves all vendor credentials automatically from Azure Key Vault. You never need to enter or know vendor admin passwords.

**Q: Why can I see a browser window opening?**
This is by design. Nexus uses a real browser to interact with vendor websites. The browser is visible so you can watch what's happening and step in if needed — for example, to enter a verification code.

**Q: What if a vendor site has changed and the automation fails?**
Contact the IT department. Vendor websites occasionally update their layouts, which may require an update to the Nexus automation for that vendor.

**Q: Can I run Nexus for multiple employees at the same time?**
No. Nexus processes one employee at a time. Complete the current run before starting the next one.

**Q: What if I accidentally close the browser window?**
The automation for that vendor will fail, but Nexus will continue with the remaining vendors. You can re-run the failed vendor later.

**Q: Where are the logs if I need to report a problem?**
Logs are saved to `%APPDATA%\Nexus\logs\`. When reporting an issue, include the log file for the day the problem occurred (named `nexus_YYYYMMDD.log`).

---

## Need Help?

Contact the IT department for:

- Access issues (can't sign in, permission errors)
- Vendor automation failures
- Missing vendors or incorrect auto-detection
- Any other Nexus questions

---

*Nexus is an internal tool built by Highland Mortgage Services IT.*
