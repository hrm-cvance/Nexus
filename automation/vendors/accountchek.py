"""
AccountChek Automation Module

Automates user account creation in AccountChek Verifier Platform using Playwright.
Uses Azure Key Vault for secure credential retrieval.
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout

from models.user import EntraUser
from services.ai_matcher import AIMatcherService
from services.keyvault_service import get_keyvault_service, KeyVaultError
from utils.logger import get_logger

logger = get_logger(__name__)


class AccountChekAutomation:
    """Automation for AccountChek account creation"""

    def __init__(self, vendor_config_path: str, api_key: Optional[str] = None):
        """
        Initialize AccountChek automation

        Args:
            vendor_config_path: Path to vendor config JSON file
            api_key: Anthropic API key for AI matching (optional)
        """
        self.config_path = Path(vendor_config_path)
        self.config = self._load_config()
        self.roles_config = self._load_roles()
        self.ai_matcher = AIMatcherService(api_key=api_key)

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

    def _load_roles(self) -> List[Dict[str, Any]]:
        """Load roles configuration"""
        try:
            roles_path = self.config_path.parent / 'roles.json'
            with open(roles_path, 'r') as f:
                roles_data = json.load(f)
            logger.info(f"Loaded {len(roles_data['roles'])} roles from {roles_path}")
            return roles_data['roles']
        except Exception as e:
            logger.error(f"Failed to load roles config: {e}")
            # Return default roles if file doesn't exist
            return [
                {'value': 'User', 'description': 'Standard User', 'keywords': ['user', 'officer', 'specialist']}
            ]

    async def create_account(self, user: EntraUser, headless: bool = False) -> Dict[str, Any]:
        """
        Create an AccountChek account for the user

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
            logger.info(f"Starting AccountChek automation for {user.display_name}")

            # Prepare user data with AI matching
            user_data = await self._prepare_user_data(user)
            logger.info(f"Prepared user data: {user_data}")

            # Add AI suggestions to result
            if 'ai_suggestions' in user_data:
                result['ai_suggestions'] = user_data['ai_suggestions']

            # Start browser
            await self._start_browser(headless=headless)

            # Login
            await self._login()
            result['messages'].append("✓ Logged in successfully")

            # Navigate to user management
            await self._navigate_to_user_management()
            result['messages'].append("✓ Navigated to User Management")

            # Click New User button
            await self._click_new_user()
            result['messages'].append("✓ Opened new user form")

            # Fill form
            await self._fill_user_form(user_data)
            result['messages'].append("✓ Filled user form")

            # Submit form
            await self._submit_form()
            result['messages'].append("✓ Submitted form")

            # Wait for success confirmation
            success_result = await self._wait_for_success()

            if success_result['success']:
                result['success'] = True
                result['messages'].append(f"✓ {success_result['message']}")
                logger.info(f"Successfully created AccountChek account for {user.display_name}")
            elif success_result.get('skip', False):
                # Duplicate user - don't treat as failure, return immediately
                result['success'] = False
                result['warnings'].append(f"⚠ {success_result['message']} - Account was not created (user already exists)")
                logger.info(f"User already exists in AccountChek: {user.display_name}")
                return result
            else:
                # Real error
                result['errors'].append(f"✗ {success_result['message']}")
                logger.warning(f"Account creation failed for {user.display_name}: {success_result['message']}")

            # Add any warnings from AI matching
            if user_data.get('branch_fallback', False):
                cost_center = user_data.get('cost_center')
                if cost_center:
                    # Cost center was found but didn't match any branch
                    result['warnings'].append(
                        f"⚠ Branch fallback: Cost center '{cost_center}' not found in dropdown. "
                        f"Used '{user_data['branch']}' instead."
                    )
                else:
                    # No office location set in Entra ID
                    result['warnings'].append(
                        f"⚠ Branch fallback: User has no office location in Entra ID. "
                        f"Used '{user_data['branch']}' instead."
                    )

        except Exception as e:
            logger.error(f"Error during AccountChek automation: {e}")
            result['errors'].append(str(e))

        finally:
            # Close browser
            await self._close_browser()

        return result

    async def _prepare_user_data(self, user: EntraUser) -> Dict[str, Any]:
        """
        Prepare user data for form filling with AI matching

        Args:
            user: EntraUser object

        Returns:
            Dict with prepared user data including AI suggestions
        """
        # Get newuser password from Key Vault
        try:
            newuser_password = self.keyvault.get_vendor_credential('accountchek', 'newuser-password')
        except KeyVaultError as e:
            logger.error(f"Failed to retrieve newuser password from Key Vault: {e}")
            raise

        data = {
            'firstName': user.given_name or user.display_name.split()[0],
            'lastName': user.surname or user.display_name.split()[-1],
            'email': user.email,
            'title': user.job_title or 'User',
            'password': newuser_password,  # From Key Vault
            'mustChangePassword': True,
            'region': 'Corporate',  # Always Corporate per requirements
            'ai_suggestions': {}
        }

        # Extract cost center from office location OR department
        cost_center = None
        cost_center_source = None

        # Try office location first
        if user.office_location:
            cost_center = AIMatcherService.extract_cost_center(user.office_location)
            if cost_center:
                cost_center_source = "office location"
                data['cost_center'] = cost_center
                logger.info(f"Extracted cost center: {cost_center} from office location: {user.office_location}")

        # If not found, try department field
        if not cost_center and user.department:
            cost_center = AIMatcherService.extract_cost_center(user.department)
            if cost_center:
                cost_center_source = "department"
                data['cost_center'] = cost_center
                logger.info(f"Extracted cost center: {cost_center} from department: {user.department}")

        if not cost_center:
            logger.warning(f"Could not extract cost center from office location or department")

        # AI-based role suggestion
        if user.job_title:
            role_suggestion = self.ai_matcher.suggest_role(
                job_title=user.job_title,
                available_roles=self.roles_config,
                department=user.department
            )

            data['role'] = role_suggestion['suggested_role']
            data['ai_suggestions']['role'] = role_suggestion
            logger.info(
                f"AI suggested role: {role_suggestion['suggested_role']} "
                f"(confidence: {role_suggestion['confidence']:.2f})"
            )
        else:
            data['role'] = 'User'  # Default role
            logger.info("No job title available, using default role: User")

        # Branch will be matched dynamically from dropdown
        # Store cost center for later matching
        data['branch'] = None  # To be determined from dropdown
        data['branch_fallback'] = False

        return data

    async def _start_browser(self, headless: bool = False):
        """Start Playwright browser"""
        logger.info("Starting browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.page = await self.browser.new_page()
        logger.info("Browser started")

    async def _login(self):
        """Login to AccountChek using Key Vault credentials"""
        logger.info("Logging in to AccountChek...")

        # Get login credentials from Key Vault
        try:
            login_url = self.keyvault.get_vendor_credential('accountchek', 'login-url')
            login_email = self.keyvault.get_vendor_credential('accountchek', 'login-email')
            login_password = self.keyvault.get_vendor_credential('accountchek', 'login-password')
        except KeyVaultError as e:
            logger.error(f"Failed to retrieve login credentials from Key Vault: {e}")
            raise

        # Navigate to login page
        await self.page.goto(login_url)
        await self.page.wait_for_load_state('networkidle')

        # Fill login form
        await self.page.fill('input[type="email"], input[name="email"]', login_email)
        await self.page.fill('input[type="password"], input[name="password"]', login_password)

        # Click login button
        await self.page.click('button[type="submit"], input[type="submit"]')

        # Wait for navigation
        await self.page.wait_for_load_state('networkidle')
        logger.info("✓ Login successful")

    async def _navigate_to_user_management(self):
        """Navigate to user management page"""
        logger.info("Navigating to User Management...")

        # Click on user name/dropdown in top-right corner - try multiple selectors
        try:
            await self.page.click('.dropdown-toggle, [class*="user"], [class*="dropdown"]', timeout=5000)
        except:
            # If that doesn't work, try looking for name text
            await self.page.click('text=/CHRIS|VANCE/i')

        # Wait for dropdown menu to appear
        await asyncio.sleep(1)

        # Click "Verifiers" link in dropdown
        await self.page.click('a:has-text("Verifiers")')

        # Wait for User Management page to load
        await self.page.wait_for_load_state('networkidle')
        await self.page.wait_for_selector('text=User Management', timeout=10000)

        # Press Escape to close dropdown if still open
        await self.page.keyboard.press('Escape')
        await asyncio.sleep(0.5)

        logger.info("User Management page loaded")

    async def _click_new_user(self):
        """Click New User button"""
        logger.info("Clicking New User button...")

        # Find and click New User button by iterating through buttons
        buttons = await self.page.query_selector_all('button, a.btn, a[class*="btn"]')
        for btn in buttons:
            text = await btn.text_content()
            if text and 'New User' in text:
                await btn.click()
                logger.info("Clicked New User button")
                break

        # Wait for modal/form to appear
        await asyncio.sleep(2)
        await self.page.wait_for_selector('form input, [role="dialog"] input, .modal input', timeout=10000)
        logger.info("New User modal opened")

    async def _fill_user_form(self, user_data: Dict[str, Any]):
        """Fill the new user form"""
        logger.info("Filling user form...")

        # Fill text fields using getByPlaceholder (Playwright recommended approach)
        await self.page.get_by_placeholder('First Name', exact=False).fill(user_data['firstName'])
        await self.page.get_by_placeholder('Last Name', exact=False).fill(user_data['lastName'])
        await self.page.get_by_placeholder('Email', exact=False).fill(user_data['email'])
        await self.page.get_by_placeholder('Job Title', exact=False).fill(user_data['title'])
        await self.page.get_by_placeholder('Password', exact=False).fill(user_data['password'])

        # Get all select dropdowns
        selects = await self.page.query_selector_all('select')
        logger.info(f"Found {len(selects)} select dropdowns")

        # Select Role - first select
        if len(selects) >= 1:
            await selects[0].select_option(label=user_data['role'])
            logger.info(f"Selected role: {user_data['role']}")

        # Select Region - second select
        if len(selects) >= 2:
            await selects[1].select_option(label=user_data['region'])
            logger.info(f"Selected region: {user_data['region']}")
            # Wait for Branch dropdown to populate (cascading dropdown)
            await asyncio.sleep(1)

        # Get branch dropdown options - third select
        branch_options = []
        if len(selects) >= 3:
            # Re-get selects after region selection (may have changed)
            selects = await self.page.query_selector_all('select')
            branch_select = selects[2]

            branch_options = await self.page.evaluate(
                'select => Array.from(select.options).map(opt => opt.text)',
                branch_select
            )
        logger.info(f"Available branches: {branch_options}")

        # Match branch from dropdown using cost center
        if user_data.get('cost_center'):
            branch_match = AIMatcherService.match_branch_from_dropdown(
                user_data['cost_center'],
                branch_options
            )

            user_data['branch'] = branch_match['matched_branch']
            user_data['branch_fallback'] = (branch_match['match_type'] == 'fallback')

            logger.info(
                f"Branch match: {branch_match['matched_branch']} "
                f"(type: {branch_match['match_type']}, confidence: {branch_match['confidence']:.2f})"
            )

            if user_data['branch_fallback']:
                logger.warning(f"Using fallback branch: {branch_match['reasoning']}")
        else:
            # No cost center - use Main as fallback
            main_option = next((opt for opt in branch_options if 'Main' in opt), branch_options[0] if branch_options else 'Main')
            user_data['branch'] = main_option
            user_data['branch_fallback'] = True
            logger.warning(f"No cost center available, using fallback branch: {main_option}")

        # Select branch using the select element directly
        if len(selects) >= 3:
            selects = await self.page.query_selector_all('select')
            branch_select = selects[2]

            # Try multiple methods to select the branch
            try:
                # Method 1: Select by exact label match
                await branch_select.select_option(label=user_data['branch'])
                logger.info(f"Selected branch by label: {user_data['branch']}")
            except Exception as e:
                logger.warning(f"Could not select by label, trying value: {e}")
                # Method 2: Find the option with matching text and select by value
                try:
                    option_value = await self.page.evaluate('''(select, searchText) => {
                        const options = Array.from(select.options);
                        const match = options.find(opt => opt.text === searchText);
                        return match ? match.value : null;
                    }''', branch_select, user_data['branch'])

                    if option_value:
                        await branch_select.select_option(value=option_value)
                        logger.info(f"Selected branch by value: {option_value}")
                    else:
                        logger.error(f"Could not find option for branch: {user_data['branch']}")
                except Exception as e2:
                    logger.error(f"Failed to select branch: {e2}")

        # Check "Must Change Password" checkbox using JavaScript (more reliable)
        if user_data.get('mustChangePassword', True):
            await self.page.evaluate('''() => {
                const checkboxes = document.querySelectorAll('input[type="checkbox"]');
                if (checkboxes.length >= 2) {
                    checkboxes[1].click();
                }
            }''')
            logger.info("Checked 'Must Change Password'")

        logger.info("Form filled successfully")

    async def _submit_form(self):
        """Submit the user creation form"""
        logger.info("Submitting form...")

        # Click Save button using role selector
        await self.page.get_by_role('button', name='Save').click()
        logger.info("Save button clicked")

    async def _wait_for_success(self) -> Dict[str, Any]:
        """
        Wait for success confirmation or handle errors

        Returns:
            Dict with success status, message type, and details
        """
        logger.info("Waiting for success confirmation...")

        # Wait longer for the response to fully render
        await asyncio.sleep(3)

        # Take a screenshot to capture the result
        try:
            screenshot_path = Path.home() / 'Desktop' / f'accountchek_result_{self.current_user.display_name.replace(" ", "_")}.png'
            await self.page.screenshot(path=str(screenshot_path))
            logger.info(f"Screenshot saved to: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Could not save screenshot: {e}")

        # Check for error alerts (duplicate user, validation errors, etc.)
        # Look for any alert-danger or error message
        try:
            # Check for any visible error alerts
            error_alerts = await self.page.locator('.alert-danger, .alert-error, .alert.alert-danger').all()
            for alert in error_alerts:
                if await alert.is_visible():
                    error_text = await alert.text_content()
                    logger.warning(f"Error alert detected: {error_text}")

                    # Check if it's a duplicate user error
                    error_lower = error_text.lower()
                    if ('taken' in error_lower) or \
                       ('already' in error_lower and 'exist' in error_lower) or \
                       ('duplicate' in error_lower):
                        return {
                            'success': False,
                            'type': 'duplicate',
                            'message': 'User already exists - email address is already taken',
                            'skip': True  # Don't treat as failure, just skip
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
            success_visible = await self.page.locator('text=/Verifier Saved|User Created|Success/i').is_visible(timeout=5000)
            if success_visible:
                logger.info("Success message detected")
                return {
                    'success': True,
                    'type': 'success',
                    'message': 'Account created successfully'
                }
        except:
            pass

        # Check if modal closed (alternative success indicator)
        try:
            modal_visible = await self.page.is_visible('.modal, [role="dialog"]')
            if not modal_visible:
                logger.info("Modal closed - assuming success")
                return {
                    'success': True,
                    'type': 'success',
                    'message': 'Account created successfully (modal closed)'
                }
        except:
            pass

        # Unknown result
        logger.warning("Could not determine success or failure - check screenshot")
        return {
            'success': False,
            'type': 'unknown',
            'message': 'Could not confirm account creation - see screenshot',
            'skip': False
        }

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
    Main entry point for AccountChek user provisioning

    Args:
        user: EntraUser object
        config_path: Path to AccountChek config.json
        api_key: Anthropic API key (optional)

    Returns:
        Dict with provisioning result
    """
    automation = AccountChekAutomation(config_path, api_key=api_key)
    result = await automation.create_account(user, headless=False)
    return result
