# TheWorkNumber Auto-MFA OTP Entry

## Problem

TheWorkNumber login requires a one-time passcode (OTP) sent via email. The current automation clicks "Send code" and then waits up to 5 minutes for the operator to manually check their email, find the code, and enter it. This is error-prone — the OTP often goes unnoticed, causing the automation to time out.

## Solution

Automate the OTP entry by reading the code from the `nexus@highlandsmortgage.com` inbox via Microsoft Graph API, then filling it into the MFA form automatically.

## Prerequisites (Manual — Completed)

1. **Entra App Registration**: Add `Mail.Read.Shared` delegated permission, admin consent granted
2. **Exchange Admin Center**: Grant Full Access on `nexus@highlandsmortgage.com` mailbox to Nexus operator accounts
3. **TheWorkNumber MFA config**: Updated to send OTP codes to `nexus@highlandsmortgage.com`
4. **Confirm UPN**: `nexus@highlandsmortgage.com` must be the mailbox's actual UPN (not just an SMTP alias), since Graph API resolves mailboxes by UPN or object ID

## Design

### Component 1: Config — `app_config.json`

Add `Mail.Read.Shared` to the Microsoft scopes array:

```json
"scopes": [
    "User.Read.All",
    "GroupMember.Read.All",
    "Group.Read.All",
    "Mail.Read.Shared"
]
```

Update `app_config.example.json` to match.

### Component 2: Graph API Mail Reader — `services/graph_api.py`

Add a new method to `GraphAPIClient`:

```python
def read_recent_emails(self, mailbox: str, subject_filter: str = None,
                       since_timestamp: str = None, minutes_ago: int = 5) -> List[Dict]:
```

**Behavior:**
- Calls `GET /users/{mailbox}/messages`
- Filters server-side by `receivedDateTime` using either `since_timestamp` (ISO 8601) or `minutes_ago` as fallback
- Optionally filters server-side by subject keyword using `$filter=contains(subject, '...')`
- Does NOT filter by `from` server-side (OData does not support `$filter` on `from` — it's a complex type). Sender filtering is done client-side by the caller.
- Passes `Prefer: outlook.body-content-type="text"` header to get plain text bodies (avoids HTML parsing)
- Orders by `receivedDateTime desc`, limits to 5 results
- Selects: `id`, `subject`, `body`, `from`, `receivedDateTime`, `isRead`
- Returns list of message dicts

**Error handling:**
- Wraps `_make_request()` in a try/except for `GraphAPIError` (unlike other methods which let exceptions propagate). This is intentional — mail reading is best-effort and must not crash the automation.
- 403 Forbidden: Logs that Full Access delegation or `Mail.Read.Shared` consent may be missing, returns empty list
- Other errors: Logs and returns empty list (caller handles fallback)

**Note on `_make_request()` enhancement:** Add an optional `extra_headers` parameter to `_make_request()` to support the `Prefer` header. This is a minimal change — just merge extra headers into the existing headers dict.

### Component 3: MFA Auto-Entry — `automation/vendors/theworknumber.py`

Replace the manual MFA wait loop in `_handle_mfa()` with an auto-entry flow:

**New method: `_auto_enter_mfa_code() -> bool`**

1. Record `send_code_timestamp` (UTC ISO 8601) at the moment "Send code" is clicked
2. Wait 10 seconds initial delay (give email time to arrive)
3. Poll `nexus@highlandsmortgage.com` inbox every 10 seconds, up to 2 minutes total
4. On each poll, call `graph_client.read_recent_emails()` with `since_timestamp=send_code_timestamp`
5. Client-side filter: check sender address contains "equifax" (case-insensitive)
6. Extract OTP from plain text email body via regex: `r'\b(\d{6})\b'` (6-digit code — TWN uses 6-digit OTP). If multiple matches, take the first standalone 6-digit number.
7. Find the code input field in the browser iframe (`input[type="text"]`, `input[name*="code"]`, `input[id*="code"]`, `input.form-control`)
8. Fill the code and click Submit/Verify/Continue
9. Verify MFA completion using existing dashboard detection logic
10. Return `True` on success, `False` on any failure

**Fallback:** If `_auto_enter_mfa_code()` returns `False` for any reason (no Graph client, permission error, no email found, can't extract code, can't find input field), `_handle_mfa()` falls back to the existing manual wait loop. The operator can still enter the code themselves.

**Flow:**

```
MFA detected
  -> Click email option (existing)
  -> Click "Send code" (existing)
  -> Record send_code_timestamp
  -> Try _auto_enter_mfa_code()
    -> Success (True)? -> Continue to dashboard
    -> Failure (False)? -> Fall back to manual wait loop (existing)
```

### Plumbing: Pass Graph Client to TWN Automation

The `GraphAPIClient` needs to reach `_handle_mfa()`. The plumbing path:

1. **`gui/main_window.py`**: `self.graph_client` exists on `MainWindow` (line 111)
2. **`gui/tab_automation.py`**: `AutomationStatusTab.__init__()` does NOT currently receive `graph_client`. Add it as a new parameter, passed from `MainWindow._create_tabs()`.
3. **`automation/vendors/theworknumber.py`**: `provision_user()` accepts an optional `graph_client` parameter. `TheWorkNumberAutomation.__init__()` stores it. `_handle_mfa()` uses it if available.

This keeps the change backward-compatible — if no graph client is passed, the manual flow still works.

## Error Handling Summary

| Failure | Behavior |
|---|---|
| `Mail.Read.Shared` not consented | Graph returns 403 -> fall back to manual |
| No Full Access on mailbox | Graph returns 403 -> fall back to manual |
| No graph_client passed | Skip auto-entry -> fall back to manual |
| OTP email not found within 2 min | Timeout -> fall back to manual |
| Regex can't extract code | Log email subject for debugging -> fall back to manual |
| Code input field not found | Log selectors tried -> fall back to manual |
| Code rejected by TWN | Log error -> fall back to manual |

Every failure path lands on the existing manual wait loop. No new failure modes that would break automation.

## Files Changed

1. `config/app_config.example.json` — add `Mail.Read.Shared` scope
2. `services/graph_api.py` — add `read_recent_emails()` method, add `extra_headers` support to `_make_request()`
3. `automation/vendors/theworknumber.py` — add `_auto_enter_mfa_code()`, modify `_handle_mfa()` to try auto-entry first, add `graph_client` parameter to init and `provision_user()`
4. `gui/tab_automation.py` — accept `graph_client` in `__init__()`, pass it when calling TWN `provision_user()`
5. `gui/main_window.py` — pass `graph_client` to `AutomationStatusTab`

## Out of Scope

- Reading OTP for other vendors (can reuse `read_recent_emails()` later if needed)
- Application-level permissions (staying with delegated + mailbox delegation)
- Marking OTP emails as read (would require `Mail.ReadWrite.Shared` — not worth the scope expansion)
- Migrating the admin account credentials in Key Vault (Issue #8 — separate task)
