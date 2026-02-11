"""
Experience.com User Provisioning Automation

This module automates the creation and configuration of user accounts in
Experience.com using Playwright for web automation.

Workflow:
1. Login to Experience.com
2. Navigate to Hierarchy -> Users
3. Add new user (Add Single User)
4. Fill user form with Entra data
5. Configure Profile Settings (Review Management, Social Share, etc.)
6. Publish user profile
7. Capture Widget Code (for Bigfish)
8. Capture Profile URL (for Total Expert)
9. Fill Profile Info fields (Title, Contact, NMLS)
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

from playwright.async_api import async_playwright, Page, Browser, Playwright

from models.user import EntraUser
from services.keyvault_service import KeyVaultService

# Configure logging
logger = logging.getLogger('automation.vendors.experience')


class ExperienceAutomation:
    """Handles Experience.com user provisioning automation"""

    def __init__(self, config_path: str, keyvault: KeyVaultService):
        """
        Initialize Experience.com automation

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
        self.screenshot_counter = 0

    def _load_config(self) -> Dict[str, Any]:
        """Load vendor configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded config from {self.config_path}")
        return config

    def _prepare_user_data(self, user: EntraUser) -> Dict[str, Any]:
        """
        Prepare user data for Experience.com form from Entra user

        Args:
            user: EntraUser object from Entra ID

        Returns:
            Dict with formatted user data for Experience.com
        """
        # Get first/last name from Entra
        first_name = user.given_name or user.display_name.split()[0]
        last_name = user.surname or (user.display_name.split()[-1] if len(user.display_name.split()) > 1 else '')

        # Email from Entra
        email = user.mail or user.user_principal_name

        # Employee ID from Entra
        employee_id = user.employee_id or ''

        # Determine role based on job title
        role = self._determine_role(user.job_title)

        # Get tier (branch location) from office_location or default
        tier = self.config.get('tier_mapping', {}).get('default_tier', 'Plano')

        return {
            'firstName': first_name,
            'lastName': last_name,
            'email': email,
            'employeeId': employee_id,
            'tier': tier,
            'role': role,
            'title': user.job_title or '',
            'phone': user.business_phones[0] if user.business_phones else '',
            'mobile': user.mobile_phone or '',
            'nmls_number': user.nmls_number or '',
            'headshot_url': user.headshot_url or '',
            'website_url': user.website_url or '',
        }

    def _determine_role(self, job_title: str) -> str:
        """Determine Experience.com role based on job title"""
        if not job_title:
            return self.config.get('role_mapping', {}).get('roles', {}).get('default', 'User')

        job_title_lower = job_title.lower()
        manager_keywords = self.config.get('role_mapping', {}).get('manager_keywords', [])

        for keyword in manager_keywords:
            if keyword.lower() in job_title_lower:
                return self.config.get('role_mapping', {}).get('roles', {}).get('manager', 'Tier Manager')

        return self.config.get('role_mapping', {}).get('roles', {}).get('default', 'User')

    async def _screenshot(self, name: str):
        """Take a screenshot with numbered prefix"""
        self.screenshot_counter += 1
        filename = f'experience_{self.screenshot_counter:02d}_{name}.png'
        await self.page.screenshot(path=filename)
        logger.debug(f"Screenshot: {filename}")

    async def _wait_for_loading(self, timeout: int = 30):
        """Wait for any loading spinners to disappear"""
        logger.debug("Waiting for loading spinners to disappear...")
        start_time = asyncio.get_event_loop().time()

        while True:
            # Check for Ant Design spinner
            spinner = await self.page.query_selector('.ant-spin-spinning')
            if not spinner:
                break

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                logger.warning(f"Loading spinner still present after {timeout}s timeout")
                break

            await asyncio.sleep(0.5)

        # Additional wait for page to stabilize
        await asyncio.sleep(1)
        logger.debug("Loading complete")

    async def provision_user(self, user: EntraUser, headless: bool = False) -> Dict[str, Any]:
        """
        Provision an Experience.com account for the given user

        Args:
            user: EntraUser object with user details from Entra ID
            headless: Whether to run browser in headless mode

        Returns:
            Dict with success status, messages, widget_code, profile_url
        """
        self.current_user = user
        self.screenshot_counter = 0
        user_data = self._prepare_user_data(user)
        logger.info(f"Starting Experience.com automation for {user.display_name}")
        logger.info(f"Prepared user data: {user_data}")

        result = {
            'success': False,
            'user': user.display_name,
            'messages': [],
            'warnings': [],
            'errors': [],
            'widget_code': '',
            'profile_url': ''
        }

        try:
            # Start browser
            await self._start_browser(headless=headless)

            # Login
            await self._login()
            result['messages'].append("Logged in successfully")

            # Navigate to Users
            await self._navigate_to_users()
            result['messages'].append("Navigated to Users")

            # Add new user
            user_created = await self._add_new_user(user_data)
            if user_created:
                result['messages'].append("Created new user")
            else:
                result['messages'].append("User already exists - updating profile")

            # Configure Profile Settings
            await self._configure_profile_settings(user_data)
            result['messages'].append("Configured profile settings")

            # Publish user profile
            published = await self._publish_user(user_data)
            if published:
                result['messages'].append("Published user profile")
            else:
                result['warnings'].append("Could not publish user profile - toggle may be disabled")

            # Capture widget code
            widget_code = await self._get_widget_code(user_data)
            if widget_code:
                result['widget_code'] = widget_code
                result['messages'].append(f"Captured widget code ({len(widget_code)} chars)")
            else:
                result['warnings'].append("Could not capture widget code")

            # Capture profile URL
            profile_url = await self._get_profile_url(user_data)
            if profile_url:
                result['profile_url'] = profile_url
                result['messages'].append(f"Captured profile URL: {profile_url}")
            else:
                result['warnings'].append("Could not capture profile URL")

            # Fill profile info
            await self._fill_profile_info(user_data)
            result['messages'].append("Filled profile info fields")

            result['success'] = True
            logger.info(f"Successfully provisioned Experience.com account for {user.display_name}")

        except Exception as e:
            error_msg = f"Error during Experience.com automation: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            result['success'] = False

            try:
                if self.page:
                    await self._screenshot('error')
            except:
                pass

        finally:
            await self._cleanup()

        return result

    async def _start_browser(self, headless: bool = False):
        """Start Playwright browser"""
        logger.info("Starting browser...")
        self.playwright = await async_playwright().start()

        # Grant clipboard permissions and set larger viewport
        self.browser = await self.playwright.chromium.launch(headless=headless)
        context = await self.browser.new_context(
            permissions=['clipboard-read', 'clipboard-write'],
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await context.new_page()
        logger.info("Browser started with 1920x1080 viewport")

    async def _login(self):
        """Login to Experience.com"""
        login_url = self.keyvault.get_vendor_credential('experience', 'login-url')
        admin_email = self.keyvault.get_vendor_credential('experience', 'admin-email')
        admin_password = self.keyvault.get_vendor_credential('experience', 'admin-password')

        logger.info(f"Navigating to {login_url}")
        await self.page.goto(login_url, timeout=60000)
        # Wait for DOM to be ready, then give extra time for JS to initialize
        await self.page.wait_for_load_state('domcontentloaded', timeout=60000)
        await asyncio.sleep(3)

        await self._screenshot('login_page')

        # Enter email using the working selector from test script
        email_field = await self.page.query_selector('input[name="mail"]')
        if email_field:
            await email_field.fill(admin_email)
            logger.info(f"Filled email: {admin_email}")
        else:
            # Fallback selectors
            for selector in ['input[placeholder*="email" i]', 'input[type="text"]']:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.fill(admin_email)
                    logger.info(f"Filled email with fallback selector: {selector}")
                    break

        await self._screenshot('email_entered')

        # Check for CAPTCHA
        captcha_frame = await self.page.query_selector('iframe[title*="reCAPTCHA"]')
        if captcha_frame:
            logger.info("CAPTCHA detected - waiting for manual completion")
            print("*** MANUAL ACTION REQUIRED: Please complete the CAPTCHA ***")

            # Wait for CAPTCHA completion (password option appears)
            for i in range(120):
                await asyncio.sleep(1)
                password_block = await self.page.query_selector('#password-block')
                if password_block and await password_block.is_visible():
                    logger.info(f"CAPTCHA completed after {i+1} seconds")
                    break

        await asyncio.sleep(1)

        # Click "Sign in with password" option
        password_option_selectors = [
            '#password-block',
            'div#password-block',
            'text="Or sign in with a password instead."',
            'text="sign in with a password"',
        ]

        password_clicked = False
        for selector in password_option_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    password_clicked = True
                    logger.info(f"Clicked password option: {selector}")
                    await asyncio.sleep(2)
                    break
            except:
                continue

        if not password_clicked:
            logger.warning("Could not find password option - trying magic link flow")

        await self._screenshot('password_option_clicked')

        # Wait for password page
        try:
            await self.page.wait_for_load_state('networkidle', timeout=10000)
        except:
            pass
        await asyncio.sleep(3)

        # Enter password
        password_field = await self.page.query_selector('input[type="password"]')
        if password_field and await password_field.is_visible():
            await password_field.fill(admin_password)
            logger.info("Filled password")

            await self._screenshot('password_entered')

            # Click login button
            login_selectors = [
                'button[type="submit"]',
                'button:has-text("Sign in")',
                'button:has-text("Login")',
                'button:has-text("Log in")',
            ]

            for selector in login_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.click()
                        logger.info(f"Clicked login: {selector}")
                        break
                except:
                    continue

            # Wait for navigation
            try:
                await self.page.wait_for_load_state('networkidle', timeout=15000)
            except:
                pass
            await asyncio.sleep(3)

        await self._screenshot('after_login')

        # Verify login success
        page_content = await self.page.content()
        if 'Dashboard' in page_content or 'Hierarchy' in page_content:
            logger.info("Login successful - found dashboard elements")
        else:
            logger.warning("May not be logged in - check screenshots")

    async def _navigate_to_users(self):
        """Navigate to Hierarchy -> Users"""
        logger.info("Navigating to Users...")

        # Click Hierarchy
        hierarchy_selectors = [
            'text="Hierarchy"',
            '[href*="hierarchy"]',
            'a:has-text("Hierarchy")',
            'button:has-text("Hierarchy")',
        ]

        for selector in hierarchy_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    logger.info(f"Clicked Hierarchy: {selector}")
                    break
            except:
                continue

        await asyncio.sleep(1)

        # Click Users
        users_selectors = [
            'button:has-text("Users")',
            'text="Users"',
            '[role="tab"]:has-text("Users")',
        ]

        for selector in users_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    if element and await element.is_visible():
                        await element.click()
                        logger.info(f"Clicked Users: {selector}")
                        break
            except:
                continue

        await asyncio.sleep(2)
        await self._screenshot('users_page')

    async def _add_new_user(self, user_data: Dict[str, Any]) -> bool:
        """Add a new user to Experience.com

        Returns:
            True if user was created, False if user already exists
        """
        logger.info(f"Adding new user: {user_data['firstName']} {user_data['lastName']}")

        await self._screenshot('before_add_user')

        # Click Add New User
        add_user_selectors = [
            'button:has-text("Add New User")',
            'text="Add New User"',
            'button:has-text("Add User")',
        ]

        add_clicked = False
        for selector in add_user_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    logger.info(f"Clicked Add New User: {selector}")
                    add_clicked = True
                    break
            except:
                continue

        if not add_clicked:
            logger.warning("Could not find Add New User button")
            await self._screenshot('add_new_user_not_found')

        await asyncio.sleep(2)
        await self._screenshot('after_add_new_user_click')

        # Click Add Single User
        single_user_selectors = [
            'text="Add Single User"',
            'label:has-text("Add Single User")',
        ]

        single_clicked = False
        for selector in single_user_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    logger.info(f"Clicked Add Single User: {selector}")
                    single_clicked = True
                    break
            except:
                continue

        if not single_clicked:
            logger.warning("Could not find Add Single User option")
            await self._screenshot('add_single_user_not_found')

        await asyncio.sleep(1)
        await self._screenshot('add_user_form')

        # Fill First Name
        first_filled = False
        for selector in ['input[placeholder*="First" i]', 'input[name*="first" i]']:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.fill(user_data['firstName'])
                    logger.info(f"Filled First Name: {user_data['firstName']}")
                    first_filled = True
                    break
            except:
                continue

        if not first_filled:
            logger.warning("Could not find First Name field")

        # Fill Last Name
        last_filled = False
        for selector in ['input[placeholder*="Last" i]', 'input[name*="last" i]']:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.fill(user_data['lastName'])
                    logger.info(f"Filled Last Name: {user_data['lastName']}")
                    last_filled = True
                    break
            except:
                continue

        if not last_filled:
            logger.warning("Could not find Last Name field")

        # Fill Email
        email_filled = False
        for selector in ['input[type="email"]', 'input[placeholder*="email" i]', 'input[name*="email" i]']:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    value = await element.input_value()
                    if not value:  # Skip if already filled (login email field)
                        await element.fill(user_data['email'])
                        logger.info(f"Filled Email: {user_data['email']}")
                        email_filled = True
                        break
            except:
                continue

        if not email_filled:
            logger.warning("Could not find Email field")

        # Check for "Email Already Registered" error after filling email
        await asyncio.sleep(1)  # Wait for validation
        email_error = await self.page.query_selector('.ant-form-item-explain-error')
        if email_error and await email_error.is_visible():
            error_text = await email_error.text_content()
            if error_text and "Already Registered" in error_text:
                logger.warning(f"Email already registered: {user_data['email']}")
                # Close the modal and return - user already exists
                close_btn = await self.page.query_selector('button.ant-modal-close')
                if close_btn and await close_btn.is_visible():
                    await close_btn.click()
                    await asyncio.sleep(1)
                return False  # Indicate user already exists

        # Fill Employee ID
        if user_data['employeeId']:
            emp_filled = False
            for selector in ['input[placeholder*="Employee" i]', 'input[name*="employee" i]']:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.fill(user_data['employeeId'])
                        logger.info(f"Filled Employee ID: {user_data['employeeId']}")
                        emp_filled = True
                        break
                except:
                    continue

            if not emp_filled:
                logger.warning("Could not find Employee ID field")

        await self._screenshot('form_basic_info')

        # Configure toggles - Turn OFF "Allow user to expire a survey"
        expire_toggle_selectors = [
            '//*[contains(text(), "Allow user to expire a survey")]/following::button[contains(@class, "ant-switch")][1]',
            '//*[contains(text(), "expire a survey")]/ancestor::div[1]//button[contains(@class, "ant-switch")]',
        ]

        for selector in expire_toggle_selectors:
            try:
                toggle = await self.page.query_selector(selector)
                if toggle and await toggle.is_visible():
                    is_checked = await toggle.evaluate('el => el.classList.contains("ant-switch-checked")')
                    if is_checked:
                        await toggle.click()
                        logger.info("Turned OFF 'Allow user to expire a survey'")
                    break
            except:
                continue

        await self._screenshot('after_toggles')

        # Scroll to find Tier and Role section
        tier_section = await self.page.query_selector('text="Tier and Role Assignment"')
        if tier_section:
            await tier_section.scroll_into_view_if_needed()
            logger.info("Found and scrolled to Tier and Role Assignment section")
            await asyncio.sleep(0.5)
        else:
            logger.warning("Could not find Tier and Role Assignment section")

        await self._screenshot('before_tier_selection')

        # Select Tier using Experience.com's Ant Design dropdown
        await self._select_experience_dropdown('Tier', user_data['tier'])

        await self._screenshot('after_tier_selection')

        # Select Role using Experience.com's Ant Design dropdown
        await self._select_experience_dropdown('Role', user_data['role'])

        await self._screenshot('after_role_selection')

        # Click plus button to add Tier/Role
        plus_selectors = [
            'svg[viewBox="0 0 11 11"]',
            'button:has(svg[viewBox="0 0 11 11"])',
        ]

        plus_clicked = False
        for selector in plus_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    if element and await element.is_visible():
                        await element.click()
                        logger.info("Clicked plus button for Tier/Role")
                        plus_clicked = True
                        break
                if plus_clicked:
                    break
            except:
                continue

        if not plus_clicked:
            logger.warning("Could not find plus button for Tier/Role")

        await asyncio.sleep(1)
        await self._screenshot('after_plus_button')

        # Fill Title if available
        if user_data['title']:
            title_filled = False
            for selector in ['input[placeholder*="Title" i]', 'input[name*="title" i]']:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.fill(user_data['title'])
                        logger.info(f"Filled Title: {user_data['title']}")
                        title_filled = True
                        break
                except:
                    continue

            if not title_filled:
                logger.warning("Could not find Title field")

        await self._screenshot('form_complete')

        # Click Create User
        create_btn = await self.page.query_selector('button:has-text("Create User")')
        if create_btn and await create_btn.is_visible():
            await create_btn.click()
            logger.info("Clicked Create User")
            await asyncio.sleep(2)
        else:
            logger.warning("Could not find Create User button")
            await self._screenshot('create_user_not_found')

        await self._screenshot('after_create_user')

        # Click Confirm
        confirm_btn = await self.page.query_selector('button:has-text("Confirm")')
        if confirm_btn and await confirm_btn.is_visible():
            await confirm_btn.click()
            logger.info("Clicked Confirm")
            await asyncio.sleep(2)
        else:
            logger.warning("Could not find Confirm button")

        # Wait for user creation to complete (loading spinner to disappear)
        await self._wait_for_loading()

        await self._screenshot('user_created')
        return True  # User was created successfully

    async def _select_experience_dropdown(self, label: str, value: str):
        """Select a value from Experience.com's Ant Design dropdown

        Uses specific input IDs for Tier and Role dropdowns.
        """
        try:
            logger.info(f"Selecting {label}: {value}")

            # Experience.com uses Ant Design select components with specific IDs
            input_id_map = {
                'Tier': 'selectTier',
                'Role': 'selectRole',
            }
            input_id = input_id_map.get(label)

            dropdown_clicked = False

            # Approach 1: Click directly on the input by ID
            if input_id:
                try:
                    input_el = await self.page.query_selector(f'#{input_id}')
                    if input_el:
                        await input_el.click()
                        dropdown_clicked = True
                        logger.info(f"Clicked input #{input_id}")
                except Exception as e:
                    logger.debug(f"Input click failed: {e}")

            # Approach 2: Click on the ant-select-selection-item (already selected value)
            if not dropdown_clicked:
                selection_selectors = [
                    'span.ant-select-selection-item',
                    '[class*="ant-select-selection-item"]',
                ]

                for selector in selection_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        for el in elements:
                            if el and await el.is_visible():
                                await el.click()
                                dropdown_clicked = True
                                logger.info(f"Clicked selection item")
                                break
                        if dropdown_clicked:
                            break
                    except:
                        continue

            # Approach 3: Click on the select container with placeholder
            if not dropdown_clicked:
                placeholder_map = {
                    'Tier': 'Select Tier',
                    'Role': 'Select Tier Roles',
                }
                placeholder = placeholder_map.get(label, f'Select {label}')

                dropdown_selectors = [
                    f'[class*="ant-select"]:has-text("{placeholder}")',
                    f'[class*="select"]:has-text("{placeholder}")',
                ]

                for selector in dropdown_selectors:
                    try:
                        dropdown = await self.page.query_selector(selector)
                        if dropdown and await dropdown.is_visible():
                            await dropdown.click()
                            dropdown_clicked = True
                            logger.info(f"Clicked dropdown with placeholder: {placeholder}")
                            break
                    except:
                        continue

            if not dropdown_clicked:
                logger.warning(f"Could not find dropdown for '{label}'")
                return

            await asyncio.sleep(0.5)

            # Clear any existing text and type to filter the options
            await self.page.keyboard.press('Control+a')
            await self.page.keyboard.press('Backspace')
            await self.page.keyboard.type(value, delay=50)
            await asyncio.sleep(1)

            # Try to click matching option from Ant Design dropdown
            option_selectors = [
                f'[class*="ant-select-item"]:has-text("{value}")',
                f'[class*="ant-select-item-option"]:has-text("{value}")',
                f'div[role="option"]:has-text("{value}")',
            ]

            option_found = False
            for opt_sel in option_selectors:
                try:
                    options = await self.page.query_selector_all(opt_sel)
                    for option in options:
                        if option and await option.is_visible():
                            opt_text = await option.inner_text()
                            if value.lower() in opt_text.lower():
                                await option.click()
                                logger.info(f"Selected option: '{opt_text}'")
                                option_found = True
                                await asyncio.sleep(0.5)
                                break
                    if option_found:
                        break
                except:
                    continue

            if not option_found:
                # Fallback: press Enter to select first filtered result
                logger.info(f"Pressing Enter to select first match")
                await self.page.keyboard.press('Enter')
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.warning(f"Could not select dropdown {label}: {e}")

    async def _search_user(self, user_data: Dict[str, Any]):
        """Search for a user in the users list"""
        user_name = f"{user_data['firstName']} {user_data['lastName']}"

        # Wait for any loading to complete first
        await self._wait_for_loading()

        # Check if filter sidebar is visible
        search_box = await self.page.query_selector('input[placeholder="Search"]')
        if not search_box or not await search_box.is_visible():
            filter_btn = await self.page.query_selector('text="Show filter"')
            if filter_btn and await filter_btn.is_visible():
                await filter_btn.click()
                await asyncio.sleep(1)
                search_box = await self.page.query_selector('input[placeholder="Search"]')

        if search_box and await search_box.is_visible():
            await search_box.fill('')
            await search_box.fill(user_name)
            logger.info(f"Searching for user: {user_name}")
            await asyncio.sleep(2)

    async def _configure_profile_settings(self, user_data: Dict[str, Any]):
        """Configure user's Profile Settings tab

        Configures settings per Experience User Guide:
        - Review Management: reply toggle ON, min score 3, AI reply ON
        - Social Share: autopost ON, min score 4.5, max 3/day, 2hr gap
        - Expire Survey: toggle OFF
        - Send Settings: notifications ON
        """
        user_name = f"{user_data['firstName']} {user_data['lastName']}"
        logger.info(f"Configuring profile settings for {user_name}")

        # Navigate to Users page first (in case we're still on user creation modal)
        await self._navigate_to_users()
        await asyncio.sleep(2)

        await self._search_user(user_data)

        # Click three dots menu
        menu_btn = await self.page.query_selector('button:has(svg path[d*="M12"])')
        if menu_btn and await menu_btn.is_visible():
            await menu_btn.click()
            await asyncio.sleep(1)

        # Click Edit
        edit_btn = await self.page.query_selector('text="Edit"')
        if edit_btn and await edit_btn.is_visible():
            await edit_btn.click()
            await asyncio.sleep(2)

        # Click Profile Settings tab
        profile_settings_tab = await self.page.query_selector('text="Profile Settings"')
        if profile_settings_tab and await profile_settings_tab.is_visible():
            await profile_settings_tab.click()
            await asyncio.sleep(1)

        await self._screenshot('profile_settings')

        # Get config defaults
        defaults = self.config.get('defaults', {})

        # ============================================================
        # SECTION 1: REVIEW MANAGEMENT SETTINGS
        # ============================================================
        review_mgmt_label = await self.page.query_selector('text="Review Management Settings"')
        if review_mgmt_label:
            await review_mgmt_label.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)

        # Verify "Allow user to reply to reviews" is ON
        await self._verify_toggle_on("Allow user to reply to reviews")

        # Set "Minimum score to reply on reviews" slider
        await self._set_slider_value('Minimum score to reply on reviews', defaults.get('minimum_score_to_reply', 3))

        # Verify "Allow user to reply using AI" is ON
        await self._verify_toggle_on("Allow user to reply using AI")

        # ============================================================
        # SECTION 2: SOCIAL SHARE SETTINGS
        # ============================================================
        social_share_label = await self.page.query_selector('text="Social Share Settings"')
        if social_share_label:
            await social_share_label.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)

        # Verify "Allow autopost" is ON
        await self._verify_toggle_on("Allow autopost")

        # Set "Minimum Score to Auto-post" slider
        await self._set_slider_value('Minimum Score to Auto-post', defaults.get('autopost_minimum_score', 4.5))

        # Set "Maximum number of posts per day"
        max_posts = defaults.get('autopost_max_per_day', 3)
        await self._set_number_input("Maximum number of posts per day", str(max_posts))

        # Set "Minimum gap between posts" - 2 hours
        await self._set_number_input("Minimum gap between posts", "2")

        # ============================================================
        # SECTION 3: EXPIRE SURVEY
        # ============================================================
        expire_label = await self.page.query_selector('text="Allow to Expire Survey"')
        if expire_label:
            await expire_label.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)

        # Turn OFF "Allow user to expire a survey"
        await self._set_toggle_off("Allow user to expire a survey")

        # ============================================================
        # SECTION 4: SEND SETTINGS
        # ============================================================
        send_label = await self.page.query_selector('text="Send Settings"')
        if send_label:
            await send_label.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)

        # Verify notifications are ON
        await self._verify_toggle_on("Allow survey completion notification")
        await self._verify_toggle_on("Allow reply to reviews notification")

        await self._screenshot('profile_settings_configured')

        # Click Update
        update_btn = await self.page.query_selector('button:has-text("Update")')
        if update_btn and await update_btn.is_visible():
            await update_btn.click()
            await asyncio.sleep(1)

        # Click Confirm
        confirm_btn = await self.page.query_selector('button:has-text("Confirm")')
        if confirm_btn and await confirm_btn.is_visible():
            await confirm_btn.click()
            await asyncio.sleep(2)

        await self._screenshot('profile_settings_saved')

    async def _verify_toggle_on(self, label_text: str) -> bool:
        """Verify a toggle is ON, turn it ON if not"""
        try:
            switch_selectors = [
                f'//*[contains(text(), "{label_text}")]/following::button[contains(@class, "ant-switch")][1]',
                f'//*[contains(text(), "{label_text}")]/ancestor::div[1]//button[contains(@class, "ant-switch")]',
            ]

            for selector in switch_selectors:
                try:
                    switch = await self.page.query_selector(selector)
                    if switch and await switch.is_visible():
                        is_checked = await switch.evaluate('el => el.classList.contains("ant-switch-checked")')
                        if not is_checked:
                            await switch.click()
                            logger.info(f"Turned ON toggle: {label_text}")
                            await asyncio.sleep(0.3)
                        else:
                            logger.debug(f"Toggle already ON: {label_text}")
                        return True
                except:
                    continue
            return False
        except Exception as e:
            logger.warning(f"Could not verify toggle {label_text}: {e}")
            return False

    async def _set_toggle_off(self, label_text: str) -> bool:
        """Set a toggle to OFF"""
        try:
            switch_selectors = [
                f'//*[contains(text(), "{label_text}")]/following::button[contains(@class, "ant-switch")][1]',
                f'//*[contains(text(), "{label_text}")]/ancestor::div[1]//button[contains(@class, "ant-switch")]',
            ]

            for selector in switch_selectors:
                try:
                    switch = await self.page.query_selector(selector)
                    if switch and await switch.is_visible():
                        is_checked = await switch.evaluate('el => el.classList.contains("ant-switch-checked")')
                        if is_checked:
                            await switch.click()
                            logger.info(f"Turned OFF toggle: {label_text}")
                            await asyncio.sleep(0.3)
                        else:
                            logger.debug(f"Toggle already OFF: {label_text}")
                        return True
                except:
                    continue
            return False
        except Exception as e:
            logger.warning(f"Could not set toggle off {label_text}: {e}")
            return False

    async def _set_number_input(self, label_text: str, value: str) -> bool:
        """Set a number input field to a specific value"""
        try:
            input_selectors = [
                f'//*[contains(text(), "{label_text}")]/following::input[1]',
                f'//*[contains(text(), "{label_text}")]/ancestor::div[1]//input',
            ]

            for selector in input_selectors:
                try:
                    input_field = await self.page.query_selector(selector)
                    if input_field and await input_field.is_visible():
                        await input_field.click()
                        await input_field.fill('')
                        await input_field.fill(value)
                        logger.info(f"Set {label_text} to {value}")
                        return True
                except:
                    continue
            return False
        except Exception as e:
            logger.warning(f"Could not set input {label_text}: {e}")
            return False

    async def _set_slider_value(self, label: str, value: float, min_val: float = 1, max_val: float = 5):
        """Set an Ant Design slider to a specific value"""
        try:
            # Find slider near label
            slider_selectors = [
                f'//*[contains(text(), "{label}")]/following::*[contains(@class, "ant-slider")][1]',
                f'//*[contains(text(), "{label}")]/ancestor::div[1]//*[contains(@class, "ant-slider")]',
            ]

            for selector in slider_selectors:
                try:
                    slider = await self.page.query_selector(selector)
                    if slider and await slider.is_visible():
                        box = await slider.bounding_box()
                        if box:
                            percentage = (value - min_val) / (max_val - min_val)
                            click_x = box['x'] + (box['width'] * percentage)
                            click_y = box['y'] + (box['height'] / 2)
                            await self.page.mouse.click(click_x, click_y)
                            logger.debug(f"Set slider {label} to {value}")
                            await asyncio.sleep(0.3)
                        break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Could not set slider {label}: {e}")

    async def _publish_user(self, user_data: Dict[str, Any]) -> bool:
        """Publish user profile

        Returns:
            True if publish was attempted, False on error
        """
        user_name = f"{user_data['firstName']} {user_data['lastName']}"
        logger.info(f"Publishing profile for {user_name}")

        # Close any open drawers
        await self.page.keyboard.press('Escape')
        await asyncio.sleep(1)

        await self._search_user(user_data)

        await self._screenshot('before_publish')

        # Look for Published toggle showing "No" - click to change to "Yes"
        # Try multiple approaches to find and click the toggle
        publish_clicked = False

        # Approach 1: Find ant-switch that is not checked
        toggle = await self.page.query_selector('.ant-switch:not(.ant-switch-checked)')
        if toggle and await toggle.is_visible():
            try:
                await toggle.click(timeout=5000)
                publish_clicked = True
                logger.info("Clicked Published toggle")
            except Exception as e:
                logger.warning(f"Toggle click failed: {e}")

        # Approach 2: Look for "No" text in Published column area
        if not publish_clicked:
            try:
                published_no = await self.page.query_selector('[class*="published"] >> text="No"')
                if published_no and await published_no.is_visible():
                    await published_no.click()
                    publish_clicked = True
                    logger.info("Clicked 'No' under Published")
            except:
                pass

        await asyncio.sleep(1)
        await self._screenshot('after_publish_click')

        # Confirm publish popup if it appears
        if publish_clicked:
            confirm_btn = await self.page.query_selector('button:has-text("Confirm")')
            if confirm_btn and await confirm_btn.is_visible():
                await confirm_btn.click()
                logger.info("Clicked Confirm to publish")
                await asyncio.sleep(2)

        await self._screenshot('published')
        return publish_clicked

    async def _get_widget_code(self, user_data: Dict[str, Any]) -> str:
        """Capture widget code for the user"""
        user_name = f"{user_data['firstName']} {user_data['lastName']}"
        logger.info(f"Capturing widget code for {user_name}")
        widget_code = ""

        try:
            # Navigate to Widgets -> Review Widget
            widgets_el = await self.page.query_selector('text="Widgets"')
            if widgets_el and await widgets_el.is_visible():
                await widgets_el.click()
                await asyncio.sleep(2)

            review_widget = await self.page.query_selector('text="Review Widget"')
            if review_widget and await review_widget.is_visible():
                await review_widget.click()
                await asyncio.sleep(2)

            # Click Basic Review tab
            basic_review = await self.page.query_selector('text="Basic Review"')
            if basic_review and await basic_review.is_visible():
                await basic_review.click()
                await asyncio.sleep(1)

            # Select User filter
            user_label = await self.page.query_selector('label:has-text("User")')
            if user_label:
                await user_label.click()
                await asyncio.sleep(1)

            # Open dropdown and select user
            dropdown = await self.page.query_selector('.ant-select-selector')
            if dropdown and await dropdown.is_visible():
                await dropdown.click()
                await asyncio.sleep(1)
                await self.page.keyboard.type(user_name)
                await asyncio.sleep(2)

                option = await self.page.query_selector(f'[class*="ant-select-item"]:has-text("{user_name}")')
                if option:
                    await option.click()
                    await asyncio.sleep(2)

            # Click Get Code
            get_code_btn = await self.page.query_selector('button:has-text("Get Code")')
            if get_code_btn and await get_code_btn.is_visible():
                await get_code_btn.click()
                await asyncio.sleep(2)

            # Click Copy Code button
            copy_btn = await self.page.query_selector('button:has-text("Copy Code")')
            if copy_btn and await copy_btn.is_visible():
                await copy_btn.click()
                await asyncio.sleep(1)

                # Read from clipboard
                widget_code = await self.page.evaluate('''async () => {
                    try {
                        return await navigator.clipboard.readText();
                    } catch (e) {
                        return null;
                    }
                }''')

            # Close modal
            close_btn = await self.page.query_selector('button:has-text("Close")')
            if close_btn and await close_btn.is_visible():
                await close_btn.click()
                await asyncio.sleep(1)

            if widget_code:
                logger.info(f"Captured widget code ({len(widget_code)} chars)")

        except Exception as e:
            logger.error(f"Error capturing widget code: {e}")

        return widget_code or ""

    async def _get_profile_url(self, user_data: Dict[str, Any]) -> str:
        """Capture the user's public profile URL

        Per Experience User Guide (Page 9-10):
        1. Navigate to Hierarchy → Users
        2. Search for user
        3. Click hamburger menu (three dots) in Actions column
        4. Select "View Profile"
        5. Copy URL from "Visit user profile" field (format: https://pro.experience.com/reviews/...)
        """
        user_name = f"{user_data['firstName']} {user_data['lastName']}"
        logger.info(f"Capturing profile URL for {user_name}")
        profile_url = ""

        try:
            # Close any open drawers
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)

            await self._navigate_to_users()
            await self._search_user(user_data)

            await self._screenshot('profile_url_search')

            # Click on hamburger/three-dots menu in Actions column
            menu_clicked = False
            menu_selectors = [
                'button:has(svg path[d*="M12"])',  # Three dots icon
                '[class*="actions"] button:last-child',  # Actions column button
                'td:last-child button',  # Last column button
                'button[aria-label*="menu" i]',
                'button[aria-label*="action" i]',
            ]

            for selector in menu_selectors:
                try:
                    menu_btns = await self.page.query_selector_all(selector)
                    for menu_btn in menu_btns:
                        if menu_btn and await menu_btn.is_visible():
                            await menu_btn.click()
                            menu_clicked = True
                            logger.info(f"Clicked three-dots menu: {selector}")
                            await asyncio.sleep(1)
                            break
                    if menu_clicked:
                        break
                except:
                    continue

            if not menu_clicked:
                logger.warning("Could not click three-dots menu")

            await self._screenshot('profile_menu_open')

            # Click "View Profile" option from the dropdown menu
            view_profile_clicked = False
            view_profile_selectors = [
                'text="View Profile"',
                '[role="menuitem"]:has-text("View Profile")',
                'li:has-text("View Profile")',
                'a:has-text("View Profile")',
            ]

            for selector in view_profile_selectors:
                try:
                    view_profile_btn = await self.page.query_selector(selector)
                    if view_profile_btn and await view_profile_btn.is_visible():
                        await view_profile_btn.click()
                        view_profile_clicked = True
                        logger.info(f"Clicked View Profile: {selector}")
                        await asyncio.sleep(3)  # Wait for profile page to load
                        break
                except:
                    continue

            if not view_profile_clicked:
                logger.warning("Could not click 'View Profile' option")

            await self._screenshot('profile_view')

            # Extract profile URL from "Visit user profile" link
            # Per PDF: The link is at the top showing "Visit user profile: https://pro.experience.com/reviews/..."
            profile_link_selectors = [
                'a[href*="pro.experience.com/reviews"]',
                'a[href*="experience.com/reviews"]',
                '//*[contains(text(), "Visit user profile")]/following::a[1]',
                '//*[contains(text(), "Visit user profile")]//a',
                '#profile-link',
                '[data-test-profile-link="true"]',
            ]

            for selector in profile_link_selectors:
                try:
                    link = await self.page.query_selector(selector)
                    if link:
                        href = await link.get_attribute('href')
                        if href and 'experience.com/reviews' in href:
                            profile_url = href
                            logger.info(f"Found profile URL: {profile_url}")
                            break
                        # Also try getting text content if it's a displayed URL
                        text = await link.inner_text()
                        if text and 'experience.com/reviews' in text:
                            profile_url = text.strip()
                            logger.info(f"Found profile URL from text: {profile_url}")
                            break
                except:
                    continue

            # Fallback: Search page content for URL pattern
            if not profile_url:
                page_content = await self.page.content()
                patterns = [
                    r'https://pro\.experience\.com/reviews/[a-zA-Z0-9\-_]+(?:-\d+)?',
                    r'https://www\.experience\.com/reviews/[a-zA-Z0-9\-_]+(?:-\d+)?',
                    r'https://experience\.com/reviews/[a-zA-Z0-9\-_]+(?:-\d+)?',
                ]
                for pattern in patterns:
                    match = re.search(pattern, page_content)
                    if match:
                        profile_url = match.group(0)
                        logger.info(f"Found profile URL from page content: {profile_url}")
                        break

            # Fallback: Evaluate JavaScript to find the URL
            if not profile_url:
                profile_url = await self.page.evaluate(r'''() => {
                    // Look for "Visit user profile" text and get the URL
                    const visitText = document.body.innerText;
                    const match = visitText.match(/https?:\/\/(?:pro\.)?experience\.com\/reviews\/[a-zA-Z0-9\-_]+(?:-\d+)?/);
                    if (match) return match[0];

                    // Look for profile link elements
                    const links = document.querySelectorAll('a[href*="experience.com/reviews"]');
                    if (links.length > 0) return links[0].href;

                    return null;
                }''')
                if profile_url:
                    logger.info(f"Found profile URL via JavaScript: {profile_url}")

            if not profile_url:
                logger.warning("Could not extract profile URL")

        except Exception as e:
            logger.error(f"Error capturing profile URL: {e}")

        return profile_url or ""

    async def _fill_profile_info(self, user_data: Dict[str, Any]):
        """Fill Profile Info fields including Business Info, Contact Info, Licenses, and Headshot"""
        user_name = f"{user_data['firstName']} {user_data['lastName']}"
        logger.info(f"Filling profile info for {user_name}")

        try:
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)

            await self._navigate_to_users()
            await self._search_user(user_data)

            # Open Edit menu via three dots/hamburger menu
            menu_btn = await self.page.query_selector('button:has(svg path[d*="M12"])')
            if not menu_btn:
                # Try alternate selector for three dots menu
                menu_btn = await self.page.query_selector('[class*="actions"] button')
            if menu_btn and await menu_btn.is_visible():
                await menu_btn.click()
                await asyncio.sleep(1)

            edit_btn = await self.page.query_selector('text="Edit"')
            if edit_btn and await edit_btn.is_visible():
                await edit_btn.click()
                await asyncio.sleep(2)

            # Click Profile Info tab
            profile_info_tab = await self.page.query_selector('text="Profile Info"')
            if profile_info_tab and await profile_info_tab.is_visible():
                await profile_info_tab.click()
                await asyncio.sleep(1)

            # ============================================================
            # BUSINESS INFORMATION SECTION
            # ============================================================
            business_info = await self.page.query_selector('text="Business Information"')
            if business_info:
                await business_info.click()
                await asyncio.sleep(0.5)

            # Fill Title (replace default with user's title)
            if user_data.get('title'):
                title_input = await self.page.query_selector('input[placeholder*="Title" i]')
                if not title_input:
                    title_input = await self.page.query_selector('//*[contains(text(), "Title")]/following::input[1]')
                if title_input and await title_input.is_visible():
                    await title_input.fill('')
                    await title_input.fill(user_data['title'])
                    logger.info(f"Filled Title: {user_data['title']}")

            # ============================================================
            # CONTACT INFORMATION SECTION
            # ============================================================
            contact_info = await self.page.query_selector('text="Contact Information"')
            if contact_info:
                await contact_info.click()
                await asyncio.sleep(0.5)

            # Fill Phone Number
            if user_data.get('phone'):
                phone_input = await self.page.query_selector('input[placeholder*="Phone" i]')
                if not phone_input:
                    phone_input = await self.page.query_selector('//*[contains(text(), "Phone Number")]/following::input[1]')
                if phone_input and await phone_input.is_visible():
                    await phone_input.fill('')
                    await phone_input.fill(user_data['phone'])
                    logger.info(f"Filled Phone: {user_data['phone']}")

            # Fill Mobile Number
            if user_data.get('mobile'):
                mobile_input = await self.page.query_selector('input[placeholder*="Mobile" i]')
                if not mobile_input:
                    mobile_input = await self.page.query_selector('//*[contains(text(), "Mobile")]/following::input[1]')
                if mobile_input and await mobile_input.is_visible():
                    await mobile_input.fill('')
                    await mobile_input.fill(user_data['mobile'])
                    logger.info(f"Filled Mobile: {user_data['mobile']}")

            # Fill Website URL
            if user_data.get('website_url'):
                website_input = await self.page.query_selector('input[placeholder*="Website" i]')
                if not website_input:
                    website_input = await self.page.query_selector('//*[contains(text(), "Website URL")]/following::input[1]')
                if website_input and await website_input.is_visible():
                    await website_input.fill('')
                    await website_input.fill(user_data['website_url'])
                    logger.info(f"Filled Website URL: {user_data['website_url']}")

            # ============================================================
            # LICENSES SECTION - NMLS Number
            # ============================================================
            if user_data.get('nmls_number'):
                licenses_section = await self.page.query_selector('text="Licenses"')
                if licenses_section:
                    await licenses_section.click()
                    await asyncio.sleep(0.5)

                # Look for License Name input field
                license_input = await self.page.query_selector('input[placeholder*="License" i]')
                if not license_input:
                    license_input = await self.page.query_selector('//*[contains(text(), "License Name")]/following::input[1]')
                if license_input and await license_input.is_visible():
                    nmls_value = user_data['nmls_number']
                    # Format as "NMLS# 123456" if not already formatted
                    if not nmls_value.upper().startswith('NMLS'):
                        nmls_value = f"NMLS# {nmls_value}"
                    await license_input.fill('')
                    await license_input.fill(nmls_value)
                    logger.info(f"Filled NMLS License: {nmls_value}")

                    # Click the plus button to add the license
                    plus_btn = await self.page.query_selector('//*[contains(text(), "License")]/ancestor::div[1]//button[contains(@class, "plus")] | //*[contains(text(), "License")]/following::button[1]')
                    if plus_btn and await plus_btn.is_visible():
                        await plus_btn.click()
                        logger.info("Clicked plus to add license")
                        await asyncio.sleep(0.5)

            # ============================================================
            # IMAGES SECTION - Headshot Upload
            # ============================================================
            if user_data.get('headshot_url'):
                await self._upload_headshot(user_data['headshot_url'])

            await self._screenshot('profile_info_filled')

            # Click Update/Save
            update_btn = await self.page.query_selector('button:has-text("Update")')
            if not update_btn:
                update_btn = await self.page.query_selector('button:has-text("Save")')
            if update_btn and await update_btn.is_visible():
                await update_btn.click()
                await asyncio.sleep(1)

            confirm_btn = await self.page.query_selector('button:has-text("Confirm")')
            if confirm_btn and await confirm_btn.is_visible():
                await confirm_btn.click()
                await asyncio.sleep(2)

            await self._screenshot('profile_info_saved')

        except Exception as e:
            logger.error(f"Error filling profile info: {e}")

    async def _upload_headshot(self, headshot_url: str):
        """Upload user's headshot photo from URL

        Args:
            headshot_url: URL to the headshot image (from Entra extensionAttribute3)
        """
        logger.info(f"Uploading headshot from: {headshot_url}")

        try:
            # Expand Images section
            images_section = await self.page.query_selector('text="Images"')
            if images_section:
                await images_section.click()
                await asyncio.sleep(0.5)

            # Look for Upload button or file input
            upload_btn = await self.page.query_selector('text="Upload"')
            if not upload_btn:
                upload_btn = await self.page.query_selector('[class*="upload"]')

            if upload_btn and await upload_btn.is_visible():
                # Download the image first to a temp file
                import tempfile
                import urllib.request
                import os

                # Create temp file for the image
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                    temp_path = tmp_file.name

                try:
                    # Download image from URL
                    urllib.request.urlretrieve(headshot_url, temp_path)
                    logger.info(f"Downloaded headshot to: {temp_path}")

                    # Find file input element
                    file_input = await self.page.query_selector('input[type="file"]')
                    if file_input:
                        await file_input.set_input_files(temp_path)
                        logger.info("Uploaded headshot file")
                        await asyncio.sleep(2)  # Wait for upload to process
                    else:
                        # Click upload button which may trigger file chooser
                        async with self.page.expect_file_chooser() as fc_info:
                            await upload_btn.click()
                        file_chooser = await fc_info.value
                        await file_chooser.set_files(temp_path)
                        logger.info("Uploaded headshot via file chooser")
                        await asyncio.sleep(2)

                except Exception as download_error:
                    logger.warning(f"Could not download/upload headshot: {download_error}")

                finally:
                    # Clean up temp file
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
            else:
                logger.warning("Could not find upload button for headshot")

        except Exception as e:
            logger.warning(f"Error uploading headshot: {e}")

    async def _cleanup(self):
        """Clean up browser resources"""
        logger.info("Cleaning up browser...")
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


async def provision_user(user: EntraUser, config_path: str) -> Dict[str, Any]:
    """
    Main entry point for Experience.com user provisioning

    Args:
        user: EntraUser object from Entra ID
        config_path: Path to vendor config JSON

    Returns:
        Dict with provisioning result including widget_code and profile_url
    """
    from services.keyvault_service import KeyVaultService

    keyvault = KeyVaultService()
    automation = ExperienceAutomation(config_path, keyvault)
    result = await automation.provision_user(user, headless=False)

    return result
