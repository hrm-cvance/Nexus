"""
Experience.com User Provisioning Automation

This module automates the creation and configuration of user accounts in
Experience.com using Playwright for web automation.

Workflow:
1. Login to Experience.com
2. Navigate to Hierarchy -> Users
3. Add new user or configure existing user
4. Configure Profile Settings (Review Management, Social Share, etc.)
5. Publish user profile
6. Capture Widget Code (for Bigfish)
7. Capture Profile URL (for Total Expert)
8. Fill Profile Info fields (Title, Contact, NMLS)
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional

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

    def _load_config(self) -> Dict[str, Any]:
        """Load vendor configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded config from {self.config_path}")
        return config

    async def provision_user(self, user: EntraUser, headless: bool = False) -> Dict[str, Any]:
        """
        Provision an Experience.com account for the given user

        Args:
            user: EntraUser object with user details
            headless: Whether to run browser in headless mode

        Returns:
            Dict with success status, messages, widget_code, profile_url
        """
        self.current_user = user
        logger.info(f"Starting Experience.com automation for {user.display_name}")

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

            # Navigate to Users and configure
            await self._navigate_to_users()
            result['messages'].append("Navigated to Users")

            # Configure user profile settings
            await self._configure_profile_settings(user)
            result['messages'].append("Configured profile settings")

            # Publish user profile
            await self._publish_user(user)
            result['messages'].append("Published user profile")

            # Capture widget code
            widget_code = await self._get_widget_code(user.display_name)
            if widget_code:
                result['widget_code'] = widget_code
                result['messages'].append("Captured widget code")
            else:
                result['warnings'].append("Could not capture widget code")

            # Capture profile URL
            profile_url = await self._get_profile_url(user.display_name)
            if profile_url:
                result['profile_url'] = profile_url
                result['messages'].append(f"Captured profile URL: {profile_url}")
            else:
                result['warnings'].append("Could not capture profile URL")

            # Fill profile info from Azure data
            await self._fill_profile_info(user)
            result['messages'].append("Filled profile info fields")

            result['success'] = True
            logger.info(f"Successfully provisioned Experience.com account for {user.display_name}")

        except Exception as e:
            error_msg = f"Error during Experience.com automation: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            result['success'] = False

            # Take error screenshot
            try:
                if self.page:
                    await self.page.screenshot(path=f'experience_error_{user.display_name.replace(" ", "_")}.png')
            except:
                pass

        finally:
            await self._cleanup()

        return result

    async def _start_browser(self, headless: bool = False):
        """Start Playwright browser"""
        logger.info("Starting browser...")
        self.playwright = await async_playwright().start()

        # Grant clipboard permissions
        self.browser = await self.playwright.chromium.launch(headless=headless)
        context = await self.browser.new_context(
            permissions=['clipboard-read', 'clipboard-write']
        )
        self.page = await context.new_page()
        logger.info("Browser started")

    async def _login(self):
        """Login to Experience.com"""
        login_url = self.keyvault.get_vendor_credential('experience', 'login-url')
        admin_email = self.keyvault.get_vendor_credential('experience', 'admin-email')
        admin_password = self.keyvault.get_vendor_credential('experience', 'admin-password')

        logger.info(f"Navigating to {login_url}")
        await self.page.goto(login_url)
        await self.page.wait_for_load_state('networkidle')

        # Enter email
        email_input = await self.page.query_selector('input[placeholder="Work email"]')
        if email_input:
            await email_input.fill(admin_email)
            await asyncio.sleep(1)

        # Check for CAPTCHA
        captcha = await self.page.query_selector('iframe[title*="reCAPTCHA"]')
        if captcha:
            logger.info("CAPTCHA detected - waiting for manual completion")
            print("*** MANUAL ACTION REQUIRED: Please complete the CAPTCHA ***")

            # Wait for CAPTCHA completion (password option appears)
            for _ in range(120):
                password_option = await self.page.query_selector('#password-block')
                if password_option and await password_option.is_visible():
                    break
                await asyncio.sleep(1)

        # Click "Sign in with password" option
        password_option = await self.page.query_selector('#password-block')
        if password_option and await password_option.is_visible():
            await password_option.click()
            await asyncio.sleep(2)

        # Enter password
        password_input = await self.page.query_selector('input[type="password"]')
        if password_input:
            await password_input.fill(admin_password)
            await asyncio.sleep(1)

        # Click login button
        login_btn = await self.page.query_selector('button[type="submit"]')
        if login_btn:
            await login_btn.click()
            await asyncio.sleep(3)

        logger.info("Login completed")

    async def _navigate_to_users(self):
        """Navigate to Hierarchy -> Users"""
        logger.info("Navigating to Users...")

        hierarchy = await self.page.query_selector('text="Hierarchy"')
        if hierarchy and await hierarchy.is_visible():
            await hierarchy.click()
            await asyncio.sleep(1)

        users_btn = await self.page.query_selector('button:has-text("Users")')
        if users_btn and await users_btn.is_visible():
            await users_btn.click()
            await asyncio.sleep(2)

        logger.info("Navigated to Users page")

    async def _search_user(self, user_name: str):
        """Search for a user in the users list"""
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
            await asyncio.sleep(2)

    async def _configure_profile_settings(self, user: EntraUser):
        """Configure user's Profile Settings tab"""
        logger.info(f"Configuring profile settings for {user.display_name}")

        await self._search_user(user.display_name)

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

        # Configure settings based on config defaults
        defaults = self.config.get('defaults', {})

        # Set minimum score sliders
        await self._set_slider_value('Minimum score to reply on reviews', defaults.get('minimum_score_to_reply', 3))
        await self._set_slider_value('Minimum Score to Auto-post', defaults.get('autopost_minimum_score', 4.5))

        # Set max posts per day
        max_posts_input = await self.page.query_selector('input[type="number"]')
        if max_posts_input:
            await max_posts_input.fill(str(defaults.get('autopost_max_per_day', 3)))

        # Click Update and Confirm
        update_btn = await self.page.query_selector('button:has-text("Update")')
        if update_btn and await update_btn.is_visible():
            await update_btn.click()
            await asyncio.sleep(1)

        confirm_btn = await self.page.query_selector('button:has-text("Confirm")')
        if confirm_btn and await confirm_btn.is_visible():
            await confirm_btn.click()
            await asyncio.sleep(2)

        logger.info("Profile settings configured")

    async def _set_slider_value(self, label: str, value: float):
        """Set a slider to a specific value"""
        try:
            sliders = await self.page.query_selector_all('.ant-slider')
            for slider in sliders:
                if await slider.is_visible():
                    box = await slider.bounding_box()
                    if box:
                        # Calculate position based on value (1-5 scale)
                        percentage = (value - 1) / 4
                        x = box['x'] + (box['width'] * percentage)
                        y = box['y'] + (box['height'] / 2)
                        await self.page.mouse.click(x, y)
                        await asyncio.sleep(0.3)
                        break
        except Exception as e:
            logger.debug(f"Could not set slider for {label}: {e}")

    async def _publish_user(self, user: EntraUser):
        """Publish user profile"""
        logger.info(f"Publishing profile for {user.display_name}")

        # Close any open drawers
        await self.page.keyboard.press('Escape')
        await asyncio.sleep(1)

        await self._search_user(user.display_name)

        # Find and click Published toggle if it's currently "No"
        toggle = await self.page.query_selector('.ant-switch:not(.ant-switch-checked)')
        if toggle and await toggle.is_visible():
            await toggle.click()
            await asyncio.sleep(1)

            # Click Confirm
            confirm_btn = await self.page.query_selector('button:has-text("Confirm")')
            if confirm_btn and await confirm_btn.is_visible():
                await confirm_btn.click()
                await asyncio.sleep(2)

        logger.info("Profile published")

    async def _get_widget_code(self, user_name: str) -> str:
        """Navigate to Widgets and capture the user's Review Widget embed code"""
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

                # Click the user option
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
                logger.info(f"Captured widget code ({len(widget_code)} characters)")

        except Exception as e:
            logger.error(f"Error capturing widget code: {e}")

        return widget_code or ""

    async def _get_profile_url(self, user_name: str) -> str:
        """Navigate to user profile and capture the public profile URL"""
        logger.info(f"Capturing profile URL for {user_name}")
        profile_url = ""

        try:
            # Close any open modals
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)

            # Navigate to Users
            await self._navigate_to_users()
            await self._search_user(user_name)

            # Click on user name to view profile
            name_el = await self.page.query_selector(f'a:has-text("{user_name}")')
            if name_el and await name_el.is_visible():
                await name_el.click()
                await asyncio.sleep(3)

            # Extract profile URL from #profile-link
            profile_link = await self.page.query_selector('#profile-link')
            if profile_link:
                profile_url = await profile_link.get_attribute('href')

            # Fallback: search all links
            if not profile_url:
                all_links = await self.page.query_selector_all('a[href*="experience.com/reviews"]')
                for link in all_links:
                    href = await link.get_attribute('href')
                    if href and 'experience.com/reviews' in href:
                        profile_url = href
                        break

            if profile_url:
                logger.info(f"Captured profile URL: {profile_url}")

        except Exception as e:
            logger.error(f"Error capturing profile URL: {e}")

        return profile_url or ""

    async def _fill_profile_info(self, user: EntraUser):
        """Fill Profile Info fields from user data"""
        logger.info(f"Filling profile info for {user.display_name}")

        try:
            # Close any open drawers
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)

            await self._navigate_to_users()
            await self._search_user(user.display_name)

            # Open Edit menu
            menu_btn = await self.page.query_selector('button:has(svg path[d*="M12"])')
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

            # Fill Title
            if user.job_title:
                title_input = await self.page.query_selector('label:has-text("Title") >> following::input[1]')
                if title_input:
                    await title_input.fill(user.job_title)

            # Fill Phone
            if user.business_phones:
                phone = user.business_phones[0] if isinstance(user.business_phones, list) else user.business_phones
                phone_input = await self.page.query_selector('label:has-text("Phone Number") >> following::input[1]')
                if phone_input:
                    await phone_input.fill(phone)

            # Fill Mobile
            if user.mobile_phone:
                mobile_input = await self.page.query_selector('label:has-text("Mobile Number") >> following::input[1]')
                if mobile_input:
                    await mobile_input.fill(user.mobile_phone)

            # Click Update
            update_btn = await self.page.query_selector('button:has-text("Update")')
            if update_btn and await update_btn.is_visible():
                await update_btn.click()
                await asyncio.sleep(1)

            confirm_btn = await self.page.query_selector('button:has-text("Confirm")')
            if confirm_btn and await confirm_btn.is_visible():
                await confirm_btn.click()
                await asyncio.sleep(2)

            logger.info("Profile info filled")

        except Exception as e:
            logger.error(f"Error filling profile info: {e}")

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
    Main entry point for Experience.com user provisioning

    Args:
        user: EntraUser object
        config_path: Path to vendor config JSON

    Returns:
        Dict with provisioning result including widget_code and profile_url
    """
    from services.keyvault_service import KeyVaultService

    # Initialize KeyVault service
    keyvault = KeyVaultService()

    # Create automation instance
    automation = ExperienceAutomation(config_path, keyvault)

    # Run automation
    result = await automation.provision_user(user, headless=False)

    return result
