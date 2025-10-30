"""
Partners Credit User Provisioning Automation

This module automates the creation of user account requests in Partners Credit
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
logger = logging.getLogger('automation.vendors.partnerscredit')


class PartnersCreditAutomation:
    """Handles Partners Credit user provisioning automation"""

    def __init__(self, config_path: str, keyvault: KeyVaultService):
        """
        Initialize Partners Credit automation

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
        self.current_user: Optional[EntraUser] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load vendor configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded config from {self.config_path}")
        return config

    async def create_account(self, user: EntraUser, headless: bool = False) -> Dict[str, Any]:
        """
        Create a Partners Credit account request for the given user

        Args:
            user: EntraUser object with user details
            headless: Whether to run browser in headless mode

        Returns:
            Dict with success status and messages
        """
        self.current_user = user
        logger.info(f"Starting Partners Credit automation for {user.display_name}")

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

            # Navigate to Admin -> User Admin
            await self._navigate_to_user_admin()
            result['messages'].append("✓ Navigated to User Admin")

            # Click New User Requests
            await self._click_new_user_requests()
            result['messages'].append("✓ Opened New User Requests")

            # Input number of users (1)
            await self._input_number_of_users(1)
            result['messages'].append("✓ Set number of users to 1")

            # Fill user form
            await self._fill_user_form(user_data)
            result['messages'].append("✓ Filled user form")

            # Submit request
            await self._submit_request()
            result['messages'].append("✓ User request submitted")

            result['success'] = True
            result['warnings'].append("⚠ Manual step required: Check email for encrypted PDF with user credentials from Partners Credit")
            result['messages'].append("ℹ Partners Credit will send credentials via encrypted PDF email")
            result['messages'].append("ℹ Use your Partners Credit admin password to decrypt the PDF")
            logger.info(f"✓ Successfully submitted Partners Credit request for {user.display_name}")

        except Exception as e:
            error_msg = f"Error during Partners Credit automation: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            result['success'] = False

            # Take error screenshot
            try:
                if self.page:
                    await self.page.screenshot(path=f'partnerscredit_error_{user.display_name.replace(" ", "_")}.png')
            except:
                pass

        finally:
            await self._cleanup()

        logger.info(f"Partners Credit result: {result}")
        return result

    def _prepare_user_data(self, user: EntraUser) -> Dict[str, Any]:
        """
        Prepare user data for Partners Credit form

        Args:
            user: EntraUser object

        Returns:
            Dict with formatted user data
        """
        # Get user details
        first_name = user.given_name or user.display_name.split()[0]
        last_name = user.surname or user.display_name.split()[-1]

        # Phone number without dashes
        phone = user.mobile_phone or (user.business_phones[0] if user.business_phones else "")
        phone_clean = phone.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")

        # Email
        email = user.mail or user.user_principal_name

        # Title/Job Title
        title = user.job_title or ""

        # Department logic based on cost center (if available in department field)
        department = "Plano Division"  # Default
        comments = self.config['user_settings']['default_comments']

        # Check if department field contains cost center info
        if user.department:
            dept_str = str(user.department)
            # Check for 8000 range cost centers
            if any(cc in dept_str for cc in ['8000', '8001', '8002', '8003', '8004', '8005', '8006', '8007', '8008', '8009']):
                department = "East Region"
            # Check for special cost centers
            elif any(cc in dept_str for cc in ['7003', '7074', '7075']):
                department = "Plano Division"
                comments = "Place derogatory and tradelines at the bottom of the report. Eliminate the ability to pull credit on the website and order score updates."

        return {
            'firstName': first_name,
            'lastName': last_name,
            'phoneNumber': phone_clean,
            'email': email,
            'title': title,
            'reportAccessLevel': 'Department',
            'department': department,
            'comments': comments
        }

    async def _start_browser(self, headless: bool = False):
        """Start Playwright browser"""
        logger.info("Starting browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.page = await self.browser.new_page()
        logger.info("Browser started")

    async def _login(self):
        """Login to Partners Credit"""
        login_url = self.keyvault.get_vendor_credential('partnerscredit', 'login-url')
        admin_username = self.keyvault.get_vendor_credential('partnerscredit', 'admin-username')
        admin_password = self.keyvault.get_vendor_credential('partnerscredit', 'admin-password')

        logger.info(f"Navigating to {login_url}")
        await self.page.goto(login_url)
        await self.page.wait_for_load_state('networkidle')

        # Take screenshot of login page
        await self.page.screenshot(path='partnerscredit_login_page.png')

        # Find and fill login form
        await self.page.wait_for_selector('input[type="text"], input[name*="user"], input[id*="user"]', timeout=10000)

        # Fill username - try common selectors
        username_filled = False
        for selector in ['input[type="text"]', 'input[name*="user"]', 'input[id*="user"]', 'input[name*="login"]']:
            try:
                await self.page.fill(selector, admin_username)
                username_filled = True
                logger.info(f"Filled username with selector: {selector}")
                break
            except:
                continue

        if not username_filled:
            raise Exception("Could not find username field")

        # Fill password
        password_filled = False
        for selector in ['input[type="password"]', 'input[name*="pass"]', 'input[id*="pass"]']:
            try:
                await self.page.fill(selector, admin_password)
                password_filled = True
                logger.info(f"Filled password with selector: {selector}")
                break
            except:
                continue

        if not password_filled:
            raise Exception("Could not find password field")

        # Click "Client Login" button
        await self.page.click('input[value="Client Login"]')
        logger.info("Clicked Client Login button")

        # Wait for login to complete
        await self.page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)

        # Take screenshot after login
        await self.page.screenshot(path='partnerscredit_after_login.png')
        logger.info("Login completed")

    async def _navigate_to_user_admin(self):
        """Navigate to Admin -> User Admin"""
        logger.info("Navigating to User Admin...")

        # Click Admin menu
        await self.page.click('text="Admin"')
        await asyncio.sleep(1)

        # Click User Admin from dropdown
        await self.page.click('text="User Admin"')
        await self.page.wait_for_load_state('networkidle')
        await asyncio.sleep(1)

        # Take screenshot
        await self.page.screenshot(path='partnerscredit_admin_page.png')
        logger.info("Navigated to User Admin")

    async def _click_new_user_requests(self):
        """Click New User Requests tab"""
        logger.info("Clicking New User Requests...")

        # Click New User Requests tab
        await self.page.click('text="New User Requests"')
        await self.page.wait_for_load_state('networkidle')
        await asyncio.sleep(1)

        # Take screenshot
        await self.page.screenshot(path='partnerscredit_new_user_requests.png')
        logger.info("Clicked New User Requests")

    async def _input_number_of_users(self, num_users: int):
        """Input number of users and click Next"""
        logger.info(f"Setting number of users to {num_users}...")

        # Find the input field for number of users
        await self.page.wait_for_selector('input[type="text"], input[type="number"]', timeout=10000)

        # Fill number of users
        number_input_filled = False
        for selector in ['input[type="number"]', 'input[type="text"]']:
            try:
                await self.page.fill(selector, str(num_users))
                number_input_filled = True
                logger.info(f"Filled number of users with selector: {selector}")
                break
            except:
                continue

        if not number_input_filled:
            raise Exception("Could not find number of users input")

        # Click Next button
        await self.page.click('button:has-text("Next"), input[value="Next"]')
        await self.page.wait_for_load_state('networkidle')
        await asyncio.sleep(1)

        # Take screenshot
        await self.page.screenshot(path='partnerscredit_user_form.png')
        logger.info("Number of users set, form loaded")

    async def _fill_user_form(self, user_data: Dict[str, Any]):
        """Fill the new user form"""
        logger.info("Filling user form...")

        # Wait for form to be ready
        await self.page.wait_for_selector('input', timeout=10000)
        await asyncio.sleep(1)

        # Save HTML for inspection
        html_content = await self.page.content()
        with open('partnerscredit_form_html.html', 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Fill First Name
        await self.page.fill('input[id*="First"], input[name*="First"]', user_data['firstName'])
        logger.info(f"Filled First Name: {user_data['firstName']}")

        # Fill Last Name
        await self.page.fill('input[id*="Last"], input[name*="Last"]', user_data['lastName'])
        logger.info(f"Filled Last Name: {user_data['lastName']}")

        # Fill Phone Number
        await self.page.fill('input[id*="Phone"], input[name*="Phone"]', user_data['phoneNumber'])
        logger.info(f"Filled Phone Number: {user_data['phoneNumber']}")

        # Fill Email Address
        await self.page.fill('input[id*="Email"], input[name*="Email"]', user_data['email'])
        logger.info(f"Filled Email: {user_data['email']}")

        # Fill Title (optional field)
        try:
            await self.page.fill('input[id*="Title"], input[name*="Title"]', user_data['title'])
            logger.info(f"Filled Title: {user_data['title']}")
        except:
            logger.warning("Could not fill Title field")

        # Select Report Access Level - Department (radio button)
        await self.page.click('input[type="radio"][value="Department"], input[type="radio"]:near(:text("Department"))')
        logger.info("Selected Report Access Level: Department")

        # Select Department from dropdown
        await self.page.select_option('select', label=user_data['department'])
        logger.info(f"Selected Department: {user_data['department']}")

        # Fill Comments
        await self.page.fill('textarea, input[id*="Comment"], input[name*="Comment"]', user_data['comments'])
        logger.info(f"Filled Comments: {user_data['comments']}")

        # Take screenshot of filled form
        await self.page.screenshot(path='partnerscredit_form_filled.png')
        logger.info("User form filled")

    async def _submit_request(self):
        """Submit the user request"""
        logger.info("Submitting user request...")

        # Click Request New Users button
        await self.page.click('button:has-text("Request"), input[value*="Request"]')
        await self.page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)

        # Take screenshot of confirmation
        await self.page.screenshot(path='partnerscredit_request_submitted.png')
        logger.info("User request submitted")

    async def _cleanup(self):
        """Clean up browser resources"""
        logger.info("Cleaning up browser...")
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")


async def provision_user(user: EntraUser, config_path: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entry point for Partners Credit user provisioning

    Args:
        user: EntraUser object
        config_path: Path to vendor config JSON
        api_key: Optional API key (not used for Partners Credit)

    Returns:
        Dict with provisioning result
    """
    from services.keyvault_service import KeyVaultService

    # Initialize KeyVault service
    keyvault = KeyVaultService()

    # Create automation instance
    automation = PartnersCreditAutomation(config_path, keyvault)

    # Run automation
    result = await automation.create_account(user, headless=False)

    return result
