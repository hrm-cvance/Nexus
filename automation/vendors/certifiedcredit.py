"""
Certified Credit User Provisioning Automation

This module automates the creation of user accounts in Certified Credit
using Playwright for web automation.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from playwright.async_api import async_playwright, Page, Browser, Playwright

from models.user import EntraUser
from services.keyvault_service import KeyVaultService

# Configure logging
logger = logging.getLogger('automation.vendors.certifiedcredit')


class CertifiedCreditAutomation:
    """Handles Certified Credit user provisioning automation"""

    def __init__(self, config_path: str, keyvault: KeyVaultService):
        """
        Initialize Certified Credit automation

        Args:
            config_path: Path to vendor config.json
            keyvault: KeyVaultService instance for credential retrieval
        """
        self.config_path = Path(config_path)
        self.keyvault = keyvault
        self.config = self._load_config()
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.popup: Optional[Page] = None  # Popup window for user form
        self.current_user: Optional[EntraUser] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load vendor configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded config from {self.config_path}")
        return config

    async def create_account(self, user: EntraUser, headless: bool = False) -> Dict[str, Any]:
        """
        Create a Certified Credit account for the given user

        Args:
            user: EntraUser object with user details
            headless: Whether to run browser in headless mode

        Returns:
            Dict with success status and messages
        """
        self.current_user = user
        logger.info(f"Starting Certified Credit automation for {user.display_name}")

        result = {
            'success': False,
            'user': user.display_name,
            'messages': [],
            'warnings': [],
            'errors': []
        }

        try:
            # Prepare user data
            user_data = self._prepare_user_data(user)
            logger.info(f"Prepared user data: {user_data}")

            # Start browser
            await self._start_browser(headless=headless)

            # Login
            await self._login()
            result['messages'].append("✓ Logged in successfully")

            # Wait for MFA completion
            await self._wait_for_mfa_completion()
            result['messages'].append("✓ MFA completed")

            # Navigate to User Setup
            await self._navigate_to_user_setup()
            result['messages'].append("✓ Navigated to User Setup")

            # Click Add button
            await self._click_add_button()
            result['messages'].append("✓ Opened New User form")

            # Try to create user with duplicate username handling
            max_attempts = 10
            original_username = user_data['username']

            for attempt in range(max_attempts):
                if attempt > 0:
                    # Modify username by adding a number
                    user_data['username'] = f"{original_username}{attempt}"
                    logger.info(f"Retrying with username: {user_data['username']}")
                    result['messages'].append(f"ℹ Retrying with username: {user_data['username']}")

                    # Clear and refill username field
                    await self.popup.fill('#ctrlBasicInfo_txtLogin_Input', '')
                    await asyncio.sleep(0.5)
                    await self.popup.fill('#ctrlBasicInfo_txtLogin_Input', user_data['username'])
                    logger.info(f"Updated username to: {user_data['username']}")

                # Fill user form (first time) or just update username (retry)
                if attempt == 0:
                    await self._fill_user_form(user_data)
                    result['messages'].append("✓ Filled user form")

                    # Configure Access Permissions
                    await self._configure_access_permissions()
                    result['messages'].append("✓ Configured access permissions")

                # Save user and check for duplicate
                save_result = await self._save_user()

                if save_result:
                    # Save succeeded, no duplicate
                    result['messages'].append("✓ Saved user")
                    if attempt > 0:
                        result['warnings'].append(f"Username '{original_username}' was taken, used '{user_data['username']}' instead")
                    break
                else:
                    # Duplicate detected
                    if attempt == max_attempts - 1:
                        error_msg = f"Could not find available username after {max_attempts} attempts"
                        logger.error(error_msg)
                        result['errors'].append(error_msg)
                        result['success'] = False
                        return result
                    logger.info(f"Username '{user_data['username']}' already exists, trying next number...")

            # Configure Restrictions
            await self._configure_restrictions(user_data)
            result['messages'].append("✓ Configured restrictions")

            # Final save
            await self._save_user()
            result['messages'].append("✓ User created successfully")

            result['success'] = True
            logger.info(f"✓ Successfully created Certified Credit account for {user.display_name}")

        except Exception as e:
            error_msg = f"Error during Certified Credit automation: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            result['success'] = False

            # Take error screenshot
            try:
                if self.page:
                    await self.page.screenshot(path=f'certifiedcredit_error_{user.display_name.replace(" ", "_")}.png')
            except:
                pass

        finally:
            await self._cleanup()

        logger.info(f"Certified Credit result: {result}")
        return result

    def _prepare_user_data(self, user: EntraUser) -> Dict[str, Any]:
        """
        Prepare user data for Certified Credit form

        Args:
            user: EntraUser object

        Returns:
            Dict with formatted user data
        """
        # Generate username using First initial + Last name convention
        first_name = user.given_name or user.display_name.split()[0]
        last_name = user.surname or user.display_name.split()[-1]
        username = f"{first_name[0]}{last_name}".replace(" ", "")

        # Get default password from Key Vault
        default_password = self.keyvault.get_vendor_credential('certifiedcredit', 'default-password')

        user_data = {
            'username': username,
            'firstName': first_name,
            'lastName': last_name,
            'fullName': user.display_name,
            'email': user.mail or user.user_principal_name,
            'phone': user.business_phones[0] if user.business_phones else '',
            'cellPhone': user.mobile_phone or '',
            'department': user.department or '',
            'jobTitle': '',  # Leave blank per instructions
            'fax': '',  # Leave blank unless available
            'fullAddress': '',  # Leave blank per instructions
            'password': default_password
        }

        return user_data

    async def _start_browser(self, headless: bool = False):
        """Start Playwright browser"""
        logger.info("Starting browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=['--start-maximized']
        )
        context = await self.browser.new_context(
            viewport=None  # Use maximized window size
        )
        self.page = await context.new_page()
        logger.info("Browser started")

    async def _cleanup(self):
        """Close browser and cleanup resources"""
        logger.info("Cleaning up...")
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser closed")
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")

    async def _login(self):
        """Login to Certified Credit"""
        logger.info("Logging in to Certified Credit...")

        # Get credentials from Key Vault
        login_url = self.keyvault.get_vendor_credential('certifiedcredit', 'login-url')
        admin_username = self.keyvault.get_vendor_credential('certifiedcredit', 'admin-username')
        admin_password = self.keyvault.get_vendor_credential('certifiedcredit', 'admin-password')

        # Navigate to login page
        await self.page.goto(login_url)
        await self.page.wait_for_load_state('networkidle')

        try:
            # Take screenshot of login page
            await self.page.screenshot(path='certifiedcredit_login_page.png')
            logger.info("Screenshot saved: certifiedcredit_login_page.png")

            # Wait for login form
            await self.page.wait_for_selector('input[type="text"], input[name*="user"], input[name*="User"]', timeout=10000)

            # Fill username
            await self.page.fill('input[type="text"], input[name*="user"], input[name*="User"]', admin_username)
            logger.info(f"Filled username")

            # Fill password
            await self.page.fill('input[type="password"]', admin_password)
            logger.info("Filled password")

            # Save HTML for inspection
            page_html = await self.page.content()
            with open('certifiedcredit_login_page.html', 'w', encoding='utf-8') as f:
                f.write(page_html)

            # Take screenshot before clicking login
            await self.page.screenshot(path='certifiedcredit_before_login.png')

            # Click login button (image element)
            await self.page.click('img#btnLogin')
            logger.info("Clicked login button")

            # Wait for page to load
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)

            logger.info("✓ Login credentials submitted")

        except Exception as e:
            logger.error(f"Login failed: {e}")
            await self.page.screenshot(path='certifiedcredit_login_error.png')
            raise

    async def _wait_for_mfa_completion(self):
        """
        Wait for user to complete MFA manually

        Monitors the page for MFA prompts and waits for the home page to appear,
        indicating MFA completion.
        """
        logger.info("Checking for MFA requirement...")

        mfa_config = self.config.get('mfa', {})
        if not mfa_config.get('enabled', False):
            logger.info("MFA not configured, skipping")
            return

        max_wait_time = mfa_config.get('wait_timeout', 300000) / 1000  # Convert to seconds
        check_interval = mfa_config.get('check_interval', 2000) / 1000  # Convert to seconds
        success_indicators = mfa_config['detection']['success_indicators']

        # Take screenshot to see current page
        await self.page.screenshot(path='certifiedcredit_after_login.png')
        logger.info("Screenshot after login saved")

        # Check if we're already on the home page (no MFA required)
        try:
            for indicator in success_indicators:
                element = await self.page.query_selector(indicator)
                if element:
                    logger.info("Home page detected - no MFA required or already completed")
                    return
        except:
            pass

        # MFA may be required - wait for completion
        logger.info("⏸ Waiting for MFA completion - please enter your verification code in the browser")
        logger.info(f"Maximum wait time: {max_wait_time} seconds")

        elapsed_time = 0
        while elapsed_time < max_wait_time:
            await asyncio.sleep(check_interval)
            elapsed_time += check_interval

            # Check for success indicators (home page elements)
            try:
                for indicator in success_indicators:
                    element = await self.page.query_selector(indicator)
                    if element and await element.is_visible():
                        logger.info(f"✓ MFA completed - detected: {indicator}")
                        await self.page.screenshot(path='certifiedcredit_mfa_complete.png')
                        return
            except Exception as e:
                logger.debug(f"Error checking for success indicators: {e}")

            # Log progress every 30 seconds
            if int(elapsed_time) % 30 == 0:
                logger.info(f"Still waiting for MFA... ({int(elapsed_time)}/{int(max_wait_time)} seconds)")

        # Timeout reached
        logger.error(f"MFA timeout after {max_wait_time} seconds")
        await self.page.screenshot(path='certifiedcredit_mfa_timeout.png')
        raise TimeoutError("MFA completion timeout - please complete authentication within the time limit")

    async def _navigate_to_user_setup(self):
        """Navigate to Tools > User Setup"""
        logger.info("Navigating to User Setup...")

        try:
            # Take screenshot of home page
            await self.page.screenshot(path='certifiedcredit_home_page.png')

            # Click "User Setup" link
            await self.page.click('a:has-text("User Setup")', timeout=10000)
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(1)

            # Take screenshot of User Setup page
            await self.page.screenshot(path='certifiedcredit_user_setup_page.png')

            # Save HTML for inspection
            page_html = await self.page.content()
            with open('certifiedcredit_user_setup_page.html', 'w', encoding='utf-8') as f:
                f.write(page_html)
            logger.info("User Setup page loaded, HTML saved")

        except Exception as e:
            logger.error(f"Navigation to User Setup failed: {e}")
            await self.page.screenshot(path='certifiedcredit_navigation_error.png')
            raise

    async def _click_add_button(self):
        """Click the Add button to open New User popup window"""
        logger.info("Clicking Add button...")

        try:
            # Set up listener for new popup window
            logger.info("Setting up popup listener...")
            async with self.page.expect_popup(timeout=30000) as popup_info:
                # Click "Add" button
                logger.info("Clicking Add button to trigger popup...")
                await self.page.click('input[value="Add"]', timeout=10000)
                logger.info("Add button clicked, waiting for popup window...")

            # Get the popup window
            popup = await popup_info.value
            logger.info(f"Popup window detected! URL: {popup.url}")

            await popup.wait_for_load_state('domcontentloaded')
            logger.info("Popup window loaded")

            # Switch to popup window for form operations
            self.popup = popup
            await asyncio.sleep(1)

            # Take screenshot of popup
            await self.popup.screenshot(path='certifiedcredit_new_user_form.png')

            # Save HTML for inspection
            popup_html = await self.popup.content()
            with open('certifiedcredit_new_user_form.html', 'w', encoding='utf-8') as f:
                f.write(popup_html)
            logger.info("New User form popup opened and HTML saved")

        except Exception as e:
            logger.error(f"Failed to open New User form: {e}")
            await self.page.screenshot(path='certifiedcredit_add_button_error.png')
            # Save page HTML to debug
            page_html = await self.page.content()
            with open('certifiedcredit_add_button_page.html', 'w', encoding='utf-8') as f:
                f.write(page_html)
            raise

    async def _fill_user_form(self, user_data: Dict[str, Any]):
        """
        Fill the New User form

        Args:
            user_data: User data dictionary
        """
        logger.info("Filling user form...")

        try:
            # Wait for form to load in popup (wait for Full Name field specifically)
            await self.popup.wait_for_selector('#ctrlBasicInfo_txtFullName_Input', timeout=10000)
            logger.info("Form loaded successfully")

            # Department (text field, not dropdown!)
            if user_data['department']:
                await self.popup.fill('#ctrlBasicInfo_txtDepartment_Input', user_data['department'])
                logger.info(f"Filled department: {user_data['department']}")

            # Job Title (leave blank per instructions)
            # Skip this field intentionally

            # Full Name
            await self.popup.fill('#ctrlBasicInfo_txtFullName_Input', user_data['fullName'])
            logger.info(f"Filled full name: {user_data['fullName']}")

            # Phone
            if user_data['phone']:
                await self.popup.fill('#ctrlBasicInfo_txtPhone_Input', user_data['phone'])
                logger.info(f"Filled phone: {user_data['phone']}")

            # Fax
            if user_data['fax']:
                await self.popup.fill('#ctrlBasicInfo_txtFax_Input', user_data['fax'])
                logger.info(f"Filled fax: {user_data['fax']}")

            # Login (username)
            await self.popup.fill('#ctrlBasicInfo_txtLogin_Input', user_data['username'])
            logger.info(f"Filled login: {user_data['username']}")

            # Email
            await self.popup.fill('#ctrlBasicInfo_txtEmail_Input', user_data['email'])
            logger.info(f"Filled email: {user_data['email']}")

            # Cell Phone (for 2FA)
            if user_data['cellPhone']:
                await self.popup.fill('#ctrlBasicInfo_txtCellphone_Input', user_data['cellPhone'])
                logger.info(f"Filled cell phone: {user_data['cellPhone']}")

            # Click "SET PASSWORD MANUALLY" tab/link
            await self.popup.click('#ctrlBasicInfo_ctrlAddUserOptions_lnkSetPwdMan')
            logger.info("Clicked SET PASSWORD MANUALLY")
            await asyncio.sleep(1)

            # Enter password
            await self.popup.fill('#ctrlBasicInfo_ctrlAddUserOptions_txtPassword_Input', user_data['password'])
            logger.info("Filled password")

            # Re-type password
            await self.popup.fill('#ctrlBasicInfo_ctrlAddUserOptions_txtPassword2_Input', user_data['password'])
            logger.info("Filled re-type password")

            # Check "Force user to change password on the first system login" - REQUIRED
            await self.popup.check('#ctrlBasicInfo_ctrlAddUserOptions_chkForceChangePwd')
            logger.info("Checked force password change (REQUIRED)")

            logger.info("Form filled successfully")

        except Exception as e:
            logger.error(f"Form filling failed: {e}")
            await self.popup.screenshot(path='certifiedcredit_form_error.png')
            raise

    async def _configure_access_permissions(self):
        """
        Configure Access Permissions using the admin checkbox trick

        Per instructions:
        1. Check "Is this user an administrator" (checks all yellow boxes)
        2. Uncheck "Is this user an administrator" (keeps permissions)
        3. Change "Rescore Ordering" to "No access"
        """
        logger.info("Configuring access permissions...")

        try:
            # Scroll down to Access Permission section if needed in popup
            await self.popup.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
            await asyncio.sleep(0.5)

            # Step 1: Check "Is this user an administrator"
            await self.popup.check('#chkP_Admin')
            logger.info("Checked 'Is this user an administrator'")
            await asyncio.sleep(0.5)

            # Step 2: Uncheck "Is this user an administrator"
            await self.popup.uncheck('#chkP_Admin')
            logger.info("Unchecked 'Is this user an administrator' - permissions retained")
            await asyncio.sleep(0.5)

            # Step 3: Change "Rescore Ordering" to "No access"
            # First, let's get the available options to see what value we need
            options = await self.popup.evaluate('''() => {
                const select = document.getElementById('cboP_OrderRescore');
                return Array.from(select.options).map(opt => ({
                    value: opt.value,
                    text: opt.textContent.trim()
                }));
            }''')
            logger.info(f"Rescore Ordering options: {options}")

            # Select "No access" option - try different possible values
            try:
                await self.popup.select_option('#cboP_OrderRescore', label='No access')
            except:
                try:
                    await self.popup.select_option('#cboP_OrderRescore', value='N')
                except:
                    logger.warning("Could not set Rescore Ordering to 'No access'")

            # Take screenshot
            await self.popup.screenshot(path='certifiedcredit_permissions_configured.png')

        except Exception as e:
            logger.error(f"Access permissions configuration failed: {e}")
            await self.popup.screenshot(path='certifiedcredit_permissions_error.png')
            raise

    async def _save_user(self):
        """Click Save button in popup"""
        logger.info("Saving user...")

        try:
            # Take screenshot before save
            await self.popup.screenshot(path='certifiedcredit_before_save.png')

            # Click Save button in popup (input type="submit")
            logger.info("⚠️ CLICKING SAVE BUTTON NOW")
            await self.popup.click('input[type="submit"]#btnSave')
            logger.info("✓ Save button clicked successfully")

            # Wait for save to complete
            await asyncio.sleep(2)

            # Check for duplicate login error (case-insensitive partial match)
            try:
                logger.info("Checking page content for duplicate login error...")
                # Check page content for duplicate login message
                page_content = await self.popup.content()
                if 'duplicate' in page_content.lower() and 'login' in page_content.lower():
                    logger.warning("❌ DUPLICATE LOGIN DETECTED in page content")
                    await self.popup.screenshot(path='certifiedcredit_duplicate_login.png')

                    # Save HTML for debugging
                    with open('certifiedcredit_duplicate_error.html', 'w', encoding='utf-8') as f:
                        f.write(page_content)

                    return False  # Indicate duplicate
                else:
                    logger.info("✓ No duplicate login error found")
            except Exception as e:
                logger.warning(f"Error checking for duplicate: {e}")

            await asyncio.sleep(1)
            logger.info("✓ User saved successfully")
            return True  # Successful save

        except Exception as e:
            logger.error(f"Save failed: {e}")
            await self.popup.screenshot(path='certifiedcredit_save_error.png')
            raise

    async def _configure_restrictions(self, user_data: Dict[str, Any]):
        """
        Configure user restrictions in the popup window

        After first save, the popup should remain open.
        We need to:
        1. Wait for the popup to finish saving (it may reload/refresh)
        2. Click Restrictions tab in the popup
        3. Check WORDER box
        """
        logger.info("Configuring restrictions...")

        try:
            # After save, popup closes and we're back on User Setup page
            logger.info("Waiting for popup to close after save...")
            await asyncio.sleep(3)

            # Find the newly created user in the list by DISPLAY NAME (not username)
            logger.info("Finding user in User Setup list by display name...")
            display_name = user_data['fullName']  # Use the full display name

            # Wait for main page to be ready
            await self.page.wait_for_selector('input[value="Add"]', timeout=10000)

            # Take screenshot to see the user list
            await self.page.screenshot(path='certifiedcredit_user_list.png')
            logger.info("Screenshot of user list saved")

            # Find the table row with matching display name and click the Name link
            # We need to find the most recently created user (last in the list with this name)
            username = user_data['username']

            # Use JavaScript to find and click the correct row
            clicked = await self.page.evaluate(f'''() => {{
                const displayName = "{display_name}";

                // Find all rows in the table
                const rows = Array.from(document.querySelectorAll('tr'));

                // Find rows where Name matches displayName
                const matchingRows = rows.filter(row => {{
                    const cells = row.querySelectorAll('td');
                    if (cells.length === 0) return false;
                    const nameCell = cells[0]; // First column is Name
                    return nameCell.textContent.trim().toUpperCase() === displayName.toUpperCase();
                }});

                // Get the last matching row (most recently added)
                if (matchingRows.length > 0) {{
                    const targetRow = matchingRows[matchingRows.length - 1];
                    const nameLink = targetRow.querySelector('td:first-child a');
                    if (nameLink) {{
                        nameLink.click();
                        return true;
                    }}
                }}
                return false;
            }}''')

            if not clicked:
                raise Exception(f"Could not find and click user with display name: {display_name}")

            logger.info(f"Clicked on user by display name: {display_name}")
            await asyncio.sleep(2)

            # Check if a popup opened
            try:
                # Wait briefly for popup
                async with self.page.expect_popup(timeout=3000) as popup_info:
                    pass
                self.popup = await popup_info.value
                await self.popup.wait_for_load_state('domcontentloaded')
                logger.info("User popup opened")
            except:
                # No popup, use main page
                await self.page.wait_for_load_state('networkidle')
                self.popup = self.page
                logger.info("Using main page for user edit")

            # Click Restrictions tab (it's a link at the top)
            await self.popup.click('a:has-text("RESTRICTIONS")')
            logger.info("Clicked Restrictions tab")
            await asyncio.sleep(1)

            # Save HTML to find the checkbox
            restrictions_html = await self.popup.content()
            with open('certifiedcredit_restrictions_tab.html', 'w', encoding='utf-8') as f:
                f.write(restrictions_html)
            logger.info("Saved Restrictions tab HTML")

            # Take screenshot of Restrictions tab
            await self.popup.screenshot(path='certifiedcredit_restrictions_tab.png')

            # Check WORDER checkbox using the correct ID
            await self.popup.check('#chkDisableWebOrder')
            logger.info("Checked WORDER restriction (chkDisableWebOrder)")

            # Take screenshot after checking
            await self.popup.screenshot(path='certifiedcredit_restrictions_configured.png')

        except Exception as e:
            logger.error(f"Restrictions configuration failed: {e}")
            await self.popup.screenshot(path='certifiedcredit_restrictions_error.png')
            raise


async def provision_user(user: EntraUser, config_path: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Provision a Certified Credit user account

    Args:
        user: EntraUser object with user details
        config_path: Path to vendor config.json
        api_key: Optional API key (not used for Certified Credit)

    Returns:
        Dict with status, success boolean, and any messages/errors
    """
    # Get KeyVault service
    from services.config_manager import ConfigManager
    from services.keyvault_service import get_keyvault_service

    config_manager = ConfigManager()
    keyvault = get_keyvault_service()

    # Create automation instance
    automation = CertifiedCreditAutomation(config_path, keyvault)

    # Run automation
    result = await automation.create_account(user, headless=False)

    return result
