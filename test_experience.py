"""
Experience.com Automation Test Script

This script automates the Experience.com user provisioning workflow.
It performs login, user creation, profile settings configuration, and publishing.

Based on the Experience User Guide PDF:

WORKFLOW:
1. Login to https://app.experience.com/user/signin
2. Navigate to Hierarchy -> Users
3. Click "Add New User" -> "Add Single User"
4. Fill user form:
   - First Name, Last Name, Email, Employee ID
   - Opt-in to Experience login: ON (blue)
   - Allow Survey Completion: ON (default - leave as is)
   - Allow user to expire Survey: OFF (turn off from default ON)
   - Select Tier (Branch Location)
   - Select Role (Tier Manager for managers, Agent for LO/LOA)
5. Click "Create User" -> "Confirm"
6. Edit user's Profile Settings (settings not available during creation):

   REVIEW MANAGEMENT SETTINGS:
   - Allow user to reply to reviews: ON (verify)
   - Minimum score to reply on reviews: 3 (can default to 2.5 or 4)
   - Allow user to reply using AI: ON (verify)

   SOCIAL SHARE SETTINGS (CONFIRM ALL):
   - Allow Autopost: ON
   - Minimum Score to Auto-post on Social networks: 4.5
   - Maximum number of posts per day: 3
   - Minimum gap between posts: 2 hours 0 minutes

   ALLOW TO EXPIRE SURVEY:
   - Allow user to expire a survey: OFF (typically defaults to ON)

   SEND SETTINGS:
   - Allow survey completion notification: ON (verify)
   - Allow reply to reviews notification: ON (verify)

7. Click "Update" -> "Confirm" to save settings
8. Publish user profile (click "No" under Published -> Confirm)
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright, Page, Browser, Playwright


class ExperienceTestAutomation:
    """Test automation for Experience.com

    Can either launch its own browser or connect to an existing one via CDP.
    To connect to Playwright MCP's browser, pass cdp_url to start_browser().
    """

    def __init__(self):
        self.playwright: Playwright = None
        self.browser: Browser = None
        self.page: Page = None
        self.owns_browser = True  # Whether we launched the browser (vs connected to existing)

        # Test user data
        self.test_user = {
            'firstName': 'Test',
            'lastName': 'User',
            'email': 'noemail@highlandsmortgage.com',
            'employeeId': '999999',
            'tier': 'Plano',  # Branch location - will need to be configured
            'role': 'User',  # Will be determined by job title: 'Tier Manager' or 'User'
            'title': 'Loan Officer'
        }

        # Role mapping based on job title
        # Tier Manager: Branch Manager, Sales Manager, Regional Manager, and above
        # User: Loan Officer, Loan Officer Assistant (LOA), and others
        self.manager_titles = [
            'branch manager',
            'sales manager',
            'regional manager',
            'division manager',
            'area manager',
            'district manager',
            'vp',
            'vice president',
            'director',
            'president',
            'ceo',
            'coo',
            'cfo',
            'chief',
            'executive',
            'svp',
            'senior vice president',
            'evp',
            'managing director',
        ]

    def get_role_for_title(self, job_title: str) -> str:
        """Determine the Experience.com role based on job title

        Role options in Experience.com:
        - 'Tier Manager': For Branch Managers, Sales Managers, Regional Managers, and above
        - 'User': For Loan Officers, Loan Officer Assistants (LOA), and others
        """
        if not job_title:
            return 'User'  # Default to User

        title_lower = job_title.lower()

        # Check if title matches any manager keywords
        for manager_keyword in self.manager_titles:
            if manager_keyword in title_lower:
                return 'Tier Manager'

        # Default to User for Loan Officers, LOAs, and others
        return 'User'

    async def start_browser(self, headless: bool = False, cdp_url: str = None):
        """Start Playwright browser or connect to existing one via CDP

        Args:
            headless: Whether to run headless (only used when launching new browser)
            cdp_url: CDP endpoint URL to connect to existing browser (e.g., from Playwright MCP)
                     Example: "http://localhost:9222" or ws://localhost:9222/devtools/browser/...
        """
        print("Starting browser...")
        self.playwright = await async_playwright().start()

        if cdp_url:
            # Connect to existing browser via CDP (e.g., Playwright MCP's browser)
            print(f"Connecting to existing browser at {cdp_url}...")
            self.browser = await self.playwright.chromium.connect_over_cdp(cdp_url)
            self.owns_browser = False

            # Get existing page or create new one
            contexts = self.browser.contexts
            if contexts and contexts[0].pages:
                self.page = contexts[0].pages[0]
                print(f"Using existing page: {self.page.url}")
            else:
                context = await self.browser.new_context()
                self.page = await context.new_page()
                print("Created new page in existing browser")
        else:
            # Launch new browser
            self.browser = await self.playwright.chromium.launch(headless=headless)
            self.page = await self.browser.new_page()
            self.owns_browser = True

        print("Browser ready")

    async def login(self, login_url: str, username: str, password: str):
        """Login to Experience.com - Two-step login with CAPTCHA"""
        print(f"\n{'='*60}")
        print("STEP 1: Login to Experience.com")
        print(f"{'='*60}")

        print(f"Navigating to {login_url}")
        await self.page.goto(login_url)
        await self.page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)

        # Take screenshot of login page
        await self.page.screenshot(path='experience_01_login_page.png')
        print("Screenshot: experience_01_login_page.png")

        # STEP 1A: Enter work email
        print("\nSTEP 1A: Enter work email...")
        email_field = await self.page.query_selector('input[name="mail"]')
        if email_field:
            await email_field.fill(username)
            print(f"  Filled email: {username}")
        else:
            # Try alternate selectors
            email_selectors = [
                'input[placeholder*="email" i]',
                'input[placeholder*="phone" i]',
                'input[type="text"]',
            ]
            for selector in email_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.fill(username)
                        print(f"  Filled email with selector: {selector}")
                        break
                except:
                    continue

        await self.page.screenshot(path='experience_02_email_entered.png')
        print("Screenshot: experience_02_email_entered.png")

        # STEP 1B: Handle reCAPTCHA first
        print("\nSTEP 1B: Checking for CAPTCHA...")
        captcha_frame = await self.page.query_selector('iframe[title*="reCAPTCHA"]')
        if captcha_frame:
            print("  reCAPTCHA detected!")
            print("  *** MANUAL ACTION REQUIRED ***")
            print("  Please complete the CAPTCHA in the browser window:")
            print("    1. Click the 'I'm not a robot' checkbox")
            print("    2. Complete any image challenges if presented")
            print("  Waiting up to 120 seconds for CAPTCHA completion...")

            # Wait for user to complete CAPTCHA
            for i in range(120):
                await asyncio.sleep(1)

                # Check if password-block appeared (it shows after CAPTCHA)
                password_block = await self.page.query_selector('#password-block')
                if password_block and await password_block.is_visible():
                    print(f"  CAPTCHA completed - password option appeared after {i+1} seconds")
                    await self.page.screenshot(path='experience_02b_captcha_done.png')
                    break

                # Also check for submit button as fallback
                try:
                    continue_btn = await self.page.query_selector('button[type="submit"]')
                    if continue_btn and await continue_btn.is_visible():
                        # Check if password block also visible
                        password_block = await self.page.query_selector('#password-block')
                        if password_block:
                            print(f"  CAPTCHA completed after {i+1} seconds")
                            await self.page.screenshot(path='experience_02b_captcha_done.png')
                            break
                except:
                    pass

                if i % 10 == 9:
                    print(f"  Still waiting... ({i+1} seconds)")

        await asyncio.sleep(1)
        await self.page.screenshot(path='experience_02c_after_captcha.png')
        print("Screenshot: experience_02c_after_captcha.png")

        # STEP 1C: Click "Sign in with password" option INSTEAD of magic link
        print("\nSTEP 1C: Looking for 'Sign in with password' option...")
        password_option_selectors = [
            '#password-block',
            'div#password-block',
            'text="Or sign in with a password instead."',
            'text="sign in with a password"',
            '*:has-text("password instead")',
        ]

        password_clicked = False
        for selector in password_option_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    password_clicked = True
                    print(f"  Clicked password option with selector: {selector}")
                    await asyncio.sleep(2)
                    await self.page.screenshot(path='experience_03_password_option_clicked.png')
                    print("Screenshot: experience_03_password_option_clicked.png")
                    break
            except Exception as e:
                print(f"  Selector {selector} failed: {e}")
                continue

        if not password_clicked:
            print("  WARNING: Could not find password option - will try magic link flow")
            # Fall back to clicking submit (magic link)
            continue_selectors = [
                'button[type="submit"]',
                'button:has-text("Continue")',
            ]
            for selector in continue_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.click()
                        print(f"  Clicked submit with selector: {selector}")
                        break
                except:
                    continue

        # Wait for password page
        print("\nWaiting for password page...")
        try:
            await self.page.wait_for_load_state('networkidle', timeout=10000)
        except:
            pass
        await asyncio.sleep(3)

        await self.page.screenshot(path='experience_03_after_password_click.png')
        print("Screenshot: experience_03_after_password_click.png")

        # STEP 1D: Enter password
        print("\nSTEP 1D: Looking for password field...")

        # Check for password field
        password_field = await self.page.query_selector('input[type="password"]')
        if password_field and await password_field.is_visible():
            print("  Password field found!")
            await password_field.fill(password)
            print("  Filled password")

            await self.page.screenshot(path='experience_04_password_entered.png')
            print("Screenshot: experience_04_password_entered.png")

            # Click login/submit button
            print("\nLooking for login button...")
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
                        print(f"  Clicked login with selector: {selector}")
                        break
                except Exception as e:
                    continue

            # Wait for navigation
            try:
                await self.page.wait_for_load_state('networkidle', timeout=15000)
            except:
                pass
            await asyncio.sleep(3)

        await self.page.screenshot(path='experience_05_after_login.png')
        print("Screenshot: experience_05_after_login.png")

        # Check if we're on dashboard
        page_content = await self.page.content()
        if 'Dashboard' in page_content or 'Hierarchy' in page_content:
            print("SUCCESS: Login appears successful - found dashboard elements")
        else:
            print("WARNING: May not be logged in - check screenshots")
            current_url = self.page.url
            print(f"  Current URL: {current_url}")

            # Check for error messages
            error_selectors = ['.error', '.alert-danger', '[class*="error"]', '[class*="Error"]']
            for selector in error_selectors:
                try:
                    error = await self.page.query_selector(selector)
                    if error and await error.is_visible():
                        error_text = await error.inner_text()
                        print(f"  ERROR MESSAGE: {error_text}")
                except:
                    continue

    async def navigate_to_users(self):
        """Navigate to Hierarchy -> Users"""
        print(f"\n{'='*60}")
        print("STEP 2: Navigate to Hierarchy -> Users")
        print(f"{'='*60}")

        # Click on Hierarchy in sidebar
        print("Looking for Hierarchy menu...")
        hierarchy_selectors = [
            'text="Hierarchy"',
            '[href*="hierarchy"]',
            'a:has-text("Hierarchy")',
            'button:has-text("Hierarchy")',
            '.sidebar >> text="Hierarchy"',
        ]

        hierarchy_clicked = False
        for selector in hierarchy_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    hierarchy_clicked = True
                    print(f"  Clicked Hierarchy with selector: {selector}")
                    break
            except Exception as e:
                continue

        if not hierarchy_clicked:
            print("  WARNING: Could not find Hierarchy menu")

        await asyncio.sleep(1)
        await self.page.screenshot(path='experience_04_hierarchy_menu.png')
        print("Screenshot: experience_04_hierarchy_menu.png")

        # Click on Users tab/button
        print("\nLooking for Users option...")
        users_selectors = [
            'button:has-text("Users")',
            'text="Users"',
            '[role="tab"]:has-text("Users")',
            '.tab:has-text("Users")',
        ]

        users_clicked = False
        for selector in users_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    if element and await element.is_visible():
                        await element.click()
                        users_clicked = True
                        print(f"  Clicked Users with selector: {selector}")
                        break
                if users_clicked:
                    break
            except Exception as e:
                continue

        await asyncio.sleep(2)
        await self.page.screenshot(path='experience_05_users_page.png')
        print("Screenshot: experience_05_users_page.png")

    async def click_add_new_user(self):
        """Click Add New User button"""
        print(f"\n{'='*60}")
        print("STEP 3: Click Add New User")
        print(f"{'='*60}")

        add_user_selectors = [
            'button:has-text("Add New User")',
            'text="Add New User"',
            '[data-testid="add-user"]',
            'button:has-text("Add User")',
        ]

        add_clicked = False
        for selector in add_user_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    add_clicked = True
                    print(f"  Clicked Add New User with selector: {selector}")
                    break
            except Exception as e:
                continue

        if not add_clicked:
            print("  WARNING: Could not find Add New User button")

        await asyncio.sleep(2)
        await self.page.screenshot(path='experience_06_add_user_modal.png')
        print("Screenshot: experience_06_add_user_modal.png")

        # Click "Add Single User" option
        print("\nLooking for 'Add Single User' option...")
        single_user_selectors = [
            'text="Add Single User"',
            'label:has-text("Add Single User")',
            'input[value="single"]',
            '[data-testid="add-single-user"]',
        ]

        for selector in single_user_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    print(f"  Clicked Add Single User with selector: {selector}")
                    break
            except Exception as e:
                continue

        await asyncio.sleep(1)
        await self.page.screenshot(path='experience_07_single_user_form.png')
        print("Screenshot: experience_07_single_user_form.png")

    async def fill_user_form(self):
        """Fill in the user creation form"""
        print(f"\n{'='*60}")
        print("STEP 4: Fill User Form")
        print(f"{'='*60}")

        # Fill First Name
        print(f"\nFilling First Name: {self.test_user['firstName']}")
        first_name_selectors = [
            'input[placeholder*="First" i]',
            'input[name*="first" i]',
            'label:has-text("First Name") + input',
            'label:has-text("First Name") >> xpath=following-sibling::input',
        ]

        for selector in first_name_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.fill(self.test_user['firstName'])
                    print(f"  Filled with selector: {selector}")
                    break
            except Exception as e:
                continue

        # Fill Last Name
        print(f"\nFilling Last Name: {self.test_user['lastName']}")
        last_name_selectors = [
            'input[placeholder*="Last" i]',
            'input[name*="last" i]',
            'label:has-text("Last Name") + input',
        ]

        for selector in last_name_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.fill(self.test_user['lastName'])
                    print(f"  Filled with selector: {selector}")
                    break
            except Exception as e:
                continue

        # Fill Email
        print(f"\nFilling Email: {self.test_user['email']}")
        email_selectors = [
            'input[type="email"]',
            'input[placeholder*="email" i]',
            'input[name*="email" i]',
            'label:has-text("Email") + input',
        ]

        for selector in email_selectors:
            try:
                # Skip if it's the login form email field
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    # Check if field is empty (not the login email field)
                    value = await element.input_value()
                    if not value:
                        await element.fill(self.test_user['email'])
                        print(f"  Filled with selector: {selector}")
                        break
            except Exception as e:
                continue

        # Fill Employee ID
        print(f"\nFilling Employee ID: {self.test_user['employeeId']}")
        emp_id_selectors = [
            'input[placeholder*="Employee" i]',
            'input[name*="employee" i]',
            'label:has-text("Employee ID") + input',
        ]

        for selector in emp_id_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.fill(self.test_user['employeeId'])
                    print(f"  Filled with selector: {selector}")
                    break
            except Exception as e:
                continue

        await self.page.screenshot(path='experience_08_form_basic_info.png')
        print("Screenshot: experience_08_form_basic_info.png")

        # Handle toggle switches
        print("\nConfiguring toggle switches...")

        # Opt-in to Experience login - should be ON (blue)
        await self._set_toggle('Opt-in to Experience', True)

        # Allow Survey Completion - defaults to ON, leave it as is

        # Allow user to expire Survey - defaults to ON (blue), turn it OFF per guide
        # This toggle is in the "Allow to Expire Survey" section of the Create New User form
        print("\nTurning OFF 'Allow user to expire a survey' toggle...")
        expire_survey_turned_off = False

        # First scroll to find the "Allow to Expire Survey" section
        expire_section = await self.page.query_selector('text="Allow to Expire Survey"')
        if expire_section:
            await expire_section.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)
            print("  Found 'Allow to Expire Survey' section")

        # Look for the toggle with various selectors
        expire_toggle_selectors = [
            '//*[contains(text(), "Allow user to expire a survey")]/following::button[contains(@class, "ant-switch")][1]',
            '//*[contains(text(), "Allow user to expire")]/following::button[contains(@class, "ant-switch")][1]',
            '//*[contains(text(), "expire a survey")]/ancestor::div[1]//button[contains(@class, "ant-switch")]',
            # Also try looking within the Allow to Expire Survey section
            '//*[contains(text(), "Allow to Expire Survey")]/following::button[contains(@class, "ant-switch")][1]',
        ]

        for selector in expire_toggle_selectors:
            try:
                toggle = await self.page.query_selector(selector)
                if toggle and await toggle.is_visible():
                    is_checked = await toggle.evaluate('el => el.classList.contains("ant-switch-checked")')
                    if is_checked:
                        await toggle.click()
                        print("  Turned OFF 'Allow user to expire a survey' toggle")
                        expire_survey_turned_off = True
                    else:
                        print("  'Allow user to expire a survey' is already OFF")
                        expire_survey_turned_off = True
                    break
            except Exception as e:
                continue

        if not expire_survey_turned_off:
            print("  WARNING: Could not find 'Allow user to expire a survey' toggle in Create form")
            print("  Will configure this in Profile Settings after user creation")

        await self.page.screenshot(path='experience_09_form_toggles.png')
        print("Screenshot: experience_09_form_toggles.png")

        # Scroll down in the modal to find Tier and Role
        print("\nScrolling form to find Tier and Role...")
        try:
            # Find the modal/form container and scroll it
            modal = await self.page.query_selector('[class*="modal"], [class*="dialog"], [role="dialog"]')
            if modal:
                await modal.evaluate('el => el.scrollTop = el.scrollHeight')
            else:
                # Try scrolling the page
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        except:
            pass
        await asyncio.sleep(1)

        # Look for "Tier and Role Assignment" section
        tier_section = await self.page.query_selector('text="Tier and Role Assignment"')
        if tier_section:
            await tier_section.scroll_into_view_if_needed()
            print("  Found 'Tier and Role Assignment' section")

        await self.page.screenshot(path='experience_09b_scrolled.png')
        print("Screenshot: experience_09b_scrolled.png")

        # Select Tier (Branch Location) - Experience.com uses a combobox/searchable dropdown
        print(f"\nSelecting Tier: {self.test_user['tier']}")
        await self._select_experience_dropdown('Tier', self.test_user['tier'])

        # Select Role
        print(f"\nSelecting Role: {self.test_user['role']}")
        await self._select_experience_dropdown('Role', self.test_user['role'])

        await self.page.screenshot(path='experience_10_form_tier_role.png')
        print("Screenshot: experience_10_form_tier_role.png")

        # Click the plus button to ADD the Tier/Role assignment
        print("\nClicking plus button to add Tier/Role assignment...")
        plus_button_selectors = [
            'svg[viewBox="0 0 11 11"]',  # The plus icon SVG
            'button:has(svg[viewBox="0 0 11 11"])',
            '[class*="add"] svg',
            'button:has(path[d*="10.281"])',  # Unique path in the plus icon
            # Look for plus button near Tier and Role section
            '//*[contains(text(), "Tier and Role")]/following::button[1]',
            '//*[contains(text(), "Tier and Role")]/following::*[contains(@class, "add")][1]',
            'button[class*="add"]',
        ]

        plus_clicked = False
        for selector in plus_button_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    if element and await element.is_visible():
                        await element.click()
                        plus_clicked = True
                        print(f"  Clicked plus button with selector: {selector}")
                        break
                if plus_clicked:
                    break
            except Exception as e:
                continue

        if not plus_clicked:
            print("  WARNING: Could not find plus button - trying to find any add button near Tier/Role section")
            # Try clicking any button that might be the add button
            try:
                # Look for clickable elements near the dropdowns
                add_btn = await self.page.query_selector('button:near(:text("Tier and Role Assignment"))')
                if add_btn:
                    await add_btn.click()
                    plus_clicked = True
                    print("  Clicked nearby button")
            except:
                pass

        await asyncio.sleep(1)
        await self.page.screenshot(path='experience_10b_after_plus.png')
        print("Screenshot: experience_10b_after_plus.png")

        # Fill in Title field (required after adding Tier/Role)
        print(f"\nFilling Title: {self.test_user['title']}")
        title_selectors = [
            'input[placeholder*="Title" i]',
            'input[name*="title" i]',
            'label:has-text("Title") + input',
            'input[id*="title" i]',
        ]

        title_filled = False
        for selector in title_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.fill(self.test_user['title'])
                    title_filled = True
                    print(f"  Filled Title with selector: {selector}")
                    break
            except:
                continue

        if not title_filled:
            print("  WARNING: Could not find Title field")

        await self.page.screenshot(path='experience_10c_after_title.png')
        print("Screenshot: experience_10c_after_title.png")

    async def _set_toggle(self, label_text: str, should_be_on: bool):
        """Set a toggle switch on or off"""
        try:
            # Find toggle near the label
            toggle_selectors = [
                f'label:has-text("{label_text}") >> xpath=following-sibling::*//input[type="checkbox"]',
                f'label:has-text("{label_text}") + * input[type="checkbox"]',
                f'text="{label_text}" >> xpath=ancestor::*[1]//input[type="checkbox"]',
                f'//*[contains(text(), "{label_text}")]/following::input[@type="checkbox"][1]',
            ]

            for selector in toggle_selectors:
                try:
                    toggle = await self.page.query_selector(selector)
                    if toggle:
                        is_checked = await toggle.is_checked()
                        if is_checked != should_be_on:
                            await toggle.click()
                            print(f"  Toggled '{label_text}' to {'ON' if should_be_on else 'OFF'}")
                        else:
                            print(f"  '{label_text}' already {'ON' if should_be_on else 'OFF'}")
                        return
                except:
                    continue

            # Try clicking on toggle switch element
            switch_selectors = [
                f'//*[contains(text(), "{label_text}")]/following::*[contains(@class, "switch") or contains(@class, "toggle")][1]',
            ]

            for selector in switch_selectors:
                try:
                    switch = await self.page.query_selector(selector)
                    if switch and await switch.is_visible():
                        await switch.click()
                        print(f"  Clicked toggle switch for '{label_text}'")
                        return
                except:
                    continue

            print(f"  WARNING: Could not find toggle for '{label_text}'")
        except Exception as e:
            print(f"  ERROR setting toggle '{label_text}': {e}")

    async def _set_slider_value(self, label_text: str, target_value: float, min_val: float = 1, max_val: float = 5):
        """Set an Ant Design slider to a specific value

        Args:
            label_text: The label text near the slider (e.g., "Minimum score to reply on reviews")
            target_value: The value to set (e.g., 3 or 4.5)
            min_val: Minimum value of the slider (default 1)
            max_val: Maximum value of the slider (default 5)
        """
        try:
            print(f"  Setting slider '{label_text}' to {target_value}...")

            # Find the label element
            label = await self.page.query_selector(f'text="{label_text}"')
            if not label:
                # Try partial match
                label = await self.page.query_selector(f'*:has-text("{label_text}")')

            if label:
                await label.scroll_into_view_if_needed()
                await asyncio.sleep(0.3)

            # Find the slider - look for ant-slider near the label
            slider = None
            slider_selectors = [
                f'//*[contains(text(), "{label_text}")]/following::*[contains(@class, "ant-slider")][1]',
                f'//*[contains(text(), "{label_text}")]/ancestor::div[1]//*[contains(@class, "ant-slider")]',
                f'//*[contains(text(), "{label_text}")]/parent::*/following-sibling::*[contains(@class, "ant-slider")]',
            ]

            for selector in slider_selectors:
                try:
                    slider = await self.page.query_selector(selector)
                    if slider and await slider.is_visible():
                        break
                except:
                    continue

            if not slider:
                # Try finding any slider on page and match by proximity
                all_sliders = await self.page.query_selector_all('[class*="ant-slider"]')
                print(f"    Found {len(all_sliders)} sliders on page")
                # Use the first visible one near our label
                for s in all_sliders:
                    if await s.is_visible():
                        slider = s
                        break

            if slider:
                # Get slider dimensions
                box = await slider.bounding_box()
                if box:
                    # Calculate click position based on value
                    # Slider typically goes from left (min) to right (max)
                    percentage = (target_value - min_val) / (max_val - min_val)
                    click_x = box['x'] + (box['width'] * percentage)
                    click_y = box['y'] + (box['height'] / 2)

                    # Click at calculated position
                    await self.page.mouse.click(click_x, click_y)
                    print(f"    Clicked slider at {percentage*100:.0f}% position for value {target_value}")
                    await asyncio.sleep(0.5)

                    # Verify by checking if handle moved (optional)
                    return True
            else:
                print(f"    WARNING: Could not find slider for '{label_text}'")
                return False

        except Exception as e:
            print(f"  ERROR setting slider '{label_text}': {e}")
            return False

    async def _set_number_input(self, label_text: str, value: str):
        """Set a number input field to a specific value

        Args:
            label_text: The label text near the input (e.g., "Maximum number of posts per day")
            value: The value to set (as string)
        """
        try:
            print(f"  Setting input '{label_text}' to {value}...")

            # Find input near the label
            input_selectors = [
                f'//*[contains(text(), "{label_text}")]/following::input[1]',
                f'//*[contains(text(), "{label_text}")]/ancestor::div[1]//input',
                f'//*[contains(text(), "{label_text}")]/parent::*/following-sibling::*//input',
            ]

            input_field = None
            for selector in input_selectors:
                try:
                    input_field = await self.page.query_selector(selector)
                    if input_field and await input_field.is_visible():
                        break
                except:
                    continue

            if input_field:
                # Clear and fill
                await input_field.click()
                await input_field.fill('')
                await input_field.fill(value)
                print(f"    Set input to {value}")
                return True
            else:
                print(f"    WARNING: Could not find input for '{label_text}'")
                return False

        except Exception as e:
            print(f"  ERROR setting input '{label_text}': {e}")
            return False

    async def _verify_toggle_on(self, label_text: str) -> bool:
        """Verify a toggle is ON, turn it ON if not

        Returns True if toggle is/was set to ON successfully
        """
        try:
            print(f"  Verifying toggle '{label_text}' is ON...")

            # Find the toggle switch near the label
            switch_selectors = [
                f'//*[contains(text(), "{label_text}")]/following::button[contains(@class, "ant-switch")][1]',
                f'//*[contains(text(), "{label_text}")]/ancestor::div[1]//button[contains(@class, "ant-switch")]',
                f'//*[contains(text(), "{label_text}")]/parent::*/following-sibling::*//button[contains(@class, "ant-switch")]',
            ]

            switch = None
            for selector in switch_selectors:
                try:
                    switch = await self.page.query_selector(selector)
                    if switch and await switch.is_visible():
                        break
                except:
                    continue

            if switch:
                is_checked = await switch.evaluate('el => el.classList.contains("ant-switch-checked")')
                if is_checked:
                    print(f"    Toggle is ON (correct)")
                    return True
                else:
                    await switch.click()
                    print(f"    Toggle was OFF - clicked to turn ON")
                    await asyncio.sleep(0.3)
                    return True
            else:
                print(f"    WARNING: Could not find toggle for '{label_text}'")
                return False

        except Exception as e:
            print(f"  ERROR verifying toggle '{label_text}': {e}")
            return False

    async def _set_toggle_off(self, label_text: str) -> bool:
        """Set a toggle to OFF

        Returns True if toggle is/was set to OFF successfully
        """
        try:
            print(f"  Setting toggle '{label_text}' to OFF...")

            # Find the toggle switch near the label
            switch_selectors = [
                f'//*[contains(text(), "{label_text}")]/following::button[contains(@class, "ant-switch")][1]',
                f'//*[contains(text(), "{label_text}")]/ancestor::div[1]//button[contains(@class, "ant-switch")]',
                f'//*[contains(text(), "{label_text}")]/parent::*/following-sibling::*//button[contains(@class, "ant-switch")]',
            ]

            switch = None
            for selector in switch_selectors:
                try:
                    switch = await self.page.query_selector(selector)
                    if switch and await switch.is_visible():
                        break
                except:
                    continue

            if switch:
                is_checked = await switch.evaluate('el => el.classList.contains("ant-switch-checked")')
                if not is_checked:
                    print(f"    Toggle is already OFF (correct)")
                    return True
                else:
                    await switch.click()
                    print(f"    Toggle was ON - clicked to turn OFF")
                    await asyncio.sleep(0.3)
                    return True
            else:
                print(f"    WARNING: Could not find toggle for '{label_text}'")
                return False

        except Exception as e:
            print(f"  ERROR setting toggle '{label_text}' to OFF: {e}")
            return False

    async def _select_dropdown(self, label_text: str, value: str):
        """Select a value from a dropdown"""
        try:
            # Find dropdown near label
            dropdown_selectors = [
                f'label:has-text("{label_text}") + select',
                f'label:has-text("{label_text}") >> xpath=following-sibling::select',
                f'text="{label_text}" >> xpath=following::select[1]',
                f'//*[contains(text(), "{label_text}")]/following::select[1]',
            ]

            for selector in dropdown_selectors:
                try:
                    dropdown = await self.page.query_selector(selector)
                    if dropdown and await dropdown.is_visible():
                        await dropdown.select_option(label=value)
                        print(f"  Selected '{value}' in '{label_text}' dropdown")
                        return
                except:
                    continue

            # Try clicking to open dropdown and then selecting
            click_selectors = [
                f'//*[contains(text(), "{label_text}")]/following::*[contains(@class, "select") or contains(@class, "dropdown")][1]',
            ]

            for selector in click_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.click()
                        await asyncio.sleep(0.5)
                        # Try to click the option
                        option = await self.page.query_selector(f'text="{value}"')
                        if option and await option.is_visible():
                            await option.click()
                            print(f"  Selected '{value}' via click")
                            return
                except:
                    continue

            print(f"  WARNING: Could not select '{value}' in '{label_text}' dropdown")
        except Exception as e:
            print(f"  ERROR selecting dropdown '{label_text}': {e}")

    async def _select_experience_dropdown(self, label_text: str, value: str):
        """Select a value from Experience.com's Ant Design dropdown"""
        try:
            print(f"  Looking for {label_text} dropdown...")

            # Experience.com uses Ant Design select components
            # The input IDs are 'selectTier' and 'selectRole'
            input_id_map = {
                'Tier': 'selectTier',
                'Role': 'selectRole',
            }
            input_id = input_id_map.get(label_text)

            dropdown_clicked = False

            # Approach 1: Click directly on the input by ID
            if input_id:
                try:
                    input_el = await self.page.query_selector(f'#{input_id}')
                    if input_el:
                        await input_el.click()
                        dropdown_clicked = True
                        print(f"    Clicked input #{input_id}")
                except Exception as e:
                    print(f"    Input click failed: {e}")

            # Approach 2: Click on the ant-select-selection-item (already selected value)
            if not dropdown_clicked:
                # The dropdown may already have a value selected
                # Look for the selection item span with ant-select-selection-item class
                selection_selectors = [
                    'span.ant-select-selection-item',
                    '[class*="ant-select-selection-item"]',
                    'span.ant-tooltip-open',  # Tier dropdown shows this class
                ]

                for selector in selection_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        for el in elements:
                            if el and await el.is_visible():
                                await el.click()
                                dropdown_clicked = True
                                el_text = await el.inner_text()
                                print(f"    Clicked selection item: '{el_text}'")
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
                placeholder = placeholder_map.get(label_text, f'Select {label_text}')

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
                            print(f"    Clicked dropdown with selector: {selector}")
                            break
                    except:
                        continue

            if not dropdown_clicked:
                print(f"    Could not find dropdown for '{label_text}'")
                await self.page.screenshot(path=f'experience_dropdown_{label_text.lower()}_not_found.png')
                return

            await asyncio.sleep(0.5)

            # Clear any existing text and type to filter the options
            print(f"    Typing '{value}' to filter options...")
            # Select all and delete first to clear any existing filter
            await self.page.keyboard.press('Control+a')
            await self.page.keyboard.press('Backspace')
            await self.page.keyboard.type(value, delay=50)
            await asyncio.sleep(1)

            await self.page.screenshot(path=f'experience_dropdown_{label_text.lower()}_filtered.png')

            # Try to click matching option from Ant Design dropdown
            option_selectors = [
                f'[class*="ant-select-item"]:has-text("{value}")',
                f'[class*="ant-select-item-option"]:has-text("{value}")',
                f'div[role="option"]:has-text("{value}")',
                f'[class*="option"]:has-text("{value}")',
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
                                print(f"    Selected: '{opt_text}'")
                                option_found = True
                                await asyncio.sleep(0.5)
                                break
                    if option_found:
                        break
                except:
                    continue

            if not option_found:
                # Fallback: press Enter to select first filtered result
                print(f"    Pressing Enter to select first match...")
                await self.page.keyboard.press('Enter')
                await asyncio.sleep(0.5)

        except Exception as e:
            print(f"  ERROR with dropdown '{label_text}': {e}")

    async def create_user(self, actually_create: bool = False):
        """Click Create User button"""
        print(f"\n{'='*60}")
        print("STEP 5: Create User")
        print(f"{'='*60}")

        # Scroll to bottom of form to find Create User button
        await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(1)

        create_selectors = [
            'button:has-text("Create User")',
            'text="Create User"',
            '[data-testid="create-user"]',
            'button[type="submit"]:has-text("Create")',
        ]

        create_clicked = False
        for selector in create_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    print(f"  FOUND Create User button with selector: {selector}")
                    if actually_create:
                        await element.click()
                        print("  Clicked Create User button!")
                        create_clicked = True
                    else:
                        print("  ** NOT CLICKING - Test mode **")
                        create_clicked = True
                    break
            except Exception as e:
                continue

        if not create_clicked:
            print("  WARNING: Could not find Create User button")

        await self.page.screenshot(path='experience_11_create_user_button.png')
        print("Screenshot: experience_11_create_user_button.png")

        if actually_create and create_clicked:
            await asyncio.sleep(2)
            await self.page.screenshot(path='experience_12_after_create_click.png')
            print("Screenshot: experience_12_after_create_click.png")

            # Look for confirmation dialog/button
            print("\nLooking for Confirm button...")
            confirm_selectors = [
                'button:has-text("Confirm")',
                'button:has-text("Yes")',
                'button:has-text("OK")',
                '[class*="confirm"]:has-text("Confirm")',
            ]

            for selector in confirm_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.click()
                        print(f"  Clicked Confirm with selector: {selector}")
                        break
                except:
                    continue

            await asyncio.sleep(3)
            await self.page.screenshot(path='experience_13_after_confirm.png')
            print("Screenshot: experience_13_after_confirm.png")

            # Check for success message or errors
            page_content = await self.page.content()
            if 'success' in page_content.lower() or 'created' in page_content.lower():
                print("\nSUCCESS: User appears to have been created!")
            elif 'error' in page_content.lower() or 'failed' in page_content.lower():
                print("\nWARNING: There may have been an error - check screenshots")
            else:
                print("\nUser creation completed - check screenshots for result")

    async def analyze_page_structure(self):
        """Analyze the current page structure for debugging"""
        print(f"\n{'='*60}")
        print("PAGE ANALYSIS")
        print(f"{'='*60}")

        # Get current URL
        url = self.page.url
        print(f"\nCurrent URL: {url}")

        # Get page title
        title = await self.page.title()
        print(f"Page Title: {title}")

        # Find all buttons
        print("\n--- Buttons on page ---")
        buttons = await self.page.query_selector_all('button')
        for btn in buttons[:20]:  # Limit to first 20
            try:
                text = await btn.inner_text()
                visible = await btn.is_visible()
                if visible and text.strip():
                    print(f"  Button: '{text.strip()[:50]}'")
            except:
                continue

        # Find all inputs
        print("\n--- Input fields on page ---")
        inputs = await self.page.query_selector_all('input')
        for inp in inputs[:20]:
            try:
                inp_type = await inp.get_attribute('type') or 'text'
                name = await inp.get_attribute('name') or ''
                placeholder = await inp.get_attribute('placeholder') or ''
                visible = await inp.is_visible()
                if visible:
                    print(f"  Input: type='{inp_type}', name='{name}', placeholder='{placeholder}'")
            except:
                continue

        # Find sidebar/menu items
        print("\n--- Menu/Navigation items ---")
        nav_items = await self.page.query_selector_all('nav a, .sidebar a, [role="navigation"] a')
        for item in nav_items[:15]:
            try:
                text = await item.inner_text()
                visible = await item.is_visible()
                if visible and text.strip():
                    print(f"  Nav: '{text.strip()}'")
            except:
                continue

    async def cleanup(self):
        """Clean up browser resources"""
        print("\nCleaning up...")
        if self.owns_browser:
            # Only close browser if we launched it
            if self.browser:
                await self.browser.close()
            print("Browser closed")
        else:
            # We connected to existing browser - just disconnect, don't close
            print("Disconnected from browser (leaving it open)")
        if self.playwright:
            await self.playwright.stop()

    async def configure_existing_user(self, search_name: str):
        """Find and configure an existing user's settings"""
        print(f"\n{'='*60}")
        print("STEP 6: Configure Existing User Settings")
        print(f"{'='*60}")

        # Navigate to Hierarchy -> Users
        print("\nNavigating to Hierarchy -> Users...")
        hierarchy_el = await self.page.query_selector('text="Hierarchy"')
        if hierarchy_el:
            await hierarchy_el.click()
            await asyncio.sleep(1)

        users_el = await self.page.query_selector('button:has-text("Users")')
        if users_el:
            await users_el.click()
            await asyncio.sleep(2)

        await self.page.screenshot(path='experience_14_users_list.png')
        print("Screenshot: experience_14_users_list.png")

        # Search for the user
        print(f"\nSearching for user: {search_name}")
        search_box = await self.page.query_selector('input[placeholder="Search"]')
        if search_box:
            await search_box.fill(search_name)
            await asyncio.sleep(2)
            await self.page.screenshot(path='experience_15_user_search.png')
            print("Screenshot: experience_15_user_search.png")

        # Find the user row and click the three dots menu (Actions)
        print("\nLooking for user in results and clicking three dots menu...")
        await asyncio.sleep(1)

        # According to PDF, click on "three dots" in Actions column
        # The three dots icon is typically a vertical ellipsis
        three_dots_selectors = [
            'button:has(svg path[d*="M12"])',  # Typical three dots SVG
            '[class*="ellipsis"]',
            '[class*="more-vert"]',
            '[class*="kebab"]',
            '[class*="dots"]',
            'button[class*="action"]',
            # Look for buttons in the Actions column area
            'td:last-child button',
            '[class*="actions"] button',
        ]

        three_dots_clicked = False
        for selector in three_dots_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for el in elements:
                    if el and await el.is_visible():
                        await el.click()
                        three_dots_clicked = True
                        print(f"  Clicked three dots with selector: {selector}")
                        break
                if three_dots_clicked:
                    break
            except:
                continue

        await asyncio.sleep(1)
        await self.page.screenshot(path='experience_16_action_menu.png')
        print("Screenshot: experience_16_action_menu.png")

        # Click "Edit" from the dropdown menu
        # According to PDF page 11, the menu shows: Edit, View Profile, Move User, Deactivate, Unpublish Profile
        print("\nLooking for Edit option in menu...")
        await asyncio.sleep(1)  # Wait for menu to fully appear

        # Take screenshot of menu
        await self.page.screenshot(path='experience_16b_menu_visible.png')
        print("Screenshot: experience_16b_menu_visible.png")

        edit_selectors = [
            'text="Edit"',
            'div:has-text("Edit"):not(:has-text("Edit Test"))',  # Avoid matching "Edit Test User"
            '[role="menuitem"]:has-text("Edit")',
            'li:has-text("Edit")',
            'a:has-text("Edit")',
            'span:text-is("Edit")',
        ]

        edit_clicked = False
        for selector in edit_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for edit_option in elements:
                    if edit_option and await edit_option.is_visible():
                        text = await edit_option.inner_text()
                        # Make sure it's just "Edit" not "Edit User" header
                        if text.strip() == "Edit":
                            await edit_option.click()
                            edit_clicked = True
                            print(f"  Clicked Edit with selector: {selector}")
                            break
                if edit_clicked:
                    break
            except Exception as e:
                print(f"  Selector {selector} error: {e}")
                continue

        if not edit_clicked:
            print("  WARNING: Could not find Edit in menu - looking for gear icon in row")
            # The gear icon is in the Actions column - try clicking it directly
            gear_selectors = [
                'svg[viewBox*="20"]',  # Common gear icon viewBox
                '[class*="setting"]',
                '[class*="gear"]',
                '[class*="cog"]',
            ]
            for selector in gear_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for gear in elements:
                        if gear and await gear.is_visible():
                            await gear.click()
                            edit_clicked = True
                            print(f"  Clicked gear icon with selector: {selector}")
                            break
                    if edit_clicked:
                        break
                except:
                    continue

        await asyncio.sleep(2)
        await self.page.screenshot(path='experience_17_edit_user.png')
        print("Screenshot: experience_17_edit_user.png")

        # Now we need to go to Profile Settings tab (not Profile Info)
        print("\nLooking for Profile Settings tab...")
        profile_settings_selectors = [
            'text="Profile Settings"',
            '[role="tab"]:has-text("Profile Settings")',
            'button:has-text("Profile Settings")',
            'a:has-text("Profile Settings")',
        ]

        for selector in profile_settings_selectors:
            try:
                tab = await self.page.query_selector(selector)
                if tab and await tab.is_visible():
                    await tab.click()
                    print(f"  Clicked Profile Settings tab with selector: {selector}")
                    await asyncio.sleep(2)
                    break
            except:
                continue

        await self.page.screenshot(path='experience_18_profile_settings.png')
        print("Screenshot: experience_18_profile_settings.png")

        # Configure the settings according to the PDF guide
        await self._configure_profile_settings()

    async def _configure_profile_settings(self):
        """Configure the profile settings according to the PDF guide

        The User Settings drawer has these collapsible sections (ALREADY EXPANDED when opened):
        - Login Settings
        - Listings Settings
        - Review Management Settings
        - Social Share Settings
        - Allow to Expire Survey
        - Send Settings
        - Campaigns Access

        Settings to configure per PDF guide:

        REVIEW MANAGEMENT SETTINGS:
        - Allow user to reply to reviews: ON (verify)
        - Minimum score to reply on reviews: SET TO 3 (can default to 2.5 or 4)
        - Allow user to reply using AI: ON (verify)

        SOCIAL SHARE SETTINGS (CONFIRM ALL):
        - Allow Autopost: ON
        - Minimum Score to Auto-post on Social networks: 4.5
        - Maximum number of posts per day: 3
        - Minimum gap between posts: 2 hours 0 minutes

        ALLOW TO EXPIRE SURVEY:
        - Allow user to expire a survey: OFF (typically defaults to ON)

        SEND SETTINGS:
        - Allow survey completion notification: ON (verify)

        IMPORTANT: Sections are ALREADY EXPANDED - do NOT click section headers!
        """
        print("\n--- Configuring Profile Settings (Per User Guide) ---")
        print("  IMPORTANT: Sections are already expanded - NOT clicking headers")

        # Get reference to drawer for scrolling
        drawer = await self.page.query_selector('[class*="ant-drawer-body"]')

        # First scroll to TOP of drawer to see all sections from beginning
        if drawer:
            await drawer.evaluate('el => el.scrollTop = 0')
            await asyncio.sleep(0.5)

        await self.page.screenshot(path='experience_19_drawer_top.png')
        print("Screenshot: experience_19_drawer_top.png")

        # ============================================================
        # SECTION 1: REVIEW MANAGEMENT SETTINGS
        # ============================================================
        print("\n" + "="*50)
        print("SECTION 1: Review Management Settings")
        print("="*50)

        # Scroll to find Review Management Settings section
        review_mgmt_label = await self.page.query_selector('text="Review Management Settings"')
        if review_mgmt_label:
            await review_mgmt_label.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            print("  Found Review Management Settings section")

        # 1a. Verify "Allow user to reply to reviews" is ON
        await self._verify_toggle_on("Allow user to reply to reviews")

        # 1b. Set "Minimum score to reply on reviews" to 3
        # The slider goes from 1 to 5, we need to set it to 3
        await self._set_slider_value("Minimum score to reply on reviews", 3.0, min_val=1, max_val=5)

        # 1c. Verify "Allow user to reply using AI" is ON
        await self._verify_toggle_on("Allow user to reply using AI")

        await self.page.screenshot(path='experience_19a_review_mgmt_configured.png')
        print("Screenshot: experience_19a_review_mgmt_configured.png")

        # ============================================================
        # SECTION 2: SOCIAL SHARE SETTINGS
        # ============================================================
        print("\n" + "="*50)
        print("SECTION 2: Social Share Settings (CONFIRM ALL)")
        print("="*50)

        # Scroll to find Social Share Settings section
        social_share_label = await self.page.query_selector('text="Social Share Settings"')
        if social_share_label:
            await social_share_label.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            print("  Found Social Share Settings section")

        # 2a. Verify "Allow autopost" is ON (note: lowercase 'a' in autopost)
        await self._verify_toggle_on("Allow autopost")

        # 2b. Set "Minimum Score to Auto-post on Social networks" to 4.5
        # The slider goes from 1 to 5, we need 4.5
        await self._set_slider_value("Minimum Score to Auto-post", 4.5, min_val=1, max_val=5)

        # 2c. Verify "Maximum number of posts per day" is 3
        await self._set_number_input("Maximum number of posts per day", "3")

        # 2d. Verify "Minimum gap between posts" is 2 hours 0 minutes
        # This has two inputs: Hours and Minutes
        print("  Setting minimum gap between posts to 2 hours 0 minutes...")

        # Find the hours input
        gap_label = await self.page.query_selector('text="Minimum gap between"')
        if gap_label:
            await gap_label.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)

        # Look for inputs near "Minimum gap between posts"
        hours_input_selectors = [
            '//*[contains(text(), "Minimum gap between")]/following::input[1]',
            '//*[contains(text(), "gap between posts")]/following::input[1]',
        ]

        hours_set = False
        for selector in hours_input_selectors:
            try:
                hours_input = await self.page.query_selector(selector)
                if hours_input and await hours_input.is_visible():
                    await hours_input.click()
                    await hours_input.fill('')
                    await hours_input.fill('2')
                    print("    Set Hours to 2")
                    hours_set = True
                    break
            except:
                continue

        # Minutes input is typically the second input in the same row
        mins_input_selectors = [
            '//*[contains(text(), "Minimum gap between")]/following::input[2]',
            '//*[contains(text(), "gap between posts")]/following::input[2]',
        ]

        mins_set = False
        for selector in mins_input_selectors:
            try:
                mins_input = await self.page.query_selector(selector)
                if mins_input and await mins_input.is_visible():
                    await mins_input.click()
                    await mins_input.fill('')
                    await mins_input.fill('0')
                    print("    Set Minutes to 0")
                    mins_set = True
                    break
            except:
                continue

        if not hours_set or not mins_set:
            print("    WARNING: Could not set gap between posts inputs")

        await self.page.screenshot(path='experience_19b_social_share_configured.png')
        print("Screenshot: experience_19b_social_share_configured.png")

        # ============================================================
        # SECTION 3: ALLOW TO EXPIRE SURVEY
        # ============================================================
        print("\n" + "="*50)
        print("SECTION 3: Allow to Expire Survey")
        print("="*50)

        # Scroll to the Allow to Expire Survey section
        expire_section = await self.page.query_selector('text="Allow to Expire Survey"')
        if expire_section:
            await expire_section.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)
            print("  Found 'Allow to Expire Survey' section")

        # 3a. Set "Allow user to expire a survey" to OFF
        await self._set_toggle_off("Allow user to expire a survey")

        await self.page.screenshot(path='experience_20_expire_survey_configured.png')
        print("Screenshot: experience_20_expire_survey_configured.png")

        # ============================================================
        # SECTION 4: SEND SETTINGS
        # ============================================================
        print("\n" + "="*50)
        print("SECTION 4: Send Settings")
        print("="*50)

        # Scroll to the Send Settings section
        send_settings_label = await self.page.query_selector('text="Send Settings"')
        if send_settings_label:
            await send_settings_label.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)
            print("  Found 'Send Settings' section")

        # 4a. Verify "Allow survey completion notification" is ON
        await self._verify_toggle_on("Allow survey completion notification")

        # 4b. Verify "Allow reply to reviews notification" is ON (if present)
        await self._verify_toggle_on("Allow reply to reviews notification")

        await self.page.screenshot(path='experience_21_send_settings_configured.png')
        print("Screenshot: experience_21_send_settings_configured.png")

        # ============================================================
        # SAVE CHANGES
        # ============================================================
        print("\n" + "="*50)
        print("SAVING CHANGES")
        print("="*50)

        # List all switches on page for debugging/verification
        all_switches = await self.page.query_selector_all('button[class*="ant-switch"]')
        print(f"  Total switches found: {len(all_switches)}")

        # Scroll to bottom to find Update button
        if drawer:
            await drawer.evaluate('el => el.scrollTop = el.scrollHeight')
            await asyncio.sleep(0.5)

        await self.page.screenshot(path='experience_22_before_update.png')
        print("Screenshot: experience_22_before_update.png")

        # Click Update button to save changes
        print("\nClicking Update button...")
        update_btn = await self.page.query_selector('button:has-text("Update")')
        if update_btn and await update_btn.is_visible():
            await update_btn.click()
            print("  Clicked Update button")
            await asyncio.sleep(2)

            await self.page.screenshot(path='experience_23_confirm_popup.png')
            print("Screenshot: experience_23_confirm_popup.png")

            # Click Confirm in the popup
            print("\nClicking Confirm button...")
            confirm_btn = await self.page.query_selector('button:has-text("Confirm")')
            if confirm_btn and await confirm_btn.is_visible():
                await confirm_btn.click()
                print("  Clicked Confirm button")
                await asyncio.sleep(2)
            else:
                # Try modal-specific selectors
                confirm_selectors = [
                    '[class*="ant-modal"] button:has-text("Confirm")',
                    '[class*="modal"] button:has-text("Confirm")',
                    'button[class*="ant-btn-primary"]:has-text("Confirm")',
                ]
                for sel in confirm_selectors:
                    try:
                        btn = await self.page.query_selector(sel)
                        if btn and await btn.is_visible():
                            await btn.click()
                            print(f"  Clicked Confirm with: {sel}")
                            await asyncio.sleep(2)
                            break
                    except:
                        continue
        else:
            print("  WARNING: Update button not found")

        await self.page.screenshot(path='experience_24_after_confirm.png')
        print("Screenshot: experience_24_after_confirm.png")

        # Wait for any animations/modals to close
        await asyncio.sleep(2)

        # Press Escape to close drawer if still open
        await self.page.keyboard.press('Escape')
        await asyncio.sleep(1)

        print("\n" + "="*50)
        print("PROFILE SETTINGS CONFIGURATION COMPLETE")
        print("="*50)

    async def publish_user(self, search_name: str):
        """Publish the user's profile"""
        print(f"\n{'='*60}")
        print("STEP 7: Publish User Profile")
        print(f"{'='*60}")

        # Navigate to Users list if not already there
        hierarchy_el = await self.page.query_selector('text="Hierarchy"')
        if hierarchy_el and await hierarchy_el.is_visible():
            await hierarchy_el.click()
            await asyncio.sleep(1)

        users_el = await self.page.query_selector('button:has-text("Users")')
        if users_el and await users_el.is_visible():
            await users_el.click()
            await asyncio.sleep(2)

        # Search for user
        search_box = await self.page.query_selector('input[placeholder="Search"]')
        if search_box:
            await search_box.fill('')
            await search_box.fill(search_name)
            await asyncio.sleep(2)

        await self.page.screenshot(path='experience_23_publish_search.png')
        print("Screenshot: experience_23_publish_search.png")

        # Check the checkbox next to the user
        print("\nLooking for user checkbox...")
        checkbox = await self.page.query_selector('input[type="checkbox"]:not([disabled])')
        if checkbox and await checkbox.is_visible():
            is_checked = await checkbox.is_checked()
            if not is_checked:
                await checkbox.click()
                print("  Checked user checkbox")

        await asyncio.sleep(1)

        # Look for Published toggle (should show "No" - click to change to "Yes")
        print("\nLooking for Published toggle...")
        published_toggle = await self.page.query_selector('text="No" >> xpath=ancestor::*[contains(@class, "published") or contains(@class, "toggle")][1]')
        if not published_toggle:
            # Try finding by the Published column
            published_no = await self.page.query_selector('[class*="published"] >> text="No"')
            if published_no:
                await published_no.click()
                print("  Clicked 'No' under Published to toggle")

        await asyncio.sleep(2)
        await self.page.screenshot(path='experience_24_publish_toggle.png')
        print("Screenshot: experience_24_publish_toggle.png")

        # Confirm publish popup
        confirm_btn = await self.page.query_selector('button:has-text("Confirm")')
        if confirm_btn and await confirm_btn.is_visible():
            await confirm_btn.click()
            print("  Clicked Confirm to publish")
            await asyncio.sleep(2)

        await self.page.screenshot(path='experience_25_published.png')
        print("Screenshot: experience_25_published.png")


async def main():
    """Main test function

    Usage:
        python test_experience.py                    # Launch own browser
        python test_experience.py --cdp URL          # Connect to existing browser via CDP
        python test_experience.py --cdp http://localhost:9222
    """
    import argparse
    parser = argparse.ArgumentParser(description='Experience.com automation test')
    parser.add_argument('--cdp', type=str, help='CDP URL to connect to existing browser (e.g., http://localhost:9222)')
    args = parser.parse_args()

    print("="*60)
    print("EXPERIENCE.COM AUTOMATION TEST")
    print("="*60)
    if args.cdp:
        print(f"\nConnecting to existing browser at: {args.cdp}")
    print("\nThis test script will:")
    print("1. Login to Experience.com")
    print("2. Navigate to Hierarchy -> Users")
    print("3. Search for existing test user")
    print("4. Configure Profile Settings")
    print("5. Publish the user profile")
    print("="*60)

    # For testing, we need credentials
    # In production, these come from Azure Key Vault
    print("\n** CREDENTIALS REQUIRED **")
    print("You need to set these Azure Key Vault secrets:")
    print("  - experience-login-url")
    print("  - experience-admin-email")
    print("  - experience-admin-password")
    print()

    # For manual testing, you can hardcode credentials here temporarily
    # Or fetch from Key Vault
    LOGIN_URL = "https://app.experience.com/user/signin"
    ADMIN_EMAIL = ""  # Set this for testing
    ADMIN_PASSWORD = ""  # Set this for testing

    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        print("ERROR: Please set ADMIN_EMAIL and ADMIN_PASSWORD in the script for testing")
        print("       Or integrate with KeyVaultService")

        # Try to get from Key Vault
        try:
            from services.keyvault_service import get_keyvault_service
            keyvault = get_keyvault_service()
            LOGIN_URL = keyvault.get_vendor_credential('experience', 'login-url') or LOGIN_URL
            ADMIN_EMAIL = keyvault.get_vendor_credential('experience', 'admin-email')
            ADMIN_PASSWORD = keyvault.get_vendor_credential('experience', 'admin-password')
            print("\nLoaded credentials from Azure Key Vault")
        except Exception as e:
            print(f"\nCould not load from Key Vault: {e}")
            print("Please set credentials manually in the script for testing")
            return

    # Test user that was already created
    TEST_USER_NAME = "Test User"
    TEST_USER_EMAIL = "noemail@highlandsmortgage.com"

    automation = ExperienceTestAutomation()

    try:
        await automation.start_browser(headless=False, cdp_url=args.cdp)
        await automation.login(LOGIN_URL, ADMIN_EMAIL, ADMIN_PASSWORD)

        # Skip user creation - go directly to configuring existing user
        print("\n" + "="*60)
        print(f"CONFIGURING EXISTING USER: {TEST_USER_NAME}")
        print(f"Email: {TEST_USER_EMAIL}")
        print("="*60)

        # Configure the existing user's profile settings
        await automation.configure_existing_user(TEST_USER_NAME)

        # Publish the user profile
        await automation.publish_user(TEST_USER_NAME)

        print("\n" + "="*60)
        print("TEST COMPLETE")
        print("="*60)
        print("\nReview the screenshots to see what happened:")
        print("  - experience_14_users_list.png")
        print("  - experience_15_user_search.png")
        print("  - experience_16_action_menu.png")
        print("  - experience_17_edit_user.png")
        print("  - experience_18_profile_settings.png")
        print("  - experience_19_drawer_top.png")
        print("  - experience_19a_review_section.png")
        print("  - experience_20_settings_configured.png")
        print("  - experience_21_confirm_popup.png")
        print("  - experience_22_after_confirm.png")
        print("  - experience_23_publish_search.png")
        print("  - experience_24_publish_toggle.png")
        print("  - experience_25_published.png")

        # Keep browser open for inspection
        print("\nBrowser will stay open for 30 seconds for inspection...")
        await asyncio.sleep(30)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

        # Take error screenshot
        try:
            await automation.page.screenshot(path='experience_error.png')
            print("Error screenshot saved: experience_error.png")
        except:
            pass

        # Keep browser open for inspection on error
        print("\nBrowser will stay open for 60 seconds for inspection...")
        await asyncio.sleep(60)

    finally:
        await automation.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
