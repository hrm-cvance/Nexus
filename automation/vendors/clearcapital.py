"""
ClearCapital Vendor Automation

This module handles automated user provisioning for ClearCapital.

Requirements:
- Azure Key Vault credentials for admin account
- Playwright for browser automation
- User data from Entra ID

Process:
1. Login to ClearCapital secure portal
2. Navigate to My Account > New User
3. Create username using Firstname.Lastname convention
4. Fill user form with Entra ID data
5. Set appropriate roles/permissions
6. Submit and verify success
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClearCapitalAutomation:
    """Handles ClearCapital user account automation"""

    def __init__(self, config_path: str, keyvault: KeyVaultService):
        """
        Initialize ClearCapital automation

        Args:
            config_path: Path to vendor config.json
            keyvault: KeyVaultService instance for credential retrieval
        """
        self.config_path = config_path
        self.keyvault = keyvault
        self.config = self._load_config()
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.current_user: Optional[EntraUser] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load vendor configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded config from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

    async def create_account(self, user: EntraUser, headless: bool = False) -> Dict[str, Any]:
        """
        Create a ClearCapital account for the user

        Args:
            user: EntraUser object with user details
            headless: Run browser in headless mode (default: False for debugging)

        Returns:
            Dict with status, success boolean, and any messages/errors
        """
        self.current_user = user
        result = {
            'success': False,
            'user': user.display_name,
            'messages': [],
            'warnings': [],
            'errors': []
        }

        try:
            logger.info(f"Starting ClearCapital automation for {user.display_name}")

            # Prepare user data
            user_data = self._prepare_user_data(user)
            logger.info(f"Prepared user data: {user_data}")

            # Start browser
            await self._start_browser(headless=headless)

            # Login
            await self._login()
            result['messages'].append("✓ Logged in successfully")

            # Navigate to New User page
            await self._navigate_to_new_user()
            result['messages'].append("✓ Navigated to New User page")

            # Fill user form
            await self._fill_user_form(user_data)
            result['messages'].append("✓ Filled user form")

            # Submit form
            await self._submit_form()
            result['messages'].append("✓ Submitted form")

            # Wait for success confirmation
            success_result = await self._wait_for_success()

            # Handle duplicate username - retry with alternate username
            if success_result.get('duplicate_username'):
                logger.info(f"Username {user_data['username']} already exists, retrying with {user_data['username_if_exists']}")
                result['warnings'].extend(success_result.get('warnings', []))

                # Click "Click here to go back" link to return to form
                try:
                    back_link = await self.page.query_selector('a[href="javascript:history.back();"]')
                    if back_link:
                        await back_link.click()
                        await self.page.wait_for_load_state('networkidle')
                        await asyncio.sleep(1)
                        logger.info("Clicked 'go back' link to return to form")
                except Exception as e:
                    logger.warning(f"Could not click back link, navigating manually: {e}")
                    await self._navigate_to_new_user()

                # Update username to alternate format
                user_data['username'] = user_data['username_if_exists']

                # Fill form again with new username
                await self._fill_user_form(user_data)
                result['messages'].append(f"✓ Retrying with alternate username: {user_data['username']}")

                # Submit form again
                await self._submit_form()

                # Wait for success confirmation again
                success_result = await self._wait_for_success()

            # Merge results
            result['success'] = success_result.get('success', False)
            result['messages'].extend(success_result.get('messages', []))
            result['warnings'].extend(success_result.get('warnings', []))
            result['errors'].extend(success_result.get('errors', []))

            if result['success']:
                logger.info(f"✓ Successfully created ClearCapital account for {user.display_name} with username: {user_data['username']}")
            else:
                logger.warning(f"ClearCapital account creation completed with warnings for {user.display_name}")

        except Exception as e:
            error_msg = f"Error during ClearCapital automation: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            result['success'] = False

            # Take error screenshot
            try:
                if self.page:
                    await self.page.screenshot(path=f'clearcapital_error_{user.display_name.replace(" ", "_")}.png')
            except:
                pass

        finally:
            await self._cleanup()

        logger.info(f"ClearCapital result: {result}")
        return result

    def _format_phone_number(self, phone: str) -> str:
        """
        Format phone number to XXX-XXX-XXXX format

        Args:
            phone: Phone number string (may contain spaces, dashes, parens, etc.)

        Returns:
            Formatted phone number as XXX-XXX-XXXX
        """
        if not phone:
            return ''

        # Remove all non-numeric characters
        digits = ''.join(c for c in phone if c.isdigit())

        # Handle different length numbers
        if len(digits) == 10:
            # Format as XXX-XXX-XXXX
            return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
        elif len(digits) == 11 and digits[0] == '1':
            # Remove leading 1 and format
            return f"{digits[1:4]}-{digits[4:7]}-{digits[7:11]}"
        else:
            # Return original if not standard format
            return phone

    def _prepare_user_data(self, user: EntraUser) -> Dict[str, Any]:
        """
        Prepare user data for ClearCapital form

        Args:
            user: EntraUser object

        Returns:
            Dict with formatted user data
        """
        # Generate username using Firstname.Lastname convention
        first_name = user.given_name or user.display_name.split()[0]
        last_name = user.surname or user.display_name.split()[-1]
        username = f"{first_name}.{last_name}"

        # Get default settings from config
        user_settings = self.config.get('user_settings', {})
        default_roles = user_settings.get('default_roles', {})

        # Format phone numbers
        business_phone = user.business_phones[0] if user.business_phones else ''
        formatted_phone = self._format_phone_number(business_phone)
        formatted_mobile = self._format_phone_number(user.mobile_phone or '')

        user_data = {
            'username': username,
            'username_if_exists': f"{username}1",  # Append 1 if username exists
            'firstName': first_name,
            'lastName': last_name,
            'fullName': user.display_name,
            'email': user.mail or user.user_principal_name,
            'phone': formatted_phone,
            'mobilePhone': formatted_mobile,
            'accountActive': user_settings.get('default_account_active', True),
            'roles': default_roles
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
        """Login to ClearCapital using Key Vault credentials"""
        logger.info("Logging in to ClearCapital...")

        # Get login credentials from Key Vault
        try:
            login_url = self.keyvault.get_vendor_credential('clearcapital', 'login-url')
            admin_username = self.keyvault.get_vendor_credential('clearcapital', 'admin-username')
            admin_password = self.keyvault.get_vendor_credential('clearcapital', 'admin-password')
        except Exception as e:
            logger.error(f"Failed to retrieve login credentials from Key Vault: {e}")
            raise

        # Navigate to login page
        await self.page.goto(login_url)
        await self.page.wait_for_load_state('networkidle')

        # ClearCapital has a two-step login process:
        # Step 1: Enter username and click "Next"
        # Step 2: Enter password and submit
        try:
            # Step 1: Fill username and click Next
            await self.page.wait_for_selector('input[type="text"], input[type="email"], input[name*="user"]', timeout=10000)

            # Fill username field
            await self.page.fill('input[type="text"], input[type="email"], input[name*="user"]', admin_username)
            logger.info("Filled username field")

            # Click Next button (ID: submitButton, value: "Next")
            await self.page.click('#submitButton')
            logger.info("Clicked Next button")

            # Wait for password page to load
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(1)

            # Step 2: Fill password and submit
            await self.page.wait_for_selector('input[type="password"]', timeout=10000)

            # Fill password field
            await self.page.fill('input[type="password"]', admin_password)
            logger.info("Filled password field")

            # Click submit button (could be different ID, will check if this fails)
            await self.page.click('button[type="submit"], input[type="submit"]')
            logger.info("Clicked submit button")

            # Wait for navigation to complete
            await self.page.wait_for_load_state('networkidle')
            logger.info("✓ Login successful")

            # Handle Terms of Use agreement popup if it appears
            await asyncio.sleep(2)
            try:
                # Check if Terms of Use popup is present (button ID: agree-link)
                agree_button = await self.page.query_selector('#agree-link')
                if agree_button:
                    logger.info("Terms of Use popup detected, clicking I Agree...")
                    await agree_button.click()
                    await self.page.wait_for_load_state('networkidle')
                    await asyncio.sleep(1)
                    logger.info("✓ Terms of Use accepted")
            except Exception as terms_error:
                # Terms popup might not always appear, so this is optional
                logger.debug(f"No Terms of Use popup found (this is normal): {terms_error}")

        except Exception as e:
            logger.error(f"Login failed: {e}")
            await self.page.screenshot(path='clearcapital_login_error.png')
            raise

    async def _navigate_to_new_user(self):
        """Navigate to New User form via My Account > User Accounts > New User"""
        logger.info("Navigating to New User page...")

        try:
            # Step 1: Click "My Account"
            await self.page.click('text="My Account"')
            logger.info("Clicked My Account")
            await asyncio.sleep(1)

            # Step 2: Click "User Accounts" link
            await self.page.click('a[href="https://secure.clearcapital.com/secure/outsource/account/account_company.cfm"]')
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(1)
            logger.info("User Accounts page loaded")

            # Step 3: Click "New User" button
            await self.page.click('a[href="user_detail.cfm?user=-9999"]')
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(1)
            logger.info("New User form loaded")

        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            await self.page.screenshot(path='clearcapital_navigation_error.png')
            raise

    async def _fill_user_form(self, user_data: Dict[str, Any]):
        """
        Fill the new user form

        Args:
            user_data: User data dictionary
        """
        logger.info("Filling user form...")

        try:
            # Wait for form to load
            await self.page.wait_for_selector('#CUST_USERNAME_S', timeout=10000)

            # Login Username (ID: CUST_USERNAME_S) - with convention Firstname.Lastname
            await self.page.fill('#CUST_USERNAME_S', user_data['username'])
            logger.info(f"Filled login username: {user_data['username']}")

            # Account Active - radio buttons (name: ACTIVE_B, value: 1=Yes, 0=No)
            if user_data['accountActive']:
                await self.page.check('input[name="ACTIVE_B"][value="1"]')
                logger.info("Set account to Active")
            else:
                await self.page.check('input[name="ACTIVE_B"][value="0"]')
                logger.info("Set account to Inactive")

            # Full Name (ID: CUST_USER_NAME_S)
            await self.page.fill('#CUST_USER_NAME_S', user_data['fullName'])
            logger.info(f"Filled full name: {user_data['fullName']}")

            # Email (ID: CUST_EMAIL_S)
            await self.page.fill('#CUST_EMAIL_S', user_data['email'])
            logger.info(f"Filled email: {user_data['email']}")

            # Phone (ID: CUST_PHONE_DIRECT_S)
            if user_data['phone']:
                await self.page.fill('#CUST_PHONE_DIRECT_S', user_data['phone'])
                logger.info(f"Filled phone: {user_data['phone']}")

            # Phone Extension (ID: CUST_PHONE_DIRECT_EXT_S) - leave blank
            # await self.page.fill('#CUST_PHONE_DIRECT_EXT_S', '')

            # Mobile Phone (ID: MOBILE_PHONE)
            if user_data['mobilePhone']:
                await self.page.fill('#MOBILE_PHONE', user_data['mobilePhone'])
                logger.info(f"Filled mobile phone: {user_data['mobilePhone']}")

            # Roles/Permissions - checkboxes by roleId value
            # roleId=9: Create Orders (checked by default)
            # roleId=10: View All Orders (checked by default)
            # roleId=11: Accounts Payable
            # roleId=12: User Management

            roles = user_data.get('roles', {})

            # Create Orders - roleId=9 (default checked, uncheck if false)
            if not roles.get('create_orders', True):
                await self.page.uncheck('input[name="roleId"][value="9"]')
                logger.info("Unchecked 'Create Orders'")

            # View All Orders is always checked (roleId=10)
            # This corresponds to the second checkbox which is checked by default

            # Accounts Payable - roleId=11
            if roles.get('accounts_payable', False):
                await self.page.check('input[name="roleId"][value="11"]')
                logger.info("Checked 'Accounts Payable'")

            # User Management - roleId=12
            if roles.get('user_management', False):
                await self.page.check('input[name="roleId"][value="12"]')
                logger.info("Checked 'User Management'")

            logger.info("Form filled successfully")

        except Exception as e:
            logger.error(f"Form filling failed: {e}")
            await self.page.screenshot(path='clearcapital_form_error.png')
            raise

    async def _submit_form(self):
        """Submit the new user form"""
        logger.info("Submitting form...")

        try:
            # Wait for the submit button to be ready
            await self.page.wait_for_selector('#submitAndSend', state='visible', timeout=5000)
            logger.info("Submit button is visible")

            # Scroll to button to ensure it's in view
            await self.page.evaluate('document.getElementById("submitAndSend").scrollIntoView({block: "center"})')
            await asyncio.sleep(0.5)

            # Try to submit the form directly via JavaScript
            # This triggers form validation and submission
            submit_result = await self.page.evaluate('''() => {
                const button = document.getElementById("submitAndSend");
                if (button && button.form) {
                    button.form.submit();
                    return "form.submit()";
                } else if (button) {
                    button.click();
                    return "button.click()";
                } else {
                    return "button not found";
                }
            }''')
            logger.info(f"Submit executed via: {submit_result}")

            # Wait longer for the server to process and respond
            await asyncio.sleep(4)
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            logger.info("✓ Form submitted, waiting for response")

            # Give it extra time for any error messages to render
            await asyncio.sleep(3)

        except Exception as e:
            logger.error(f"Form submission failed: {e}")
            await self.page.screenshot(path='clearcapital_submit_error.png')
            raise

    async def _wait_for_success(self) -> Dict[str, Any]:
        """
        Wait for success confirmation or handle errors

        Returns:
            Dict with success status, messages, and duplicate_username flag
        """
        logger.info("Waiting for success confirmation...")

        result = {
            'success': True,
            'messages': [],
            'warnings': [],
            'errors': [],
            'duplicate_username': False
        }

        # Wait for the response to fully render (ClearCapital may take a moment to check duplicates)
        await asyncio.sleep(5)

        # Take a screenshot to capture the result
        try:
            screenshot_path = Path.home() / 'Desktop' / f'clearcapital_result_{self.current_user.display_name.replace(" ", "_")}.png'
            await self.page.screenshot(path=str(screenshot_path))
            logger.info(f"Screenshot saved to: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Could not save screenshot: {e}")

        # Check for success message or errors
        try:
            # Log current URL
            logger.info(f"Current URL after submit: {self.page.url}")

            # First check for the error heading using selector (more reliable)
            error_heading = await self.page.query_selector('text=/Sorry!.*errors exist/i')
            logger.info(f"Error heading found: {error_heading is not None}")

            if error_heading:
                logger.warning("Error page detected (Sorry! The following errors exist!)")

                # Get page HTML to search for error text
                page_html = await self.page.content()

                # Check for ClearCapital's specific duplicate username error message
                # "Please choose a different username. 'XXX' is already being used."
                duplicate_indicators = [
                    'already being used',
                    'choose a different username',
                    'username already',
                    'already exists',
                    'user already exists',
                    'duplicate username',
                    'username is taken',
                    'already in use'
                ]

                for indicator in duplicate_indicators:
                    if indicator.lower() in page_html.lower():
                        logger.warning(f"Duplicate username detected with indicator: '{indicator}'")
                        result['duplicate_username'] = True
                        result['success'] = False
                        result['warnings'].append("Username already exists, will retry with alternate username")
                        return result

                # Error page but not duplicate - some other error
                logger.warning("Error page detected but no duplicate username indicator found")
                result['errors'].append("Form submission failed - errors were found")
                result['success'] = False
                return result

            # Look for other error messages
            error_elements = await self.page.query_selector_all('.error, .alert-error, .alert-danger, [class*="error"]')
            for elem in error_elements:
                if await elem.is_visible():
                    text = await elem.text_content()
                    logger.warning(f"Error message: {text}")
                    result['errors'].append(text)
                    result['success'] = False

            # Only consider it successful if we actually navigated away from the form
            # The user_detail.cfm page should redirect on success
            if 'user_detail.cfm?user=-9999' in self.page.url:
                # Still on the new user form - this means there was an error
                logger.warning("Still on new user form after submit - likely an error occurred")
                result['success'] = False
                if not result['errors']:
                    result['errors'].append("Form submission did not complete - still on form page")
            else:
                # Successfully navigated away from form
                result['messages'].append("✓ User created successfully")
                result['success'] = True

            # Look for success indicators
            success_elements = await self.page.query_selector_all('.success, .alert-success, [class*="success"]')
            for elem in success_elements:
                if await elem.is_visible():
                    text = await elem.text_content()
                    logger.info(f"Success message: {text}")
                    result['messages'].append(f"✓ {text}")

        except Exception as e:
            logger.warning(f"Could not verify success: {e}")

        return result


async def provision_user(user: EntraUser, config_path: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Provision a ClearCapital user account

    Args:
        user: EntraUser object with user details
        config_path: Path to vendor config.json
        api_key: Optional API key (not used for ClearCapital)

    Returns:
        Dict with status, success boolean, and any messages/errors
    """
    # Get KeyVault service
    from services.config_manager import ConfigManager
    from services.keyvault_service import get_keyvault_service

    config_manager = ConfigManager()
    keyvault = get_keyvault_service()

    # Create automation instance
    automation = ClearCapitalAutomation(config_path, keyvault)

    # Run automation
    result = await automation.create_account(user, headless=False)

    return result
