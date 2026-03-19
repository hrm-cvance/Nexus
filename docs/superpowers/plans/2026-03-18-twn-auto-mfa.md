# TheWorkNumber Auto-MFA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically read OTP codes from the `nexus@highlandsmortgage.com` inbox and enter them during TheWorkNumber MFA, eliminating the manual email check.

**Architecture:** Add `read_recent_emails()` to the existing `GraphAPIClient`, then call it from a new `_auto_enter_mfa_code()` method in the TWN automation. The graph client is plumbed from `MainWindow` through `AutomationStatusTab` to the TWN module. All failures fall back to the existing manual MFA wait loop.

**Tech Stack:** Microsoft Graph API (Mail), MSAL delegated auth (`Mail.Read.Shared`), Playwright (form fill)

**Spec:** `docs/superpowers/specs/2026-03-18-twn-auto-mfa-design.md`

**Note:** This project has no test suite. Steps focus on implementation and manual verification.

---

### Task 1: Add `Mail.Read.Shared` scope to config

**Files:**
- Modify: `config/app_config.example.json:11-14`

- [ ] **Step 1: Add the scope**

In `config/app_config.example.json`, add `"Mail.Read.Shared"` to the `scopes` array:

```json
"scopes": [
    "User.Read.All",
    "GroupMember.Read.All",
    "Group.Read.All",
    "Mail.Read.Shared"
]
```

- [ ] **Step 2: Commit**

```bash
git add config/app_config.example.json
git commit -m "feat: add Mail.Read.Shared scope for auto-MFA email reading"
```

---

### Task 2: Add `extra_headers` support to `_make_request()` and add `read_recent_emails()`

**Files:**
- Modify: `services/graph_api.py:63-116` (`_make_request` signature and body)
- Modify: `services/graph_api.py` (add new method after `get_user_groups`)

- [ ] **Step 1: Add `extra_headers` parameter to `_make_request()`**

In `services/graph_api.py`, update the `_make_request` method signature and body. Add `extra_headers: Dict = None` parameter and merge it into headers before the request:

```python
def _make_request(self, method: str, endpoint: str, params: Dict = None, extra_headers: Dict = None) -> Dict:
```

Add the merge right after the existing `ConsistencyLevel` handling (after line 84):

```python
        # Merge any extra headers (e.g., Prefer for mail content type)
        if extra_headers:
            headers.update(extra_headers)
```

Leave the existing `ConsistencyLevel` hack untouched.

- [ ] **Step 2: Add `read_recent_emails()` method**

Add the following method to `GraphAPIClient` after `get_user_groups()` (after line 242):

```python
def read_recent_emails(self, mailbox: str, subject_filter: str = None,
                       since_timestamp: str = None, minutes_ago: int = 5) -> List[Dict]:
    """
    Read recent emails from a mailbox (requires Mail.Read.Shared and Full Access delegation).

    Args:
        mailbox: UPN of the mailbox to read (e.g., nexus@highlandsmortgage.com)
        subject_filter: Optional keyword to filter by subject (server-side)
        since_timestamp: ISO 8601 UTC timestamp floor (e.g., 2026-03-18T12:00:00Z).
                         If provided, overrides minutes_ago.
        minutes_ago: Fallback time window if since_timestamp not provided (default: 5)

    Returns:
        List of message dicts, or empty list on any error
    """
    from datetime import datetime, timedelta, timezone

    logger.info(f"Reading recent emails from {mailbox}")

    # Build receivedDateTime filter
    if since_timestamp:
        time_filter = f"receivedDateTime ge {since_timestamp}"
    else:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
        time_filter = f"receivedDateTime ge {cutoff.strftime('%Y-%m-%dT%H:%M:%SZ')}"

    # Build full OData filter
    odata_filter = time_filter
    if subject_filter:
        safe_subject = subject_filter.replace("'", "''")
        odata_filter += f" and contains(subject,'{safe_subject}')"

    params = {
        "$filter": odata_filter,
        "$orderby": "receivedDateTime desc",
        "$top": 5,
        "$select": "id,subject,body,from,receivedDateTime,isRead"
    }

    extra_headers = {
        "Prefer": 'outlook.body-content-type="text"'
    }

    try:
        response = self._make_request(
            "GET", f"/users/{mailbox}/messages",
            params=params, extra_headers=extra_headers
        )
        messages = response.get("value", [])
        logger.info(f"Found {len(messages)} recent email(s) in {mailbox}")
        return messages

    except GraphAPIError as e:
        if "403" in str(e) or "Insufficient permissions" in str(e):
            logger.warning(f"Cannot read mailbox {mailbox}: {e}. "
                          f"Ensure Mail.Read.Shared is consented and Full Access is granted.")
        else:
            logger.warning(f"Failed to read emails from {mailbox}: {e}")
        return []

    except Exception as e:
        logger.warning(f"Unexpected error reading emails from {mailbox}: {e}")
        return []
```

- [ ] **Step 3: Add List and Dict imports if missing**

Check the top of `services/graph_api.py`. `List` and `Dict` are already imported from `typing` (line 3). No change needed.

- [ ] **Step 4: Commit**

```bash
git add services/graph_api.py
git commit -m "feat: add read_recent_emails() to GraphAPIClient for auto-MFA"
```

---

### Task 3: Plumb `graph_client` from MainWindow through to TWN automation

**Files:**
- Modify: `gui/tab_automation.py:589-594` (`AutomationStatusTab.__init__` signature)
- Modify: `gui/main_window.py:191-195` (`AutomationStatusTab` instantiation)
- Modify: `automation/vendors/theworknumber.py:1350-1391` (`provision_user` and `TheWorkNumberAutomation.__init__`)

- [ ] **Step 1: Add `graph_client` to `AutomationStatusTab.__init__()`**

In `gui/tab_automation.py`, update the `__init__` signature (line 589-594) to accept `graph_client`:

```python
def __init__(
    self,
    parent: ctk.CTkFrame,
    config_manager: ConfigManager,
    on_view_summary: Optional[Callable] = None,
    graph_client=None
):
    self.parent = parent
    self.config_manager = config_manager
    self.on_view_summary = on_view_summary
    self.graph_client = graph_client
```

- [ ] **Step 2: Pass `graph_client` from MainWindow**

In `gui/main_window.py`, update the `AutomationStatusTab` instantiation (line 191-195):

```python
self.tab_automation = AutomationStatusTab(
    parent=self.tabview.tab("Automation Status"),
    config_manager=self.config_manager,
    on_view_summary=self._on_view_summary,
    graph_client=self.graph_client
)
```

- [ ] **Step 3: Add `graph_client` parameter to `TheWorkNumberAutomation.__init__()`**

In `automation/vendors/theworknumber.py`, update `__init__` (line 27-42) to accept and store `graph_client`:

```python
def __init__(self, config_path: str, keyvault: KeyVaultService, graph_client=None):
    self.config_path = Path(config_path)
    self.keyvault = keyvault
    self.graph_client = graph_client
    self.config = self._load_config()
    # ... rest unchanged
```

- [ ] **Step 4: Add `graph_client` parameter to `provision_user()`**

In `automation/vendors/theworknumber.py`, update `provision_user()` (line 1350-1391):

```python
async def provision_user(
    user: EntraUser,
    config_path: str,
    api_key: Optional[str] = None,
    graph_client=None,
    on_username_conflict: Optional[Callable[[str, str], Awaitable[Optional[str]]]] = None,
    on_email_conflict: Optional[Callable[[str, str, str], Awaitable[Optional[Dict[str, str]]]]] = None
) -> Dict[str, Any]:
```

And pass it through to the automation instance (line 1380):

```python
automation = TheWorkNumberAutomation(config_path, keyvault, graph_client=graph_client)
```

- [ ] **Step 5: Pass `graph_client` in `_run_theworknumber_automation()`**

In `gui/tab_automation.py`, update the `provision_user()` call in `_run_theworknumber_automation()` (line 1645-1651):

```python
result = await provision_user(
    self.current_user,
    str(config_path),
    api_key=None,
    graph_client=self.graph_client,
    on_username_conflict=handle_username_conflict,
    on_email_conflict=handle_email_conflict
)
```

- [ ] **Step 6: Commit**

```bash
git add gui/tab_automation.py gui/main_window.py automation/vendors/theworknumber.py
git commit -m "feat: plumb graph_client from MainWindow to TWN automation"
```

---

### Task 4: Implement `_auto_enter_mfa_code()` and integrate into `_handle_mfa()`

**Files:**
- Modify: `automation/vendors/theworknumber.py:516-733` (add new method, modify `_handle_mfa`)

- [ ] **Step 1: Add `_auto_enter_mfa_code()` method**

Add this method to `TheWorkNumberAutomation` class, before `_handle_mfa()` (before line 516):

```python
async def _auto_enter_mfa_code(self) -> bool:
    """
    Attempt to automatically read OTP from nexus@ inbox and enter it.
    Returns True on success, False on any failure (caller falls back to manual).
    """
    if not self.graph_client:
        logger.info("No graph_client available - skipping auto MFA entry")
        return False

    from datetime import datetime, timezone
    import re

    mailbox = "nexus@highlandsmortgage.com"
    send_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    logger.info(f"Attempting auto MFA code entry from {mailbox}")

    # Initial delay - give the email time to arrive
    await asyncio.sleep(10)

    # Poll for OTP email (every 10s, up to 2 minutes)
    max_attempts = 12
    for attempt in range(max_attempts):
        logger.info(f"Polling inbox for OTP email (attempt {attempt + 1}/{max_attempts})...")

        messages = self.graph_client.read_recent_emails(
            mailbox=mailbox,
            since_timestamp=send_time
        )

        # Client-side filter: look for emails from Equifax
        for msg in messages:
            sender = msg.get('from', {}).get('emailAddress', {}).get('address', '').lower()
            subject = (msg.get('subject') or '').lower()

            if 'equifax' not in sender and 'equifax' not in subject:
                continue

            # Extract 6-digit OTP from plain text body
            body_text = msg.get('body', {}).get('content', '')
            otp_match = re.search(r'\b(\d{6})\b', body_text)

            if not otp_match:
                logger.info(f"Found Equifax email but no 6-digit code. Subject: {msg.get('subject')}")
                continue

            otp_code = otp_match.group(1)
            logger.info(f"Extracted OTP code: {otp_code}")

            # Find the code input field in the iframe
            code_entered = False
            code_selectors = [
                'input[type="text"]',
                'input[name*="code"]',
                'input[id*="code"]',
                'input[name*="otp"]',
                'input[id*="otp"]',
                'input.form-control[type="text"]',
            ]

            for frame in self.page.frames:
                if code_entered:
                    break
                try:
                    for selector in code_selectors:
                        try:
                            element = await frame.query_selector(selector)
                            if element and await element.is_visible():
                                await element.fill(otp_code)
                                code_entered = True
                                logger.info(f"Entered OTP code using selector: {selector}")
                                break
                        except:
                            continue
                except:
                    continue

            if not code_entered:
                logger.warning("Found OTP code but could not find input field")
                return False

            await asyncio.sleep(1)
            await safe_screenshot(self.page, 'theworknumber_mfa_auto_code_entered.png')

            # Click Submit/Verify/Continue
            submit_clicked = False
            submit_selectors = [
                'input[value*="Verify"]',
                'button:has-text("Verify")',
                'input[value*="Submit"]',
                'button:has-text("Submit")',
                'input[value*="Continue"]',
                'button:has-text("Continue")',
            ]

            for frame in self.page.frames:
                if submit_clicked:
                    break
                try:
                    for selector in submit_selectors:
                        try:
                            btn = await frame.query_selector(selector)
                            if btn and await btn.is_visible():
                                await btn.click()
                                submit_clicked = True
                                logger.info(f"Clicked submit using selector: {selector}")
                                break
                        except:
                            continue
                except:
                    continue

            if not submit_clicked:
                logger.warning("Entered OTP but could not find submit button")
                return False

            await asyncio.sleep(3)
            await safe_screenshot(self.page, 'theworknumber_mfa_auto_submitted.png')

            logger.info("Auto MFA code entry completed successfully")
            return True

        # No matching email yet - wait and retry
        if attempt < max_attempts - 1:
            logger.info("OTP email not found yet, waiting 10s...")
            await asyncio.sleep(10)

    logger.warning(f"OTP email not found after {max_attempts} attempts - falling back to manual")
    return False
```

- [ ] **Step 2: Modify `_handle_mfa()` to try auto-entry first**

In the `_handle_mfa()` method, after the "Send code" button click section (after line 633, where `await asyncio.sleep(2)` follows the send code click), insert the auto-entry attempt before the manual wait loop:

```python
            await asyncio.sleep(2)

            # Try automatic OTP entry first
            auto_success = await self._auto_enter_mfa_code()

            if auto_success:
                # Verify MFA completion with dashboard check
                await asyncio.sleep(3)
                # Check if we reached the dashboard
                dashboard_keywords = ["New Order", "Order History", "User Management", "Verifiers", "Administration"]
                found_keyword = None
                try:
                    page_content = await self.page.content()
                    for keyword in dashboard_keywords:
                        if keyword in page_content:
                            found_keyword = keyword
                            break
                except:
                    pass
                if not found_keyword:
                    for frame in self.page.frames:
                        try:
                            frame_content = await frame.content()
                            for keyword in dashboard_keywords:
                                if keyword in frame_content:
                                    found_keyword = keyword
                                    break
                            if found_keyword:
                                break
                        except:
                            continue
                if not found_keyword:
                    current_url = self.page.url
                    if 'vsportal' in current_url or 'dashboard' in current_url or 'home' in current_url:
                        found_keyword = f"URL: {current_url}"

                if found_keyword:
                    logger.info(f"Auto MFA completed - detected: {found_keyword}")
                    await safe_screenshot(self.page, 'theworknumber_mfa_auto_complete.png')
                    return

                logger.warning("Auto MFA code submitted but dashboard not detected - falling back to manual wait")

            # Fall back to manual wait loop (existing code below)
```

This goes right before the existing `# Take screenshot after clicking email` line (line 636). The existing manual wait loop (lines 636-728) remains as-is as the fallback.

- [ ] **Step 3: Commit**

```bash
git add automation/vendors/theworknumber.py
git commit -m "feat: auto-enter MFA OTP code from nexus@ inbox for TheWorkNumber"
```

---

### Task 5: Verify and test

- [ ] **Step 1: Syntax check**

```bash
python -c "import py_compile; py_compile.compile('services/graph_api.py', doraise=True)"
python -c "import py_compile; py_compile.compile('automation/vendors/theworknumber.py', doraise=True)"
python -c "import py_compile; py_compile.compile('gui/tab_automation.py', doraise=True)"
python -c "import py_compile; py_compile.compile('gui/main_window.py', doraise=True)"
```

Expected: All compile without errors.

- [ ] **Step 2: Import check**

```bash
python -c "from services.graph_api import GraphAPIClient; print('graph_api OK')"
```

Expected: `graph_api OK`

- [ ] **Step 3: Manual end-to-end test**

Run the full app and test the TWN automation:
1. `python main.py`
2. Sign in (will prompt for `Mail.Read.Shared` consent on first use)
3. Search for a test user, select TheWorkNumber
4. Start automation
5. Observe: after login, MFA page should appear, automation should auto-read OTP from nexus@ inbox and enter it
6. Check logs at `%APPDATA%\Nexus\logs\` for the auto-entry log messages

- [ ] **Step 4: Commit final state**

```bash
git add -A
git commit -m "feat: complete auto-MFA OTP entry for TheWorkNumber (Issue #7)"
```
