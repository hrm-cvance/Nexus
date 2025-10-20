const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

// Load configuration
const config = JSON.parse(
  fs.readFileSync(path.join(__dirname, 'config.json'), 'utf-8')
);

test.describe('AccountChek User Management', () => {

  test('Create new user account', async ({ page }) => {
    // Navigate to login page
    await page.goto(config.login.url);

    // Login
    await page.fill('input[type="email"], input[name="email"]', config.login.email);
    await page.fill('input[type="password"], input[name="password"]', config.login.password);
    await page.click('button[type="submit"], button:has-text("Login")');

    // Wait for navigation after login
    await page.waitForLoadState('networkidle');

    // Take a screenshot to see what we're dealing with
    await page.screenshot({ path: 'test-results/after-login.png', fullPage: true });

    // Click on Name/dropdown in top right corner - try multiple selectors
    try {
      await page.click('.dropdown-toggle, [class*="user"], [class*="dropdown"]', { timeout: 5000 });
    } catch {
      // If that doesn't work, try looking for the name text
      await page.click('text=/CHRIS/i');
    }

    // Wait for dropdown menu to appear
    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'test-results/dropdown-menu.png', fullPage: true });

    // Click on "Verifiers" option - need to click the link/button in the dropdown
    await page.click('a:has-text("Verifiers")');

    // Wait for User Management page to load
    await page.waitForLoadState('networkidle');

    // Wait for User Management heading to confirm we're on the right page
    await page.waitForSelector('text=User Management', { timeout: 10000 });

    // Give the page a moment to finish any loading
    await page.waitForTimeout(3000);

    // Close the dropdown if it's still open by clicking elsewhere or pressing Escape
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // Take screenshot before clicking New User button
    await page.screenshot({ path: 'test-results/before-new-user-click.png', fullPage: true });

    // Click New User button - try CSS selector or XPath
    const buttons = await page.$$('button, a.btn, a[class*="btn"]');
    for (const btn of buttons) {
      const text = await btn.textContent();
      if (text && text.includes('New User')) {
        await btn.click();
        console.log('Clicked New User button');
        break;
      }
    }

    // Wait for the modal/form dialog to appear
    await page.waitForTimeout(2000);

    // Wait specifically for a form or dialog with form inputs
    await page.waitForSelector('form input, [role="dialog"] input, .modal input', { timeout: 10000 });

    // Take screenshot of the form
    await page.screenshot({ path: 'test-results/new-user-form.png', fullPage: true });

    // Fill form fields using labels to identify them
    await page.getByPlaceholder(/first name/i).fill(config.newUser.firstName);
    await page.getByPlaceholder(/last name/i).fill(config.newUser.lastName);
    await page.getByPlaceholder(/email/i).fill(config.newUser.email);
    await page.getByPlaceholder(/job title/i).fill(config.newUser.title);

    // Select Role
    await page.locator('select').first().selectOption({ label: config.newUser.role });

    // Fill Password
    await page.getByPlaceholder(/password/i).fill(config.newUser.password);

    // Select Region - it's the second select
    const selects = await page.$$('select');
    if (selects.length >= 2) {
      await selects[1].selectOption({ label: config.newUser.region });
      // Wait for branch options to load after selecting region
      await page.waitForTimeout(1000);
    }

    // Select Branch - it's the third select
    if (selects.length >= 3) {
      // Re-get selects after region was selected (may have changed)
      const selectsAfterRegion = await page.$$('select');
      const branchSelect = selectsAfterRegion[2];

      // Get all available branch options
      const branchOptions = await page.evaluate(select => {
        return Array.from(select.options).map(opt => ({ text: opt.text, value: opt.value }));
      }, branchSelect);

      console.log('Available branch options:', branchOptions);

      // Try to find a matching option
      const matchingOption = branchOptions.find(opt =>
        opt.text.includes('1200') || opt.text.includes('Eckert')
      );

      if (matchingOption &&  matchingOption.value) {
        await branchSelect.selectOption({ value: matchingOption.value });
        console.log('Selected branch:', matchingOption.text);
      } else {
        console.log('Could not find matching branch, skipping...');
      }
    }

    // Check "Must Change Password" checkbox - use JavaScript to click it
    if (config.newUser.mustChangePassword) {
      await page.evaluate(() => {
        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        if (checkboxes.length >= 2) {
          checkboxes[1].click();
        }
      });
    }

    // Take screenshot before saving
    await page.screenshot({ path: 'test-results/before-save.png', fullPage: true });

    // Click Save button
    await page.getByRole('button', { name: 'Save' }).click();

    // Wait for confirmation (adjust based on actual behavior)
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Take screenshot after save to see result
    await page.screenshot({ path: 'test-results/after-save.png', fullPage: true });

    // Check for success message
    const successMessage = await page.locator('text=/Verifier Saved|User Created|Success/i').isVisible().catch(() => false);

    // Check for actual error alerts (more specific - only check alerts, not all elements with "error" class)
    const errorAlert = await page.locator('.alert-danger, .alert-error').filter({ hasText: /taken|failed|error/i }).isVisible().catch(() => false);

    if (errorAlert) {
      const errorText = await page.locator('.alert-danger, .alert-error').filter({ hasText: /taken|failed|error/i }).textContent();

      // Check if it's a "user already exists" error
      if (/email.*taken|already.*exist/i.test(errorText)) {
        console.log(`⚠ User already exists: ${config.newUser.email}`);
        console.log('Skipping user creation - user already exists in the system');
        return; // Exit test gracefully
      }

      // For any other error, log details and fail the test
      console.error('='.repeat(60));
      console.error('ERROR CREATING USER');
      console.error('='.repeat(60));
      console.error('Error message:', errorText);
      console.error('User details:', JSON.stringify(config.newUser, null, 2));
      console.error('Screenshot saved to: test-results/after-save.png');
      console.error('='.repeat(60));
      throw new Error(`User creation failed: ${errorText}`);
    }

    // Check if modal is still visible (indicates failure) - only if no success message
    if (!successMessage) {
      const modalStillVisible = await page.locator('[role="dialog"] form, .modal form').isVisible().catch(() => false);
      if (modalStillVisible) {
        console.error('='.repeat(60));
        console.error('ERROR: Modal still visible after save');
        console.error('='.repeat(60));
        console.error('This usually indicates a validation error or form submission failure');
        console.error('User details:', JSON.stringify(config.newUser, null, 2));
        console.error('Screenshot saved to: test-results/after-save.png');
        console.error('='.repeat(60));
        throw new Error('User creation failed: form/modal still visible after save');
      }
    }

    // Wait a moment for the user list to refresh
    await page.waitForTimeout(2000);

    // Verify the user appears in the list
    const userEmail = config.newUser.email;
    const userInList = page.locator(`text=${userEmail}`);

    try {
      await expect(userInList).toBeVisible({ timeout: 5000 });
      console.log(`✓ User ${config.newUser.firstName} ${config.newUser.lastName} (${userEmail}) created successfully and verified in list`);
    } catch (error) {
      console.error(`User ${userEmail} not found in the user list after creation`);
      await page.screenshot({ path: 'test-results/user-not-found.png', fullPage: true });
      throw new Error(`User creation verification failed: ${userEmail} not found in user list`);
    }
  });

  test('Unlock locked out user', async ({ page }) => {
    // Navigate to login page
    await page.goto(config.login.url);

    // Login
    await page.fill('input[type="email"], input[name="email"]', config.login.email);
    await page.fill('input[type="password"], input[name="password"]', config.login.password);
    await page.click('button[type="submit"], button:has-text("Login")');

    // Wait for navigation after login
    await page.waitForLoadState('networkidle');

    // Click on Name dropdown in top right corner
    await page.click('text=/DONNA/i');

    // Click on "Verifiers" option
    await page.click('text=Verifiers');

    // Wait for User Management page to load
    await page.waitForLoadState('networkidle');

    // Click "Locked Out?" button to view locked users
    await page.click('button:has-text("Locked Out?")');

    // Wait for locked users list
    await page.waitForTimeout(1000);

    // Find and click on the locked user (example: searching by email)
    // Adjust selector based on how users are displayed
    const userRow = page.locator(`tr:has-text("${config.newUser.email}")`);
    if (await userRow.count() > 0) {
      await userRow.dblclick();

      // Uncheck "Locked Out" checkbox
      await page.uncheck('input[type="checkbox"]:near(:text("Locked Out"))');

      // Click "Save Edits" button
      await page.click('button:has-text("Save Edits")');

      await page.waitForLoadState('networkidle');

      console.log(`User ${config.newUser.email} unlocked successfully`);
    } else {
      console.log('No locked out users found');
    }
  });

  test('Reset user password', async ({ page }) => {
    // Navigate to login page
    await page.goto(config.login.url);

    // Login
    await page.fill('input[type="email"], input[name="email"]', config.login.email);
    await page.fill('input[type="password"], input[name="password"]', config.login.password);
    await page.click('button[type="submit"], button:has-text("Login")');

    // Wait for navigation after login
    await page.waitForLoadState('networkidle');

    // Click on Name dropdown in top right corner
    await page.click('text=/DONNA/i');

    // Click on "Verifiers" option
    await page.click('text=Verifiers');

    // Wait for User Management page to load
    await page.waitForLoadState('networkidle');

    // Search for user (adjust based on search field availability)
    const searchField = page.locator('input[placeholder*="Firstname"], input[placeholder*="Lastname"], input[placeholder*="Email"]').first();
    await searchField.fill(config.newUser.email);

    // Wait for search results
    await page.waitForTimeout(1000);

    // Click "Reset Password" for the user
    const resetButton = page.locator(`button:has-text("Reset Password"):near(:text("${config.newUser.email}"))`);
    if (await resetButton.count() > 0) {
      await resetButton.click();

      // Wait for confirmation
      await page.waitForLoadState('networkidle');

      console.log(`Password reset for ${config.newUser.email}`);
    } else {
      console.log('User not found or Reset Password button not available');
    }
  });
});
