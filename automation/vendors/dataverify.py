"""
DataVerify Drive automation module for account provisioning

This module handles automated user account creation in DataVerify Drive,
following the username convention: First initial + Last name (e.g., THurley)
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Page

from models.user import EntraUser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataVerifyAutomation:
    """Handles DataVerify Drive user provisioning automation"""

    def __init__(self, config_path: str, keyvault_service):
        """
        Initialize DataVerify automation

        Args:
            config_path: Path to vendor config.json file
            keyvault_service: KeyVault service instance for credential retrieval
        """
        self.config_path = config_path
        self.keyvault = keyvault_service
        self.config = self._load_config()
        self.playwright = None
        self.browser = None
        self.page: Optional[Page] = None
        self.current_user = None

    def _load_config(self) -> Dict[str, Any]:
        """Load vendor configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded config from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            raise

    async def create_account(self, user: EntraUser, headless: bool = True) -> Dict[str, Any]:
        """
        Create a DataVerify account for the given user

        Args:
            user: EntraUser object with user details
            headless: Whether to run browser in headless mode

        Returns:
            Dict with status, success boolean, and any messages/errors
        """
        self.current_user = user
        logger.info(f"Starting DataVerify automation for {user.display_name}")

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

            # Navigate to User Manager
            await self._navigate_to_user_manager()
            result['messages'].append("✓ Navigated to User Manager")

            # Click Add New User
            await self._click_add_new_user()
            result['messages'].append("✓ Opened Add New User form")

            # Try to create user with duplicate username handling
            max_attempts = 10  # Try up to username + numbers 1-9
            original_username = user_data['username']

            for attempt in range(max_attempts):
                if attempt > 0:
                    # Modify username by adding a number
                    user_data['username'] = f"{original_username}{attempt}"
                    logger.info(f"Retrying with username: {user_data['username']}")
                    result['messages'].append(f"ℹ Retrying with username: {user_data['username']}")

                    # Clear the username field and refill
                    await self.page.fill('input[name="username"]', '')
                    await asyncio.sleep(0.5)

                # Fill user form
                await self._fill_user_form(user_data)
                if attempt == 0:
                    result['messages'].append("✓ Filled user form")

                # Submit form and check for duplicate error
                submission_success = await self._submit_form(user_data)

                if submission_success:
                    # No duplicate error, submission succeeded
                    result['messages'].append("✓ Submitted form")
                    if attempt > 0:
                        result['warnings'].append(f"Username '{original_username}' was taken, used '{user_data['username']}' instead")
                    break
                else:
                    # Duplicate username detected
                    if attempt == max_attempts - 1:
                        # Exhausted all attempts
                        error_msg = f"Could not find available username after {max_attempts} attempts"
                        logger.error(error_msg)
                        result['errors'].append(error_msg)
                        result['success'] = False
                        return result
                    # Continue to next attempt
                    logger.info(f"Username '{user_data['username']}' already exists, trying next number...")

            # Wait for success confirmation
            success_result = await self._wait_for_success()
            result['success'] = success_result.get('success', False)
            result['messages'].extend(success_result.get('messages', []))
            result['warnings'].extend(success_result.get('warnings', []))
            result['errors'].extend(success_result.get('errors', []))

            if result['success']:
                logger.info(f"✓ Successfully created DataVerify account for {user.display_name} with username: {user_data['username']}")
            else:
                logger.warning(f"DataVerify account creation completed with warnings for {user.display_name}")

        except Exception as e:
            error_msg = f"Error during DataVerify automation: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            result['success'] = False

            # Take error screenshot
            try:
                if self.page:
                    await self.page.screenshot(path=f'dataverify_error_{user.display_name.replace(" ", "_")}.png')
            except:
                pass

        finally:
            await self._cleanup()

        logger.info(f"DataVerify result: {result}")
        return result

    def _prepare_user_data(self, user: EntraUser) -> Dict[str, Any]:
        """
        Prepare user data for DataVerify form

        Args:
            user: EntraUser object

        Returns:
            Dict with formatted user data
        """
        # Generate username using First initial + Last name convention
        first_name = user.given_name or user.display_name.split()[0]
        last_name = user.surname or user.display_name.split()[-1]
        username = f"{first_name[0]}{last_name}".replace(" ", "")

        # Get default settings from config
        user_settings = self.config.get('user_settings', {})
        form_settings = self.config.get('form_settings', {})

        # Determine user profile based on job title
        job_title = user.job_title or ""
        default_profile = user_settings.get('default_user_profile', 'Processor')

        # Map job title to profile
        if 'underwriter' in job_title.lower():
            user_profile = 'Underwriter'
        elif 'processor' in job_title.lower():
            user_profile = 'Processor'
        else:
            user_profile = default_profile

        user_data = {
            'username': username,
            'firstName': first_name,
            'lastName': last_name,
            'fullName': user.display_name,
            'email': user.mail or user.user_principal_name,
            'phone': user.business_phones[0] if user.business_phones else '',
            'jobTitle': user.job_title or 'Loan Processor',
            'userProfile': user_profile,
            'accountActive': user_settings.get('default_account_active', True),
            'receiveFraudUpdates': form_settings.get('receive_fraud_updates', False),
            'enableXML': form_settings.get('enable_xml', False),
            'permissions': form_settings.get('permissions', {})
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
        """Login to DataVerify"""
        logger.info("Logging in to DataVerify...")

        # Get credentials from Key Vault
        login_url = self.keyvault.get_vendor_credential('dataverify', 'login-url')
        admin_username = self.keyvault.get_vendor_credential('dataverify', 'admin-username')
        admin_password = self.keyvault.get_vendor_credential('dataverify', 'admin-password')

        # Navigate to login page
        await self.page.goto(login_url)
        await self.page.wait_for_load_state('networkidle')

        try:
            # Take screenshot of login page to inspect
            await self.page.screenshot(path='dataverify_login_page.png')
            logger.info("Screenshot saved: dataverify_login_page.png")

            # Get the actual field names from the page
            username_field = await self.page.query_selector('input[type="text"]')
            password_field = await self.page.query_selector('input[type="password"]')

            if username_field:
                username_name = await username_field.get_attribute('name')
                logger.info(f"Username field name: {username_name}")

            if password_field:
                password_name = await password_field.get_attribute('name')
                logger.info(f"Password field name: {password_name}")

            # Wait for login form
            await self.page.wait_for_selector('input[id*="txtUsername"]', timeout=10000)

            # Fill username using exact field ID
            await self.page.fill('input[id*="txtUsername"]', admin_username)
            logger.info(f"Filled username: {admin_username}")

            # Verify username was filled
            username_value = await self.page.input_value('input[id*="txtUsername"]')
            logger.info(f"Username value after fill: {username_value}")

            # Fill password using exact field ID
            await self.page.fill('input[id*="txtPassword"]', admin_password)
            logger.info("Filled password")

            # Verify password was filled
            password_value = await self.page.input_value('input[id*="txtPassword"]')
            logger.info(f"Password length after fill: {len(password_value) if password_value else 0}")

            # Take screenshot before clicking login
            await self.page.screenshot(path='dataverify_before_login.png')
            logger.info("Screenshot before login saved")

            # Click login button
            await self.page.click('input[type="submit"], button[type="submit"]')
            logger.info("Clicked login button")

            # Wait for navigation
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)

            # Check for error message
            error_message = await self.page.query_selector('text="Please enter a valid Username and Password."')
            if error_message:
                logger.error("Login failed - invalid credentials")
                await self.page.screenshot(path='dataverify_login_error.png')
                raise Exception("Invalid username or password. Please check your Key Vault credentials.")

            # Check if we're still on login page
            still_on_login = await self.page.query_selector('text="ACCOUNT LOGIN"')
            if still_on_login:
                logger.error("Still on login page after login attempt")
                await self.page.screenshot(path='dataverify_login_error.png')
                raise Exception("Login failed - still on login page")

            logger.info("✓ Login successful")

        except Exception as e:
            logger.error(f"Login failed: {e}")
            await self.page.screenshot(path='dataverify_login_error.png')
            raise

    async def _navigate_to_user_manager(self):
        """Navigate to Admin > User Manager"""
        logger.info("Navigating to User Manager...")

        try:
            # Click "Admin" tab (the image button)
            await self.page.click('img[src="assets/images/button_admin.jpg"]')
            logger.info("Clicked Admin tab")
            await asyncio.sleep(1)

            # Click "User Manager" link in the dropdown
            await self.page.click('a[id="User Manager"]')
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(1)

            # Take screenshot of User Manager page
            await self.page.screenshot(path='dataverify_user_manager.png')
            logger.info("User Manager page loaded, screenshot saved")

            # Save HTML for inspection
            page_html = await self.page.content()
            with open('dataverify_user_manager.html', 'w', encoding='utf-8') as f:
                f.write(page_html)
            logger.info("User Manager HTML saved")

        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            await self.page.screenshot(path='dataverify_navigation_error.png')
            raise

    async def _click_add_new_user(self):
        """Scroll to bottom and click Add New User button"""
        logger.info("Clicking Add New User...")

        try:
            # Scroll to bottom of page
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1)

            # Take screenshot before clicking
            await self.page.screenshot(path='dataverify_before_add_user.png')
            logger.info("Screenshot before Add New User saved")

            # Search for the button in the HTML
            button_html = await self.page.evaluate('''() => {
                // Look for any element containing "Add New User" or "Add User"
                const buttons = Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"], a'));
                const addButton = buttons.find(el =>
                    el.textContent.includes('Add') ||
                    el.value?.includes('Add') ||
                    el.title?.includes('Add')
                );
                if (addButton) {
                    return {
                        tag: addButton.tagName,
                        text: addButton.textContent || addButton.value,
                        id: addButton.id,
                        name: addButton.name,
                        class: addButton.className,
                        outerHTML: addButton.outerHTML.substring(0, 200)
                    };
                }
                return null;
            }''')
            logger.info(f"Found button info: {button_html}")

            # Try multiple selectors for Add New User button
            try:
                await self.page.click('input[value*="Add"], button:has-text("Add"), a:has-text("Add")', timeout=5000)
                logger.info("Clicked Add button")
            except:
                # If that doesn't work, try to find it by searching the page
                await self.page.click('input[type="button"], input[type="submit"], button', timeout=5000)
                logger.info("Clicked button element")

            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(1)

            # Take screenshot of the add user form
            await self.page.screenshot(path='dataverify_add_user_form.png')

            # Save HTML for inspection
            form_html = await self.page.content()
            with open('dataverify_add_user_form.html', 'w', encoding='utf-8') as f:
                f.write(form_html)
            logger.info("Add user form loaded and saved")

        except Exception as e:
            logger.error(f"Failed to click Add New User: {e}")
            await self.page.screenshot(path='dataverify_add_user_error.png')
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
            await self.page.wait_for_selector('input, select', timeout=10000)

            # Username - First initial + Last name
            await self.page.fill('input[name="username"]', user_data['username'])
            logger.info(f"Filled username: {user_data['username']}")

            # First Name
            await self.page.fill('input[name="firstName"]', user_data['firstName'])
            logger.info(f"Filled first name: {user_data['firstName']}")

            # Last Name
            await self.page.fill('input[name="lastName"]', user_data['lastName'])
            logger.info(f"Filled last name: {user_data['lastName']}")

            # Account Status - Active
            if user_data['accountActive']:
                try:
                    await self.page.select_option('select[name="userAccountStatusTypeCode"]', 'ACTIVE')
                    logger.info("Set account to Active")
                except:
                    pass

            # Department (if available)
            department = user_data.get('department', '')
            if department:
                try:
                    await self.page.fill('input[name="department"]', department)
                    logger.info(f"Filled department: {department}")
                except:
                    pass

            # Job Title (text field, not dropdown)
            if user_data['jobTitle']:
                try:
                    await self.page.fill('input[name="jobTitle"]', user_data['jobTitle'])
                    logger.info(f"Filled job title: {user_data['jobTitle']}")
                except Exception as e:
                    logger.warning(f"Could not fill job title: {e}")

            # Email
            await self.page.fill('input[name="email"]', user_data['email'])
            logger.info(f"Filled email: {user_data['email']}")

            # Phone (if available)
            if user_data['phone']:
                try:
                    await self.page.fill('input[name="phone"]', user_data['phone'])
                    logger.info(f"Filled phone: {user_data['phone']}")
                except:
                    pass

            # User Profile dropdown - Look for the value (ID) that matches userProfile text
            try:
                # Get all options and find the one that matches our user profile
                profile_options = await self.page.evaluate('''() => {
                    const select = document.querySelector('select[name="userProfile"]');
                    return Array.from(select.options).map(opt => ({
                        value: opt.value,
                        text: opt.textContent.trim()
                    }));
                }''')
                logger.info(f"Available user profiles: {profile_options}")

                # Find the matching profile
                target_profile = user_data['userProfile']
                matching_option = next((opt for opt in profile_options if target_profile.lower() in opt['text'].lower()), None)

                if matching_option:
                    await self.page.select_option('select[name="userProfile"]', matching_option['value'])
                    logger.info(f"Selected user profile: {matching_option['text']} (value={matching_option['value']})")
                else:
                    logger.warning(f"Could not find matching user profile for: {target_profile}")
            except Exception as e:
                logger.warning(f"Could not select user profile: {e}")

            # Checkboxes for fraud updates, XML, etc.
            if user_data['receiveFraudUpdates']:
                try:
                    await self.page.check('input[type="checkbox"][name*="fraud"]')
                    logger.info("Checked: Receive Mortgage Fraud News Article Updates")
                except:
                    pass

            logger.info("Form filled successfully")

        except Exception as e:
            logger.error(f"Form filling failed: {e}")
            await self.page.screenshot(path='dataverify_form_error.png')
            raise

    async def _submit_form(self, user_data: Dict[str, Any]) -> bool:
        """
        Submit the new user form and handle duplicate username errors

        Args:
            user_data: User data dictionary (for retry with modified username)

        Returns:
            True if submission succeeded, False if duplicate username error
        """
        logger.info("Submitting form...")

        try:
            # Take screenshot before submitting
            await self.page.screenshot(path='dataverify_before_submit.png')
            logger.info("Screenshot before submit saved")

            # Look for save/submit button using JavaScript
            submit_result = await self.page.evaluate('''() => {
                // Look for Save buttons
                const buttons = Array.from(document.querySelectorAll('input[type="button"], input[type="submit"], button'));
                const saveButton = buttons.find(btn =>
                    btn.value?.includes('Save') ||
                    btn.textContent?.includes('Save') ||
                    btn.innerText?.includes('Save')
                );

                if (saveButton) {
                    const buttonInfo = {
                        tag: saveButton.tagName,
                        type: saveButton.type,
                        value: saveButton.value || saveButton.textContent,
                        id: saveButton.id,
                        name: saveButton.name
                    };

                    saveButton.click();
                    return {result: "button.click()", button: buttonInfo};
                } else {
                    return {result: "button not found", button: null};
                }
            }''')
            logger.info(f"Submit executed: {submit_result}")

            # Wait for response
            await asyncio.sleep(3)
            await self.page.wait_for_load_state('networkidle', timeout=15000)

            # Check for duplicate username error
            duplicate_error = await self.page.query_selector('text="ERROR: The chosen username is already in use. Please select another username."')
            if duplicate_error:
                logger.warning("Duplicate username detected")
                await self.page.screenshot(path='dataverify_duplicate_username.png')
                return False  # Indicate duplicate username

            logger.info("✓ Form submitted")

            # Extra time for confirmation
            await asyncio.sleep(2)

            return True  # Successful submission

        except Exception as e:
            logger.error(f"Form submission failed: {e}")
            await self.page.screenshot(path='dataverify_submit_error.png')
            raise

    async def _wait_for_success(self) -> Dict[str, Any]:
        """
        Wait for success confirmation or handle errors

        Returns:
            Dict with success status and messages
        """
        logger.info("Waiting for success confirmation...")

        result = {
            'success': True,
            'messages': [],
            'warnings': [],
            'errors': []
        }

        # Wait for response to render
        await asyncio.sleep(3)

        # Take screenshot
        try:
            screenshot_path = Path.home() / 'Desktop' / f'dataverify_result_{self.current_user.display_name.replace(" ", "_")}.png'
            await self.page.screenshot(path=str(screenshot_path))
            logger.info(f"Screenshot saved to: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Could not save screenshot: {e}")

        try:
            # Check current URL
            logger.info(f"Current URL after submit: {self.page.url}")

            # Check for success indicators
            page_text = await self.page.inner_text('body')

            # Look for success messages
            if 'user created' in page_text.lower() or 'successfully' in page_text.lower():
                result['messages'].append("✓ User created successfully")
                result['success'] = True
            # Check if we're back on the user list (success indicator)
            elif 'user manager' in page_text.lower() or 'user account manager' in page_text.lower():
                result['messages'].append("✓ User created successfully")
                result['success'] = True
            else:
                # Check if still on form page
                if 'add new user' in page_text.lower():
                    logger.warning("Still on add user form - may indicate error")
                    result['warnings'].append("Form submission unclear - please verify user was created")

            # Look for error messages
            error_elements = await self.page.query_selector_all('.error, .alert, [class*="error"]')
            for elem in error_elements:
                if await elem.is_visible():
                    text = await elem.text_content()
                    if text and text.strip():
                        logger.warning(f"Error message: {text}")
                        result['errors'].append(text)
                        result['success'] = False

        except Exception as e:
            logger.warning(f"Could not verify success: {e}")

        return result


async def provision_user(user: EntraUser, config_path: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Provision a DataVerify user account

    Args:
        user: EntraUser object with user details
        config_path: Path to vendor config.json
        api_key: Optional API key (not used for DataVerify)

    Returns:
        Dict with status, success boolean, and any messages/errors
    """
    # Get KeyVault service
    from services.config_manager import ConfigManager
    from services.keyvault_service import get_keyvault_service

    config_manager = ConfigManager()
    keyvault = get_keyvault_service()

    # Create automation instance
    automation = DataVerifyAutomation(config_path, keyvault)

    # Run automation
    result = await automation.create_account(user, headless=False)

    return result
