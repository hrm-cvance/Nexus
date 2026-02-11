"""
MMI (Mortgage Market Intelligence) User Provisioning Automation

This module automates the creation of user accounts in the MMI portal
using Playwright for web automation.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Awaitable

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

    async def create_account(
        self,
        user: EntraUser,
        headless: bool = False,
        on_email_conflict: Optional[Callable[[str, str], Awaitable[Optional[str]]]] = None
    ) -> Dict[str, Any]:
        """
        Create an MMI account for the given user

        Args:
            user: EntraUser object with user details
            headless: Whether to run browser in headless mode
            on_email_conflict: Async callback when email is taken.
                Receives (display_name, attempted_email).
                Should return new email to try, or None to skip this vendor.

        Returns:
            Dict with success status and messages
        """
        self.current_user = user
        self.on_email_conflict = on_email_conflict
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

            # Navigate to admin-team page
            await self._navigate_to_admin_team()
            result['messages'].append("Navigated to admin-team page")

            # Click Add Team Member tab
            await self._click_add_team_member()
            result['messages'].append("Opened Add Team Member form")

            # Fill user details
            await self._fill_user_details(user_data)
            result['messages'].append("Filled user details")

            # Set permissions
            await self._set_permissions()
            result['messages'].append("Set user permissions")

            # Create user and check for duplicates
            create_result = await self._create_user()

            if create_result == 'duplicate_email':
                # Duplicate email detected - prompt user for decision
                if on_email_conflict:
                    result['messages'].append(f"Email '{user_data['email']}' is already in use")
                    new_email = await on_email_conflict(user.display_name, user_data['email'])

                    if new_email is None:
                        # User chose to skip
                        result['success'] = False
                        result['warnings'].append(f"Email '{user_data['email']}' already exists - User chose to skip")
                        logger.info(f"User skipped MMI due to email conflict: {user.display_name}")
                        return result
                    else:
                        # User provided alternative email - go back to form and retry
                        logger.info(f"User provided alternate email: {new_email}")
                        result['messages'].append(f"Trying alternate email: {new_email}")

                        # Navigate back to admin-team for a fresh form
                        await self._navigate_to_admin_team()
                        await self._click_add_team_member()
                        user_data['email'] = new_email
                        await self._fill_user_details(user_data)
                        await self._set_permissions()

                        # Try again
                        create_result = await self._create_user()
                        if create_result != 'success':
                            result['errors'].append(f"Alternate email '{new_email}' also failed: {create_result}")
                            result['success'] = False
                            return result
                        result['messages'].append(f"Used alternate email: {new_email}")
                else:
                    # No callback provided - fail with error
                    result['success'] = False
                    result['warnings'].append(f"Email '{user_data['email']}' already exists - Account was not created")
                    logger.info(f"Email conflict in MMI, no callback provided: {user.display_name}")
                    return result

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

        # NMLS - from extensionAttribute2 in Entra ID
        nmls = ""
        if user.nmls_number:
            nmls = user.nmls_number

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

        # Check for MFA / Two-Factor Authentication
        await self._handle_mfa()

        # Take screenshot after login
        await self.page.screenshot(path='mmi_after_login.png')
        logger.info("Login completed")

    async def _handle_mfa(self):
        """Handle Two-Factor Authentication if present on the MMI login flow"""
        logger.info("Checking for MFA...")

        page_content = await self.page.content()
        if 'two-factor authentication' not in page_content.lower() and 'send verification code' not in page_content.lower():
            logger.info("No MFA detected")
            return

        logger.info("MFA (Two-Factor Authentication) detected")
        print("MFA detected - clicking Send Verification Code...")
        await self.page.screenshot(path='mmi_mfa_page.png')

        # Click "Send Verification Code" button
        try:
            send_btn = self.page.locator('button:has-text("Send Verification Code")')
            await send_btn.click()
            logger.info("Clicked Send Verification Code button")
            print("Verification code sent via SMS - waiting for user to enter code...")
        except Exception as e:
            logger.warning(f"Could not click Send Verification Code: {e}")
            print("Could not auto-click Send Verification Code - please click it manually")

        await asyncio.sleep(2)
        await self.page.screenshot(path='mmi_mfa_code_sent.png')

        # Wait for user to enter the code and complete MFA
        print("=" * 60)
        print("MFA REQUIRED: Please complete the following steps:")
        print("1. Check your phone for the SMS verification code")
        print("2. Enter the code in the browser")
        print("3. Click Verify / Submit to complete login")
        print("=" * 60)

        # Poll until MFA page is gone (user completed it)
        max_wait_time = 600  # 10 minutes
        check_interval = 3
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            await asyncio.sleep(check_interval)
            elapsed_time += check_interval

            # Primary check: if URL has changed from login page, MFA is done
            current_url = self.page.url.lower()
            if '/login' not in current_url and 'verify' not in current_url:
                logger.info(f"MFA completed - URL changed to: {self.page.url}")
                print("MFA completed - continuing automation")
                await asyncio.sleep(2)
                return

            # Secondary check: look for MFA-specific visible text
            try:
                page_text = await self.page.inner_text('body')
                page_text = page_text.lower()
            except:
                page_text = ''

            mfa_still_present = (
                'two-factor authentication' in page_text
                or 'verify my account' in page_text
                or 'enter the six-digit code' in page_text
            )

            if not mfa_still_present and page_text:
                logger.info("MFA completed - MFA text no longer visible")
                print("MFA completed - continuing automation")
                await asyncio.sleep(2)
                return

            if elapsed_time % 30 == 0:
                print(f"Still waiting for MFA completion... ({elapsed_time}s elapsed)")
                await self.page.screenshot(path=f'mmi_mfa_wait_{elapsed_time}s.png')

        raise Exception("MFA timeout - authentication not completed within 10 minutes")

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

    async def _navigate_to_admin_team(self):
        """Navigate directly to admin-team page"""
        logger.info("Navigating to admin-team page...")
        print("Navigating to admin-team page...")

        await self.page.goto('https://new.mmi.run/admin-team')

        # Wait for page to load
        try:
            await self.page.wait_for_load_state('networkidle', timeout=15000)
        except:
            pass
        await asyncio.sleep(2)

        # Take screenshot
        await self.page.screenshot(path='mmi_admin_team_page.png')
        logger.info("Navigated to admin-team page")

    async def _click_add_team_member(self):
        """Click Add Team Member tab/button on the admin-team page"""
        logger.info("Clicking Add Team Member...")
        print("Clicking Add Team Member...")

        await asyncio.sleep(1)
        await self.page.screenshot(path='mmi_before_add_member.png')

        # Look for the "Add Team Member" tab or link on the admin-team page
        add_member_clicked = False
        add_member_selectors = [
            '[role="tab"]:has-text("Add Team Member")',
            'a:has-text("Add Team Member")',
            'button:has-text("Add Team Member")',
            'text="Add Team Member"',
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
            # The admin-team page may already show the form
            # Check if form fields are visible
            form_visible = False
            try:
                first_name = await self.page.query_selector('input[placeholder*="First" i]')
                if first_name and await first_name.is_visible():
                    form_visible = True
            except:
                pass

            if not form_visible:
                try:
                    first_name = await self.page.query_selector('input[name*="first" i]')
                    if first_name and await first_name.is_visible():
                        form_visible = True
                except:
                    pass

            if form_visible:
                logger.info("Add Team Member form already visible")
            else:
                await self.page.screenshot(path='mmi_add_member_not_found.png')
                raise Exception("Could not find Add Team Member tab/button or form")

        # Wait for form to appear
        await asyncio.sleep(1)
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

    def _determine_permissions(self) -> list:
        """
        Determine which permissions to assign based on user's job title.

        Per MMI User Setup Guide:
        - All users get base Loan Officer permissions
        - Branch Managers, Executives, Recruiters also get Company Wallet Share
        - Executives, Recruiters also get Wholesale Insights
        """
        permissions_config = self.config.get('permissions', {})

        # Start with base permissions for all users
        base_permissions = permissions_config.get('loan_officer_default', [
            "Agent Tracking Alerts",
            "Builder Research",
            "Loan Officer Tools",
            "Manual Property Monitoring",
            "Past Property Tracking Alerts",
            "Property/County research",
            "Title Explorer",
            "View LO Contact Details"
        ])
        permissions = list(base_permissions)

        # Check user's title for elevated access
        job_title = (self.current_user.job_title or '').lower()
        logger.info(f"Determining permissions for job title: '{self.current_user.job_title}'")

        # Title keywords indicating branch manager level or above
        is_branch_manager = any(kw in job_title for kw in [
            'branch manager', 'area manager', 'regional manager',
            'division manager', 'production manager'
        ])

        # Title keywords indicating executive or recruiter level
        is_executive = any(kw in job_title for kw in [
            'executive', 'evp', 'svp', 'vp', 'vice president',
            'president', 'ceo', 'cfo', 'coo', 'chief',
            'director', 'recruiter', 'recruiting'
        ])

        # Branch Managers and above get Company Wallet Share
        if is_branch_manager or is_executive:
            additional = permissions_config.get('branch_manager_additional', ['Company Wallet Share'])
            for perm in additional:
                if perm not in permissions:
                    permissions.append(perm)
            logger.info("Added Branch Manager permissions (Company Wallet Share)")

        # Executives and Recruiters also get Wholesale Insights
        if is_executive:
            additional = permissions_config.get('executive_additional', ['Wholesale Insights'])
            for perm in additional:
                if perm not in permissions:
                    permissions.append(perm)
            logger.info("Added Executive permissions (Wholesale Insights)")

        logger.info(f"Final permissions list ({len(permissions)}): {permissions}")
        return permissions

    async def _set_permissions(self):
        """Set user permissions (checkboxes) based on role"""
        logger.info("Setting permissions...")

        permissions = self._determine_permissions()

        # Check each permission checkbox
        for permission in permissions:
            checked = False

            # Try checkbox inside label
            try:
                checkbox = self.page.locator(f'label:has-text("{permission}") input[type="checkbox"]')
                if await checkbox.count() > 0:
                    is_checked = await checkbox.is_checked()
                    if not is_checked:
                        await checkbox.check()
                        logger.info(f"Checked permission: {permission}")
                    else:
                        logger.info(f"Permission already checked: {permission}")
                    checked = True
            except:
                pass

            # Try checkbox next to text
            if not checked:
                try:
                    checkbox = self.page.locator(f'input[type="checkbox"]').locator(f'xpath=..//*[contains(text(), "{permission}")]/..')
                    if await checkbox.count() > 0:
                        await checkbox.locator('input[type="checkbox"]').first.check()
                        logger.info(f"Checked permission via sibling: {permission}")
                        checked = True
                except:
                    pass

            # Try clicking the label text directly (some UIs toggle on label click)
            if not checked:
                try:
                    label = self.page.locator(f'text="{permission}"')
                    if await label.count() > 0:
                        await label.first.click()
                        logger.info(f"Clicked permission label: {permission}")
                        checked = True
                except:
                    pass

            if not checked:
                logger.warning(f"Could not find permission checkbox: {permission}")

        # Take screenshot of permissions
        await self.page.screenshot(path='mmi_permissions_set.png')
        logger.info("Permissions set")

    async def _create_user(self) -> str:
        """
        Click Create button to finalize user creation and check for errors

        Returns:
            'success' if user created
            'duplicate_email' if email/user already exists
        """
        logger.info("Creating user...")

        # Take screenshot before creating
        await self.page.screenshot(path='mmi_before_create.png')

        # Click Create button - matches: <button class="button button-primary button-md" type="submit">Create</button>
        create_clicked = False
        create_selectors = [
            'button.button.button-primary[type="submit"]',
            'button[type="submit"]:has-text("Create")',
            'button:has-text("Create")',
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

        # Check for duplicate/error messages
        page_content = await self.page.content()
        page_text = page_content.lower()

        # Check for "already exists" or "duplicate" indicators
        if 'already exists' in page_text or 'duplicate' in page_text:
            logger.warning("Duplicate user/email detected")
            await self.page.screenshot(path='mmi_duplicate_detected.png')
            return 'duplicate_email'

        # Check for email-specific errors
        if 'email' in page_text and ('in use' in page_text or 'taken' in page_text or 'registered' in page_text):
            logger.warning("Email already in use detected")
            await self.page.screenshot(path='mmi_email_in_use.png')
            return 'duplicate_email'

        # Check for any visible error message elements
        error_selectors = [
            '.error', '.alert-danger', '.alert-error', '[class*="error"]',
            '.validation-error', '.field-error', '[role="alert"]',
            '.toast-error', '.notification-error', '[class*="toast"]',
            '#snackbar.error', '#snackbar'
        ]
        for selector in error_selectors:
            try:
                error_elements = await self.page.query_selector_all(selector)
                for elem in error_elements:
                    if elem and await elem.is_visible():
                        error_text = await elem.text_content()
                        if error_text:
                            error_text_lower = error_text.lower().strip()
                            if 'already' in error_text_lower or 'exists' in error_text_lower or 'duplicate' in error_text_lower or 'in use' in error_text_lower:
                                logger.warning(f"Error element detected: {error_text}")
                                await self.page.screenshot(path='mmi_error_element.png')
                                return 'duplicate_email'
            except:
                continue

        # Check for generic failure indicators (not duplicate-specific)
        generic_error_indicators = ['error', 'failed']
        for indicator in generic_error_indicators:
            if indicator in page_text:
                # Only raise if it's a non-duplicate error
                logger.warning(f"Generic error indicator found: '{indicator}'")
                raise Exception(f"User creation may have failed: found '{indicator}' in page")

        logger.info("User created successfully")
        return 'success'

    async def _cleanup(self):
        """Clean up browser resources"""
        logger.info("Cleaning up browser...")
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")


async def provision_user(
    user: EntraUser,
    config_path: str,
    api_key: Optional[str] = None,
    on_email_conflict: Optional[Callable[[str, str], Awaitable[Optional[str]]]] = None
) -> Dict[str, Any]:
    """
    Main entry point for MMI user provisioning

    Args:
        user: EntraUser object
        config_path: Path to vendor config JSON
        api_key: Optional API key (not used for MMI)
        on_email_conflict: Async callback when email is taken.
            Receives (display_name, attempted_email).
            Should return new email to try, or None to skip this vendor.

    Returns:
        Dict with provisioning result
    """
    from services.keyvault_service import KeyVaultService

    # Initialize KeyVault service
    keyvault = KeyVaultService()

    # Create automation instance
    automation = MMIAutomation(config_path, keyvault)

    # Run automation with callback
    result = await automation.create_account(
        user,
        headless=False,
        on_email_conflict=on_email_conflict
    )

    return result
