"""
Test script for Certified Credit Restrictions configuration only

This script tests just the restrictions tab configuration
without creating a new user.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def test_restrictions():
    """Test Certified Credit restrictions configuration"""

    # Import Key Vault service
    import sys
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))

    from services.keyvault_service import get_keyvault_service

    keyvault = get_keyvault_service()

    # Get credentials
    login_url = keyvault.get_vendor_credential('certifiedcredit', 'login-url')
    admin_username = keyvault.get_vendor_credential('certifiedcredit', 'admin-username')
    admin_password = keyvault.get_vendor_credential('certifiedcredit', 'admin-password')

    print("Testing Certified Credit Restrictions Configuration...")
    print("This will:")
    print("1. Login to Certified Credit")
    print("2. Navigate to User Setup")
    print("3. Find and click on 'Test Processor' user")
    print("4. Click RESTRICTIONS tab")
    print("5. Check WORDER checkbox")
    print("6. Save")
    print("-" * 60)

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False, args=['--start-maximized'])
    context = await browser.new_context(viewport=None)
    page = await context.new_page()

    try:
        # Login
        print("Logging in...")
        await page.goto(login_url)
        await page.wait_for_load_state('networkidle')

        await page.wait_for_selector('input[type="text"]', timeout=10000)
        await page.fill('input[type="text"]', admin_username)
        await page.fill('input[type="password"]', admin_password)
        await page.click('img#btnLogin')

        # Wait for MFA if needed
        print("Waiting for MFA (if required) - you have 2 minutes...")
        await asyncio.sleep(5)

        # Check if logged in
        try:
            await page.wait_for_selector('a:has-text("User Setup")', timeout=120000)
            print("[OK] Logged in successfully")
        except:
            print("[FAIL] Login failed or MFA not completed")
            return

        # Navigate to User Setup
        print("Navigating to User Setup...")
        await page.click('a:has-text("User Setup")')
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(1)

        # Take screenshot
        await page.screenshot(path='restrictions_test_user_list.png')
        print("[OK] On User Setup page (screenshot saved)")

        # Find and click "Test Processor"
        print("Looking for 'Test Processor' in the list...")

        # Use JavaScript to click
        clicked = await page.evaluate('''() => {
            const displayName = "TEST PROCESSOR";
            const rows = Array.from(document.querySelectorAll('tr'));
            const matchingRows = rows.filter(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length === 0) return false;
                const nameCell = cells[0];
                return nameCell.textContent.trim().toUpperCase() === displayName;
            });

            if (matchingRows.length > 0) {
                const targetRow = matchingRows[matchingRows.length - 1];
                const nameLink = targetRow.querySelector('td:first-child a');
                if (nameLink) {
                    nameLink.click();
                    return true;
                }
            }
            return false;
        }''')

        if not clicked:
            print("[FAIL] Could not find 'Test Processor' user")
            return

        print("[OK] Clicked on Test Processor")
        await asyncio.sleep(2)

        # Check if popup opened
        try:
            popup = context.pages[-1]  # Get the last opened page
            if popup != page:
                print("[OK] Popup opened")
                working_page = popup
            else:
                print("Using main page (no popup)")
                working_page = page
        except:
            working_page = page
            print("Using main page")

        await working_page.screenshot(path='restrictions_test_user_opened.png')

        # Click RESTRICTIONS tab
        print("Clicking RESTRICTIONS tab...")
        await working_page.click('a:has-text("RESTRICTIONS")')
        await asyncio.sleep(1)
        print("[OK] Clicked RESTRICTIONS tab")

        # Take screenshot
        await working_page.screenshot(path='restrictions_test_tab.png')
        print("[OK] Screenshot of Restrictions tab saved")

        # Save HTML
        html = await working_page.content()
        with open('restrictions_test_tab.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("[OK] HTML saved for inspection")

        # Try to find and check WORDER checkbox
        print("Looking for WORDER checkbox...")

        # Try different selectors
        worder_found = False
        selectors = [
            'input[type="checkbox"][id*="WORDER"]',
            'input[type="checkbox"][name*="WORDER"]',
            'input[type="checkbox"][id*="worder"]',
            'input[type="checkbox"][name*="worder"]',
        ]

        for selector in selectors:
            try:
                checkbox = await working_page.query_selector(selector)
                if checkbox:
                    checkbox_info = await checkbox.evaluate('''el => ({
                        id: el.id,
                        name: el.name,
                        checked: el.checked,
                        visible: el.offsetParent !== null
                    })''')
                    print(f"Found checkbox: {checkbox_info}")

                    if not checkbox_info['checked']:
                        await checkbox.check()
                        print(f"[OK] Checked WORDER checkbox using selector: {selector}")
                        worder_found = True
                        break
                    else:
                        print("Checkbox already checked")
                        worder_found = True
                        break
            except:
                continue

        if not worder_found:
            print("[FAIL] Could not find WORDER checkbox - check HTML file")
            print("   Pausing for 30 seconds so you can inspect...")
            await asyncio.sleep(30)
        else:
            # Take screenshot after checking
            await working_page.screenshot(path='restrictions_test_checked.png')
            print("[OK] Screenshot after checking WORDER saved")

            # Pause so you can verify
            print("\nPausing for 30 seconds - please verify the checkbox is checked...")
            await asyncio.sleep(30)

    finally:
        await browser.close()
        await playwright.stop()
        print("\nTest complete!")


if __name__ == "__main__":
    asyncio.run(test_restrictions())
