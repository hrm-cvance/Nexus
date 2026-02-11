# Nexus — Now Available

**To:** IT Operations Team
**From:** IT Department
**Re:** New tool for vendor account provisioning

---

## What is Nexus?

Nexus is a new desktop application that automates the process of setting up vendor accounts when onboarding new employees.

Instead of logging into each vendor portal one at a time, filling out forms, and tracking what was created in a spreadsheet, Nexus handles it for you. You search for the new hire, confirm which vendors they need, click a button, and Nexus creates the accounts automatically.

## Why are we using it?

| Before Nexus | With Nexus |
|---|---|
| Log into each vendor portal individually | One sign-in, all vendors handled |
| Manually type employee details into each form | Employee info pulled from Azure AD automatically |
| Track account creation in a spreadsheet | PDF summary generated for every run |
| Easy to miss a vendor or make a typo | Vendors auto-detected from AD group membership |
| No standard process across the team | Same consistent workflow every time |

## What vendors does it support?

Nexus currently provisions accounts for:

- AccountChek
- BankVOD
- Certified Credit
- Clear Capital
- DataVerify
- MMI
- Partners Credit
- The Work Number (Equifax)

## How do I get it?

Nexus is deployed automatically through Intune. You should see it in your Start Menu as **Nexus**. If you don't see it, contact the IT department.

## What do I need to know?

- **You sign in with your Microsoft account** — the same one you use for Outlook and Teams.
- **You don't need any vendor passwords** — Nexus retrieves admin credentials securely from Azure Key Vault.
- **The browser is visible on purpose** — you'll see a Chrome window open and fill in forms. This lets you watch what's happening and step in if needed (for example, if a site asks for a verification code).
- **It will ask you questions sometimes** — if a vendor already has an account with that email, Nexus will ask whether you want to try a different email or skip that vendor.

## Where do I go for help?

- **User guide:** See the [Nexus User Guide](USER_GUIDE.md) for step-by-step instructions
- **Issues or questions:** Contact the IT department

---

*Nexus is an internal tool built by Highland Mortgage Services IT.*
