"""
The Work Number (Equifax) User Provisioning Automation

This module automates the creation of user accounts in The Work Number
Verification Insights Portal using Playwright for web automation.
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
logger = logging.getLogger('automation.vendors.theworknumber')


class TheWorkNumberAutomation:
    """Handles The Work Number user provisioning automation"""

    def __init__(self, config_path: str, keyvault: KeyVaultService):
        """
        Initialize The Work Number automation

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
        Create a The Work Number account for the given user

        Args:
            user: EntraUser object with user details
            headless: Whether to run browser in headless mode

        Returns:
            Dict with success status and messages
        """
        self.current_user = user
        logger.info(f"Starting The Work Number automation for {user.display_name}")

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

            # Navigate to User Management
            await self._navigate_to_user_management()
            result['messages'].append("Navigated to User Management")

            # Click Add User
            await self._click_add_user()
            result['messages'].append("Opened Add User form")

            # Fill user details
            await self._fill_user_details(user_data)
            result['messages'].append("Filled user details")

            # Click Continue
            await self._click_continue()
            result['messages'].append("Clicked Continue")

            # Select Organization
            await self._select_organization()
            result['messages'].append(f"Selected Organization: {self.config['organization']['name']}")

            # Select Location
            await self._select_location()
            result['messages'].append(f"Selected Location: {self.config['location']['name']}")

            # Create User
            await self._create_user()
            result['messages'].append("User created successfully")

            result['success'] = True
            result['messages'].append("User will receive activation email from Equifax")
            logger.info(f"Successfully created The Work Number account for {user.display_name}")

        except Exception as e:
            error_msg = f"Error during The Work Number automation: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            result['success'] = False

            # Take error screenshot
            try:
                if self.page:
                    await self.page.screenshot(path=f'theworknumber_error_{user.display_name.replace(" ", "_")}.png')
            except:
                pass

        finally:
            await self._cleanup()

        logger.info(f"The Work Number result: {result}")
        return result

    def _prepare_user_data(self, user: EntraUser) -> Dict[str, Any]:
        """
        Prepare user data for The Work Number form

        Args:
            user: EntraUser object

        Returns:
            Dict with formatted user data
        """
        # Get user details
        first_name = user.given_name or user.display_name.split()[0]
        last_name = user.surname or user.display_name.split()[-1]

        # Username format: FirstName.LastName
        username = f"{first_name}.{last_name}"

        # Email
        email = user.mail or user.user_principal_name

        return {
            'firstName': first_name,
            'lastName': last_name,
            'username': username,
            'email': email
        }

    async def _start_browser(self, headless: bool = False):
        """Start Playwright browser"""
        logger.info("Starting browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.page = await self.browser.new_page()
        logger.info("Browser started")

    async def _login(self):
        """Login to The Work Number portal via multi-step flow"""
        login_url = self.keyvault.get_vendor_credential('theworknumber', 'login-url')
        admin_username = self.keyvault.get_vendor_credential('theworknumber', 'admin-username')
        admin_password = self.keyvault.get_vendor_credential('theworknumber', 'admin-password')

        logger.info(f"Navigating to {login_url}")
        await self.page.goto(login_url)
        await self.page.wait_for_load_state('networkidle')

        # Take screenshot of home page
        await self.page.screenshot(path='theworknumber_home_page.png')

        # Step 1: Click "Log In" dropdown button
        logger.info("Clicking Log In dropdown...")
        await self.page.wait_for_selector('#loginDropdown', timeout=10000)
        await self.page.click('#loginDropdown')
        await asyncio.sleep(1)

        # Take screenshot of dropdown
        await self.page.screenshot(path='theworknumber_login_dropdown.png')

        # Step 2: Click "Verify for Your Organization" from dropdown
        logger.info("Clicking 'Verify for Your Organization' from dropdown...")
        await self.page.click('div.font-weight-bold:has-text("Verify for Your Organization")')
        await self.page.wait_for_load_state('networkidle')
        await asyncio.sleep(1)

        # Take screenshot of login options page
        await self.page.screenshot(path='theworknumber_login_options.png')

        # Step 3: Click "Verify for Your Organization" link on the login page
        # This opens a NEW TAB, so we need to handle the popup
        logger.info("Clicking 'Verify for Your Organization' link (opens new tab)...")

        # Get context to track pages
        context = self.page.context

        # Click the link
        await self.page.locator('text="Verify for Your Organization"').first.click()

        # Wait for new tab to appear
        await asyncio.sleep(3)

        # Get all pages and switch to the newest one
        all_pages = context.pages
        logger.info(f"Found {len(all_pages)} pages/tabs")

        if len(all_pages) > 1:
            # Switch to the last (newest) page
            self.page = all_pages[-1]
            await self.page.bring_to_front()
            logger.info("Switched to new tab")
        else:
            logger.warning("No new tab detected")

        # Wait for the loading spinner to disappear and page to fully load
        logger.info("Waiting for page to fully load...")
        await self.page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)

        # Take screenshot of username page
        await self.page.screenshot(path='theworknumber_username_page.png')

        # Step 4: Enter username - the form is in a modal dialog
        logger.info("Entering username...")

        # Check if there's an iframe we need to switch to
        frames = self.page.frames
        logger.info(f"Found {len(frames)} frames")

        # Try to find the username input in main page or frames
        username_filled = False
        for frame in frames:
            try:
                # Try various selectors for the username field
                for selector in ['input[type="text"]', 'input.form-control', 'input[name*="user" i]', 'input']:
                    try:
                        inputs = await frame.query_selector_all(selector)
                        for inp in inputs:
                            if await inp.is_visible():
                                await inp.fill(admin_username)
                                username_filled = True
                                logger.info(f"Filled username in frame with selector: {selector}")
                                break
                    except:
                        continue
                    if username_filled:
                        break
            except:
                continue
            if username_filled:
                break

        if not username_filled:
            # Fallback: try using locator on main page
            await self.page.locator('input').first.fill(admin_username)
            logger.info("Filled username using locator fallback")

        logger.info(f"Filled username: {admin_username}")

        # Step 5: Click Continue - search across frames
        logger.info("Clicking Continue...")
        continue_clicked = False
        for frame in self.page.frames:
            try:
                for selector in ['button:has-text("Continue")', 'input[value*="Continue"]', 'a:has-text("Continue")', 'text="Continue >"']:
                    try:
                        element = await frame.query_selector(selector)
                        if element and await element.is_visible():
                            await element.click()
                            continue_clicked = True
                            logger.info(f"Clicked Continue in frame with selector: {selector}")
                            break
                    except:
                        continue
                if continue_clicked:
                    break
            except:
                continue

        if not continue_clicked:
            # Fallback: try locator
            await self.page.locator('text="Continue"').first.click()
            logger.info("Clicked Continue using locator fallback")

        try:
            await self.page.wait_for_load_state('networkidle', timeout=10000)
        except:
            pass
        await asyncio.sleep(2)

        # Wait for password field to appear with retries
        logger.info("Waiting for password field...")
        password_filled = False
        max_retries = 10
        for retry in range(max_retries):
            # Take screenshot of password page
            await self.page.screenshot(path='theworknumber_password_page.png')

            # Step 6: Enter password - search across frames
            for frame in self.page.frames:
                try:
                    password_input = await frame.query_selector('input[type="password"]')
                    if password_input and await password_input.is_visible():
                        await password_input.fill(admin_password)
                        password_filled = True
                        logger.info("Filled password in frame")
                        break
                except:
                    continue

            if password_filled:
                break

            # Try locator on main page
            try:
                pwd_locator = self.page.locator('input[type="password"]')
                if await pwd_locator.count() > 0:
                    await pwd_locator.first.fill(admin_password, timeout=2000)
                    password_filled = True
                    logger.info("Filled password using locator")
                    break
            except:
                pass

            logger.info(f"Password field not found, retry {retry + 1}/{max_retries}")
            await asyncio.sleep(1)

        if not password_filled:
            raise Exception("Could not find password field")

        logger.info("Filled password")

        # Step 7: Click Log in - search across frames
        logger.info("Clicking Log in...")
        login_clicked = False
        for frame in self.page.frames:
            try:
                for selector in ['button:has-text("Log in")', 'input[value*="Log in"]', 'button:has-text("Login")', 'text="Log in"']:
                    try:
                        element = await frame.query_selector(selector)
                        if element and await element.is_visible():
                            await element.click()
                            login_clicked = True
                            logger.info(f"Clicked Log in in frame with selector: {selector}")
                            break
                    except:
                        continue
                if login_clicked:
                    break
            except:
                continue

        if not login_clicked:
            try:
                await self.page.locator('text="Log in"').first.click(timeout=5000)
                logger.info("Clicked Log in using locator fallback")
            except:
                raise Exception("Could not find Log in button")

        logger.info("Waiting for page to load after login...")
        # Take screenshot before waiting
        await self.page.screenshot(path='theworknumber_after_login_click.png')

        try:
            await self.page.wait_for_load_state('networkidle', timeout=15000)
        except:
            logger.warning("networkidle timeout, continuing anyway")

        await asyncio.sleep(2)

        # Take screenshot after login
        await self.page.screenshot(path='theworknumber_after_login.png')

        # Check if MFA/identity validation is required
        await self._handle_mfa()

        logger.info("Login completed")

    async def _handle_mfa(self):
        """Handle MFA/identity validation if required"""
        logger.info("Checking for MFA/identity validation...")
        print("Checking for MFA/identity validation...")

        # Check if the identity validation modal is present
        try:
            mfa_detected = False

            # First check all frames for content
            all_frames = self.page.frames
            print(f"Found {len(all_frames)} frames")

            for i, frame in enumerate(all_frames):
                try:
                    frame_content = await frame.content()
                    print(f"Frame {i} content length: {len(frame_content)}")

                    # Check for MFA indicators
                    mfa_keywords = ["validate your identity", "E-mail passcode", "one-time", "Additional information"]
                    for keyword in mfa_keywords:
                        if keyword.lower() in frame_content.lower():
                            mfa_detected = True
                            print(f"MFA detected in frame {i} via keyword: {keyword}")
                            logger.info(f"MFA detected in frame {i} via keyword: {keyword}")
                            break
                    if mfa_detected:
                        break
                except Exception as e:
                    print(f"Error checking frame {i}: {e}")
                    continue

            if mfa_detected:
                logger.info("MFA identity validation detected")
                print("MFA identity validation detected - waiting for user to complete")

                # Take screenshot
                await self.page.screenshot(path='theworknumber_mfa_page.png')

                # Click on the email option (first button with email)
                # The button contains the email address like "c****e@highlandsmortgage.com"
                email_clicked = False
                for frame in self.page.frames:
                    try:
                        # Look for button with @ symbol (email)
                        email_btn = await frame.query_selector('button:has-text("@")')
                        if email_btn and await email_btn.is_visible():
                            await email_btn.click()
                            email_clicked = True
                            print("Clicked email option for MFA")
                            logger.info("Clicked email option for MFA")
                            break
                    except:
                        continue

                if not email_clicked:
                    print("Could not auto-click email button - waiting for manual action")
                    logger.info("Could not auto-click email button - user should click manually")

                await asyncio.sleep(2)

                # Take screenshot after clicking email
                await self.page.screenshot(path='theworknumber_mfa_code_sent.png')

                # Wait for user to manually enter the code
                print("=" * 60)
                print("MFA REQUIRED: Please complete the following steps:")
                print("1. Click on your email address to receive the code")
                print("2. Check your email for the one-time passcode")
                print("3. Enter the code in the browser")
                print("4. Click Submit/Continue to complete login")
                print("=" * 60)
                logger.info("Waiting for manual MFA completion (passcode entry)...")

                # Poll for MFA completion - look for dashboard elements
                max_wait_time = 300  # 5 minutes
                check_interval = 5
                elapsed_time = 0

                while elapsed_time < max_wait_time:
                    await asyncio.sleep(check_interval)
                    elapsed_time += check_interval

                    # Take periodic screenshots
                    if elapsed_time % 15 == 0:
                        await self.page.screenshot(path=f'theworknumber_mfa_wait_{elapsed_time}s.png')

                    # Check if we're past MFA - look for dashboard elements
                    page_content = await self.page.content()
                    dashboard_keywords = ["New Order", "Order History", "User Management", "Verifiers", "Administration"]
                    for keyword in dashboard_keywords:
                        if keyword in page_content:
                            print(f"MFA completed - found dashboard element: {keyword}")
                            logger.info(f"MFA completed - found: {keyword}")
                            await self.page.screenshot(path='theworknumber_mfa_complete.png')
                            return

                    # Log progress
                    if elapsed_time % 30 == 0:
                        print(f"Still waiting for MFA completion... ({elapsed_time}s elapsed)")
                        logger.info(f"Still waiting for MFA completion... ({elapsed_time}s elapsed)")

                raise Exception("MFA timeout - user did not complete MFA within 5 minutes")
            else:
                print("No MFA required - continuing")
                logger.info("No MFA required")
        except Exception as e:
            print(f"MFA handling exception: {e}")
            if "MFA timeout" in str(e):
                raise
            logger.info(f"MFA exception: {e}, continuing...")

    async def _navigate_to_user_management(self):
        """Navigate to Administration -> User Management"""
        logger.info("Navigating to User Management...")
        print("Navigating to User Management...")

        # Take screenshot of dashboard
        await self.page.screenshot(path='theworknumber_dashboard.png')

        # Wait for page to be fully loaded
        await asyncio.sleep(2)

        # Click Administration link in the header
        # The link has aria-label "Administration" and contains "login as an admin"
        admin_clicked = False

        admin_selectors = [
            'a:has-text("login as an admin")',
            '[aria-label="Administration"] a',
            'a[href*="javascript"]:has(img[alt*="admin"])',
            'img[alt*="admin"]',
            'text="Administration"',
        ]

        for selector in admin_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    admin_clicked = True
                    print(f"Clicked Administration with selector: {selector}")
                    logger.info(f"Clicked Administration with selector: {selector}")
                    break
            except:
                continue

        if not admin_clicked:
            await self.page.screenshot(path='theworknumber_admin_not_found.png')
            raise Exception("Could not find Administration link")

        await asyncio.sleep(1)

        # Take screenshot after clicking Administration
        await self.page.screenshot(path='theworknumber_admin_menu.png')

        # Click User Management button in the dropdown
        user_mgmt_clicked = False
        for selector in ['button:has-text("User Management")', 'text="User Management"', '[role="button"]:has-text("User Management")']:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    user_mgmt_clicked = True
                    print(f"Clicked User Management with selector: {selector}")
                    logger.info(f"Clicked User Management with selector: {selector}")
                    break
            except:
                continue

        if not user_mgmt_clicked:
            await self.page.screenshot(path='theworknumber_usermgmt_not_found.png')
            raise Exception("Could not find User Management button")

        try:
            await self.page.wait_for_load_state('networkidle', timeout=10000)
        except:
            pass
        await asyncio.sleep(1)

        # Take screenshot
        await self.page.screenshot(path='theworknumber_user_management.png')
        logger.info("Navigated to User Management")

    async def _click_add_user(self):
        """Click Add User button"""
        logger.info("Clicking Add User...")
        print("Clicking Add User...")

        await asyncio.sleep(1)

        # Take screenshot before clicking Add User
        await self.page.screenshot(path='theworknumber_before_add_user.png')

        # Wait for Add User button to be visible
        try:
            await self.page.wait_for_selector('button:has-text("Add User")', timeout=10000)
        except:
            pass

        # Click the Add User button
        add_user_clicked = False
        for selector in ['button:has-text(" Add User")', 'button:has-text("Add User")', 'text="Add User"']:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    add_user_clicked = True
                    print(f"Clicked Add User with selector: {selector}")
                    logger.info(f"Clicked Add User with selector: {selector}")
                    break
            except:
                continue

        if not add_user_clicked:
            await self.page.screenshot(path='theworknumber_add_user_not_found.png')
            raise Exception("Could not find Add User button")

        try:
            await self.page.wait_for_load_state('networkidle', timeout=10000)
        except:
            pass
        await asyncio.sleep(2)

        # Take screenshot
        await self.page.screenshot(path='theworknumber_add_user_form.png')
        logger.info("Add User form opened")

    async def _fill_user_details(self, user_data: Dict[str, Any]):
        """Fill the user details form"""
        logger.info("Filling user details...")

        # Wait for form fields
        await asyncio.sleep(1)

        # The form has labeled textboxes: "First Name:", "Last Name:", "Username:", "Email:"
        # Fill First Name
        try:
            await self.page.get_by_label('First Name:').fill(user_data['firstName'])
            logger.info(f"Filled First Name: {user_data['firstName']}")
        except Exception as e:
            logger.error(f"Could not fill First Name: {e}")
            raise Exception("Could not find First Name field")

        # Fill Last Name
        try:
            await self.page.get_by_label('Last Name:').fill(user_data['lastName'])
            logger.info(f"Filled Last Name: {user_data['lastName']}")
        except Exception as e:
            logger.error(f"Could not fill Last Name: {e}")
            raise Exception("Could not find Last Name field")

        # Fill Username
        try:
            await self.page.get_by_label('Username:').fill(user_data['username'])
            logger.info(f"Filled Username: {user_data['username']}")
        except Exception as e:
            logger.error(f"Could not fill Username: {e}")
            raise Exception("Could not find Username field")

        # Fill Email
        try:
            await self.page.get_by_label('Email:').fill(user_data['email'])
            logger.info(f"Filled Email: {user_data['email']}")
        except Exception as e:
            logger.error(f"Could not fill Email: {e}")
            raise Exception("Could not find Email field")

        # Take screenshot of filled form
        await self.page.screenshot(path='theworknumber_form_filled.png')
        logger.info("User details filled")

    async def _click_continue(self):
        """Click Continue button to go to Organization & Location page"""
        logger.info("Clicking Continue...")

        try:
            await self.page.get_by_role('button', name='Continue').click()
            logger.info("Clicked Continue button")
        except Exception as e:
            logger.error(f"Could not click Continue: {e}")
            raise Exception("Could not find Continue button")

        try:
            await self.page.wait_for_load_state('networkidle', timeout=10000)
        except:
            pass
        await asyncio.sleep(1)

        # Take screenshot
        await self.page.screenshot(path='theworknumber_organization_page.png')
        logger.info("Clicked Continue, now on Organization & Location page")

    async def _select_organization(self):
        """Select the organization (Highlands Residential Mortgages - 82989)"""
        logger.info("Selecting organization...")

        org_id = self.config['organization']['id']
        org_name = self.config['organization']['name']

        # Wait for organization table
        await asyncio.sleep(1)

        # Select the organization by clicking the radio button
        # The radio button has aria-label like "Select Row for Id 82989"
        try:
            await self.page.get_by_role('radio', name=f'Select Row for Id {org_id}').click()
            logger.info(f"Selected organization radio button for ID {org_id}")
        except Exception as e:
            # Fallback: try clicking on the row containing the org ID
            try:
                row = self.page.locator(f'tr:has-text("{org_id}")')
                radio = row.locator('input[type="radio"]')
                await radio.click()
                logger.info(f"Selected organization via row locator")
            except:
                logger.error(f"Could not select organization: {e}")
                raise Exception(f"Could not find organization: {org_name} (ID: {org_id})")

        await asyncio.sleep(0.5)

        # Click Save Selection button
        try:
            await self.page.get_by_role('button', name='Save Selection').click()
            logger.info("Clicked Save Selection for organization")
        except Exception as e:
            logger.warning(f"Could not click Save Selection: {e}")

        await asyncio.sleep(1)

        # Take screenshot
        await self.page.screenshot(path='theworknumber_org_selected.png')
        logger.info(f"Selected organization: {org_name}")

    async def _select_location(self):
        """Select the location (Highlands Residential Mortgage - 339552)"""
        logger.info("Selecting location...")

        loc_id = self.config['location']['id']
        loc_name = self.config['location']['name']

        # Wait for location table to appear after org selection
        await asyncio.sleep(1)

        # Select the location by clicking the radio button
        # The radio button has aria-label like "Select Row for Id 339552"
        try:
            await self.page.get_by_role('radio', name=f'Select Row for Id {loc_id}').click()
            logger.info(f"Selected location radio button for ID {loc_id}")
        except Exception as e:
            # Fallback: try clicking on the row containing the loc ID
            try:
                row = self.page.locator(f'tr:has-text("{loc_id}")')
                radio = row.locator('input[type="radio"]')
                await radio.click()
                logger.info(f"Selected location via row locator")
            except:
                logger.error(f"Could not select location: {e}")
                raise Exception(f"Could not find location: {loc_name} (ID: {loc_id})")

        await asyncio.sleep(1)

        # Take screenshot
        await self.page.screenshot(path='theworknumber_location_selected.png')
        logger.info(f"Selected location: {loc_name}")

    async def _create_user(self):
        """Click Create User button to finalize"""
        logger.info("Creating user...")

        try:
            await self.page.get_by_role('button', name='Create User').click()
            logger.info("Clicked Create User button")
        except Exception as e:
            logger.error(f"Could not click Create User: {e}")
            raise Exception("Could not find Create User button")

        try:
            await self.page.wait_for_load_state('networkidle', timeout=15000)
        except:
            pass
        await asyncio.sleep(2)

        # Take screenshot of confirmation
        await self.page.screenshot(path='theworknumber_user_created.png')
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
    Main entry point for The Work Number user provisioning

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
    automation = TheWorkNumberAutomation(config_path, keyvault)

    # Run automation
    result = await automation.create_account(user, headless=False)

    return result
