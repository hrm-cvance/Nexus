# AccountChek Playwright Automation

This directory contains Playwright automation scripts for managing users in AccountChek.

## Files

- **config.json** - Configuration file containing login credentials and test user data
- **accountchek.spec.js** - Playwright test script with three test scenarios
- **AccountChek SOP.pdf** - Standard Operating Procedures documentation

## Configuration

Edit `config.json` to set your credentials and test data:

```json
{
  "login": {
    "url": "https://verifier.accountchek.com/login",
    "email": "your-email@example.com",
    "password": "your-password"
  },
  "newUser": {
    "firstName": "John",
    "lastName": "Doe",
    "email": "john.doe@example.com",
    "title": "Loan Officer",
    "role": "User",
    "region": "Corporate",
    "branch": "1200 - Eckert Division",
    "password": "HRM_DEFAULT_PASSWORD",
    "mustChangePassword": true
  }
}
```

## Available Tests

The script includes three test scenarios:

1. **Create new user account** - Automates the full user creation workflow
2. **Unlock locked out user** - Finds and unlocks users who are locked out
3. **Reset user password** - Searches for a user and resets their password

## Prerequisites

Install Playwright if not already installed:

```bash
npm init playwright@latest
```

Or if you have an existing project:

```bash
npm install -D @playwright/test
npx playwright install
```

## Running Tests

Run all tests:
```bash
npx playwright test Vendors/AccountChek/accountchek.spec.js
```

Run a specific test:
```bash
npx playwright test Vendors/AccountChek/accountchek.spec.js -g "Create new user"
```

Run with UI mode:
```bash
npx playwright test Vendors/AccountChek/accountchek.spec.js --ui
```

Run in headed mode (see browser):
```bash
npx playwright test Vendors/AccountChek/accountchek.spec.js --headed
```

## Future Integration

This script currently reads from `config.json`. To integrate with Active Directory:

1. Replace the config loading with AD queries
2. Pull user data from AD attributes
3. Map AD groups to AccountChek roles
4. Automate user provisioning based on AD events

## Error Handling

The test includes intelligent error handling:

- **User already exists**: If the email is already taken, the test logs a warning and exits gracefully without failing
- **Other errors**: Displays detailed error information including:
  - Error message from the application
  - User details that were attempted
  - Screenshot location for visual debugging

## Verification

The "Create new user" test now includes comprehensive verification:

1. Checks for success message ("Verifier Saved")
2. Detects and handles error alerts appropriately
3. Verifies the user appears in the user list after creation
4. Captures screenshots at key steps for debugging

All screenshots are saved to the `test-results/` directory.

## Notes

- The selectors in the script may need adjustment based on the actual HTML structure
- Some timing delays (`waitForTimeout`) may need tuning based on network speed
- The script follows the SOP documented in `AccountChek SOP.pdf`
- If a user already exists, the test will pass with a warning rather than failing
