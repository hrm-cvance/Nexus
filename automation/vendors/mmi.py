"""
MMI (Mortgage Market Intelligence) User Provisioning Automation

This module automates the creation of user accounts in the MMI portal
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
logger = logging.getLogger('automation.vendors.mmi')


class MMIAutomation:
    """Handles MMI user provisioning automation"""

    def __init__(self, config_path: str, keyvault: KeyVaultService):
        """
        Initialize MMI automation

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
        Create an MMI account for the given user

        Args:
            user: EntraUser object with user details
            headless: Whether to run browser in headless mode

        Returns:
            Dict with success status and messages
        """
        self.current_user = user
        logger.info(f"Starting MMI automation for {user.display_name}")

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
            result['messages'].append("Logged in successfully")

            # Navigate to Manage Seats
            await self._navigate_to_manage_seats()
            result['messages'].append("Navigated to Manage Seats")

            # Click Add Team Member tab
            await self._click_add_team_member()
            result['messages'].append("Opened Add Team Member form")

            # Fill user details
            await self._fill_user_details(user_data)
            result['messages'].append("Filled user details")

            # Set permissions
            await self._set_permissions()
            result['messages'].append("Set user permissions")

            # Create user
            await self._create_user()
            result['messages'].append("User created successfully")

            result['success'] = True
            result['messages'].append("User will receive activation email from MMI")
            logger.info(f"Successfully created MMI account for {user.display_name}")

        except Exception as e:
            error_msg = f"Error during MMI automation: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            result['success'] = False

            # Take error screenshot
            try:
                if self.page:
                    await self.page.screenshot(path=f'mmi_error_{user.display_name.replace(" ", "_")}.png')
            except:
                pass

        finally:
            await self._cleanup()

        logger.info(f"MMI result: {result}")
        return result

    def _prepare_user_data(self, user: EntraUser) -> Dict[str, Any]:
        """
        Prepare user data for MMI form

        Args:
            user: EntraUser object

        Returns:
            Dict with formatted user data
        """
        # Get user details
        first_name = user.given_name or user.display_name.split()[0]
        last_name = user.surname or user.display_name.split()[-1]

        # Email
        email = user.mail or user.user_principal_name

        # Phone - format as 10 digits only (no dashes, parentheses, etc.)
        phone = ""
        if user.mobile_phone:
            phone = ''.join(filter(str.isdigit, user.mobile_phone))
            # Ensure it's 10 digits
            if len(phone) > 10:
                phone = phone[-10:]  # Take last 10 digits
        elif user.business_phones and len(user.business_phones) > 0:
            phone = ''.join(filter(str.isdigit, user.business_phones[0]))
            if len(phone) > 10:
                phone = phone[-10:]

        # NMLS - may be in employee_id or custom attribute
        nmls = ""
        if hasattr(user, 'employee_id') and user.employee_id:
            # Check if employee_id looks like an NMLS number
            if user.employee_id.isdigit():
                nmls = user.employee_id

        return {
            'firstName': first_name,
            'lastName': last_name,
            'email': email,
            'phone': phone,
            'nmls': nmls
        }

    async def _start_browser(self, headless: bool = False):
        """Start Playwright browser"""
        logger.info("Starting browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.page = await self.browser.new_page()
        logger.info("Browser started")

    async def _login(self):
        """Login to MMI portal"""
        login_url = self.keyvault.get_vendor_credential('mmi', 'login-url')
        admin_username = self.keyvault.get_vendor_credential('mmi', 'admin-username')
        admin_password = self.keyvault.get_vendor_credential('mmi', 'admin-password')

        logger.info(f"Navigating to {login_url}")
        await self.page.goto(login_url)
        await self.page.wait_for_load_state('networkidle')

        # Take screenshot of initial page
        await self.page.screenshot(path='mmi_initial_page.png')

        # Check if we're on a login page or already logged in
        page_content = await self.page.content()

        # Look for login form elements
        login_needed = False
        login_selectors = [
            'input[type="email"]',
            'input[type="text"][name*="user" i]',
            'input[type="text"][name*="email" i]',
            'input[placeholder*="email" i]',
            'input[placeholder*="username" i]'
        ]

        for selector in login_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    login_needed = True
                    logger.info(f"Login form detected with selector: {selector}")
                    break
            except:
                continue

        if login_needed:
            logger.info("Login form detected, entering credentials...")

            # Fill username/email
            username_filled = False
            for selector in login_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.fill(admin_username)
                        username_filled = True
                        logger.info(f"Filled username with selector: {selector}")
                        break
                except:
                    continue

            if not username_filled:
                # Try by label
                try:
                    await self.page.get_by_label('Email').fill(admin_username)
                    username_filled = True
                except:
                    pass

            # Fill password
            try:
                password_input = await self.page.query_selector('input[type="password"]')
                if password_input and await password_input.is_visible():
                    await password_input.fill(admin_password)
                    logger.info("Filled password")
            except Exception as e:
                logger.warning(f"Could not fill password: {e}")

            # Take screenshot before clicking login
            await self.page.screenshot(path='mmi_login_filled.png')

            # Click login/submit button
            login_clicked = False
            login_button_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Log in")',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
                'button:has-text("Submit")'
            ]

            for selector in login_button_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.click()
                        login_clicked = True
                        logger.info(f"Clicked login button with selector: {selector}")
                        break
                except:
                    continue

            if not login_clicked:
                # Try pressing Enter
                await self.page.keyboard.press('Enter')
                logger.info("Pressed Enter to submit login")

            # Wait for navigation
            try:
                await self.page.wait_for_load_state('networkidle', timeout=15000)
            except:
                pass
            await asyncio.sleep(2)

        # Check for SSO/OAuth redirects
        await self._handle_sso()

        # Take screenshot after login
        await self.page.screenshot(path='mmi_after_login.png')
        logger.info("Login completed")

    async def _handle_sso(self):
        """Handle SSO/OAuth authentication if redirected"""
        logger.info("Checking for SSO authentication...")

        # Check if we're on Microsoft login page
        current_url = self.page.url
        if 'login.microsoftonline.com' in current_url or 'login.microsoft.com' in current_url:
            logger.info("Microsoft SSO detected - waiting for manual authentication")
            print("=" * 60)
            print("SSO LOGIN REQUIRED: Please complete Microsoft authentication")
            print("in the browser window, then the automation will continue.")
            print("=" * 60)

            # Wait for redirect back to MMI
            max_wait_time = 300  # 5 minutes
            check_interval = 3
            elapsed_time = 0

            while elapsed_time < max_wait_time:
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval

                current_url = self.page.url
                if 'mmi.run' in current_url or 'mmi.' in current_url.lower():
                    logger.info("SSO completed, returned to MMI")
                    print("SSO completed - continuing automation")
                    await asyncio.sleep(2)
                    return

                if elapsed_time % 30 == 0:
                    print(f"Waiting for SSO completion... ({elapsed_time}s)")

            raise Exception("SSO timeout - authentication not completed within 5 minutes")

        # Check for other SSO providers (Okta, etc.)
        if 'okta' in current_url.lower():
            logger.info("Okta SSO detected - waiting for manual authentication")
            # Similar wait logic as above
            pass

        logger.info("No SSO redirect detected")

    async def _navigate_to_manage_seats(self):
        """Navigate to Manage Seats from hamburger menu"""
        logger.info("Navigating to Manage Seats...")
        print("Navigating to Manage Seats...")

        # Take screenshot of current page
        await self.page.screenshot(path='mmi_before_manage_seats.png')

        # Wait for page to be fully loaded
        await asyncio.sleep(2)

        # First, check if "Manage Seats" is already visible (might be in sidebar)
        manage_seats_visible = False
        try:
            element = await self.page.query_selector('text="Manage Seats"')
            if element and await element.is_visible():
                manage_seats_visible = True
        except:
            pass

        if not manage_seats_visible:
            # Click hamburger menu if needed (the menu icon)
            hamburger_selectors = [
                'button[aria-label="menu"]',
                'button[aria-label="Menu"]',
                '[class*="hamburger"]',
                '[class*="menu-toggle"]',
                'button:has([class*="menu"])',
                'svg[class*="menu"]'
            ]

            for selector in hamburger_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.click()
                        logger.info(f"Clicked hamburger menu with selector: {selector}")
                        await asyncio.sleep(1)
                        break
                except:
                    continue

        # Take screenshot after opening menu
        await self.page.screenshot(path='mmi_menu_open.png')

        # Click "Manage Seats" in the menu
        manage_seats_clicked = False
        manage_seats_selectors = [
            'text="Manage Seats"',
            'a:has-text("Manage Seats")',
            '[href*="manage"]',
            'span:has-text("Manage Seats")',
            'div:has-text("Manage Seats")'
        ]

        for selector in manage_seats_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    manage_seats_clicked = True
                    logger.info(f"Clicked Manage Seats with selector: {selector}")
                    break
            except:
                continue

        if not manage_seats_clicked:
            # Try using locator
            try:
                await self.page.locator('text="Manage Seats"').click()
                manage_seats_clicked = True
            except:
                pass

        if not manage_seats_clicked:
            await self.page.screenshot(path='mmi_manage_seats_not_found.png')
            raise Exception("Could not find Manage Seats menu item")

        # Wait for page to load
        try:
            await self.page.wait_for_load_state('networkidle', timeout=10000)
        except:
            pass
        await asyncio.sleep(2)

        # Take screenshot
        await self.page.screenshot(path='mmi_manage_seats_page.png')
        logger.info("Navigated to Manage Seats")

    async def _click_add_team_member(self):
        """Click Add Team Member tab/button"""
        logger.info("Clicking Add Team Member...")
        print("Clicking Add Team Member...")

        await asyncio.sleep(1)

        # Take screenshot
        await self.page.screenshot(path='mmi_before_add_member.png')

        # Click "Add Team Member" tab or button
        add_member_clicked = False
        add_member_selectors = [
            'text="Add Team Member"',
            'button:has-text("Add Team Member")',
            '[role="tab"]:has-text("Add Team Member")',
            'a:has-text("Add Team Member")',
            'div:has-text("Add Team Member")'
        ]

        for selector in add_member_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    add_member_clicked = True
                    logger.info(f"Clicked Add Team Member with selector: {selector}")
                    break
            except:
                continue

        if not add_member_clicked:
            # Try using locator
            try:
                await self.page.locator('text="Add Team Member"').click()
                add_member_clicked = True
            except:
                pass

        if not add_member_clicked:
            await self.page.screenshot(path='mmi_add_member_not_found.png')
            raise Exception("Could not find Add Team Member tab/button")

        # Wait for form to appear
        try:
            await self.page.wait_for_load_state('networkidle', timeout=10000)
        except:
            pass
        await asyncio.sleep(1)

        # Take screenshot
        await self.page.screenshot(path='mmi_add_member_form.png')
        logger.info("Add Team Member form opened")

    async def _fill_user_details(self, user_data: Dict[str, Any]):
        """Fill the user details form"""
        logger.info("Filling user details...")

        # Wait for form fields
        await asyncio.sleep(1)

        # Fill First Name
        first_name_filled = False
        first_name_selectors = [
            'input[placeholder*="First" i]',
            'input[name*="first" i]',
            'input[id*="first" i]'
        ]

        for selector in first_name_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.fill(user_data['firstName'])
                    first_name_filled = True
                    logger.info(f"Filled First Name with selector: {selector}")
                    break
            except:
                continue

        if not first_name_filled:
            # Try by label
            try:
                await self.page.get_by_label('First Name').fill(user_data['firstName'])
                first_name_filled = True
            except:
                pass

        if not first_name_filled:
            raise Exception("Could not find First Name field")

        # Fill Last Name
        last_name_filled = False
        last_name_selectors = [
            'input[placeholder*="Last" i]',
            'input[name*="last" i]',
            'input[id*="last" i]'
        ]

        for selector in last_name_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.fill(user_data['lastName'])
                    last_name_filled = True
                    logger.info(f"Filled Last Name with selector: {selector}")
                    break
            except:
                continue

        if not last_name_filled:
            try:
                await self.page.get_by_label('Last Name').fill(user_data['lastName'])
                last_name_filled = True
            except:
                pass

        if not last_name_filled:
            raise Exception("Could not find Last Name field")

        # Fill Phone Number (optional)
        if user_data['phone']:
            phone_selectors = [
                'input[placeholder*="Phone" i]',
                'input[name*="phone" i]',
                'input[id*="phone" i]',
                'input[type="tel"]'
            ]

            for selector in phone_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.fill(user_data['phone'])
                        logger.info(f"Filled Phone with selector: {selector}")
                        break
                except:
                    continue

        # Fill Email Address
        email_filled = False
        email_selectors = [
            'input[placeholder*="Email" i]',
            'input[name*="email" i]',
            'input[id*="email" i]',
            'input[type="email"]'
        ]

        for selector in email_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.fill(user_data['email'])
                    email_filled = True
                    logger.info(f"Filled Email with selector: {selector}")
                    break
            except:
                continue

        if not email_filled:
            try:
                await self.page.get_by_label('Email').fill(user_data['email'])
                email_filled = True
            except:
                try:
                    await self.page.get_by_label('Email Address').fill(user_data['email'])
                    email_filled = True
                except:
                    pass

        if not email_filled:
            raise Exception("Could not find Email field")

        # Fill NMLS (optional, for Loan Officers)
        if user_data['nmls']:
            nmls_selectors = [
                'input[placeholder*="NMLS" i]',
                'input[name*="nmls" i]',
                'input[id*="nmls" i]'
            ]

            for selector in nmls_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.fill(user_data['nmls'])
                        logger.info(f"Filled NMLS with selector: {selector}")
                        break
                except:
                    continue

        # Take screenshot of filled form
        await self.page.screenshot(path='mmi_form_filled.png')
        logger.info("User details filled")

    async def _set_permissions(self):
        """Set user permissions (checkboxes)"""
        logger.info("Setting permissions...")

        # Get default permissions from config
        default_permissions = self.config.get('permissions', {}).get('loan_officer_default', [])

        if not default_permissions:
            # Use hardcoded defaults if not in config
            default_permissions = [
                "Agent Tracking Alerts",
                "Builder Research",
                "Loan Officer Tools",
                "Manual Property Monitoring",
                "Past Property Tracking Alerts",
                "Property/County research",
                "Title Explorer",
                "View LO Contact Details"
            ]

        # Check each permission checkbox
        for permission in default_permissions:
            try:
                # Try clicking by label text
                checkbox = self.page.locator(f'label:has-text("{permission}") input[type="checkbox"]')
                if await checkbox.count() > 0:
                    # Check if not already checked
                    is_checked = await checkbox.is_checked()
                    if not is_checked:
                        await checkbox.check()
                        logger.info(f"Checked permission: {permission}")
                    continue
            except:
                pass

            try:
                # Alternative: click the label itself
                label = self.page.locator(f'text="{permission}"')
                if await label.count() > 0:
                    await label.click()
                    logger.info(f"Clicked permission label: {permission}")
            except:
                logger.warning(f"Could not find permission checkbox: {permission}")

        # Take screenshot of permissions
        await self.page.screenshot(path='mmi_permissions_set.png')
        logger.info("Permissions set")

    async def _create_user(self):
        """Click Create button to finalize user creation"""
        logger.info("Creating user...")

        # Take screenshot before creating
        await self.page.screenshot(path='mmi_before_create.png')

        # Click Create button
        create_clicked = False
        create_selectors = [
            'button:has-text("Create")',
            'input[type="submit"][value*="Create" i]',
            'button[type="submit"]:has-text("Create")',
            'text="Create"'
        ]

        for selector in create_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    create_clicked = True
                    logger.info(f"Clicked Create button with selector: {selector}")
                    break
            except:
                continue

        if not create_clicked:
            # Try using locator
            try:
                await self.page.locator('button:has-text("Create")').click()
                create_clicked = True
            except:
                pass

        if not create_clicked:
            await self.page.screenshot(path='mmi_create_not_found.png')
            raise Exception("Could not find Create button")

        # Wait for response
        try:
            await self.page.wait_for_load_state('networkidle', timeout=15000)
        except:
            pass
        await asyncio.sleep(2)

        # Take screenshot of result
        await self.page.screenshot(path='mmi_user_created.png')

        # Check for success indicators
        page_content = await self.page.content()
        success_indicators = ['success', 'created', 'added', 'welcome']
        error_indicators = ['error', 'failed', 'already exists', 'duplicate']

        for indicator in error_indicators:
            if indicator.lower() in page_content.lower():
                raise Exception(f"User creation may have failed: found '{indicator}' in page")

        logger.info("User created successfully")

    async def _cleanup(self):
        """Clean up browser resources"""
        logger.info("Cleaning up browser...")
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")


async def provision_user(user: EntraUser, config_path: str) -> Dict[str, Any]:
    """
    Main entry point for MMI user provisioning

    Args:
        user: EntraUser object
        config_path: Path to vendor config JSON

    Returns:
        Dict with provisioning result
    """
    from services.keyvault_service import KeyVaultService

    # Initialize KeyVault service
    keyvault = KeyVaultService()

    # Create automation instance
    automation = MMIAutomation(config_path, keyvault)

    # Run automation
    result = await automation.create_account(user, headless=False)

    return result
