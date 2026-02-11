"""
Partners Credit User Provisioning Automation

This module automates the creation of user account requests in Partners Credit
using Playwright for web automation.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Awaitable

from playwright.async_api import async_playwright, Page, Browser, Playwright

from models.user import EntraUser
from services.keyvault_service import KeyVaultService
from services.ai_matcher import AIMatcherService

# Configure logging
logger = logging.getLogger('automation.vendors.partnerscredit')


class PartnersCreditAutomation:
    """Handles Partners Credit user provisioning automation"""

    def __init__(self, config_path: str, keyvault: KeyVaultService, api_key: Optional[str] = None):
        """
        Initialize Partners Credit automation

        Args:
            config_path: Path to vendor config.json
            keyvault: KeyVaultService instance for credential retrieval
            api_key: Anthropic API key for AI matching (optional)
        """
        self.config_path = Path(config_path)
        self.keyvault = keyvault
        self.config = self._load_config()
        self.title_mappings = self._load_title_mappings()
        self.ai_matcher = AIMatcherService(api_key=api_key)
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

    def _load_title_mappings(self) -> List[Dict[str, Any]]:
        """Load title to Report Access Level mappings"""
        try:
            mapping_path = self.config_path.parent / 'title_mapping.json'
            with open(mapping_path, 'r') as f:
                mapping_data = json.load(f)
            logger.info(f"Loaded {len(mapping_data['title_mappings'])} title mappings from {mapping_path}")
            return mapping_data['title_mappings']
        except Exception as e:
            logger.error(f"Failed to load title mappings: {e}")
            # Return default if file doesn't exist
            return [
                {'title': 'Default', 'report_access_level': 'User', 'keywords': []}
            ]

    async def create_account(
        self,
        user: EntraUser,
        headless: bool = False,
        on_email_conflict: Optional[Callable[[str, str], Awaitable[Optional[str]]]] = None
    ) -> Dict[str, Any]:
        """
        Create a Partners Credit account request for the given user

        Args:
            user: EntraUser object with user details
            headless: Whether to run browser in headless mode
            on_email_conflict: Async callback when email is already in use.
                Receives (display_name, attempted_email).
                Should return new email to try, or None to skip this vendor.

        Returns:
            Dict with success status and messages
        """
        self.current_user = user
        self.on_email_conflict = on_email_conflict
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

            # Handle MFA
            await self._handle_mfa()
            result['messages'].append("✓ MFA completed")

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

            # Submit request and check for duplicates
            submit_result = await self._submit_request()

            if submit_result.get('duplicate_email', False):
                if on_email_conflict:
                    result['messages'].append(f"ℹ Email '{user_data['email']}' appears to already be in use")
                    new_email = await on_email_conflict(user.display_name, user_data['email'])

                    if new_email is None:
                        # User chose to skip
                        result['success'] = False
                        result['warnings'].append(f"⚠ Email '{user_data['email']}' already exists - User chose to skip")
                        logger.info(f"User skipped Partners Credit due to email conflict: {user.display_name}")
                        return result
                    else:
                        # User provided alternative email - update and retry
                        user_data['email'] = new_email
                        result['messages'].append(f"ℹ Trying alternate email: {new_email}")

                        await self._update_email_field(new_email)

                        # Retry submit
                        submit_result = await self._submit_request()
                        if not submit_result['success']:
                            result['errors'].append(f"✗ Retry failed: {submit_result.get('message', 'Unknown error')}")
                            result['success'] = False
                            return result
                        result['messages'].append(f"✓ Used alternate email: {new_email}")
                else:
                    result['success'] = False
                    result['warnings'].append(f"⚠ Email '{user_data['email']}' already exists - Account was not created")
                    return result

            elif not submit_result['success']:
                result['errors'].append(f"✗ {submit_result.get('message', 'Submission failed')}")
                result['success'] = False
                return result
            else:
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

        # Phone number - cell phone only, digits only (no spaces, dashes, or other characters)
        phone = user.mobile_phone or (user.business_phones[0] if user.business_phones else "")
        # Remove all non-numeric characters
        phone_clean = ''.join(filter(str.isdigit, phone))

        # Email
        email = user.mail or user.user_principal_name

        # Title/Job Title
        title = user.job_title or ""

        # AI-based Report Access Level matching
        report_access_level = "Department"  # Default (radio button selection)
        if user.job_title:
            role_suggestion = self.ai_matcher.suggest_role(
                job_title=user.job_title,
                available_roles=self.title_mappings,
                department=user.department
            )
            if role_suggestion and 'match' in role_suggestion:
                report_access_level = role_suggestion['match'].get('value', 'Department')
                logger.info(f"AI matched job title '{user.job_title}' to Report Access Level: {report_access_level}")
            else:
                logger.warning(f"No AI match for job title '{user.job_title}', using default: Department")

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
            'reportAccessLevel': report_access_level,
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

    async def _handle_mfa(self):
        """Handle MFA: auto-select private computer, select email delivery, then wait for code entry"""
        logger.info("Handling MFA flow...")

        # Wait a moment for MFA page to load
        await asyncio.sleep(2)

        # Take screenshot to see MFA page
        await self.page.screenshot(path='partnerscredit_mfa_page.png')

        try:
            # Step 1: Handle the public/private computer selection page (SecureAuth)
            private_radio = await self.page.query_selector('#ContentPlaceHolder1_RadioButtonListPublicPrivate_1')
            if private_radio:
                await private_radio.click()
                logger.info("Selected 'This is a private computer'")
                await asyncio.sleep(0.5)

                # Click Submit button
                await self.page.click('#ContentPlaceHolder1_Button1')
                logger.info("Clicked Submit on public/private page")

                await self.page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)

                await self.page.screenshot(path='partnerscredit_after_private_select.png')
                logger.info("Public/private selection completed")
            else:
                logger.info("No public/private selection page detected, continuing...")

            # Step 2: Handle delivery method selection (Email vs Phone/SMS)
            email_radio = await self.page.query_selector('#ContentPlaceHolder1_MFALoginControl1_RegistrationMethodView_rbEmail1')
            if email_radio:
                await email_radio.click()
                logger.info("Selected 'Email' delivery method")
                await asyncio.sleep(0.5)

                # Click Submit button
                await self.page.click('#ContentPlaceHolder1_MFALoginControl1_RegistrationMethodView_btnSubmit')
                logger.info("Clicked Submit on delivery method page")

                await self.page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)

                await self.page.screenshot(path='partnerscredit_after_email_select.png')
                logger.info("Email delivery method selected - code sent to admin email")
            else:
                logger.info("No delivery method selection page detected, continuing...")

            # Step 3: Wait for user to enter the email verification code manually
            logger.info("Waiting for user to enter verification code from email...")

            # Poll for MFA completion by looking for dashboard or admin elements
            max_wait_time = 300  # 5 minutes
            check_interval = 2  # Check every 2 seconds
            elapsed_time = 0

            success_indicators = [
                'text="Admin"',
                'text="Dashboard"',
                'a:has-text("Admin")',
                'a:has-text("Dashboard")'
            ]

            while elapsed_time < max_wait_time:
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval

                # Check for success indicators
                for indicator in success_indicators:
                    try:
                        element = await self.page.query_selector(indicator)
                        if element and await element.is_visible():
                            logger.info(f"✓ MFA completed - found: {indicator}")
                            await self.page.screenshot(path='partnerscredit_mfa_complete.png')
                            return
                    except:
                        continue

                # Log progress every 30 seconds
                if elapsed_time % 30 == 0:
                    logger.info(f"Still waiting for MFA completion... ({elapsed_time}s elapsed)")

            # Timeout
            raise Exception("MFA completion timeout - user did not complete MFA within 5 minutes")

        except Exception as e:
            logger.error(f"MFA handling error: {e}")
            await self.page.screenshot(path='partnerscredit_mfa_error.png')
            raise

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

        # Wait for the specific input field
        await self.page.wait_for_selector('#content_ctl00_txtUserTotal', timeout=10000)

        # Fill number of users
        await self.page.fill('#content_ctl00_txtUserTotal', str(num_users))
        logger.info(f"Filled number of users: {num_users}")

        # Click Next button
        await self.page.click('#content_ctl00_btnGenUserBoxes')
        logger.info("Clicked Next button")

        await self.page.wait_for_load_state('networkidle')
        await asyncio.sleep(1)

        # Take screenshot of the user form
        await self.page.screenshot(path='partnerscredit_user_form.png')
        logger.info("Number of users set, form loaded")

    async def _fill_user_form(self, user_data: Dict[str, Any]):
        """Fill the new user form"""
        logger.info("Filling user form...")

        # Wait for form to be ready
        await self.page.wait_for_selector('#content_ctl00_rpUserEntries_txtFirstName_0', timeout=10000)
        await asyncio.sleep(1)

        # Save HTML for inspection
        html_content = await self.page.content()
        with open('partnerscredit_form_html.html', 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Fill First Name
        await self.page.fill('#content_ctl00_rpUserEntries_txtFirstName_0', user_data['firstName'])
        logger.info(f"Filled First Name: {user_data['firstName']}")

        # Fill Last Name
        await self.page.fill('#content_ctl00_rpUserEntries_txtLastName_0', user_data['lastName'])
        logger.info(f"Filled Last Name: {user_data['lastName']}")

        # Fill Phone Number
        await self.page.fill('#content_ctl00_rpUserEntries_txtPhone_0', user_data['phoneNumber'])
        logger.info(f"Filled Phone Number: {user_data['phoneNumber']}")

        # Fill Email Address
        await self.page.fill('#content_ctl00_rpUserEntries_txtEmail_0', user_data['email'])
        logger.info(f"Filled Email: {user_data['email']}")

        # Fill Title
        await self.page.fill('#content_ctl00_rpUserEntries_txtUserTitle_0', user_data['title'])
        logger.info(f"Filled Title: {user_data['title']}")

        # Select Report Access Level (radio button) - Company, Department, or User
        report_access_level = user_data['reportAccessLevel']

        # Map report access level to the exact radio button ID
        radio_button_map = {
            'Company': '#content_ctl00_rpUserEntries_rblPermList_0_0_0',
            'Department': '#content_ctl00_rpUserEntries_rblPermList_0_1_0',
            'User': '#content_ctl00_rpUserEntries_rblPermList_0_2_0'
        }

        if report_access_level in radio_button_map:
            await self.page.click(radio_button_map[report_access_level])
            logger.info(f"Selected Report Access Level: {report_access_level}")
        else:
            logger.warning(f"Unknown Report Access Level: {report_access_level}, defaulting to Department")
            await self.page.click('#content_ctl00_rpUserEntries_rblPermList_0_1_0')

        # Select Department from dropdown
        await self.page.select_option('select', label=user_data['department'])
        logger.info(f"Selected Department: {user_data['department']}")

        # Fill Comments
        await self.page.fill('#content_ctl00_rpUserEntries_txtComments_0', user_data['comments'])
        logger.info(f"Filled Comments: {user_data['comments']}")

        # Take screenshot of filled form
        await self.page.screenshot(path='partnerscredit_form_filled.png')
        logger.info("User form filled")

    async def _submit_request(self) -> Dict[str, Any]:
        """
        Submit the user request and check for duplicate/error indicators

        Returns:
            Dict with 'success', 'duplicate_email', and 'message' keys
        """
        logger.info("Submitting user request...")

        submit_result = {
            'success': True,
            'duplicate_email': False,
            'message': 'User request submitted successfully'
        }

        try:
            # Click Request New Users button (exact ID from user)
            await self.page.click('#content_ctl00_btnCreateUsers')
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)

            # Take screenshot of result
            await self.page.screenshot(path='partnerscredit_request_submitted.png')

            # Save HTML for debugging/inspection
            page_content = await self.page.content()
            with open('partnerscredit_submit_result.html', 'w', encoding='utf-8') as f:
                f.write(page_content)

            page_lower = page_content.lower()

            # Check for duplicate email indicators
            email_duplicate_indicators = [
                'email' in page_lower and 'already' in page_lower,
                'email' in page_lower and 'exists' in page_lower,
                'email' in page_lower and 'in use' in page_lower,
                'email' in page_lower and 'duplicate' in page_lower,
                'email' in page_lower and 'taken' in page_lower,
                'email' in page_lower and 'registered' in page_lower,
            ]

            if any(email_duplicate_indicators):
                logger.warning("Duplicate email detected after submit")
                await self.page.screenshot(path='partnerscredit_duplicate_email.png')
                submit_result['success'] = False
                submit_result['duplicate_email'] = True
                submit_result['message'] = 'Email address already in use'
                return submit_result

            # Check for duplicate user/name indicators
            user_duplicate_indicators = [
                'user' in page_lower and 'already' in page_lower and 'exists' in page_lower,
                'duplicate' in page_lower and 'user' in page_lower,
                'account' in page_lower and 'already' in page_lower,
            ]

            if any(user_duplicate_indicators):
                logger.warning("Duplicate user detected after submit")
                await self.page.screenshot(path='partnerscredit_duplicate_user.png')
                submit_result['success'] = False
                submit_result['duplicate_email'] = True  # Treat as email conflict so tech can adjust
                submit_result['message'] = 'User already exists'
                return submit_result

            # Check for visible error elements (snackbar, alert, validation messages)
            error_selectors = [
                '.error', '.alert-danger', '.alert-error', '[class*="error"]',
                '.validation-error', '.field-error', '[role="alert"]',
                '#snackbar.error', '#snackbar', '.toast-error'
            ]
            for selector in error_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for elem in elements:
                        if elem and await elem.is_visible():
                            error_text = await elem.text_content()
                            if error_text:
                                error_lower = error_text.lower().strip()
                                if any(kw in error_lower for kw in ['already', 'exists', 'duplicate', 'in use', 'taken']):
                                    logger.warning(f"Duplicate indicator in error element: {error_text.strip()}")
                                    await self.page.screenshot(path='partnerscredit_error_element.png')
                                    submit_result['success'] = False
                                    submit_result['duplicate_email'] = True
                                    submit_result['message'] = error_text.strip()
                                    return submit_result
                                elif error_lower and 'success' not in error_lower:
                                    logger.warning(f"Non-duplicate error element: {error_text.strip()}")
                                    submit_result['success'] = False
                                    submit_result['message'] = error_text.strip()
                                    return submit_result
                except:
                    continue

            logger.info("✓ User request submitted successfully - no errors detected")

        except Exception as e:
            logger.error(f"Submit failed: {e}")
            await self.page.screenshot(path='partnerscredit_submit_error.png')
            submit_result['success'] = False
            submit_result['message'] = str(e)

        return submit_result

    async def _update_email_field(self, new_email: str):
        """
        Update the email field with a new value after duplicate detected

        Args:
            new_email: The new email address to try
        """
        logger.info(f"Updating email field to: {new_email}")

        # Clear and refill the email field
        email_selector = '#content_ctl00_rpUserEntries_txtEmail_0'
        await self.page.fill(email_selector, '')
        await asyncio.sleep(0.3)
        await self.page.fill(email_selector, new_email)

        # Trigger blur event
        await self.page.press(email_selector, 'Tab')
        await asyncio.sleep(0.5)

        await self.page.screenshot(path='partnerscredit_email_updated.png')
        logger.info(f"Email field updated to: {new_email}")

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
    Main entry point for Partners Credit user provisioning

    Args:
        user: EntraUser object
        config_path: Path to vendor config JSON
        api_key: Anthropic API key for AI matching (optional)
        on_email_conflict: Async callback when email is taken.
            Receives (display_name, attempted_email).
            Should return new email to try, or None to skip this vendor.

    Returns:
        Dict with provisioning result
    """
    from services.keyvault_service import KeyVaultService

    # Initialize KeyVault service
    keyvault = KeyVaultService()

    # Create automation instance with AI matcher support
    automation = PartnersCreditAutomation(config_path, keyvault, api_key=api_key)

    # Run automation with callback
    result = await automation.create_account(
        user,
        headless=False,
        on_email_conflict=on_email_conflict
    )

    return result
