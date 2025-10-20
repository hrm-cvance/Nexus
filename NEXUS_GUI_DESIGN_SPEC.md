# Nexus GUI Design Specification

**Version:** 1.0
**Last Updated:** 2025-10-15
**Application Name:** Nexus - Automated Vendor Account Provisioning
**Technology Stack:** Python, CustomTkinter/PyQt6, Playwright, Microsoft Graph API

---

## Table of Contents
1. [Overview](#overview)
2. [User Workflow](#user-workflow)
3. [Tab Structure](#tab-structure)
4. [Detailed Component Specifications](#detailed-component-specifications)
5. [Data Flow Architecture](#data-flow-architecture)
6. [Technical Architecture](#technical-architecture)
7. [Security Considerations](#security-considerations)
8. [Future Enhancements](#future-enhancements)

---

## 1. Overview

### 1.1 Purpose
Nexus is a GUI application that automates the creation of vendor accounts by:
- Connecting to Microsoft Entra ID via Graph API
- Searching for users and retrieving their attributes
- Auto-detecting which vendor accounts are needed based on Entra ID group membership
- Collecting vendor-specific configuration from the technician
- Automating account creation using Playwright browser automation
- Providing real-time status monitoring and error handling

### 1.2 Target Users
- IT Support Technicians
- Help Desk Staff
- Identity & Access Management Teams

### 1.3 Key Benefits
- **Reduces manual effort** from 5-10 minutes per vendor to seconds
- **Eliminates human error** in data entry
- **Ensures consistency** across vendor accounts
- **Provides audit trail** of all account creations
- **Scalable** to any number of vendors

---

## 2. User Workflow

### 2.1 High-Level Workflow
```
┌─────────────────────────────────────────────────────────────────┐
│                    NEXUS USER WORKFLOW                          │
└─────────────────────────────────────────────────────────────────┘

1. Launch Application
   ↓
2. Sign In to Microsoft (Delegated Authentication)
   │  • Interactive browser sign-in
   │  • User consents to permissions (first time only)
   │  • Single token works for both Graph API and Key Vault
   ↓
3. Search for User (by name, email, employee ID, etc.)
   │  • Queries Microsoft Graph API using user's token
   ↓
4. View User Summary (photo, attributes, group memberships)
   ↓
5. Review Auto-Detected Vendor Accounts
   │  • Based on Entra ID group membership
   │  • Pre-checked boxes for detected vendors
   │  • App retrieves credentials from Azure Key Vault
   ↓
6. Configure Vendor-Specific Fields
   │  • Adjust dropdowns, text fields, radio buttons
   │  • Validate all required fields
   ↓
7. Start Automation
   │  • Vendor credentials fetched from Key Vault in real-time
   ↓
8. Monitor Real-Time Progress
   │  • Color-coded status indicators
   │  • Live logs and screenshots
   ↓
9. Review Results
   │  • Success/Error summary
   │  • Export report
   │  • Retry failed vendors if needed
```

### 2.2 Detailed Step-by-Step Flow

#### Step 1: Application Launch
- App opens to **Tab 1: User Search**
- Microsoft sign-in button is **prominently displayed** at top
- Status indicator shows "Not Connected"

#### Step 2: Authentication
- User clicks "Sign In with Microsoft"
- Browser window opens for Microsoft authentication (OAuth 2.0 - Delegated Permissions)
- User authenticates with their corporate account (@highlandsmortgage.com or @company.com)
- User consents to permissions (first time only):
  - Read user profiles (User.Read.All)
  - Read group memberships (GroupMember.Read.All)
  - Read groups (Group.Read.All)
- App receives access token that works for:
  - Microsoft Graph API queries
  - Azure Key Vault secret retrieval
- Status changes to "Connected as: [user@domain.com]"
- **No client secrets used** - all authentication is interactive

#### Step 3: User Search
- Search bar becomes active after authentication
- User can search by:
  - First Name
  - Last Name
  - Email Address
  - Display Name
  - Employee ID (extensionAttribute2)
- Search is performed via Graph API
- Results displayed in table (if multiple matches)

#### Step 4: User Selection & Summary
- User selects target user from results (or auto-selected if single match)
- App switches to **Tab 2: Account Provisioning**
- User summary panel shows:
  - Profile photo
  - Full name, job title, department
  - Email address
  - Office location
  - Employee ID
  - **Group Memberships** (expandable list)

#### Step 5: Vendor Auto-Detection
- App queries user's Entra ID group memberships
- Compares against vendor mapping configuration
- Example: User is member of `AccountChek_Users` → AccountChek vendor is auto-selected
- Vendor cards display with checkboxes pre-checked for detected vendors

#### Step 6: Vendor Configuration
- Tech reviews each selected vendor
- Clicks "Expand" on vendor card to see configuration fields
- Fields are pre-populated from Entra ID where possible
- Tech adjusts vendor-specific fields (Region, Branch, etc.)
- Validation indicators show if required fields are missing

#### Step 7: Execution
- Tech clicks "Start Automation" button
- App validates all fields before starting
- **App retrieves vendor credentials from Azure Key Vault** using user's token
- If validation passes, switches to **Tab 3: Automation Status**
- Playwright automation begins for each vendor sequentially
- Credentials used directly (never stored locally)

#### Step 8: Monitoring
- Each vendor shows real-time status:
  - 🔴 Red: Not Started
  - 🟡 Yellow: In Progress
  - 🟢 Green: Success
  - 🟠 Orange: Error
- Progress bars update (0-100%)
- Log panel shows live activity
- Screenshots update as Playwright navigates

#### Step 9: Completion
- Summary shows results for all vendors
- Export report button generates PDF/CSV
- Option to retry failed vendors
- Option to search for another user

---

## 3. Tab Structure

### Tab 1: User Search 🔍

**Purpose:** Authenticate and search for users in Entra ID

**Layout:**
```
┌────────────────────────────────────────────────────────────────┐
│  NEXUS - Vendor Account Provisioning                          │
├────────────────────────────────────────────────────────────────┤
│  [Tab: User Search] [Tab: Account Provisioning] [Tab: Status] │
│                                                        [Settings]│
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Microsoft Sign-In                                        │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  Status: ⚫ Not Connected                          │  │ │
│  │  │                                                     │  │ │
│  │  │  [🔑 Sign In with Microsoft]                       │  │ │
│  │  │                                                     │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  User Search                                              │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  Search By:  [Dropdown: Email ▼]                  │  │ │
│  │  │  ┌──────────────────────────────────────────────┐  │  │ │
│  │  │  │  john.doe@company.com              [🔍 Search]│  │  │ │
│  │  │  └──────────────────────────────────────────────┘  │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  │                                                            │ │
│  │  Search Results:                                          │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  Name              Email                Department  │  │ │
│  │  │  ─────────────────────────────────────────────────  │  │ │
│  │  │  John Doe          john.doe@...         IT         │  │ │
│  │  │  Jane Doe          jane.doe@...         Sales      │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  │                                                            │ │
│  │                            [Select User →]                │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Components:**

1. **Microsoft Sign-In Panel**
   - Status Indicator: Shows connection status (⚫ Not Connected, 🟢 Connected as: user@domain.com)
   - Sign In Button: Large, prominent button for Microsoft authentication
   - Sign Out Button: Appears after successful authentication

2. **User Search Panel** (Disabled until authenticated)
   - Search Type Dropdown: Email, First Name, Last Name, Display Name, Employee ID
   - Search Input Field: Text field for search query
   - Search Button: Triggers Graph API search
   - Clear Button: Clears search results

3. **Search Results Table**
   - Columns: Photo (thumbnail), Name, Email, Department, Job Title
   - Sortable columns
   - Click row to select user
   - Shows "No results found" if empty

4. **Action Buttons**
   - "Select User" button (enabled when user is selected)
   - Advances to Tab 2

---

### Tab 2: Account Provisioning ⚙️

**Purpose:** Display user summary, auto-detect vendors, configure vendor-specific fields

**Layout:**
```
┌────────────────────────────────────────────────────────────────┐
│  NEXUS - Vendor Account Provisioning                          │
├────────────────────────────────────────────────────────────────┤
│  [Tab: User Search] [Tab: Account Provisioning*] [Tab: Status]│
│                                                        [Settings]│
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  User Information                                         │ │
│  │  ┌────┐  John Doe                                        │ │
│  │  │ 📷 │  Loan Officer - Corporate                        │ │
│  │  └────┘  john.doe@highlandsmortgage.com                  │ │
│  │          Employee ID: 12345                               │ │
│  │          Office: Eckert Division                          │ │
│  │          ▼ Show Groups (5)                                │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Vendor Accounts to Create                                │ │
│  │                                                            │ │
│  │  ┌─────────────────────────┐  ┌─────────────────────────┐│ │
│  │  │ ✅ AccountChek          │  │ ⬜ VendorXYZ            ││ │
│  │  │ 🔴 Not Started          │  │ 🔴 Not Started          ││ │
│  │  │ Auto-detected           │  │ Manual Selection        ││ │
│  │  │ [▼ Configure]           │  │ [▼ Configure]           ││ │
│  │  └─────────────────────────┘  └─────────────────────────┘│ │
│  │                                                            │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │ AccountChek Configuration                            │ │ │
│  │  │                                                       │ │ │
│  │  │  Role:          User (Standard)  [Read-only]        │ │ │
│  │  │  Region:        [Corporate ▼]    ✅                  │ │ │
│  │  │  Branch:        [1200 - Eckert ▼] ✅                │ │ │
│  │  │  Password:      [Auto-generate]  ✅                  │ │ │
│  │  │  Must Change:   [✓] Yes                              │ │ │
│  │  │                                                       │ │ │
│  │  │  [Test Connection]        [Reset to Defaults]       │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │                                                            │ │
│  │  [← Back to Search]          [Start Automation →]        │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Components:**

1. **User Information Panel**
   - Profile Photo: Retrieved from Entra ID
   - Display Name: Bold, large font
   - Job Title & Department: Subtitle
   - Email, Employee ID, Office Location
   - Expandable Group Memberships: Collapsible list showing all Entra groups

2. **Vendor Selection Grid**
   - Card-based layout (2-3 cards per row)
   - Each card shows:
     - Checkbox (✅ checked if auto-detected, ⬜ unchecked if manual)
     - Vendor name and logo
     - Status indicator (🔴 Red = Not Started, 🟡 Yellow = In Progress, 🟢 Green = Success, 🟠 Orange = Error)
     - "Auto-detected" or "Manual Selection" badge
     - "Configure" expand/collapse button

3. **Vendor Configuration Panel** (Appears when expanded)
   - Dynamically generated based on vendor requirements
   - Pre-populated fields from Entra ID
   - Validation indicators (✅ valid, ❌ invalid/required)
   - Field types:
     - Text inputs
     - Dropdowns
     - Radio buttons
     - Checkboxes
     - Read-only fields (grayed out)
   - "Test Connection" button (validates vendor credentials)
   - "Reset to Defaults" button

4. **Action Buttons**
   - "Back to Search" - Return to Tab 1
   - "Start Automation" - Begin account creation (validates first, then switches to Tab 3)

---

### Tab 3: Automation Status 📊

**Purpose:** Real-time monitoring of account creation progress

**Layout:**
```
┌────────────────────────────────────────────────────────────────┐
│  NEXUS - Vendor Account Provisioning                          │
├────────────────────────────────────────────────────────────────┤
│  [Tab: User Search] [Tab: Account Provisioning] [Tab: Status*]│
│                                                        [Settings]│
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Creating accounts for: John Doe (john.doe@company.com)       │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Vendor Progress                                          │ │
│  │                                                            │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  🟢 AccountChek                                     │  │ │
│  │  │  ████████████████████████████████████████  100%    │  │ │
│  │  │  Status: Account created successfully               │  │ │
│  │  │  Time: 12.3 seconds                                 │  │ │
│  │  │  [View Log] [View Screenshot]                       │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  │                                                            │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  🟡 VendorXYZ                                       │  │ │
│  │  │  ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░  45%    │  │ │
│  │  │  Status: Filling user form...                       │  │ │
│  │  │  Time: 4.7 seconds elapsed                          │  │ │
│  │  │  [View Log] [View Screenshot]                       │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  │                                                            │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  🟠 VendorABC                                       │  │ │
│  │  │  ████████████████████████░░░░░░░░░░░░░░░░░  60%    │  │ │
│  │  │  Status: ERROR - Email already exists               │  │ │
│  │  │  Time: 8.1 seconds                                  │  │ │
│  │  │  [View Log] [View Screenshot] [Retry]               │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Live Activity Log                        [▼ Collapse]   │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  [10:23:45] Starting AccountChek automation         │  │ │
│  │  │  [10:23:46] Navigating to login page                │  │ │
│  │  │  [10:23:48] Logged in successfully                  │  │ │
│  │  │  [10:23:50] Clicking 'New User' button              │  │ │
│  │  │  [10:23:52] Filling form fields...                  │  │ │
│  │  │  [10:23:55] Account created: john.doe@company.com   │  │ │
│  │  │  [10:23:55] ✅ AccountChek completed                │  │ │
│  │  │  [10:23:56] Starting VendorXYZ automation           │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  [Pause] [Cancel All]      [Export Report] [New User Search] │
└────────────────────────────────────────────────────────────────┘
```

**Components:**

1. **User Context Header**
   - Shows which user accounts are being created for
   - Quick reference to avoid confusion

2. **Vendor Progress Cards**
   - One card per vendor being processed
   - Color-coded status indicator (🔴🟡🟢🟠)
   - Vendor name
   - Progress bar (0-100%)
   - Current status message
   - Elapsed time
   - Action buttons:
     - "View Log" - Opens detailed log for this vendor
     - "View Screenshot" - Shows latest Playwright screenshot
     - "Retry" - Appears only for failed vendors (orange)

3. **Live Activity Log Panel**
   - Collapsible/expandable
   - Auto-scrolls to bottom as new entries appear
   - Timestamp for each entry
   - Color-coded messages:
     - ⚪ Info (black text)
     - 🟡 Warning (yellow text)
     - 🔴 Error (red text)
     - 🟢 Success (green text)
   - Search/filter functionality
   - Copy log button
   - Save log to file button

4. **Control Buttons**
   - "Pause" - Pause automation (current vendor finishes, then stops)
   - "Cancel All" - Stop all automation immediately
   - "Export Report" - Generate summary report (PDF/CSV)
   - "New User Search" - Return to Tab 1 for another user

5. **Screenshot Viewer Modal** (Opens when "View Screenshot" clicked)
   - Full-size screenshot from Playwright
   - Navigation arrows (previous/next screenshot)
   - Timestamp
   - Close button

---

### Tab 4: Settings ⚙️

**Purpose:** Configure application settings, vendor mappings, view connection status

**Layout:**
```
┌────────────────────────────────────────────────────────────────┐
│  NEXUS - Vendor Account Provisioning                          │
├────────────────────────────────────────────────────────────────┤
│  [Tab: User Search] [Tab: Account Provisioning] [Tab: Status] │
│                                                      [Settings*]│
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Microsoft Configuration (Read-Only)                      │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  Tenant ID:      xxxxxxxx-xxxx-xxxx-xxxx   🔒      │  │ │
│  │  │  Client ID:      yyyyyyyy-yyyy-yyyy-yyyy   🔒      │  │ │
│  │  │  Auth Type:      Delegated (Interactive)   🔒      │  │ │
│  │  │                                                     │  │ │
│  │  │  Status: 🟢 Connected as: user@company.com         │  │ │
│  │  │                                                     │  │ │
│  │  │  [Test Graph API Connection]                       │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Azure Key Vault Configuration (Read-Only)                │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  Vault URL:      https://nexus-creds.vault...  🔒 │  │ │
│  │  │                                                     │  │ │
│  │  │  Status: 🟢 Connected (Read access)                │  │ │
│  │  │                                                     │  │ │
│  │  │  Available Vendors:                                │  │ │
│  │  │    ✅ AccountChek                                  │  │ │
│  │  │    ✅ VendorXYZ                                    │  │ │
│  │  │                                                     │  │ │
│  │  │  [Test Key Vault Connection]                       │  │ │
│  │  │                                                     │  │ │
│  │  │  ⓘ Credentials managed centrally by IT team       │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Group-to-Vendor Mappings                                 │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  Entra Group Name       → Vendor                   │  │ │
│  │  │  ──────────────────────────────────────────────    │  │ │
│  │  │  AccountChek_Users      → AccountChek    [Edit]    │  │ │
│  │  │  VendorXYZ_Users        → VendorXYZ      [Edit]    │  │ │
│  │  │                                                     │  │ │
│  │  │  [+ Add Mapping]                                   │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Application Settings                                     │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  [✓] Show screenshots during automation            │  │ │
│  │  │  [✓] Auto-scroll logs                               │  │ │
│  │  │  [✓] Save logs to file                              │  │ │
│  │  │  [ ] Headless mode (no visible browser)            │  │ │
│  │  │                                                     │  │ │
│  │  │  Log Level:     [Info ▼]                           │  │ │
│  │  │  Timeout (sec): [120]                               │  │ │
│  │  │                                                     │  │ │
│  │  │  [Save Settings]                                   │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Components:**

1. **Microsoft Configuration Panel (Read-Only)**
   - Displays Tenant ID and Client ID (locked - from app_config.json)
   - Shows authentication type (Delegated)
   - Current connection status (Connected as: [user])
   - Test Connection button (validates Graph API access)
   - ⓘ Info note: "Configuration managed in app_config.json"

2. **Azure Key Vault Configuration Panel (Read-Only)**
   - Displays Key Vault URL (locked - from app_config.json)
   - Shows connection status
   - Lists available vendors detected in Key Vault
   - Test Connection button (validates Key Vault access and lists secrets)
   - ⓘ Info note: "Vendor credentials managed centrally by IT team"
   - **No password fields** - credentials only in Key Vault

3. **Group-to-Vendor Mappings** (Editable)
   - Table showing Entra ID group → Vendor mappings
   - Edit button opens mapping editor dialog
   - Add Mapping button
   - Delete mapping option
   - Changes saved to vendor_mappings.json in AppData
   - **Note:** Mappings are embedded in EXE but can be customized per-user
   - Default mappings extracted on first run to AppData
   - User edits only affect their local installation

4. **Application Settings**
   - Checkboxes for various options
   - Log level dropdown
   - Timeout settings
   - Screenshot directory
   - Save Settings button

---

## 4. Detailed Component Specifications

### 4.1 Authentication Component

**Microsoft Sign-In Flow:**
1. User clicks "Sign In with Microsoft"
2. App opens system browser (or embedded webview)
3. User authenticates via Microsoft OAuth 2.0
4. Redirect URI returns authorization code
5. App exchanges code for access token
6. Token stored securely (encrypted, in-memory)
7. Token refresh handled automatically

**Required Permissions (Delegated):**
- `User.Read.All` - Read all users' profiles
- `GroupMember.Read.All` - Read group memberships
- `Group.Read.All` - Read groups
- `https://vault.azure.net/user_impersonation` - Access Azure Key Vault as the signed-in user

**Token Management:**
- Access tokens expire after 1 hour
- Refresh tokens valid for 90 days
- Automatic refresh before expiration
- Re-authentication prompt if refresh fails

### 4.2 Search Component

**Search Capabilities:**
```python
# Graph API Search Examples

# By Email
GET https://graph.microsoft.com/v1.0/users?$filter=mail eq 'john.doe@company.com'

# By Display Name
GET https://graph.microsoft.com/v1.0/users?$filter=startswith(displayName,'John Doe')

# By Employee ID (extensionAttribute2)
GET https://graph.microsoft.com/v1.0/users?$filter=extensionAttribute2 eq '12345'

# Select specific attributes
&$select=id,displayName,mail,jobTitle,department,officeLocation,extensionAttribute2
```

**Search Results Table Columns:**
- Thumbnail photo (32x32px)
- Display Name
- Email
- Job Title
- Department
- Office Location

**Interaction:**
- Single-click to select row (highlight)
- Double-click to proceed to next tab
- "Select User" button enabled when row selected

### 4.3 Vendor Cards Component

**Card States:**

1. **Not Started** (Default)
   - Border: Gray
   - Status: 🔴 Red circle
   - Checkbox: ✅ if auto-detected, ⬜ if manual

2. **In Progress**
   - Border: Yellow
   - Status: 🟡 Yellow circle + spinning animation
   - Progress bar appears below vendor name

3. **Success**
   - Border: Green
   - Status: 🟢 Green circle + checkmark
   - Shows completion time

4. **Error**
   - Border: Orange
   - Status: 🟠 Orange circle + warning icon
   - Shows error message
   - "Retry" button appears

**Card Layout:**
```
┌─────────────────────────┐
│ ✅ AccountChek          │
│ 🔴 Not Started          │
│ ─────────────────────── │
│ Auto-detected           │
│                         │
│ [▼ Configure]           │
└─────────────────────────┘
```

**Expanded Card:**
```
┌─────────────────────────────────────┐
│ ✅ AccountChek          [▲ Collapse]│
│ 🔴 Not Started                      │
│ ───────────────────────────────────  │
│ Auto-detected                        │
│                                      │
│ Configuration:                       │
│  Role:       User (Standard) 🔒     │
│  Region:     [Corporate ▼]    ✅    │
│  Branch:     [1200 - Eckert ▼] ✅   │
│  Password:   [Auto-generate]   ✅    │
│                                      │
│ [Test Connection] [Reset Defaults]  │
└─────────────────────────────────────┘
```

### 4.4 Configuration Fields Component

**Field Types:**

1. **Read-Only Field** (Role)
   - Grayed out background
   - Lock icon (🔒)
   - Tooltip: "This field is auto-assigned based on Entra group membership"

2. **Dropdown Field** (Region, Branch)
   - Pre-populated from Entra ID if possible
   - Options loaded from vendor configuration
   - Validation: Required field indicator (red border if empty)
   - Cascade behavior: Branch options depend on Region selection

3. **Text Input Field** (Password)
   - Auto-generate option (default)
   - Manual entry allowed
   - Password strength indicator
   - Show/hide toggle

4. **Checkbox Field** (Must Change Password)
   - Default: Checked
   - Label: "Require password change on first login"

**Validation States:**
- ✅ Green checkmark: Valid
- ❌ Red X: Invalid/required field empty
- ⚠️ Yellow warning: Optional but recommended

### 4.5 Progress & Status Component

**Status Indicators:**
```python
class VendorStatus(Enum):
    NOT_STARTED = "🔴"  # Red
    IN_PROGRESS = "🟡"  # Yellow
    SUCCESS = "🟢"      # Green
    ERROR = "🟠"        # Orange
    SKIPPED = "⚪"      # White/Gray
```

**Progress Bar:**
- Animated progress bar (0-100%)
- Color matches status:
  - Yellow during progress
  - Green when complete
  - Orange if error
- Shows percentage text

**Status Messages:**
- "Initializing browser..."
- "Navigating to login page..."
- "Authenticating..."
- "Opening new user form..."
- "Filling form fields..."
- "Submitting form..."
- "Verifying account creation..."
- "Account created successfully!"
- "ERROR: [specific error message]"

### 4.6 Activity Log Component

**Log Entry Format:**
```
[HH:MM:SS] [LEVEL] [VENDOR] Message
```

**Examples:**
```
[10:23:45] [INFO] [AccountChek] Starting automation
[10:23:46] [INFO] [AccountChek] Navigating to https://verifier.accountchek.com/login
[10:23:48] [INFO] [AccountChek] Login successful
[10:23:50] [INFO] [AccountChek] Clicked 'New User' button
[10:23:52] [INFO] [AccountChek] Filling form: First Name = John
[10:23:52] [INFO] [AccountChek] Filling form: Last Name = Doe
[10:23:55] [SUCCESS] [AccountChek] Account created: john.doe@company.com
[10:23:56] [INFO] [VendorXYZ] Starting automation
[10:24:10] [ERROR] [VendorXYZ] Email already exists in system
```

**Log Levels:**
- DEBUG (gray) - Detailed technical information
- INFO (black) - General information
- WARNING (yellow) - Potential issues
- ERROR (red) - Errors that stopped automation
- SUCCESS (green) - Successful completion

**Features:**
- Auto-scroll to bottom (toggle)
- Search/filter by vendor, level, keyword
- Copy to clipboard
- Export to file
- Clear log button

---

## 5. Data Flow Architecture

### 5.1 Overall Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         NEXUS DATA FLOW                         │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│   Nexus GUI  │ ◄──────── User Interaction
└──────┬───────┘
       │
       ├─► (1) Microsoft Authentication (Delegated)
       │       │
       │       ▼
       │   ┌────────────────────┐
       │   │  Microsoft Entra   │
       │   │  (Interactive Sign-In)│
       │   └────────────────────┘
       │       │
       │       └─► Returns Access Token
       │           (Works for both Graph API and Key Vault)
       │
       ├─► (2) User Search
       │       │
       │       ▼
       │   ┌────────────────────┐
       │   │  Microsoft Graph   │
       │   │  API (Entra ID)    │
       │   └────────────────────┘
       │       │
       │       ├─► User Search
       │       ├─► User Attributes
       │       └─► Group Memberships
       │
       ├─► (3) Vendor Detection
       │       │
       │       ▼
       │   ┌────────────────────┐
       │   │  Group Mapping     │
       │   │  Configuration     │
       │   └────────────────────┘
       │       │
       │       └─► Auto-select Vendors
       │
       ├─► (4) Field Population
       │       │
       │       ▼
       │   ┌────────────────────┐
       │   │  Vendor Config     │
       │   │  Templates         │
       │   └────────────────────┘
       │       │
       │       └─► Pre-fill Forms
       │
       ├─► (5) Retrieve Vendor Credentials
       │       │
       │       ▼
       │   ┌────────────────────┐
       │   │  Azure Key Vault   │
       │   │  (Vendor Passwords)│
       │   └────────────────────┘
       │       │
       │       └─► Credentials Retrieved
       │           (using same access token)
       │
       └─► (6) Automation Execution
               │
               ▼
           ┌────────────────────┐
           │    Playwright      │
           │    Automation      │
           └────────────────────┘
               │
               ├─► Login to Vendor (credentials from Key Vault)
               ├─► Navigate UI
               ├─► Fill Forms
               ├─► Submit
               └─► Verify
               │
               ▼
           ┌────────────────────┐
           │  Vendor Systems    │
           │  (AccountChek,     │
           │   VendorXYZ, etc.) │
           └────────────────────┘
               │
               └─► Account Created ✅
```

### 5.2 Authentication Flow (Delegated Permissions)

```
User                    Nexus GUI                    Microsoft Identity Platform
  │                         │                                    │
  ├──► Click "Sign In"      │                                    │
  │                         ├──► Open Browser with Auth URL ────►│
  │                         │    (PublicClientApplication)       │
  │                         │    NO CLIENT SECRET SENT           │
  │                         │                                    │
  │◄──── Browser Opens ─────┤                                    │
  │                         │                                    │
  ├──► Enter Credentials ────────────────────────────────────────►│
  │     (user@company.com)  │                                    │
  │                         │                                    │
  │◄──── MFA Challenge (if enabled) ─────────────────────────────┤
  │                         │                                    │
  ├──► Complete MFA ─────────────────────────────────────────────►│
  │                         │                                    │
  │◄──── Consent Screen ────────────────────────────────────────┤
  │     (First time only)   │                                    │
  │     - Read user profiles│                                    │
  │     - Read groups       │                                    │
  │                         │                                    │
  ├──► Accept ───────────────────────────────────────────────────►│
  │                         │                                    │
  │                         │◄──── Authorization Code ───────────┤
  │                         │                                    │
  │                         ├──── Exchange for Access Token ────►│
  │                         │                                    │
  │                         │◄──── Access Token + Refresh Token ─┤
  │                         │      (Delegated to user)           │
  │                         │                                    │
  │◄──── "Connected" Status ┤                                    │
  │     "Connected as:      │                                    │
  │      user@company.com"  │                                    │
  │                         │                                    │
  │                    [Token stored in memory]                  │
  │                    [Token works for BOTH:                    │
  │                     - Microsoft Graph API                    │
  │                     - Azure Key Vault]                       │
```

### 5.3 User Search Flow

```
User                    Nexus GUI                    Microsoft Graph API
  │                         │                                │
  ├──► Enter "john.doe"     │                                │
  ├──► Click "Search"       │                                │
  │                         ├──── GET /users?$filter=... ───►│
  │                         │                                │
  │                         │◄──── User Data (JSON) ─────────┤
  │                         │                                │
  │                    [Parse response]                      │
  │                    [Display in table]                    │
  │                         │                                │
  │◄──── Results shown ─────┤                                │
  │                         │                                │
  ├──► Click user row       │                                │
  │                         ├──── GET /users/{id} ──────────►│
  │                         ├──── GET /users/{id}/memberOf ─►│
  │                         │                                │
  │                         │◄──── Full User Data ───────────┤
  │                         │◄──── Group Memberships ────────┤
  │                         │                                │
  │                    [Load user details]                   │
  │                    [Detect vendors]                      │
  │                         │                                │
  │◄──── Switch to Tab 2 ───┤                                │
```

### 5.4 Vendor Auto-Detection Flow

```
Graph API Response          Nexus Logic                Vendor Cards
      │                         │                            │
      ├──► Group List           │                            │
      │    - AccountChek_Users  │                            │
      │    - VendorXYZ_Users    │                            │
      │    - Sales_Team         │                            │
      │                         │                            │
      │                    [Load mapping config]             │
      │                    {                                 │
      │                      "AccountChek_Users": "AccountChek",
      │                      "VendorXYZ_Users": "VendorXYZ"  │
      │                    }                                 │
      │                         │                            │
      │                    [Compare groups]                  │
      │                         │                            │
      │                         ├──► Match: AccountChek_Users
      │                         │    ├──► Check ✅ AccountChek card
      │                         │    └──► Load config template
      │                         │                            │
      │                         ├──► Match: VendorXYZ_Users  │
      │                         │    ├──► Check ✅ VendorXYZ card
      │                         │    └──► Load config template
      │                         │                            │
      │                         ├──► Display vendor cards ───►
```

### 5.5 Automation Execution Flow

```
User                  Nexus GUI              Playwright            Vendor Website
  │                       │                      │                       │
  ├──► Click "Start"      │                      │                       │
  │                       ├──── Validate Forms   │                       │
  │                       │                      │                       │
  │                  [Validation OK]             │                       │
  │                       │                      │                       │
  │                  [Switch to Tab 3]           │                       │
  │                       │                      │                       │
  │                  [For each vendor...]        │                       │
  │                       │                      │                       │
  │                       ├──── Launch Browser ─►│                       │
  │                       │                      ├──── Navigate ────────►│
  │                       │                      │                       │
  │◄──── Status: "Login"  │◄──── Screenshot ─────┤                       │
  │                       │                      │                       │
  │                       ├──── Fill Login ─────►│                       │
  │                       │                      ├──── Submit ──────────►│
  │                       │                      │                       │
  │                       │                      │◄──── Login Success ───┤
  │                       │                      │                       │
  │◄──── Progress: 25%    │◄──── Screenshot ─────┤                       │
  │                       │                      │                       │
  │                       ├──── Click "New User"►│                       │
  │                       │                      ├──── Click ───────────►│
  │                       │                      │                       │
  │                       │                      │◄──── Form Opens ──────┤
  │                       │                      │                       │
  │◄──── Progress: 50%    │◄──── Screenshot ─────┤                       │
  │                       │                      │                       │
  │                       ├──── Fill Form Fields►│                       │
  │                       │                      ├──── Type ────────────►│
  │                       │                      │                       │
  │◄──── Progress: 75%    │◄──── Screenshot ─────┤                       │
  │                       │                      │                       │
  │                       ├──── Click "Save" ───►│                       │
  │                       │                      ├──── Submit ──────────►│
  │                       │                      │                       │
  │                       │                      │◄──── Success Msg ─────┤
  │                       │                      │                       │
  │◄──── Status: Success  │◄──── Screenshot ─────┤                       │
  │◄──── Progress: 100%   │                      │                       │
  │                       │                      │                       │
  │                  [Next vendor...]            │                       │
```

### 5.6 Error Handling Flow

```
Playwright                 Nexus GUI                User
    │                         │                      │
    ├──── Error Detected      │                      │
    │     (e.g., duplicate    │                      │
    │      email)             │                      │
    │                         │                      │
    ├──── Screenshot ────────►│                      │
    ├──── Error Message ─────►│                      │
    │                         │                      │
    │                    [Update status: 🟠]        │
    │                    [Log error]                │
    │                         │                      │
    │                         ├──── Show Error ─────►│
    │                         │                      │
    │                         │◄──── Click "View" ───┤
    │                         │                      │
    │                         ├──── Show Details ───►│
    │                         │      - Error msg     │
    │                         │      - Screenshot    │
    │                         │      - Log entries   │
    │                         │      - [Retry] btn   │
    │                         │                      │
    │                         │◄──── Click "Retry" ──┤
    │                         │                      │
    │◄──── Restart Automation ┤                      │
    │                         │                      │
```

---

## 6. Technical Architecture

### 6.1 Deployment & Distribution Strategy

**EXE Packaging with PyInstaller:**
- Application bundled as single executable using PyInstaller
- Initial EXE size: ~50MB (without Playwright browsers)
- Configuration files embedded in EXE, extracted to AppData on first run
- Playwright browsers installed separately on first run (~280MB download)

**AppData Structure:**
```
C:\Users\<username>\AppData\Roaming\Nexus\
├── config/
│   ├── app_config.json              # Extracted from EXE on first run
│   ├── vendor_mappings.json         # Extracted from EXE on first run
│   └── user_settings.json           # User preferences (created at runtime)
├── logs/
│   └── nexus_YYYYMMDD.log           # Application logs
├── screenshots/
│   └── <timestamp>_<vendor>.png     # Automation screenshots
└── browsers/
    └── chromium-<version>/          # Playwright browser installation
```

**First-Run Experience:**
1. User launches Nexus.exe
2. App detects no AppData directory exists
3. Shows "First Run Setup" dialog:
   - "Setting up Nexus for the first time..."
   - Progress bar for extracting config files (~2 seconds)
   - Progress bar for installing Playwright browsers (~1-2 minutes)
   - "Checking for browser updates..."
4. App validates installation
5. App opens normally

**Subsequent Runs:**
1. User launches Nexus.exe
2. App checks browser installation (0.5 seconds)
3. If outdated: Shows "Updating Playwright browsers..." (~1-2 minutes)
4. App opens normally

**Distribution Strategy:**
- Small EXE (~50MB) easy to email or share via SharePoint
- No redeployment needed for:
  - Vendor password changes (stored in Key Vault)
  - Browser updates (auto-updated on launch)
- Redeployment only needed for:
  - New vendor automations
  - Code changes/bug fixes
  - Configuration updates (tenant ID, Key Vault URL)

**PyInstaller Configuration:**
```python
# nexus.spec file for PyInstaller
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config/*.json', 'config'),
        ('assets/*', 'assets'),
        ('Vendors/*/config.json', 'Vendors'),
        ('Vendors/*/logo.png', 'Vendors')
    ],
    hiddenimports=['msal', 'azure.keyvault.secrets', 'azure.identity'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['playwright'],  # Don't bundle Playwright browsers
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Nexus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/nexus_icon.ico'
)
```

### 6.2 Technology Stack

**Programming Language:**
- Python 3.11+

**GUI Framework:**
- **Option 1:** CustomTkinter (Recommended for simplicity)
  - Modern, clean UI
  - Easy to learn
  - Cross-platform
- **Option 2:** PyQt6 (More powerful, steeper learning curve)
  - Professional appearance
  - More widget options
  - Better for complex layouts

**Browser Automation:**
- Playwright for Python
- Chromium browser (default)

**Microsoft Graph API:**
- MSAL (Microsoft Authentication Library)
- `msal` Python package
- OAuth 2.0 authentication

**Data Storage:**
- JSON files for configuration
- SQLite for history/audit log (optional)
- Windows Credential Manager for sensitive data (passwords)

**Additional Libraries:**
- `requests` - HTTP requests
- `python-dotenv` - Environment variables
- `cryptography` - Encrypt sensitive data
- `pillow` - Image handling (screenshots, profile photos)
- `reportlab` - PDF report generation

### 6.3 Network Failure Handling & Retry Logic

**Network Resilience Strategy:**

**1. Retry Logic with Exponential Backoff:**
```python
# utils/retry_handler.py
import time
import functools
from typing import Callable, Any

class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    exponential_base: float = 2.0
    timeout: float = 120.0  # seconds

def with_retry(config: RetryConfig = RetryConfig()):
    """Decorator for automatic retry with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            delay = config.initial_delay

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError, RequestException) as e:
                    last_exception = e
                    if attempt < config.max_retries:
                        log_warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                        time.sleep(delay)
                        delay = min(delay * config.exponential_base, config.max_delay)
                    else:
                        log_error(f"All {config.max_retries} retries exhausted")
                        raise NetworkFailureError(f"Failed after {config.max_retries} retries") from last_exception

            raise last_exception
        return wrapper
    return decorator
```

**2. Graph API Retry Strategy:**
```python
# services/graph_api.py
class GraphAPIClient:
    @with_retry(RetryConfig(max_retries=3, initial_delay=2.0))
    def search_users(self, query: str) -> List[EntraUser]:
        """Search with automatic retry"""
        try:
            response = requests.get(
                f"{self.base_url}/users",
                headers=self._get_headers(),
                params={"$filter": query},
                timeout=30
            )
            response.raise_for_status()
            return self._parse_users(response.json())
        except requests.exceptions.ConnectionError:
            raise ConnectionError("Unable to connect to Microsoft Graph API")
        except requests.exceptions.Timeout:
            raise TimeoutError("Microsoft Graph API request timed out")
```

**3. Key Vault Retry Strategy:**
```python
# services/keyvault_service.py
class KeyVaultService:
    @with_retry(RetryConfig(max_retries=3, initial_delay=1.0))
    def get_vendor_credentials(self, vendor_name: str) -> dict:
        """Retrieve credentials with automatic retry"""
        try:
            username = self.client.get_secret(f"{vendor_name}-username").value
            password = self.client.get_secret(f"{vendor_name}-password").value
            url = self.client.get_secret(f"{vendor_name}-url").value
            return {"username": username, "password": password, "url": url}
        except Exception as e:
            raise ConnectionError(f"Failed to retrieve credentials from Key Vault: {str(e)}")
```

**4. Playwright Network Handling:**
```python
# automation/base_automation.py
class BaseVendorAutomation:
    async def _navigate_with_retry(self, url: str, max_attempts: int = 3):
        """Navigate to URL with retry logic"""
        for attempt in range(max_attempts):
            try:
                await self.page.goto(url, timeout=30000, wait_until='networkidle')
                return
            except PlaywrightTimeoutError:
                if attempt < max_attempts - 1:
                    self.log(f"Navigation timeout. Retry {attempt + 1}/{max_attempts - 1}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise NetworkFailureError(f"Failed to navigate to {url} after {max_attempts} attempts")
```

**5. Graceful Error Messages:**
```python
# Error message examples shown to user
NETWORK_ERROR_MESSAGES = {
    "graph_api_connection": "Unable to connect to Microsoft Entra ID. Please check your internet connection.",
    "graph_api_timeout": "Microsoft Entra ID is taking too long to respond. Please try again.",
    "keyvault_connection": "Unable to retrieve vendor credentials from Azure Key Vault. Check your permissions.",
    "vendor_site_down": "The vendor website ({vendor}) appears to be down. Please try again later.",
    "general_timeout": "Operation timed out after {timeout} seconds. Please check your network connection."
}
```

**6. User-Facing Error Handling:**
- Clear, non-technical error messages
- Automatic retry (transparent to user for transient errors)
- Manual retry button for persistent errors
- "Check Network Connection" link that tests connectivity
- Error details available in log viewer for troubleshooting

**7. Pre-Flight Network Check:**
```python
def check_network_connectivity() -> dict:
    """Check connectivity to all required services before starting automation"""
    results = {
        "internet": False,
        "graph_api": False,
        "keyvault": False,
        "vendors": {}
    }

    # Check internet connectivity
    try:
        requests.get("https://www.msftconnecttest.com/connecttest.txt", timeout=5)
        results["internet"] = True
    except:
        return results

    # Check Graph API
    try:
        # Minimal API call to test connectivity
        response = graph_client.test_connection()
        results["graph_api"] = response
    except:
        pass

    # Check Key Vault
    try:
        keyvault_client.test_connection()
        results["keyvault"] = True
    except:
        pass

    return results
```

### 6.4 Duplicate Account Detection

**Pre-Flight Duplicate Check:**
Before creating any vendor account, check if the account already exists to avoid errors and duplicates.

```python
# automation/base_automation.py
class BaseVendorAutomation:
    async def check_duplicate_account(self, email: str) -> bool:
        """
        Check if user account already exists in vendor system
        Returns True if duplicate found, False otherwise
        """
        raise NotImplementedError("Subclass must implement duplicate check")

    async def execute(self, progress_callback, log_callback) -> AutomationResult:
        """Execute automation with duplicate check"""
        try:
            await self._initialize_browser()
            await self._login()

            # Pre-flight duplicate check
            progress_callback(10, "Checking for existing account...")
            is_duplicate = await self.check_duplicate_account(self.user.mail)

            if is_duplicate:
                self.result.status = AutomationStatus.ERROR
                self.result.error_message = f"Account already exists for {self.user.mail}"
                self.result.error_type = "DUPLICATE_ACCOUNT"
                log_callback(f"❌ Duplicate account detected: {self.user.mail}")
                return self.result

            # Continue with account creation
            progress_callback(20, "Navigating to user creation...")
            await self._navigate_to_user_creation()

            # ... rest of automation

        except DuplicateAccountError as e:
            self.result.status = AutomationStatus.ERROR
            self.result.error_message = str(e)
            self.result.error_type = "DUPLICATE_ACCOUNT"
        except Exception as e:
            self.result.status = AutomationStatus.ERROR
            self.result.error_message = str(e)
        finally:
            await self._cleanup()

        return self.result
```

**Vendor-Specific Duplicate Check Example (AccountChek):**
```python
# automation/vendors/accountchek.py
class AccountChekAutomation(BaseVendorAutomation):
    async def check_duplicate_account(self, email: str) -> bool:
        """Check if account exists in AccountChek"""
        try:
            # Navigate to user management page
            await self.page.goto(f"{self.vendor.credentials.url}/users")

            # Search for email in user list
            await self.page.fill('input[type="search"]', email)
            await self.page.wait_for_timeout(1000)  # Wait for search results

            # Check if any results found
            results = await self.page.locator('.user-row').count()

            if results > 0:
                self.log(f"Found existing account for {email}")
                return True
            else:
                self.log(f"No existing account found for {email}")
                return False

        except Exception as e:
            # If check fails, log warning but allow automation to continue
            self.log(f"Warning: Could not check for duplicates: {str(e)}")
            return False  # Assume no duplicate if check fails
```

**Error Display in GUI:**
```python
# gui/components/vendor_card.py
def display_duplicate_error(self, vendor_name: str, email: str):
    """Show user-friendly duplicate account error"""
    error_dialog = CTkMessageBox(
        title=f"{vendor_name} - Duplicate Account",
        message=f"An account for {email} already exists in {vendor_name}.\n\n"
                f"This account was not created to avoid duplicates.\n\n"
                f"If you need to update this account, please do so manually.",
        icon="warning",
        option_1="OK",
        option_2="View Account"
    )

    if error_dialog.get() == "View Account":
        # Open vendor website to view existing account
        webbrowser.open(f"{vendor_url}/users?search={email}")
```

**Duplicate Error Handling Summary:**
- ✅ Check for duplicates BEFORE attempting creation
- ✅ Clear error message: "Account already exists for [email]"
- ✅ Orange status indicator (not red) to differentiate from failure
- ✅ No retry button (retrying won't help)
- ✅ Option to view existing account in vendor system
- ✅ Continue with other vendors if duplicate found
- ✅ Log duplicate detection for audit trail

### 6.5 Password Generation Strategy

**Password Generation Algorithm:**

**Default Password Format:**
- 16 characters long
- Includes: Uppercase, Lowercase, Numbers, Special Characters
- Guaranteed complexity: At least 2 of each character type
- No ambiguous characters (0/O, 1/l/I)

```python
# utils/password_generator.py
import secrets
import string

class PasswordGenerator:
    """Secure password generator for vendor accounts"""

    # Character sets (excluding ambiguous characters)
    UPPERCASE = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # Removed I, O
    LOWERCASE = "abcdefghjkmnpqrstuvwxyz"   # Removed l, o
    DIGITS = "23456789"                     # Removed 0, 1
    SPECIAL = "!@#$%^&*-_=+"                # Common allowed special chars

    @staticmethod
    def generate_password(
        length: int = 16,
        require_uppercase: int = 2,
        require_lowercase: int = 2,
        require_digits: int = 2,
        require_special: int = 2
    ) -> str:
        """
        Generate a secure random password

        Args:
            length: Total password length
            require_uppercase: Minimum uppercase letters
            require_lowercase: Minimum lowercase letters
            require_digits: Minimum digits
            require_special: Minimum special characters

        Returns:
            Secure random password string
        """
        # Validate requirements
        min_required = require_uppercase + require_lowercase + require_digits + require_special
        if length < min_required:
            raise ValueError(f"Password length {length} too short for requirements (min: {min_required})")

        # Build password with required characters
        password = []

        # Add required uppercase
        password.extend(secrets.choice(PasswordGenerator.UPPERCASE) for _ in range(require_uppercase))

        # Add required lowercase
        password.extend(secrets.choice(PasswordGenerator.LOWERCASE) for _ in range(require_lowercase))

        # Add required digits
        password.extend(secrets.choice(PasswordGenerator.DIGITS) for _ in range(require_digits))

        # Add required special
        password.extend(secrets.choice(PasswordGenerator.SPECIAL) for _ in range(require_special))

        # Fill remaining length with random mix
        all_chars = (
            PasswordGenerator.UPPERCASE +
            PasswordGenerator.LOWERCASE +
            PasswordGenerator.DIGITS +
            PasswordGenerator.SPECIAL
        )
        password.extend(secrets.choice(all_chars) for _ in range(length - min_required))

        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(password)

        return ''.join(password)

    @staticmethod
    def generate_vendor_password(vendor_config: dict) -> str:
        """
        Generate password based on vendor-specific requirements
        Reads requirements from vendor onboarding document
        """
        password_rules = vendor_config.get("password_rules", {})

        return PasswordGenerator.generate_password(
            length=password_rules.get("length", 16),
            require_uppercase=password_rules.get("min_uppercase", 2),
            require_lowercase=password_rules.get("min_lowercase", 2),
            require_digits=password_rules.get("min_digits", 2),
            require_special=password_rules.get("min_special", 2)
        )
```

**Vendor-Specific Password Requirements:**

Each vendor's configuration file includes password requirements:

```json
// Vendors/AccountChek/config.json
{
  "password_rules": {
    "length": 16,
    "min_uppercase": 2,
    "min_lowercase": 2,
    "min_digits": 2,
    "min_special": 2,
    "allowed_special": "!@#$%^&*-_=+",
    "notes": "AccountChek requires 12-20 chars with at least 1 of each type"
  }
}

// Vendors/VendorXYZ/config.json (example: vendor with restrictions)
{
  "password_rules": {
    "length": 12,
    "min_uppercase": 1,
    "min_lowercase": 1,
    "min_digits": 1,
    "min_special": 1,
    "allowed_special": "!@#$",
    "excluded_chars": "{}[]()<>",
    "notes": "VendorXYZ only allows ! @ # $ for special characters"
  }
}
```

**Password Handling in GUI:**
```python
# gui/components/password_field.py
class PasswordField(CTkFrame):
    def __init__(self, parent, vendor_config):
        self.vendor_config = vendor_config
        self.auto_generate = True

        # Auto-generate button (default selected)
        self.auto_btn = CTkRadioButton(
            self,
            text="Auto-generate secure password",
            variable=self.mode,
            value="auto",
            command=self.on_mode_change
        )

        # Manual entry option
        self.manual_btn = CTkRadioButton(
            self,
            text="Enter custom password",
            variable=self.mode,
            value="manual",
            command=self.on_mode_change
        )

        # Password preview/entry field
        self.password_field = CTkEntry(self, show="●")

    def generate_password(self):
        """Generate password based on vendor requirements"""
        password = PasswordGenerator.generate_vendor_password(self.vendor_config)
        self.password_field.delete(0, 'end')
        self.password_field.insert(0, password)
        return password
```

**Password Requirements Summary:**
- ✅ Default: 16 characters, 2 uppercase, 2 lowercase, 2 digits, 2 special
- ✅ Vendor-specific rules documented in onboarding template
- ✅ No ambiguous characters to avoid user confusion
- ✅ Cryptographically secure random generation (secrets module)
- ✅ Configurable per-vendor via config files
- ✅ Auto-generate (default) or manual entry
- ✅ Passwords never logged or stored locally

### 6.6 Project Structure

```
Nexus/
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables (not in git)
├── config/
│   ├── app_config.json              # Application settings (Tenant ID, Client ID, Key Vault URL)
│   └── vendor_mappings.json         # Group-to-vendor mappings
├── gui/
│   ├── __init__.py
│   ├── main_window.py               # Main window & tab management
│   ├── tab_search.py                # Tab 1: User Search
│   ├── tab_provisioning.py          # Tab 2: Account Provisioning
│   ├── tab_status.py                # Tab 3: Automation Status
│   ├── tab_settings.py              # Tab 4: Settings
│   ├── components/
│   │   ├── auth_panel.py            # Microsoft sign-in component
│   │   ├── user_summary.py          # User info display
│   │   ├── vendor_card.py           # Vendor card component
│   │   ├── progress_bar.py          # Custom progress bar
│   │   └── log_viewer.py            # Activity log viewer
│   └── styles.py                    # UI styling constants
├── services/
│   ├── __init__.py
│   ├── graph_api.py                 # Microsoft Graph API client
│   ├── auth_service.py              # Microsoft authentication service (delegated permissions)
│   ├── keyvault_service.py          # Azure Key Vault client for vendor credentials
│   ├── vendor_detector.py           # Group-to-vendor detection
│   └── config_manager.py            # Configuration management
├── automation/
│   ├── __init__.py
│   ├── base_automation.py           # Base class for all vendors
│   ├── playwright_manager.py        # Playwright lifecycle management
│   └── vendors/
│       ├── __init__.py
│       ├── accountchek.py           # AccountChek automation
│       └── vendorxyz.py             # Additional vendor scripts
├── utils/
│   ├── __init__.py
│   ├── logger.py                    # Logging utilities
│   ├── encryption.py                # Encrypt/decrypt credentials
│   ├── report_generator.py          # PDF/CSV report generation
│   └── validators.py                # Input validation
├── models/
│   ├── __init__.py
│   ├── user.py                      # User data model
│   ├── vendor.py                    # Vendor configuration model
│   └── automation_result.py         # Automation result model
├── Vendors/                         # Vendor configuration (existing)
│   ├── AccountChek/
│   │   ├── config.json
│   │   ├── accountchek.spec.js
│   │   └── ACCOUNTCHEK_ONBOARDING.md
│   └── ...
└── logs/                            # Application logs
    └── nexus_YYYYMMDD.log
```

### 6.3 Class Diagrams

**Core Classes:**

```python
# models/user.py
class EntraUser:
    """Represents a user from Microsoft Entra ID"""
    id: str
    display_name: str
    given_name: str
    surname: str
    mail: str
    user_principal_name: str
    job_title: str
    department: str
    office_location: str
    employee_id: str  # extensionAttribute2
    photo: bytes
    groups: List[EntraGroup]

    def __init__(self, graph_data: dict):
        # Parse Graph API response
        pass

# models/vendor.py
class VendorConfig:
    """Configuration for a vendor system"""
    name: str
    display_name: str
    logo_path: str
    entra_group_name: str
    entra_group_id: str
    fields: List[VendorField]
    credentials: VendorCredentials

class VendorField:
    """Represents a configurable field for a vendor"""
    name: str
    label: str
    field_type: FieldType  # TEXT, DROPDOWN, CHECKBOX, etc.
    required: bool
    default_value: str
    options: List[str]  # For dropdowns
    entra_attribute: str  # Which Entra attribute maps to this
    read_only: bool

class VendorCredentials:
    """Vendor login credentials (retrieved from Azure Key Vault)"""
    login_url: str
    username: str
    password: str  # Retrieved from Key Vault at runtime
    keyvault_prefix: str  # Prefix for Key Vault secret names

# models/automation_result.py
class AutomationResult:
    """Result of a vendor automation run"""
    vendor_name: str
    status: AutomationStatus  # SUCCESS, ERROR, SKIPPED
    start_time: datetime
    end_time: datetime
    duration: float
    error_message: str
    screenshots: List[str]
    log_entries: List[LogEntry]
```

**Service Classes:**

```python
# services/auth_service.py
class AuthService:
    """Microsoft authentication service using delegated permissions"""

    def __init__(self, tenant_id: str, client_id: str, redirect_uri: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.msal_app = msal.PublicClientApplication(
            client_id=client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}"
        )
        self.token = None

    def sign_in_interactive(self, scopes: List[str]) -> dict:
        """
        Interactive browser sign-in for user
        Returns access token that works for both Graph API and Key Vault
        """
        result = self.msal_app.acquire_token_interactive(scopes=scopes)
        if "access_token" in result:
            self.token = result
            return result
        else:
            raise AuthenticationError(f"Sign-in failed: {result.get('error_description')}")

    def get_token_silent(self, scopes: List[str]) -> str:
        """Get token from cache or refresh"""
        accounts = self.msal_app.get_accounts()
        if accounts:
            result = self.msal_app.acquire_token_silent(scopes=scopes, account=accounts[0])
            if result and "access_token" in result:
                return result["access_token"]
        return None

    def sign_out(self):
        """Sign out and clear cached tokens"""
        accounts = self.msal_app.get_accounts()
        for account in accounts:
            self.msal_app.remove_account(account)
        self.token = None

# services/graph_api.py
class GraphAPIClient:
    """Microsoft Graph API client"""

    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service
        self.base_url = "https://graph.microsoft.com/v1.0"

    def _get_headers(self) -> dict:
        """Get authorization headers with current token"""
        token = self.auth_service.get_token_silent([
            "User.Read.All",
            "GroupMember.Read.All",
            "Group.Read.All"
        ])
        return {"Authorization": f"Bearer {token}"}

    def authenticate(self) -> bool:
        """Check if authenticated"""
        return self.auth_service.token is not None

    def search_users(self, query: str, search_type: SearchType) -> List[EntraUser]:
        """Search for users"""
        pass

    def get_user_details(self, user_id: str) -> EntraUser:
        """Get full user details including groups"""
        pass

    def get_user_groups(self, user_id: str) -> List[EntraGroup]:
        """Get user's group memberships"""
        pass

# services/vendor_detector.py
class VendorDetector:
    """Detects which vendors a user needs based on group membership"""

    def __init__(self, mappings_file: str):
        self.mappings = self._load_mappings()

    def detect_vendors(self, user: EntraUser) -> List[VendorConfig]:
        """Return list of vendors user should have accounts for"""
        pass

# automation/base_automation.py
class BaseVendorAutomation:
    """Base class for all vendor automations"""

    def __init__(self, vendor_config: VendorConfig, user: EntraUser):
        self.vendor = vendor_config
        self.user = user
        self.page = None  # Playwright page
        self.result = AutomationResult()

    async def execute(self, progress_callback, log_callback) -> AutomationResult:
        """Execute the automation"""
        try:
            await self._initialize_browser()
            await self._login()
            await self._navigate_to_user_creation()
            await self._fill_form()
            await self._submit()
            await self._verify()
            self.result.status = AutomationStatus.SUCCESS
        except Exception as e:
            self.result.status = AutomationStatus.ERROR
            self.result.error_message = str(e)
        finally:
            await self._cleanup()
        return self.result

    # Abstract methods to be implemented by vendor-specific classes
    async def _login(self):
        raise NotImplementedError

    async def _navigate_to_user_creation(self):
        raise NotImplementedError

    async def _fill_form(self):
        raise NotImplementedError

# automation/vendors/accountchek.py
class AccountChekAutomation(BaseVendorAutomation):
    """AccountChek-specific automation"""

    async def _login(self):
        await self.page.goto(self.vendor.credentials.login_url)
        await self.page.fill('input[type="email"]', self.vendor.credentials.username)
        # ... implementation from existing accountchek.spec.js
```

### 6.4 Threading Architecture

```python
# GUI runs on main thread
# Automation runs on background threads

import threading
from queue import Queue

class AutomationRunner:
    """Manages automation execution in background threads"""

    def __init__(self, gui_callback):
        self.gui_callback = gui_callback
        self.message_queue = Queue()

    def run_automations(self, vendors: List[VendorConfig], user: EntraUser):
        """Run automations in background thread"""
        thread = threading.Thread(
            target=self._automation_worker,
            args=(vendors, user),
            daemon=True
        )
        thread.start()

    def _automation_worker(self, vendors, user):
        """Worker function that runs in background thread"""
        for vendor in vendors:
            automation = self._create_automation(vendor, user)

            # Progress callback sends updates to main thread via queue
            def progress_callback(percent, message):
                self.message_queue.put({
                    'type': 'progress',
                    'vendor': vendor.name,
                    'percent': percent,
                    'message': message
                })

            # Execute automation
            result = asyncio.run(automation.execute(progress_callback))

            # Send completion message
            self.message_queue.put({
                'type': 'complete',
                'vendor': vendor.name,
                'result': result
            })

    def check_messages(self):
        """Called periodically by GUI main thread to process messages"""
        while not self.message_queue.empty():
            message = self.message_queue.get()
            self.gui_callback(message)
```

### 6.5 Configuration File Formats

**config/app_config.json:**
```json
{
  "app": {
    "name": "Nexus",
    "version": "1.0.0"
  },
  "microsoft": {
    "tenant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "client_id": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
    "redirect_uri": "http://localhost:8400",
    "scopes": [
      "User.Read.All",
      "GroupMember.Read.All",
      "Group.Read.All",
      "https://vault.azure.net/user_impersonation"
    ]
  },
  "azure_keyvault": {
    "vault_url": "https://nexus-credentials.vault.azure.net/",
    "secret_naming_convention": "{vendor}-{field}"
  },
  "settings": {
    "timeout_seconds": 120,
    "headless_mode": false,
    "log_level": "INFO",
    "auto_screenshot": true
  }
}
```

**IMPORTANT NOTES:**
- ✅ **NO CLIENT SECRETS** in this file - uses delegated permissions
- ✅ **Tenant ID and Client ID are public** - safe to distribute in EXE
- ✅ **Key Vault URL is public** - access controlled by Azure RBAC
- ✅ **All vendor credentials stored in Azure Key Vault**, not in local files

**config/vendor_mappings.json:**
```json
{
  "mappings": [
    {
      "entra_group_name": "AccountChek_Users",
      "entra_group_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "vendor_name": "AccountChek",
      "vendor_display_name": "AccountChek Verifier",
      "vendor_logo": "assets/accountchek_logo.png"
    },
    {
      "entra_group_name": "VendorXYZ_Users",
      "entra_group_id": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
      "vendor_name": "VendorXYZ",
      "vendor_display_name": "Vendor XYZ Platform",
      "vendor_logo": "assets/vendorxyz_logo.png"
    }
  ]
}
```

**Vendors/AccountChek/config.json** (Enhanced):
```json
{
  "vendor": {
    "name": "AccountChek",
    "display_name": "AccountChek Verifier",
    "logo": "Vendors/AccountChek/logo.png"
  },
  "credentials": {
    "keyvault_secret_prefix": "accountchek",
    "note": "Credentials retrieved from Azure Key Vault: accountchek-username, accountchek-password, accountchek-url"
  },
  "fields": [
    {
      "name": "firstName",
      "label": "First Name",
      "type": "text",
      "required": true,
      "entra_attribute": "givenName",
      "read_only": false
    },
    {
      "name": "lastName",
      "label": "Last Name",
      "type": "text",
      "required": true,
      "entra_attribute": "surname",
      "read_only": false
    },
    {
      "name": "email",
      "label": "Email",
      "type": "email",
      "required": true,
      "entra_attribute": "mail",
      "read_only": false
    },
    {
      "name": "jobTitle",
      "label": "Job Title",
      "type": "text",
      "required": true,
      "entra_attribute": "jobTitle",
      "read_only": false
    },
    {
      "name": "role",
      "label": "Role",
      "type": "text",
      "required": true,
      "default_value": "User",
      "read_only": true,
      "tooltip": "Standard user role (Admin/Manager must be created manually)"
    },
    {
      "name": "region",
      "label": "Region",
      "type": "dropdown",
      "required": true,
      "entra_attribute": "department",
      "options": ["Corporate", "Western Region", "Eastern Region"],
      "read_only": false
    },
    {
      "name": "branch",
      "label": "Branch",
      "type": "dropdown",
      "required": true,
      "entra_attribute": "officeLocation",
      "depends_on": "region",
      "options_dynamic": true,
      "read_only": false
    },
    {
      "name": "password",
      "label": "Password",
      "type": "password",
      "required": true,
      "default_value": "AUTO_GENERATE",
      "read_only": false
    },
    {
      "name": "mustChangePassword",
      "label": "Must Change Password on First Login",
      "type": "checkbox",
      "required": false,
      "default_value": true,
      "read_only": false
    }
  ],
  "entra_mapping": {
    "group_name": "AccountChek_Users",
    "group_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  }
}
```

---

## 7. Security Considerations

### 7.1 Credential Storage

**Microsoft Authentication (Delegated Permissions):**
- ✅ **NO CLIENT SECRETS** stored in the application
- Tenant ID and Client ID are public identifiers (safe to distribute)
- User signs in interactively via browser
- Access tokens stored in memory only (never written to disk)
- Refresh tokens handled by MSAL automatically (in-memory only)
- Token automatically works for both Graph API and Key Vault access

**Vendor Credentials (Azure Key Vault):**
- ✅ **All vendor passwords stored in Azure Key Vault**
- Retrieved at runtime using user's Microsoft access token
- Never stored locally on user's machine
- Credentials fetched fresh for each automation run
- Access controlled by Azure RBAC (role-based access control)
- Centralized management - update once, affects all deployed apps

**Azure Key Vault Configuration:**
```
Key Vault: nexus-vendor-credentials
├── Access Policy: Azure RBAC
├── Secrets:
│   ├── accountchek-username → "cvance@highlandsmortgage.com"
│   ├── accountchek-password → "Welcome@123"
│   ├── accountchek-url → "https://verifier.accountchek.com/login"
│   ├── vendorxyz-username → "admin@company.com"
│   ├── vendorxyz-password → "SecurePass456!"
│   └── vendorxyz-url → "https://vendorxyz.com/login"
└── RBAC Permissions:
    ├── IT Admin Group → Key Vault Secrets Officer (read/write)
    └── Nexus_Users Group → Key Vault Secrets User (read only)
```

**Example Key Vault Service:**
```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

class KeyVaultService:
    """Service for retrieving vendor credentials from Azure Key Vault"""

    def __init__(self, vault_url: str, credential=None):
        # Uses the same credential from Microsoft sign-in
        self.credential = credential or DefaultAzureCredential()
        self.client = SecretClient(vault_url=vault_url, credential=self.credential)

    def get_vendor_credentials(self, vendor_name: str) -> dict:
        """
        Retrieve vendor credentials from Key Vault

        Args:
            vendor_name: Name of vendor (e.g., "accountchek")

        Returns:
            dict with username, password, url
        """
        try:
            username = self.client.get_secret(f"{vendor_name}-username").value
            password = self.client.get_secret(f"{vendor_name}-password").value
            url = self.client.get_secret(f"{vendor_name}-url").value

            return {
                "username": username,
                "password": password,
                "url": url
            }
        except Exception as e:
            raise Exception(f"Failed to retrieve credentials for {vendor_name}: {str(e)}")

    def test_connection(self, vendor_name: str) -> bool:
        """Test if credentials can be retrieved"""
        try:
            self.get_vendor_credentials(vendor_name)
            return True
        except:
            return False
```

**Benefits of This Approach:**
- ✅ **No secrets in EXE** - Can't be extracted by reverse engineering
- ✅ **Centralized updates** - Change password once in Key Vault, all apps get new password
- ✅ **No redeployment** needed for password changes
- ✅ **Audit trail** - Key Vault logs all access attempts
- ✅ **Access control** - Revoke user's access to Key Vault if needed
- ✅ **Partner-friendly** - Partners never see or manage vendor passwords

### 7.2 Token Management

- **Access tokens:** 1-hour expiration, stored in memory
- **Refresh tokens:** 90-day expiration, encrypted if persisted
- **Automatic refresh:** Before expiration to maintain session
- **Token revocation:** On sign-out, clear all tokens

### 7.3 Logging & Audit

**What to Log:**
- User searches (who searched for whom)
- Account creations (which accounts were created, when, by whom)
- Authentication events (sign-in, sign-out)
- Errors and exceptions
- Configuration changes

**What NOT to Log:**
- Passwords (ever)
- Full access tokens
- Sensitive PII beyond what's necessary

**Log Format:**
```
[2025-10-15 10:23:45] [INFO] [AUTH] User john.admin@company.com signed in
[2025-10-15 10:24:10] [INFO] [SEARCH] Searched for user: john.doe@company.com
[2025-10-15 10:25:30] [INFO] [AUTOMATION] Starting AccountChek automation for john.doe@company.com
[2025-10-15 10:25:45] [SUCCESS] [AUTOMATION] AccountChek account created: john.doe@company.com
```

### 7.4 Permissions & Access Control

**Required Graph API Permissions (Delegated):**
- `User.Read.All` - Read all users (delegated to signed-in user)
- `GroupMember.Read.All` - Read group memberships (delegated)
- `Group.Read.All` - Read groups (delegated)

**Why Delegated Permissions:**
- ✅ **More secure for EXE distribution** - No client secrets in app
- ✅ **User context** - Actions performed as the signed-in user
- ✅ **Better audit trail** - Know which user performed which action
- ✅ **Easier consent** - User consents once, remembers for future

**Azure Key Vault Permissions (Azure RBAC):**
- **IT Admin Group:** Key Vault Secrets Officer (can create/update/delete secrets)
- **Nexus Users Group:** Key Vault Secrets User (read-only access to secrets)
- User's Microsoft token automatically grants access based on group membership

**Vendor System Permissions:**
- Use dedicated service account credentials (stored in Key Vault)
- Account should only have permission to create standard users
- Cannot create admin/manager accounts

### 7.5 Network Security

- **HTTPS only** for all API calls
- **Certificate validation** enabled
- **No proxy bypass** (respect corporate proxy settings)
- **Timeout settings** to prevent hanging connections

---

## 8. Future Enhancements (V2+)

### 8.1 Documentation & Support (End of Project)

**Comprehensive Troubleshooting Guide:**
To be created at the end of the project, including:
- Common error scenarios and resolutions
- Network connectivity troubleshooting steps
- Microsoft authentication issues
- Azure Key Vault permission problems
- Vendor-specific known issues
- Screenshot examples of error states
- Step-by-step resolution guides

**Vendor Submission Process Guide:**
- How to request new vendor automations
- Vendor Onboarding Template completion instructions
- What information to gather before submitting
- Timeline expectations for new vendor implementation
- Testing and validation procedures
- Rollout process for new vendors

**End User Documentation:**
- Quick Start Guide (PDF)
- Video walkthrough of typical workflow
- FAQ document
- Contact information for support

**Note:** These comprehensive guides will be created after the initial release to ensure they reflect the actual implementation and include real-world troubleshooting scenarios encountered during testing.

### 8.2 Bulk Mode
- Upload CSV of users
- Process multiple users sequentially or in parallel
- Batch report generation
- Progress tracking for bulk operations

### 8.2 Scheduling & Automation
- Scheduled runs (nightly, weekly)
- Automatic provisioning when users are added to groups
- Webhook integration with Entra ID

### 8.3 Deprovisioning
- Disable/delete accounts when user leaves group
- Archive user data before deletion
- Compliance with retention policies

### 8.4 Advanced Reporting
- Dashboard with statistics
- Graphs and charts (accounts created over time)
- Compliance reports
- Audit trail exports

### 8.5 API Mode
- REST API for Nexus
- Allow other systems to trigger provisioning
- Integration with ITSM tools (ServiceNow, Jira)

### 8.6 Machine Learning
- Predict which vendors a user needs based on role/department
- Anomaly detection (unusual provisioning patterns)
- Auto-fill field suggestions

### 8.7 Multi-Tenancy
- Support multiple Entra ID tenants
- Separate configurations per tenant
- Tenant switching in UI

### 8.8 Mobile App
- Mobile companion app for approvals
- Push notifications for completed automations
- View reports on mobile

---

## Appendix A: Mockup Descriptions

### Mockup 1: Tab 1 - User Search (Initial State)

**Visual Description:**
- Clean, modern interface with plenty of white space
- Top bar: "NEXUS - Vendor Account Provisioning" title, tabs below
- Large, centered panel: "Microsoft Sign-In"
- Status indicator: Red circle with "Not Connected"
- Prominent blue button: "🔑 Sign In with Microsoft"
- Search section below, grayed out and disabled
- Color scheme: Blue accent (#0078D4 Microsoft blue), white background, gray text

### Mockup 2: Tab 2 - Account Provisioning (User Selected)

**Visual Description:**
- Top panel: User summary card with rounded corners, subtle shadow
- Left side: Circular profile photo (128x128px)
- Right side: User details in clean typography
- Middle section: Grid of vendor cards (2 columns on standard screen)
- Vendor cards: White background, colored left border (green if auto-detected)
- Checkboxes: Large, easy to click
- Status dots: Prominent, colored circles
- Bottom: Action buttons, right-aligned

### Mockup 3: Tab 3 - Automation Status (In Progress)

**Visual Description:**
- Full-height cards for each vendor
- Animated progress bars with gradient effect
- Color-coded borders: Yellow for in-progress, green for success, orange for error
- Live log panel at bottom: Dark background (#1E1E1E), colored text, monospace font
- Screenshots appear as thumbnails, click to enlarge
- Smooth animations for status changes

### Mockup 4: Settings Tab

**Visual Description:**
- Organized into sections with subtle dividers
- Form inputs: Clean, modern text fields
- Password fields: Masked with "show/hide" toggle
- Buttons: Consistent styling, hover effects
- Color coding: Green for "Save", red for "Delete", blue for "Test"

---

## Appendix B: User Stories

### US-001: Sign In with Microsoft
**As a** technician
**I want to** sign in with my Microsoft account
**So that** I can access Entra ID user data

**Acceptance Criteria:**
- Click "Sign In with Microsoft" opens browser authentication
- Successful auth shows "Connected as: [email]"
- Failed auth shows error message
- Can sign out and sign in again

### US-002: Search for User
**As a** technician
**I want to** search for users by various criteria
**So that** I can find the correct user quickly

**Acceptance Criteria:**
- Can search by email, name, display name, employee ID
- Results display in table with photo, name, email, department
- Can select user from results
- Shows "No results found" if no matches

### US-003: Auto-Detect Vendor Accounts
**As a** technician
**I want** vendor accounts to be automatically detected based on group membership
**So that** I don't have to manually check which accounts are needed

**Acceptance Criteria:**
- Vendor cards are pre-checked if user is in corresponding group
- "Auto-detected" badge appears on pre-checked vendors
- Can manually check/uncheck additional vendors
- Shows user's group memberships

### US-004: Configure Vendor-Specific Fields
**As a** technician
**I want to** adjust vendor-specific settings before creating accounts
**So that** the account is created with correct permissions and location

**Acceptance Criteria:**
- Fields are pre-populated from Entra ID
- Can edit text fields, select from dropdowns, check boxes
- Required fields are indicated
- Validation errors are shown clearly
- Can reset to defaults

### US-005: Monitor Automation Progress
**As a** technician
**I want to** see real-time progress of account creation
**So that** I know what's happening and can identify errors

**Acceptance Criteria:**
- Each vendor shows status indicator (red, yellow, green, orange)
- Progress bars update in real-time
- Live log shows activity
- Screenshots update as browser navigates
- Can view detailed logs and screenshots

### US-006: Handle Errors Gracefully
**As a** technician
**I want** errors to be clearly communicated with options to retry
**So that** I can resolve issues without starting over

**Acceptance Criteria:**
- Error status is clearly indicated (orange)
- Error message is displayed
- Screenshot shows where error occurred
- Can click "Retry" to attempt again
- Can continue with other vendors after error

### US-007: Export Report
**As a** technician
**I want to** export a report of created accounts
**So that** I have documentation for compliance and auditing

**Acceptance Criteria:**
- Can export as PDF or CSV
- Report includes user info, vendors, status, timestamps
- Report is saved to local file
- Can open report after generation

---

## Appendix C: Technical Dependencies

**Python Packages (requirements.txt):**
```
# GUI Framework
customtkinter==5.2.0

# Browser Automation
playwright==1.40.0

# Microsoft Authentication (Delegated Permissions)
msal==1.25.0

# Azure Key Vault
azure-keyvault-secrets==4.7.0
azure-identity==1.15.0

# HTTP Requests
requests==2.31.0

# Environment Variables (Development only)
python-dotenv==1.0.0

# Image Processing
Pillow==10.1.0

# PDF Generation
reportlab==4.0.7

# Async Support
asyncio==3.4.3
```

**Installation Commands:**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

**Azure App Registration Requirements:**
- Register app in Azure AD as **Public Client Application**
- Configure redirect URI: `http://localhost:8400` or `http://localhost`
- Grant **Delegated** API permissions:
  - Microsoft Graph: User.Read.All (delegated)
  - Microsoft Graph: GroupMember.Read.All (delegated)
  - Microsoft Graph: Group.Read.All (delegated)
- **DO NOT generate client secret** - not needed for delegated permissions
- Note Tenant ID and Client ID (these are public identifiers)
- Enable "Allow public client flows" in Authentication settings

**Azure Key Vault Setup:**
- Create Key Vault: `nexus-vendor-credentials`
- Enable Azure RBAC for access control
- Create Entra ID group: `Nexus_Users`
- Assign "Key Vault Secrets User" role to `Nexus_Users` group
- Add vendor credentials as secrets:
  - `accountchek-username`
  - `accountchek-password`
  - `accountchek-url`
  - (Repeat for each vendor)
- Users' tokens automatically grant Key Vault access based on group membership

---

**End of Design Specification**
