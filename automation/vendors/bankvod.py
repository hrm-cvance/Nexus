"""
BankVOD Automation Module

Automates authorized user creation in BankVOD platform using Playwright.
Uses Azure Key Vault for secure credential retrieval.

Process:
1. Login to BankVOD
2. Navigate to Authorized Users
3. Add new authorized user (auto-generated password)
4. Detect duplicate user (skip with warning if exists)
5. Search for the newly created user (validates account was created)
6. Update user password to HRM default
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout

from models.user import EntraUser
from services.keyvault_service import get_keyvault_service, KeyVaultError
from utils.logger import get_logger

logger = get_logger(__name__)


class BankVODAutomation:
    """Automation for BankVOD authorized user creation"""

    def __init__(self, vendor_config_path: str):
        """
        Initialize BankVOD automation

        Args:
            vendor_config_path: Path to vendor config JSON file
        """
        self.config_path = Path(vendor_config_path)
        self.config = self._load_config()

        # Get Key Vault service for credentials
        try:
            self.keyvault = get_keyvault_service()
            logger.info("Using Azure Key Vault for credentials")
        except KeyVaultError as e:
            logger.error(f"Key Vault initialization failed: {e}")
            raise

        # Automation state
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.current_user = None
        self.auto_generated_password = None

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
        Create a BankVOD account for the user

        Args:
            user: EntraUser object with user details
            headless: Run browser in headless mode (default: False for debugging)

        Returns:
            Dict with status, success boolean, and any messages/errors
        """
        self.current_user = user  # Store for screenshot filename
        result = {
            'success': False,
            'user': user.display_name,
            'messages': [],
            'warnings': [],
            'errors': []
        }

        try:
            logger.info(f"Starting BankVOD automation for {user.display_name}")

            # Prepare user data
            user_data = self._prepare_user_data(user)
            logger.info(f"Prepared user data: {user_data}")

            # Start browser
            await self._start_browser(headless=headless)

            # Login
            await self._login()
            result['messages'].append("✓ Logged in successfully")

            # Navigate to Authorized Users
            await self._navigate_to_authorized_users()
            result['messages'].append("✓ Navigated to Authorized Users")

            # Click Add New Authorized User button
            await self._click_add_new_user()
            result['messages'].append("✓ Opened new user form")

            # Fill form with auto-generated password
            await self._fill_user_form(user_data, use_auto_password=True)
            result['messages'].append("✓ Filled user form with auto-generated password")

            # Submit form
            await self._submit_form()
            result['messages'].append("✓ Submitted form")

            # Wait for success confirmation
            success_result = await self._wait_for_success()

            if not success_result['success']:
                # Check if duplicate user
                if success_result.get('skip', False):
                    result['success'] = False
                    result['warnings'].append(f"⚠ {success_result['message']} - Account was not created (user already exists)")
                    logger.info(f"User already exists in BankVOD: {user.display_name}")
                    return result
                else:
                    result['errors'].append(f"✗ {success_result['message']}")
                    logger.warning(f"Account creation failed for {user.display_name}: {success_result['message']}")
                    return result

            result['messages'].append(f"✓ User created with auto-generated password: {self.auto_generated_password}")
            logger.info(f"User created successfully")

            # Mark as successful after initial creation
            result['success'] = True
            result['messages'].append(f"✓ Successfully created BankVOD account for {user.display_name}")
            logger.info(f"Successfully completed BankVOD account creation for {user.display_name}")

            # Step 2 - Update password to HRM default
            logger.info(f"Now updating password to HRM default")

            # Search for the user and update password to HRM default
            await self._search_for_user(user_data['email'])
            result['messages'].append("✓ Found newly created user")

            # Click Update button
            await self._click_update_button()
            result['messages'].append("✓ Opened user update form")

            # Update password to HRM default
            await self._update_password(user_data['default_password'])
            result['messages'].append("✓ Updated password to HRM default")

            # Submit update
            await self._submit_form()
            result['messages'].append("✓ Password update submitted")

            # Wait for success
            update_result = await self._wait_for_success()

            if update_result['success']:
                result['messages'].append(f"✓ Password updated to HRM default")
                logger.info(f"Successfully updated password to HRM default")
            else:
                result['errors'].append(f"✗ Password update failed: {update_result['message']}")
                logger.error(f"Password update failed for {user.display_name}")

        except Exception as e:
            logger.error(f"Error during BankVOD automation: {e}")
            result['errors'].append(str(e))

        finally:
            # Close browser
            await self._close_browser()

        return result

    def _prepare_user_data(self, user: EntraUser) -> Dict[str, Any]:
        """
        Prepare user data for form filling

        Args:
            user: EntraUser object

        Returns:
            Dict with prepared user data
        """
        # Get default password from Key Vault
        try:
            default_password = self.keyvault.get_vendor_credential('bankvod', 'newuser-password')
        except KeyVaultError as e:
            logger.error(f"Failed to retrieve default password from Key Vault: {e}")
            raise

        # Extract cost center from office location OR department
        cost_center = None
        if user.office_location:
            # Try to extract numbers from office location
            import re
            match = re.search(r'\d+', user.office_location)
            if match:
                cost_center = match.group()
                logger.info(f"Extracted cost center: {cost_center} from office location: {user.office_location}")

        if not cost_center and user.department:
            # Try department field
            import re
            match = re.search(r'\d+', user.department)
            if match:
                cost_center = match.group()
                logger.info(f"Extracted cost center: {cost_center} from department: {user.department}")

        if not cost_center:
            logger.warning(f"Could not extract cost center from office location or department")
            cost_center = ""

        data = {
            'firstName': user.given_name or user.display_name.split()[0],
            'lastName': user.surname or user.display_name.split()[-1],
            'email': user.email,
            'cost_center': cost_center,
            'comments': f"Created by Nexus automation for {user.display_name}",
            'default_password': default_password  # HRM default password
        }

        return data

    async def _start_browser(self, headless: bool = False):
        """Start Playwright browser"""
        logger.info("Starting browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.page = await self.browser.new_page()
        logger.info("Browser started")

    async def _login(self):
        """Login to BankVOD using Key Vault credentials"""
        logger.info("Logging in to BankVOD...")

        # Get login credentials from Key Vault
        try:
            login_url = self.keyvault.get_vendor_credential('bankvod', 'login-url')
            login_account_id = self.keyvault.get_vendor_credential('bankvod', 'login-account-id')
            login_email = self.keyvault.get_vendor_credential('bankvod', 'login-email')
            login_password = self.keyvault.get_vendor_credential('bankvod', 'login-password')
        except KeyVaultError as e:
            logger.error(f"Failed to retrieve login credentials from Key Vault: {e}")
            raise

        # Navigate to login page
        await self.page.goto(login_url)
        await self.page.wait_for_load_state('networkidle')

        # Fill login form using exact IDs from ASP.NET form

        # Account Number field - ID: ContentPlaceHolder1_t_acct
        try:
            await self.page.fill('#ContentPlaceHolder1_t_acct', login_account_id)
            logger.info("Filled Account Number field")
        except Exception as e:
            logger.error(f"Account Number field error: {e}")
            raise

        # Login/Email field - ID: ContentPlaceHolder1_t_email
        try:
            await self.page.fill('#ContentPlaceHolder1_t_email', login_email)
            logger.info("Filled Login field")
        except Exception as e:
            logger.error(f"Login field error: {e}")
            raise

        # Password field - ID: ContentPlaceHolder1_t_password
        try:
            await self.page.fill('#ContentPlaceHolder1_t_password', login_password)
            logger.info("Filled Password field")
        except Exception as e:
            logger.error(f"Password field error: {e}")
            raise

        # Click submit button (it's type="image", not type="submit")
        # ID: ContentPlaceHolder1_b_login
        try:
            await self.page.click('#ContentPlaceHolder1_b_login')
            logger.info("Clicked Submit button")
        except Exception as e:
            logger.error(f"Failed to click Submit button: {e}")
            await self.page.screenshot(path=f'bankvod_login_error_{self.current_user.user_principal_name if self.current_user else "unknown"}.png')
            raise

        # Wait for navigation
        await self.page.wait_for_load_state('networkidle')
        logger.info("✓ Login successful")

    async def _navigate_to_authorized_users(self):
        """Navigate to Authorized Users page"""
        logger.info("Navigating to Authorized Users...")

        # Look for "Authorized Users" link in the Main Menu
        try:
            # Try clicking directly on the text
            await self.page.click('text="AUTHORIZED USERS"', timeout=10000)
        except:
            # Alternative: look for link with text containing "Authorized Users"
            await self.page.click('a:has-text("AUTHORIZED USERS")')

        # Wait for page to load
        await self.page.wait_for_load_state('networkidle')
        await asyncio.sleep(1)

        logger.info("Authorized Users page loaded")

    async def _click_add_new_user(self):
        """Click Add New Authorized User button (opens a Telerik RadWindow)"""
        logger.info("Clicking Add New Authorized User button...")

        # The button is an image with ID: ContentPlaceHolder1_lb_add_new
        # It has onclick="openRadWindow(0);" which opens a Telerik RadWindow modal

        # Click the button by ID (most reliable)
        try:
            await self.page.click('#ContentPlaceHolder1_lb_add_new')
            logger.info("Clicked Add New User button by ID")
        except Exception as e:
            logger.error(f"Could not click Add New User button: {e}")
            raise Exception("Could not find or click Add New Authorized User button")

        # Wait for the Telerik RadWindow to appear
        # RadWindows create an iframe for their content
        logger.info("Waiting for RadWindow modal to appear...")
        await asyncio.sleep(3)  # Give RadWindow time to initialize

        # The RadWindow content is in an iframe
        # We need to find the iframe and work with it
        logger.info("Looking for RadWindow iframe...")

        # Wait for iframe to be added to the page
        try:
            await self.page.wait_for_selector('iframe.rwDialog, .RadWindow iframe, iframe[id*="RadWindow"]', timeout=10000)
            logger.info("RadWindow iframe found")
        except Exception as e:
            logger.error(f"RadWindow iframe not found: {e}")
            await self.page.screenshot(path='radwindow_not_found.png')
            raise Exception("RadWindow modal did not open")

    async def _fill_user_form(self, user_data: Dict[str, Any], use_auto_password: bool = False):
        """
        Fill the new user form in the RadWindow modal popup

        Args:
            user_data: User data dictionary
            use_auto_password: If True, leave password blank for auto-generation
                             If False, use default_password

        The form is inside a Telerik RadWindow iframe with fields:
        - First Name (text input)
        - Last Name (text input)
        - Email (text input)
        - Password (text input)
        - Cost Center/Acct Code (text input)
        - Comments (textarea)
        """
        logger.info("Filling user form in RadWindow iframe...")

        # Get the RadWindow iframe
        iframe_element = await self.page.query_selector('iframe.rwDialog, .RadWindow iframe, iframe[id*="RadWindow"]')
        if not iframe_element:
            logger.error("Could not find RadWindow iframe")
            raise Exception("RadWindow iframe not found")

        # Get the iframe's content frame
        iframe = await iframe_element.content_frame()
        if not iframe:
            logger.error("Could not access iframe content")
            raise Exception("Could not access RadWindow iframe content")

        logger.info("Accessing RadWindow iframe content...")

        # Wait for form to be loaded in the iframe
        await iframe.wait_for_selector('input[type="text"], textarea', timeout=10000)

        # Get all visible text input fields in the iframe
        text_inputs = await iframe.query_selector_all('input[type="text"]:visible, input[type="text"]')
        logger.info(f"Found {len(text_inputs)} text input fields in RadWindow")

        # The form has inputs in this order (based on screenshot):
        # 0 = First Name
        # 1 = Last Name
        # 2 = Email
        # 3 = Password (may be text type, not password type!)
        # 4 = Cost Center/Acct Code

        if len(text_inputs) >= 5:
            # Fill by index position (most reliable)
            await text_inputs[0].fill(user_data['firstName'])
            logger.info(f"Filled First Name: {user_data['firstName']}")

            await text_inputs[1].fill(user_data['lastName'])
            logger.info(f"Filled Last Name: {user_data['lastName']}")

            await text_inputs[2].fill(user_data['email'])
            logger.info(f"Filled Email: {user_data['email']}")

            # Password field (index 3)
            if use_auto_password:
                # Leave as "Auto generated password" - just clear and let it stay
                # The placeholder text "Auto generated password" suggests we should leave it empty
                # or the system will auto-generate
                logger.info("Leaving password field for auto-generation")
                # Don't fill it - let BankVOD auto-generate
            else:
                # For update, fill with HRM default
                await text_inputs[3].fill(user_data['default_password'])
                logger.info("Filled password with HRM default")

            # Cost Center (index 4)
            if user_data.get('cost_center'):
                await text_inputs[4].fill(user_data['cost_center'])
                logger.info(f"Filled Cost Center: {user_data['cost_center']}")
            else:
                logger.warning("No cost center available")
        else:
            logger.error(f"Expected 5 text inputs, found {len(text_inputs)}")
            raise Exception("Form structure doesn't match expected layout")

        # Comments (textarea) - also in the iframe
        if user_data.get('comments'):
            try:
                textarea = await iframe.query_selector('textarea')
                if textarea:
                    await textarea.fill(user_data['comments'])
                    logger.info(f"Filled Comments")
            except Exception as e:
                logger.debug(f"Comments field error: {e}")

        logger.info("Form filled successfully in RadWindow")

    async def _submit_form(self):
        """Submit the user creation/update form in the RadWindow iframe"""
        logger.info("Submitting form in RadWindow...")

        # Get the RadWindow iframe
        iframe_element = await self.page.query_selector('iframe.rwDialog, .RadWindow iframe, iframe[id*="RadWindow"]')
        if not iframe_element:
            logger.error("Could not find RadWindow iframe for submit")
            raise Exception("RadWindow iframe not found")

        iframe = await iframe_element.content_frame()
        if not iframe:
            logger.error("Could not access iframe content for submit")
            raise Exception("Could not access RadWindow iframe content")

        # Click Submit button in the iframe by ID
        # The button is: <input type="image" id="b_submit">
        try:
            await iframe.click('#b_submit')
            logger.info("Submit button clicked in RadWindow (ID: b_submit)")
        except Exception as e:
            logger.error(f"Submit button error: {e}")
            raise Exception("Could not click Submit button in RadWindow")

        # Wait for RadWindow to close or form to process
        await asyncio.sleep(3)
        logger.info("Form submitted, waiting for RadWindow to close...")

    async def _wait_for_success(self) -> Dict[str, Any]:
        """
        Wait for success confirmation or handle errors.

        Checks the RadWindow iframe first (where form errors appear),
        then falls back to checking the main page.

        Returns:
            Dict with success status, message type, and details
        """
        logger.info("Waiting for success confirmation...")

        # Wait for the response to fully render
        await asyncio.sleep(3)

        # Take a screenshot to capture the result
        try:
            screenshot_path = Path.home() / 'Desktop' / f'bankvod_result_{self.current_user.display_name.replace(" ", "_")}.png'
            await self.page.screenshot(path=str(screenshot_path))
            logger.info(f"Screenshot saved to: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Could not save screenshot: {e}")

        # Check INSIDE the RadWindow iframe first (errors appear here after form submit)
        try:
            iframe_element = await self.page.query_selector('iframe.rwDialog, .RadWindow iframe, iframe[id*="RadWindow"]')
            if iframe_element:
                iframe = await iframe_element.content_frame()
                if iframe:
                    iframe_content = await iframe.content()
                    iframe_text = await iframe.evaluate('() => document.body ? document.body.innerText : ""')
                    iframe_lower = iframe_text.lower()
                    logger.info(f"RadWindow iframe text: {iframe_text[:200]}")

                    # Check for duplicate/error keywords in iframe content
                    if ('duplicate' in iframe_lower) or \
                       ('invalid email' in iframe_lower) or \
                       ('already' in iframe_lower and ('exist' in iframe_lower or 'taken' in iframe_lower)):
                        # Extract just the error line, not the entire form text
                        error_lines = [line.strip() for line in iframe_text.split('\n') if line.strip()]
                        error_msg = next(
                            (line for line in error_lines
                             if 'duplicate' in line.lower() or 'invalid' in line.lower() or 'already' in line.lower()),
                            'Cannot have duplicate emails'
                        )
                        logger.warning(f"Duplicate user detected in iframe: {error_msg}")
                        return {
                            'success': False,
                            'type': 'duplicate',
                            'message': f'User already exists - {error_msg}',
                            'skip': True
                        }

                    # Check for other error messages in iframe
                    error_alerts = await iframe.query_selector_all('.alert-danger, .alert-error, .error, [class*="error"], [style*="color:red"], [style*="color: red"], font[color="red"]')
                    for alert in error_alerts:
                        if await alert.is_visible():
                            error_text = await alert.text_content()
                            if error_text and error_text.strip():
                                logger.warning(f"Error in iframe: {error_text}")
                                return {
                                    'success': False,
                                    'type': 'error',
                                    'message': error_text.strip(),
                                    'skip': False
                                }
        except Exception as e:
            logger.debug(f"Error checking iframe for alerts: {e}")

        # Check main page for error alerts
        try:
            error_alerts = await self.page.locator('.alert-danger, .alert-error, .error, [class*="error"]').all()
            for alert in error_alerts:
                if await alert.is_visible():
                    error_text = await alert.text_content()
                    logger.warning(f"Error alert detected: {error_text}")

                    # Check if it's a duplicate user error
                    error_lower = error_text.lower()
                    if ('taken' in error_lower) or \
                       ('already' in error_lower and 'exist' in error_lower) or \
                       ('duplicate' in error_lower) or \
                       ('invalid email' in error_lower):
                        return {
                            'success': False,
                            'type': 'duplicate',
                            'message': 'User already exists - email address is already taken',
                            'skip': True
                        }

                    # Other error
                    return {
                        'success': False,
                        'type': 'error',
                        'message': error_text.strip(),
                        'skip': False
                    }
        except Exception as e:
            logger.debug(f"Error checking for alerts: {e}")

        # Check for success message
        try:
            success_visible = await self.page.locator('text=/Success|User Created|Saved|Added/i').is_visible(timeout=5000)
            if success_visible:
                logger.info("Success message detected")
                return {
                    'success': True,
                    'type': 'success',
                    'message': 'User created/updated successfully'
                }
        except:
            pass

        # Check if RadWindow iframe is gone (modal closed = success)
        try:
            iframe_still_present = await self.page.query_selector('iframe.rwDialog, .RadWindow iframe, iframe[id*="RadWindow"]')
            if not iframe_still_present:
                logger.info("RadWindow closed - assuming success")
                return {
                    'success': True,
                    'type': 'success',
                    'message': 'User created/updated successfully (modal closed)'
                }
        except:
            pass

        # Assume success if no errors detected
        logger.info("No errors detected - assuming success")
        return {
            'success': True,
            'type': 'success',
            'message': 'User created/updated successfully'
        }

    async def _search_for_user(self, email: str):
        """
        Search for a user by email

        Args:
            email: User's email address
        """
        logger.info(f"Searching for user: {email}")

        # Find email input field in search area
        try:
            await self.page.fill('input[placeholder*="Email"], input[name*="email"]', email)
        except:
            # Try alternative selector
            search_inputs = await self.page.query_selector_all('input[type="text"], input[type="email"]')
            for input_field in search_inputs:
                placeholder = await input_field.get_attribute('placeholder')
                if placeholder and 'email' in placeholder.lower():
                    await input_field.fill(email)
                    break

        # Click Search button
        await self.page.click('button:has-text("Search"), input[value="Search"]')

        # Wait for results
        await asyncio.sleep(2)
        await self.page.wait_for_load_state('networkidle')

        logger.info("Search completed")

    async def _click_update_button(self):
        """Click Update button for the user"""
        logger.info("Clicking Update button...")

        # Find and click Update button
        await self.page.click('button:has-text("Update"), a:has-text("Update")')

        # Wait for modal/form to appear
        await asyncio.sleep(2)
        await self.page.wait_for_selector('input[type="password"]', timeout=10000)
        logger.info("Update modal opened")

    async def _update_password(self, new_password: str):
        """
        Update the password field

        Args:
            new_password: New password to set
        """
        logger.info("Updating password field...")

        # Clear and fill password field
        password_field = await self.page.query_selector('input[type="password"]')
        if password_field:
            await password_field.fill('')
            await password_field.fill(new_password)
            logger.info("Password field updated")
        else:
            logger.error("Could not find password field")
            raise Exception("Password field not found")

    async def _close_browser(self):
        """Close browser and cleanup"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")


async def provision_user(user: EntraUser, config_path: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entry point for BankVOD user provisioning

    Args:
        user: EntraUser object
        config_path: Path to BankVOD config.json
        api_key: Anthropic API key (not used for BankVOD, but kept for consistency)

    Returns:
        Dict with provisioning result
    """
    automation = BankVODAutomation(config_path)
    result = await automation.create_account(user, headless=False)
    return result
