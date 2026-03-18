"""
The Work Number (Equifax) User Provisioning Automation

This module automates the creation of user accounts in The Work Number
Verification Insights Portal using Playwright for web automation.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Awaitable

from playwright.async_api import async_playwright, Page, Browser, Playwright

from models.user import EntraUser
from services.keyvault_service import KeyVaultService
from utils.screenshot import safe_screenshot

# Configure logging
logger = logging.getLogger('automation.vendors.theworknumber')


class TheWorkNumberAutomation:
    """Handles The Work Number user provisioning automation"""

    def __init__(self, config_path: str, keyvault: KeyVaultService, graph_client=None):
        """
        Initialize The Work Number automation

        Args:
            config_path: Path to vendor config.json
            keyvault: KeyVaultService instance for credential retrieval
            graph_client: Optional GraphAPIClient for email-based MFA
        """
        self.config_path = Path(config_path)
        self.keyvault = keyvault
        self.graph_client = graph_client
        self.config = self._load_config()
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.current_user: Optional[EntraUser] = None
        self._login_frame = None

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
        on_username_conflict: Optional[Callable[[str, str], Awaitable[Optional[str]]]] = None,
        on_email_conflict: Optional[Callable[[str, str, str], Awaitable[Optional[Dict[str, str]]]]] = None
    ) -> Dict[str, Any]:
        """
        Create a The Work Number account for the given user

        Args:
            user: EntraUser object with user details
            headless: Whether to run browser in headless mode
            on_username_conflict: Async callback when username is taken.
                Receives (display_name, attempted_username).
                Should return new username to try, or None to skip this vendor.
            on_email_conflict: Async callback when email/username is taken.
                Receives (display_name, attempted_email, attempted_username).
                Should return dict with 'username' and 'email' keys, or None to skip.

        Returns:
            Dict with success status and messages
        """
        self.current_user = user
        self.on_username_conflict = on_username_conflict
        self.on_email_conflict = on_email_conflict
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

            # Create User and check for duplicates
            create_result = await self._create_user(user_data)

            if create_result == 'duplicate_username':
                # Duplicate username detected - prompt user for decision
                if on_username_conflict:
                    result['messages'].append(f"ℹ Username '{user_data['username']}' is already taken")
                    new_username = await on_username_conflict(user.display_name, user_data['username'])

                    if new_username is None:
                        # User chose to skip
                        result['success'] = False
                        result['warnings'].append(f"⚠ Username '{user_data['username']}' already exists - User chose to skip")
                        logger.info(f"User skipped The Work Number due to username conflict: {user.display_name}")
                        return result
                    else:
                        # User provided alternative username - go back and retry
                        logger.info(f"User provided alternate username: {new_username}")
                        result['messages'].append(f"ℹ Trying alternate username: {new_username}")

                        # Navigate back to add user form and retry
                        await self._click_add_user()
                        user_data['username'] = new_username
                        await self._fill_user_details(user_data)
                        await self._click_continue()
                        await self._select_organization()
                        await self._select_location()

                        # Try again
                        create_result = await self._create_user(user_data)
                        if create_result != 'success':
                            result['errors'].append(f"✗ Alternate username '{new_username}' also failed: {create_result}")
                            result['success'] = False
                            return result
                        result['messages'].append(f"✓ Used alternate username: {new_username}")
                else:
                    # No callback provided - fail with error
                    result['success'] = False
                    result['warnings'].append(f"⚠ Username '{user_data['username']}' already exists - Account was not created")
                    logger.info(f"Username conflict in The Work Number, no callback provided: {user.display_name}")
                    return result

            elif create_result == 'duplicate_email':
                # Duplicate user detected - prompt user for new username + email
                if on_email_conflict:
                    result['messages'].append(f"ℹ User already exists (username: '{user_data['username']}', email: '{user_data['email']}')")
                    conflict_result = await on_email_conflict(user.display_name, user_data['email'], user_data['username'])

                    if conflict_result is None:
                        # User chose to skip
                        result['success'] = False
                        result['warnings'].append(f"⚠ User already exists - User chose to skip")
                        logger.info(f"User skipped The Work Number due to duplicate user: {user.display_name}")
                        return result
                    else:
                        # User provided alternatives - click Back, update both fields, retry
                        new_username = conflict_result.get('username', user_data['username'])
                        new_email = conflict_result.get('email', user_data['email'])
                        logger.info(f"User provided alternate username: {new_username}, email: {new_email}")
                        result['messages'].append(f"ℹ Trying alternate username: {new_username}, email: {new_email}")

                        # Click Back to return to user details form
                        await self._click_back()

                        # Update both username and email fields
                        user_data['username'] = new_username
                        user_data['email'] = new_email
                        await self._update_username_field(new_username)
                        await self._update_email_field(new_email)

                        # Click Continue to go back to org/location page
                        await self._click_continue()

                        # Wait for page to settle (org/location should still be selected)
                        await asyncio.sleep(4)

                        # Try again
                        create_result = await self._create_user(user_data)
                        if create_result != 'success':
                            result['errors'].append(f"✗ Retry with username '{new_username}' / email '{new_email}' also failed: {create_result}")
                            result['success'] = False
                            return result
                        result['messages'].append(f"✓ Used alternate username: {new_username}, email: {new_email}")
                else:
                    # No callback provided - fail with error
                    result['success'] = False
                    result['warnings'].append(f"⚠ User already exists - Account was not created")
                    logger.info(f"Duplicate user in The Work Number, no callback provided: {user.display_name}")
                    return result

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
            if self.page:
                await safe_screenshot(self.page, f'theworknumber_error_{user.display_name.replace(" ", "_")}.png')

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

    async def _find_in_frame(self, selector, frames=None, timeout=500):
        """
        Find an element across frames, trying cached login frame first.
        Returns (element, frame) tuple or (None, None) if not found.
        """
        # Try cached login frame first (instant check)
        if self._login_frame:
            try:
                element = await self._login_frame.wait_for_selector(selector, timeout=timeout)
                if element and await element.is_visible():
                    return element, self._login_frame
            except:
                pass

        # Fall back to scanning all frames
        for frame in (frames or self.page.frames):
            if frame == self._login_frame:
                continue  # Already tried
            try:
                element = await frame.wait_for_selector(selector, timeout=timeout)
                if element and await element.is_visible():
                    return element, frame
            except:
                continue
        return None, None

    async def _dismiss_privacy_banner(self):
        """Dismiss Ketch privacy consent banner if present"""
        try:
            close_selectors = [
                # Ketch banner close/X buttons
                '[class*="ketch"] [aria-label="Close"]',
                '[class*="ketch"] button:has(svg)',
                '[id*="ketch"] [aria-label="Close"]',
                '[class*="ketch"] svg',
                # Generic consent/privacy banners
                '[class*="consent"] [aria-label="Close"]',
                '[class*="privacy"] button:has(svg)',
                # Ketch banner specific patterns - the X button with SVG
                '[class*="ketch-h-6"]',
                'button:has([class*="ketch"])',
            ]
            for selector in close_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        if element and await element.is_visible():
                            # Try clicking the element's parent if it's an SVG
                            tag = await element.evaluate('el => el.tagName')
                            if tag.lower() == 'svg':
                                await element.evaluate('el => el.closest("button, a, div[role=button]")?.click()')
                            else:
                                await element.click()
                            logger.info(f"Dismissed privacy banner using: {selector}")
                            await asyncio.sleep(0.5)
                            return
                except:
                    continue

            # Fallback: try to remove the banner via JavaScript
            await self.page.evaluate('''() => {
                const el = document.querySelector('[class*="ketch"], [id*="ketch"]');
                if (el) { el.remove(); return true; }
                return false;
            }''')
            logger.debug("Privacy banner check complete")
        except Exception as e:
            logger.debug(f"Privacy banner check: {e}")

    async def _login(self):
        """Login to The Work Number portal via multi-step flow"""
        login_url = self.keyvault.get_vendor_credential('theworknumber', 'login-url')
        admin_username = self.keyvault.get_vendor_credential('theworknumber', 'admin-username')
        admin_password = self.keyvault.get_vendor_credential('theworknumber', 'admin-password')

        # Track which iframe contains the login form so we don't rescan all 11 frames
        self._login_frame = None

        logger.info(f"Navigating to {login_url}")
        await self.page.goto(login_url)
        await self.page.wait_for_load_state('networkidle')

        # Dismiss Ketch privacy consent banner if present
        await self._dismiss_privacy_banner()

        # Take screenshot of landing page for debugging
        await safe_screenshot(self.page, 'theworknumber_landing_page.png')

        # Step 1: Click "Log In" button in the top nav
        logger.info("Looking for Log In button...")
        login_clicked = False
        login_selectors = [
            '#loginDropdown',                                    # Legacy dropdown
            'a:has-text("Log In")',                              # Nav link
            'button:has-text("Log In")',                         # Nav button
            'a[href*="login"]',                                  # Login URL link
            'a[href*="signin"]',                                 # Sign-in URL link
            'a:has-text("Sign In")',                             # Alt text
        ]

        for selector in login_selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=3000)
                if element and await element.is_visible():
                    await element.click()
                    login_clicked = True
                    logger.info(f"Clicked login with selector: {selector}")
                    break
            except:
                continue

        if not login_clicked:
            await safe_screenshot(self.page, 'theworknumber_login_button_not_found.png')
            raise Exception("Could not find Log In button on the landing page")

        await asyncio.sleep(1)
        await safe_screenshot(self.page, 'theworknumber_after_login_click.png')

        # Step 2: Look for "Verify for Your Organization" link (may open a new tab)
        logger.info("Looking for 'Verify for Your Organization'...")
        context = self.page.context

        # Check if we need to click through to a verify page, or if we're already on a login form
        verify_found = False
        try:
            verify_element = await self.page.wait_for_selector(
                'text="Verify for Your Organization"', timeout=5000
            )
            if verify_element and await verify_element.is_visible():
                # This link may open a new tab
                async with context.expect_event('page', timeout=10000) as new_page_info:
                    await verify_element.click()
                new_page = await new_page_info.value
                self.page = new_page
                await self.page.bring_to_front()
                verify_found = True
                logger.info("Clicked 'Verify for Your Organization' - switched to new tab")
        except:
            logger.info("No 'Verify for Your Organization' link found, checking if already on login page")

        if not verify_found:
            # We might already be on the login page or a new tab opened automatically
            pages = context.pages
            if len(pages) > 1:
                self.page = pages[-1]
                await self.page.bring_to_front()
                logger.info(f"Switched to latest tab: {self.page.url}")

        # Wait for page to load
        logger.info("Waiting for page to fully load...")
        await self.page.wait_for_load_state('load')
        try:
            await self.page.wait_for_load_state('networkidle', timeout=10000)
        except:
            logger.info("networkidle not reached, continuing anyway")
        await asyncio.sleep(1)

        # Step 4: Enter username - the form is in an iframe
        logger.info("Entering username...")
        await asyncio.sleep(1)

        frames = self.page.frames
        logger.info(f"Found {len(frames)} frames")

        # Try the known TWN username selector across all frames
        element, frame = await self._find_in_frame('input#txtUsername', frames)

        # Fallback: try broader selectors
        if not element:
            for selector in ['input[name="txtUsername"]', 'input.form-control', 'input[type="text"]']:
                element, frame = await self._find_in_frame(selector, frames)
                if element:
                    break

        if not element:
            raise Exception("Could not find username field in any frame")

        await element.fill(admin_username)
        self._login_frame = frame  # Cache this frame for subsequent steps
        logger.info(f"Filled username: {admin_username}")

        # Step 5: Click Continue - use cached frame first
        logger.info("Clicking Continue...")
        continue_element = None
        for selector in ['input[value*="Continue"]', 'button:has-text("Continue")', 'a:has-text("Continue")']:
            continue_element, _ = await self._find_in_frame(selector)
            if continue_element:
                await continue_element.click()
                logger.info(f"Clicked Continue with selector: {selector}")
                break

        if not continue_element:
            raise Exception("Could not find Continue button")

        try:
            await self.page.wait_for_load_state('networkidle', timeout=10000)
        except:
            pass
        await asyncio.sleep(1)

        # Step 6: Wait for password field - use cached frame first
        logger.info("Waiting for password field...")
        password_filled = False
        for retry in range(10):
            pwd_element, _ = await self._find_in_frame('input[type="password"]', timeout=1000)
            if pwd_element:
                await pwd_element.fill(admin_password)
                password_filled = True
                logger.info("Filled password in frame")
                break

            if retry < 9:
                logger.info(f"Password field not found, retry {retry + 1}/10")
                await asyncio.sleep(0.5)

        if not password_filled:
            raise Exception("Could not find password field")

        logger.info("Filled password")

        # Step 7: Click Log in - use cached frame first
        logger.info("Clicking Log in...")
        login_element = None
        for selector in ['input[value*="Log in"]', 'button:has-text("Log in")', 'button:has-text("Login")']:
            login_element, _ = await self._find_in_frame(selector)
            if login_element:
                await login_element.click()
                logger.info(f"Clicked Log in with selector: {selector}")
                break

        if not login_element:
            raise Exception("Could not find Log in button")

        logger.info("Waiting for page to load after login...")
        try:
            await self.page.wait_for_load_state('networkidle', timeout=15000)
        except:
            logger.warning("networkidle timeout, continuing anyway")

        await asyncio.sleep(1)

        # Check if MFA/identity validation is required
        await self._handle_mfa()

        logger.info("Login completed")

    async def _check_dashboard_reached(self) -> bool:
        """Check if we've reached the dashboard (MFA complete)"""
        dashboard_keywords = ["New Order", "Order History", "User Management", "Verifiers", "Administration"]

        # Check main page content
        try:
            page_content = await self.page.content()
            for keyword in dashboard_keywords:
                if keyword in page_content:
                    logger.info(f"Dashboard detected via keyword: {keyword}")
                    return True
        except Exception:
            pass

        # Check all frames
        for frame in self.page.frames:
            try:
                frame_content = await frame.content()
                for keyword in dashboard_keywords:
                    if keyword in frame_content:
                        logger.info(f"Dashboard detected in frame via keyword: {keyword}")
                        return True
            except Exception:
                continue

        # Check URL as fallback
        current_url = self.page.url
        if 'vsportal' in current_url or 'dashboard' in current_url or 'home' in current_url:
            logger.info(f"Dashboard detected via URL: {current_url}")
            return True

        return False

    async def _auto_enter_mfa_code(self, send_time: str = None) -> bool:
        """
        Attempt to automatically read OTP from nexus@ inbox and enter it.
        Returns True on success, False on any failure (caller falls back to manual).

        Args:
            send_time: ISO 8601 UTC timestamp from when "Send code" was clicked.
                       Used as floor for email search to avoid stale OTPs.
        """
        if not self.graph_client:
            logger.info("No graph_client available - skipping auto MFA entry")
            return False

        from datetime import datetime, timezone
        import re

        mailbox = "nexus@highlandsmortgage.com"
        if not send_time:
            send_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        logger.info(f"Attempting auto MFA code entry from {mailbox}")

        # Initial delay - give the email time to arrive
        await asyncio.sleep(10)

        # Poll for OTP email (every 10s, up to 2 minutes)
        max_attempts = 12
        for attempt in range(max_attempts):
            logger.info(f"Polling inbox for OTP email (attempt {attempt + 1}/{max_attempts})...")

            messages = self.graph_client.read_recent_emails(
                mailbox=mailbox,
                since_timestamp=send_time
            )

            # Client-side filter: look for emails from Equifax
            for msg in messages:
                sender = msg.get('from', {}).get('emailAddress', {}).get('address', '').lower()
                subject = (msg.get('subject') or '').lower()

                if 'equifax' not in sender and 'equifax' not in subject:
                    continue

                # Extract 6-digit OTP from plain text body
                body_text = msg.get('body', {}).get('content', '')
                otp_match = re.search(r'\b(\d{6})\b', body_text)

                if not otp_match:
                    logger.info(f"Found Equifax email but no 6-digit code. Subject: {msg.get('subject')}")
                    continue

                otp_code = otp_match.group(1)
                logger.info(f"Extracted OTP code: {otp_code}")

                # Find the code input field in the iframe
                code_entered = False
                code_selectors = [
                    'input[type="text"]',
                    'input[name*="code"]',
                    'input[id*="code"]',
                    'input[name*="otp"]',
                    'input[id*="otp"]',
                    'input.form-control[type="text"]',
                ]

                for frame in self.page.frames:
                    if code_entered:
                        break
                    try:
                        for selector in code_selectors:
                            try:
                                element = await frame.query_selector(selector)
                                if element and await element.is_visible():
                                    await element.fill(otp_code)
                                    code_entered = True
                                    logger.info(f"Entered OTP code using selector: {selector}")
                                    break
                            except Exception:
                                continue
                    except Exception:
                        continue

                if not code_entered:
                    logger.warning("Found OTP code but could not find input field")
                    return False

                await asyncio.sleep(1)
                await safe_screenshot(self.page, 'theworknumber_mfa_auto_code_entered.png')

                # Click Submit/Verify/Continue
                submit_clicked = False
                submit_selectors = [
                    'input[value*="Verify"]',
                    'button:has-text("Verify")',
                    'input[value*="Submit"]',
                    'button:has-text("Submit")',
                    'input[value*="Continue"]',
                    'button:has-text("Continue")',
                ]

                for frame in self.page.frames:
                    if submit_clicked:
                        break
                    try:
                        for selector in submit_selectors:
                            try:
                                btn = await frame.query_selector(selector)
                                if btn and await btn.is_visible():
                                    await btn.click()
                                    submit_clicked = True
                                    logger.info(f"Clicked submit using selector: {selector}")
                                    break
                            except Exception:
                                continue
                    except Exception:
                        continue

                if not submit_clicked:
                    logger.warning("Entered OTP but could not find submit button")
                    return False

                await asyncio.sleep(3)
                await safe_screenshot(self.page, 'theworknumber_mfa_auto_submitted.png')

                # Verify we reached the dashboard
                if await self._check_dashboard_reached():
                    logger.info("Auto MFA completed successfully - dashboard reached")
                    await safe_screenshot(self.page, 'theworknumber_mfa_auto_complete.png')
                    return True
                else:
                    logger.warning("Auto MFA code submitted but dashboard not detected")
                    return False

            # No matching email yet - wait and retry
            if attempt < max_attempts - 1:
                logger.info("OTP email not found yet, waiting 10s...")
                await asyncio.sleep(10)

        logger.warning(f"OTP email not found after {max_attempts} attempts - falling back to manual")
        return False

    async def _handle_mfa(self):
        """Handle MFA/identity validation if required"""
        logger.info("Checking for MFA/identity validation...")
        logger.debug("Checking for MFA/identity validation...")

        # Check if the identity validation modal is present
        try:
            mfa_detected = False

            # First check all frames for content
            all_frames = self.page.frames
            logger.debug(f"Found {len(all_frames)} frames")

            for i, frame in enumerate(all_frames):
                try:
                    frame_content = await frame.content()
                    logger.debug(f"Frame {i} content length: {len(frame_content)}")

                    # Check for MFA indicators
                    mfa_keywords = ["validate your identity", "E-mail passcode", "one-time", "Additional information"]
                    for keyword in mfa_keywords:
                        if keyword.lower() in frame_content.lower():
                            mfa_detected = True
                            logger.debug(f"MFA detected in frame {i} via keyword: {keyword}")
                            logger.info(f"MFA detected in frame {i} via keyword: {keyword}")
                            break
                    if mfa_detected:
                        break
                except Exception as e:
                    logger.debug(f"Error checking frame {i}: {e}")
                    continue

            if mfa_detected:
                logger.info("MFA identity validation detected")
                logger.debug("MFA identity validation detected - waiting for user to complete")

                # Take screenshot
                await safe_screenshot(self.page, 'theworknumber_mfa_page.png')

                # Click on the email option to receive the code
                # The button may be an <a>, <button>, or <input> styled as a button
                email_clicked = False
                email_selectors = [
                    # Link/button elements containing an email address (most common)
                    'a:has-text("@highlandsmortgage")',
                    'a:has-text("@")',
                    'button:has-text("@highlandsmortgage")',
                    'button:has-text("@")',
                    # Input elements (legacy format)
                    'input.btn-challenge[value*="@"]',
                    'input[type="submit"][value*="@"]',
                    'input#btnEndpoint1',
                    'input[value*="highlandsmortgage"]',
                    'input[value*="@"]',
                ]

                for frame in self.page.frames:
                    if email_clicked:
                        break
                    try:
                        for selector in email_selectors:
                            try:
                                elements = await frame.query_selector_all(selector)
                                for elem in elements:
                                    if elem and await elem.is_visible():
                                        # Skip "None of the above" links
                                        try:
                                            elem_text = await elem.text_content()
                                            if elem_text and 'none' in elem_text.lower():
                                                continue
                                        except Exception:
                                            pass
                                        await elem.click()
                                        email_clicked = True
                                        logger.debug(f"Clicked email option using selector: {selector}")
                                        logger.info(f"Clicked email option using selector: {selector}")
                                        break
                            except Exception:
                                continue
                            if email_clicked:
                                break
                    except Exception:
                        continue

                if not email_clicked:
                    logger.debug("Could not auto-click email button - waiting for manual action")
                    logger.info("Could not auto-click email button - user should click manually")

                await asyncio.sleep(2)

                # Try to click "Send code" or similar button if present
                send_code_clicked = False
                send_code_selectors = [
                    'button:has-text("Send")',
                    'button:has-text("Send code")',
                    'input[value*="Send"]',
                    'button:has-text("Continue")',
                    'button:has-text("Submit")',
                ]
                for frame in self.page.frames:
                    if send_code_clicked:
                        break
                    try:
                        for selector in send_code_selectors:
                            try:
                                btn = await frame.query_selector(selector)
                                if btn and await btn.is_visible():
                                    await btn.click()
                                    send_code_clicked = True
                                    logger.debug(f"Clicked send code button using: {selector}")
                                    logger.info(f"Clicked send code button using: {selector}")
                                    break
                            except Exception:
                                continue
                    except Exception:
                        continue

                await asyncio.sleep(2)

                # Record timestamp for email filtering (before any delay)
                from datetime import datetime, timezone
                send_code_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

                # Try automatic OTP entry first
                auto_success = await self._auto_enter_mfa_code(send_time=send_code_time)
                if auto_success:
                    logger.info("MFA completed via automatic OTP entry")
                    return

                # Auto-entry failed or unavailable - fall back to manual
                logger.info("Falling back to manual MFA entry")

                # Take screenshot after clicking email
                await safe_screenshot(self.page, 'theworknumber_mfa_code_sent.png')

                # Wait for user to manually enter the code
                logger.debug("=" * 60)
                logger.debug("MFA REQUIRED: Please complete the following steps:")
                logger.debug("1. Click on your email address to receive the code")
                logger.debug("2. Check your email for the one-time passcode")
                logger.debug("3. Enter the code in the browser")
                logger.debug("4. Click Submit/Continue to complete login")
                logger.debug("=" * 60)
                logger.info("Waiting for manual MFA completion (passcode entry)...")

                # Poll for MFA completion - check that modal is dismissed
                max_wait_time = 300  # 5 minutes
                check_interval = 5
                elapsed_time = 0

                while elapsed_time < max_wait_time:
                    await asyncio.sleep(check_interval)
                    elapsed_time += check_interval

                    # Take periodic screenshots
                    if elapsed_time % 15 == 0:
                        await safe_screenshot(self.page, f'theworknumber_mfa_wait_{elapsed_time}s.png')

                    # Check if MFA modal is still present by looking for MFA keywords in frames
                    mfa_still_present = False
                    for frame in self.page.frames:
                        try:
                            frame_content = await frame.content()
                            mfa_keywords = ["validate your identity", "E-mail passcode", "one-time passcode", "enter the code"]
                            for keyword in mfa_keywords:
                                if keyword.lower() in frame_content.lower():
                                    mfa_still_present = True
                                    break
                            if mfa_still_present:
                                break
                        except Exception:
                            continue

                    if not mfa_still_present:
                        if await self._check_dashboard_reached():
                            logger.info("MFA completed - dashboard reached")
                            await safe_screenshot(self.page, 'theworknumber_mfa_complete.png')
                            await asyncio.sleep(2)
                            return

                    # Log progress with diagnostic info
                    if elapsed_time % 30 == 0:
                        frame_count = len(self.page.frames)
                        current_url = self.page.url
                        logger.debug(f"Still waiting for MFA completion... ({elapsed_time}s elapsed, {frame_count} frames, URL: {current_url})")
                        logger.info(f"MFA wait: {elapsed_time}s, mfa_still_present={mfa_still_present}, frames={frame_count}, url={current_url}")

                raise Exception("MFA timeout - user did not complete MFA within 5 minutes")
            else:
                logger.debug("No MFA required - continuing")
                logger.info("No MFA required")
        except Exception as e:
            logger.debug(f"MFA handling exception: {e}")
            if "MFA timeout" in str(e):
                raise
            logger.info(f"MFA exception: {e}, continuing...")

    async def _dismiss_news_modal(self):
        """Dismiss any news/announcement modal that may appear after login"""
        logger.info("Checking for news modal...")

        try:
            # Look for the close button with data-step="skip" or aria-label="Close modal"
            close_selectors = [
                'a[data-step="skip"]',
                'a[aria-label="Close modal"]',
                '[role="button"][aria-label="Close modal"]',
                'button[data-step="skip"]',
                '.modal a:has-text("×")',
                '.modal button:has-text("×")',
                '[class*="modal"] a[data-step="skip"]',
            ]

            for selector in close_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.click()
                        logger.info(f"Dismissed news modal using selector: {selector}")
                        logger.debug(f"Dismissed news modal using selector: {selector}")
                        await asyncio.sleep(1)
                        return True
                except:
                    continue

            # Also check in frames
            for frame in self.page.frames:
                try:
                    for selector in close_selectors:
                        try:
                            element = await frame.query_selector(selector)
                            if element and await element.is_visible():
                                await element.click()
                                logger.info(f"Dismissed news modal in frame using selector: {selector}")
                                logger.debug(f"Dismissed news modal in frame using selector: {selector}")
                                await asyncio.sleep(1)
                                return True
                        except:
                            continue
                except:
                    continue

            logger.info("No news modal found")
            return False
        except Exception as e:
            logger.info(f"News modal check exception: {e}")
            return False

    async def _navigate_to_user_management(self):
        """Navigate to User Management via direct URL"""
        logger.info("Navigating to User Management...")
        logger.debug("Navigating to User Management...")

        # Navigate directly to User Management URL (more reliable than clicking through menus)
        user_mgmt_url = "https://secure1.verifier.theworknumber.com/vsportal-ui/manager/users"
        logger.info(f"Navigating directly to: {user_mgmt_url}")
        logger.debug(f"Navigating directly to: {user_mgmt_url}")

        await self.page.goto(user_mgmt_url)

        try:
            await self.page.wait_for_load_state('networkidle', timeout=15000)
        except:
            pass
        await asyncio.sleep(2)

        # Dismiss any news modal that may appear after navigation
        await self._dismiss_news_modal()

        # Dismiss any tour popups that may appear (Appcues tours)
        await self._dismiss_tour()

        # Take screenshot
        await safe_screenshot(self.page, 'theworknumber_user_management.png')
        logger.info("Navigated to User Management")

    async def _dismiss_tour(self):
        """Dismiss any tour/walkthrough popups that may appear (including Appcues tours in iframes)"""
        logger.info("Checking for tour popups...")
        logger.debug("Checking for tour popups...")

        # The Appcues tour uses iframes with class 'appcues-tooltip-container'
        # We need to access the iframe content to click the buttons
        max_attempts = 15  # Handle multi-step tours

        for attempt in range(max_attempts):
            tour_dismissed = False

            # First, try to find Appcues tooltip container iframe
            try:
                appcues_container = await self.page.query_selector('.appcues-tooltip-container')
                if appcues_container:
                    logger.debug(f"  Found Appcues tooltip container (attempt {attempt + 1})")
                    logger.info(f"Found Appcues tooltip container (attempt {attempt + 1})")

                    # Get the iframe content frame
                    frame = await appcues_container.content_frame()
                    if frame:
                        # Look for buttons inside the Appcues iframe
                        appcues_button_selectors = [
                            'button:has-text("Skip")',
                            'button:has-text("I got It")',
                            'button:has-text("Got it")',
                            'button:has-text("Done")',
                            'button:has-text("Close")',
                            'button:has-text("Next")',
                            'a[data-step="skip"]',
                            'a[data-step="next"]',
                            'a.appcues-button-success',
                            'a.appcues-button',
                            'button[data-step="skip"]',
                            'button[data-step="next"]',
                        ]

                        for selector in appcues_button_selectors:
                            try:
                                element = await frame.query_selector(selector)
                                if element and await element.is_visible():
                                    try:
                                        btn_text = await element.inner_text()
                                    except:
                                        btn_text = ""

                                    await element.click()
                                    tour_dismissed = True
                                    logger.debug(f"  Clicked Appcues button: '{btn_text.strip()}' ({selector})")
                                    logger.info(f"Clicked Appcues button: '{btn_text.strip()}' ({selector})")
                                    await asyncio.sleep(0.5)
                                    break
                            except:
                                continue

                        if tour_dismissed:
                            await asyncio.sleep(0.5)
                            continue
            except Exception as e:
                logger.debug(f"Appcues iframe check: {e}")

            # Fallback: check for tour elements on main page
            tour_selectors = [
                'a[data-step="skip"]',
                'a.appcues-skip-btn',
                'button[data-step="skip"]',
                'a.appcues-button-success[data-step="next"]',
                'a[data-step="next"]',
                'button[data-step="next"]',
                'a.appcues-button-success',
                'a.appcues-button',
                'button:has-text("Next")',
                'button:has-text("Skip")',
                'button:has-text("Got it")',
                'button:has-text("Done")',
                'button:has-text("Close")',
                '[aria-label="Close"]',
                '.tour-close',
            ]

            for selector in tour_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        if element and await element.is_visible():
                            try:
                                btn_text = await element.inner_text()
                            except:
                                btn_text = ""

                            await element.click()
                            tour_dismissed = True
                            logger.debug(f"  Clicked tour button: '{btn_text.strip()}' ({selector})")
                            logger.info(f"Clicked tour button: '{btn_text.strip()}' ({selector})")
                            await asyncio.sleep(0.5)
                            break
                except Exception as e:
                    continue

                if tour_dismissed:
                    break

            if not tour_dismissed:
                # No more tour popups found
                logger.debug("  No more tour elements found")
                break

            await asyncio.sleep(0.5)

        # Final check - verify Appcues container is gone
        appcues_container = await self.page.query_selector('.appcues-tooltip-container')
        if appcues_container:
            logger.debug("  WARNING: Appcues tour still present after dismissal attempts")
            logger.warning("Appcues tour still present after dismissal")
        else:
            logger.debug("  Tour dismissed successfully")

        logger.info("Tour check complete")

    async def _click_add_user(self):
        """Click Add User button"""
        logger.info("Clicking Add User...")
        logger.debug("Clicking Add User...")

        await asyncio.sleep(1)

        # Take screenshot before clicking Add User
        await safe_screenshot(self.page, 'theworknumber_before_add_user.png')

        # First, dismiss any tour popups that may be blocking
        await self._dismiss_tour()

        # Take screenshot after dismissing tour
        await safe_screenshot(self.page, 'theworknumber_after_tour_dismiss.png')

        # Wait for any loading spinner to disappear
        logger.debug("Waiting for page to finish loading...")
        for _ in range(30):  # Wait up to 15 seconds
            loader = await self.page.query_selector('.loader-backdrop')
            if not loader:
                break
            logger.debug("  Loading spinner still present, waiting...")
            await asyncio.sleep(0.5)

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
                    logger.debug(f"Clicked Add User with selector: {selector}")
                    logger.info(f"Clicked Add User with selector: {selector}")
                    break
            except:
                continue

        if not add_user_clicked:
            await safe_screenshot(self.page, 'theworknumber_add_user_not_found.png')
            raise Exception("Could not find Add User button")

        try:
            await self.page.wait_for_load_state('networkidle', timeout=10000)
        except:
            pass
        await asyncio.sleep(2)

        # Take screenshot
        await safe_screenshot(self.page, 'theworknumber_add_user_form.png')
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
        await safe_screenshot(self.page, 'theworknumber_form_filled.png')
        logger.info("User details filled")

    async def _click_back(self):
        """Click Back button to return to user details form"""
        logger.info("Clicking Back...")

        try:
            await self.page.get_by_role('button', name='Back').click()
            logger.info("Clicked Back button")
        except Exception as e:
            # Fallback: try the specific class selector
            try:
                await self.page.click('button.cancel-button:has-text("Back")')
                logger.info("Clicked Back button via class selector")
            except:
                logger.error(f"Could not click Back: {e}")
                raise Exception("Could not find Back button")

        await asyncio.sleep(1)
        await safe_screenshot(self.page, 'theworknumber_back_to_form.png')
        logger.info("Returned to user details form")

    async def _update_username_field(self, new_username: str):
        """Update just the username field on the user details form"""
        logger.info(f"Updating username field to: {new_username}")

        try:
            # Use the specific input ID from TWN's form
            username_field = self.page.locator('#newUserUnInput')
            await username_field.clear()
            await username_field.fill(new_username)
            logger.info(f"Updated Username to: {new_username}")
        except Exception as e:
            # Fallback: try by label
            try:
                username_field = self.page.get_by_label('Username:')
                await username_field.clear()
                await username_field.fill(new_username)
                logger.info(f"Updated Username via label to: {new_username}")
            except:
                logger.error(f"Could not update Username: {e}")
                raise Exception("Could not find Username field to update")

    async def _update_email_field(self, new_email: str):
        """Update just the email field on the user details form"""
        logger.info(f"Updating email field to: {new_email}")

        try:
            email_field = self.page.get_by_label('Email:')
            await email_field.clear()
            await email_field.fill(new_email)
            logger.info(f"Updated Email to: {new_email}")
        except Exception as e:
            logger.error(f"Could not update Email: {e}")
            raise Exception("Could not find Email field to update")

        await safe_screenshot(self.page, 'theworknumber_email_updated.png')

    async def _dismiss_snackbar(self):
        """Dismiss any visible snackbar toast (e.g. 'User already exists' from a previous attempt)"""
        logger.info("Dismissing any lingering snackbar toast...")
        try:
            # Click the X button on the snackbar
            close_btn = await self.page.query_selector('#snackbar .closebtn, #snackbar button, #snackbar [class*="close"]')
            if close_btn and await close_btn.is_visible():
                await close_btn.click()
                logger.info("Dismissed snackbar via close button")
                await asyncio.sleep(0.5)
                return

            # Try clicking the X character directly
            snackbar = await self.page.query_selector('#snackbar')
            if snackbar and await snackbar.is_visible():
                # Try to find close element inside snackbar
                close_elem = await snackbar.query_selector('span, button, a')
                if close_elem:
                    close_text = await close_elem.text_content()
                    if close_text and '×' in close_text:
                        await close_elem.click()
                        logger.info("Dismissed snackbar via × element")
                        await asyncio.sleep(0.5)
                        return

                # If no close button found, try JavaScript to hide it
                await self.page.evaluate('document.getElementById("snackbar")?.remove()')
                logger.info("Removed snackbar via JavaScript")
                await asyncio.sleep(0.5)
                return

            logger.info("No snackbar toast found to dismiss")
        except Exception as e:
            logger.info(f"Snackbar dismissal: {e}")

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
        await safe_screenshot(self.page, 'theworknumber_organization_page.png')
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
        await safe_screenshot(self.page, 'theworknumber_org_selected.png')
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
        await safe_screenshot(self.page, 'theworknumber_location_selected.png')
        logger.info(f"Selected location: {loc_name}")

    async def _create_user(self, user_data: Dict[str, Any]) -> str:
        """
        Click Create User button to finalize and check for errors

        Args:
            user_data: User data dictionary (for retry with modified values)

        Returns:
            'success' if user created
            'duplicate_username' if username already exists
            'duplicate_email' if email already exists
        """
        logger.info("Creating user...")

        # Dismiss any lingering snackbar from a previous attempt
        # so old toast text doesn't cause false duplicate detection
        try:
            await self.page.evaluate('document.getElementById("snackbar")?.remove()')
            logger.info("Cleared any old snackbar before Create User")
        except:
            pass

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

        # Take screenshot of result
        await safe_screenshot(self.page, 'theworknumber_create_result.png')

        # Check for duplicate/error messages
        page_content = await self.page.content()
        page_text = page_content.lower()

        # Check for "User already exists" error (shown in snackbar toast)
        if 'user already exists' in page_text:
            logger.warning("User already exists error detected")
            await safe_screenshot(self.page, 'theworknumber_user_exists.png')
            return 'duplicate_email'

        # Check for generic "issue creating user" error
        if 'there was an issue creating the user' in page_text or 'issue creating the user' in page_text:
            logger.warning("Generic user creation error detected - likely duplicate")
            await safe_screenshot(self.page, 'theworknumber_create_error.png')
            return 'duplicate_email'

        # Check for username already exists error
        if 'username' in page_text and ('already' in page_text or 'exists' in page_text or 'in use' in page_text or 'taken' in page_text):
            logger.warning("Duplicate username detected")
            await safe_screenshot(self.page, 'theworknumber_duplicate_username.png')
            return 'duplicate_username'

        # Check for email already exists error
        if 'email' in page_text and ('already' in page_text or 'exists' in page_text or 'in use' in page_text or 'taken' in page_text):
            logger.warning("Duplicate email detected")
            await safe_screenshot(self.page, 'theworknumber_duplicate_email.png')
            return 'duplicate_email'

        # Check for snackbar error toast specifically
        try:
            snackbar = await self.page.query_selector('#snackbar.error')
            if snackbar and await snackbar.is_visible():
                snackbar_text = await snackbar.text_content()
                if snackbar_text:
                    logger.warning(f"Snackbar error detected: {snackbar_text}")
                    await safe_screenshot(self.page, 'theworknumber_snackbar_error.png')
                    if 'already exists' in snackbar_text.lower():
                        return 'duplicate_email'
        except Exception as e:
            logger.debug(f"Snackbar check error: {e}")

        # Check for any visible error message elements
        error_selectors = [
            '#snackbar.error', '.error', '.alert-danger', '.alert-error', '[class*="error"]',
            '.validation-error', '.field-error', '[role="alert"]',
            '.toast-error', '.notification-error', '[class*="toast"]'
        ]
        for selector in error_selectors:
            try:
                error_elements = await self.page.query_selector_all(selector)
                for elem in error_elements:
                    if elem and await elem.is_visible():
                        error_text = await elem.text_content()
                        if error_text:
                            error_text_lower = error_text.lower().strip()
                            # Check for generic "issue creating" error
                            if 'issue creating' in error_text_lower or 'error creating' in error_text_lower or 'already exists' in error_text_lower:
                                logger.warning(f"Creation error detected: {error_text}")
                                await safe_screenshot(self.page, 'theworknumber_create_error.png')
                                return 'duplicate_email'
                            if 'username' in error_text_lower:
                                logger.warning(f"Username error detected: {error_text}")
                                return 'duplicate_username'
                            elif 'email' in error_text_lower:
                                logger.warning(f"Email error detected: {error_text}")
                                return 'duplicate_email'
            except:
                continue

        # Take screenshot of confirmation
        await safe_screenshot(self.page, 'theworknumber_user_created.png')
        logger.info("User created successfully")
        return 'success'

    async def _cleanup(self):
        """Clean up browser resources"""
        logger.info("Cleaning up browser...")
        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass
        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        logger.info("Browser closed")


async def provision_user(
    user: EntraUser,
    config_path: str,
    api_key: Optional[str] = None,
    graph_client=None,
    on_username_conflict: Optional[Callable[[str, str], Awaitable[Optional[str]]]] = None,
    on_email_conflict: Optional[Callable[[str, str, str], Awaitable[Optional[Dict[str, str]]]]] = None
) -> Dict[str, Any]:
    """
    Main entry point for The Work Number user provisioning

    Args:
        user: EntraUser object
        config_path: Path to vendor config JSON
        api_key: Optional API key (not used for The Work Number)
        on_username_conflict: Async callback when username is taken.
            Receives (display_name, attempted_username).
            Should return new username to try, or None to skip this vendor.
        on_email_conflict: Async callback when email/username is taken.
            Receives (display_name, attempted_email, attempted_username).
            Should return dict with 'username' and 'email' keys, or None to skip.

    Returns:
        Dict with provisioning result
    """
    from services.keyvault_service import KeyVaultService

    # Initialize KeyVault service
    keyvault = KeyVaultService()

    # Create automation instance
    automation = TheWorkNumberAutomation(config_path, keyvault, graph_client=graph_client)

    # Run automation with callbacks
    result = await automation.create_account(
        user,
        headless=False,
        on_username_conflict=on_username_conflict,
        on_email_conflict=on_email_conflict
    )

    return result
