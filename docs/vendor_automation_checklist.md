# Vendor Automation Checklist

Use this checklist to vet each vendor module for completeness. Each vendor must satisfy **all** requirements before it is considered production-ready.

---

## Requirements

### R1 - End-to-End Account Creation (No Stops)
The automation must run from login to account creation without stopping or requiring manual intervention (MFA/CAPTCHA excluded). If MFA is required, the agent should wait for the user to complete it, then resume automatically.

### R2 - Duplicate Account Detection
Before or during account creation, the automation must detect if the user already exists. On duplicate detection:
- Set `skip: True` in the result so it is **not** counted as a hard failure.
- Log a clear warning message (e.g., `"User already exists - email address is already taken"`).
- Close any open modals/forms cleanly.
- Return control so the orchestrator can continue to the next vendor.

### R3 - Account Creation Validation
After submitting the creation form, the automation must verify the account was actually created. Acceptable methods:
- Check for an explicit success message/toast on the page.
- Search the user list for the newly created account.
- Verify the page URL changed away from the creation form.
- At minimum, confirm no error messages are present.

### R4 - Summary Page Data
The result dict must include enough information for the Account Summary tab to display a useful card. Required keys:
- `success` (bool)
- `user` (str - display name)
- `messages` (list - step-by-step status messages with checkmarks)
- `warnings` (list - non-fatal issues like alternate usernames)
- `errors` (list - fatal issues)
- Any vendor-specific data (account IDs, URLs, generated credentials, etc.)

### R5 - MFA / CAPTCHA Handling
If the vendor site requires MFA or CAPTCHA, the automation must:
- Detect the challenge automatically.
- Wait for manual completion (configurable timeout, minimum 2 minutes).
- Resume automatically once the challenge is resolved.
- Timeout gracefully with a clear error if not completed.

---

## Vendor Status

### AccountChek
| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| R1 | End-to-End Creation | PASS | Login, navigate to User Management, fill form, submit. Complete flow. |
| R2 | Duplicate Detection | PASS | Checks `.alert-danger`/`.alert-error` for "taken", "already exist", "duplicate". Sets `skip: True`. |
| R3 | Creation Validation | PASS | Looks for "Verifier Saved", "User Created", "Success". Falls back to screenshot if unclear. |
| R4 | Summary Data | PASS | Returns messages, warnings, errors, and AI role suggestions with confidence scores. |
| R5 | MFA Handling | N/A | No MFA required for this vendor. |

**Action items:** None - meets all requirements.

---

### BankVOD
| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| R1 | End-to-End Creation | PASS | Login, create user, search for created user, update password to HRM default. Full flow enabled. |
| R2 | Duplicate Detection | PASS | Checks `.alert-danger`/`.alert-error` for "taken", "already exist", "duplicate". Sets `skip: True`. |
| R3 | Creation Validation | PASS | Searches for newly created user by email after creation (implicit validation). Also checks success messages and modal close. |
| R4 | Summary Data | PASS | Returns step-by-step messages including password update confirmation. |
| R5 | MFA Handling | N/A | No MFA required for this vendor. |

**Action items:** None - meets all requirements.

---

### ClearCapital
| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| R1 | End-to-End Creation | PASS | Login (2-step), handles Terms of Use popup, fill form, submit. Auto-retries with alternate username on conflict. |
| R2 | Duplicate Detection | PASS | Detects "already being used", "choose a different username". Auto-retries with `username + "1"`. |
| R3 | Creation Validation | PASS | URL-based validation - checks if page navigated away from creation form. |
| R4 | Summary Data | PASS | Returns messages, warnings (alternate username used), errors. |
| R5 | MFA Handling | N/A | No MFA required (handles Terms of Use popup separately). |

**Action items:** None - meets all requirements.

---

### DataVerify
| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| R1 | End-to-End Creation | PASS | Login, navigate to User Manager, fill form. Auto-retries up to 10 times with numbered username suffixes. |
| R2 | Duplicate Detection | PASS | Detects exact error: "The chosen username is already in use." Retries with incremented username (1-9). |
| R3 | Creation Validation | PASS | Checks for "user created", "successfully" keywords. Checks for "User Manager" page text. |
| R4 | Summary Data | PASS | Returns messages, warnings (original username taken, alternate used), errors. |
| R5 | MFA Handling | N/A | No MFA required for this vendor. |

**Action items:** None - meets all requirements.

---

### CertifiedCredit
| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| R1 | End-to-End Creation | PASS | Login, MFA wait, popup window form, configure restrictions post-creation. Complete flow. |
| R2 | Duplicate Detection | PASS | Detects "duplicate" + "login" in popup page content. Auto-retries with numbered username (up to 10 attempts). |
| R3 | Creation Validation | PASS | Verifies user appears in user list. Opens user record to confirm existence. |
| R4 | Summary Data | NEEDS WORK | Returns basic messages/warnings/errors but no vendor-specific data (no account ID, username created, etc.). |
| R5 | MFA Handling | PASS | 5-minute timeout. Polls for home page elements. Logs progress every 30 seconds. |

**Action items:**
- [ ] Add the final username (if modified by retry) to the result dict for summary display.

---

### PartnersCredit
| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| R1 | End-to-End Creation | PASS (by design) | Submits a *request* form, not a direct account creation. This is the vendor's intended workflow - credentials come via encrypted email. |
| R2 | Duplicate Detection | FAIL | No duplicate checking at all. Submits the request regardless. |
| R3 | Creation Validation | FAIL | No validation after form submission. Assumes success if no error during submission. |
| R4 | Summary Data | NEEDS WORK | Only generic messages. Should note this is a request-based vendor and include expected next steps. |
| R5 | MFA Handling | PASS | Detects Public/Private prompt and MFA code entry. 5-minute timeout with polling. |

**Action items:**
- [ ] Add duplicate detection - search the existing user list before submitting a new request.
- [ ] Add validation - check for a confirmation message or request number after submission.
- [ ] Improve summary data - include request confirmation details and clear "next steps" info.

---

### TheWorkNumber
| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| R1 | End-to-End Creation | PASS | Login, MFA wait, navigate to User Management (dismiss tour), fill form, select org/location, create. |
| R2 | Duplicate Detection | FAIL | No duplicate checking. Will fail if username `FirstName.LastName` already exists with no fallback. |
| R3 | Creation Validation | FAIL | Only takes a screenshot after clicking Create. No success message check, no user search. |
| R4 | Summary Data | NEEDS WORK | Basic progression messages only. No account details, no confirmation data. |
| R5 | MFA Handling | PASS | Detects MFA, auto-clicks email option, 5-minute timeout with 30s progress logging. |

**Action items:**
- [ ] Add duplicate detection - check for error messages after form submission (e.g., "username already exists"). Add auto-retry with numbered suffix.
- [ ] Add creation validation - after clicking Create, check for success confirmation or search user list.
- [ ] Improve summary data - include the username created and activation email status.

---

### MMI (Mortgage Market Intelligence)
| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| R1 | End-to-End Creation | PASS | Login (handles SSO redirect), navigate to Manage Seats, fill form, set permissions, create. |
| R2 | Duplicate Detection | WEAK | Only checks for generic "error", "failed", "already exists", "duplicate" in page content after submission. No proactive check, no retry logic. |
| R3 | Creation Validation | WEAK | Absence-of-error check only. Falls back to assuming success if no error keywords found. |
| R4 | Summary Data | NEEDS WORK | Basic progression messages only. No vendor-specific data. |
| R5 | MFA Handling | PASS | Detects Microsoft/Okta SSO redirect. 5-minute timeout for manual authentication. |

**Action items:**
- [ ] Improve duplicate detection - add `skip: True` flag when duplicate is detected so it's not a hard failure. Add proactive check before creation if possible.
- [ ] Improve creation validation - look for explicit success message or verify user appears in team list.
- [ ] Improve summary data - include seat/license info if available.

---

### Experience.com
| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| R1 | End-to-End Creation | PASS | Login, CAPTCHA wait, create user, configure profile settings, publish, capture widget code, capture profile URL, fill profile info. Most complete flow. |
| R2 | Duplicate Detection | PASS | Checks for `.ant-form-item-explain-error` with "Already Registered". Closes modal, returns `False`, falls through to profile config. |
| R3 | Creation Validation | PASS | Multi-staged: checks for email error, verifies user in list, waits for loading spinners. |
| R4 | Summary Data | PASS | Returns messages, warnings, errors, `widget_code`, and `profile_url` for downstream integrations. |
| R5 | MFA Handling | PASS | Detects reCAPTCHA iframe. 2-minute manual wait with polling for password field appearance. |

**Action items:** None - meets all requirements. *(Currently disabled in vendor_mappings.json)*

---

## Overall Summary

| Vendor | R1 | R2 | R3 | R4 | R5 | Ready? |
|--------|----|----|----|----|----|----|
| AccountChek | PASS | PASS | PASS | PASS | N/A | YES |
| BankVOD | PASS | PASS | PASS | PASS | N/A | YES |
| ClearCapital | PASS | PASS | PASS | PASS | N/A | YES |
| DataVerify | PASS | PASS | PASS | PASS | N/A | YES |
| CertifiedCredit | PASS | PASS | PASS | NEEDS WORK | PASS | NO |
| PartnersCredit | PASS | FAIL | FAIL | NEEDS WORK | PASS | NO |
| TheWorkNumber | PASS | FAIL | FAIL | NEEDS WORK | PASS | NO |
| MMI | PASS | WEAK | WEAK | NEEDS WORK | PASS | NO |
| Experience.com | PASS | PASS | PASS | PASS | PASS | YES (disabled) |

### Priority Order for Remediation
1. **TheWorkNumber** - Missing duplicate detection and validation entirely.
2. **PartnersCredit** - Missing duplicate detection and validation entirely.
3. **MMI** - Weak duplicate detection and validation, needs hardening.
4. **CertifiedCredit** - Minor summary data improvement needed.
