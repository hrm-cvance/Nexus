"""
Tab 3: Automation Status

Shows real-time status of account provisioning automation:
- Per-vendor progress tracking
- Live status updates
- AI matching suggestions display
- Success/warning/error messages
- Final results summary
"""

import customtkinter as ctk
import asyncio
import threading
import subprocess
import sys
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from datetime import datetime
from models.user import EntraUser
from models.vendor import VendorConfig
from models.automation_result import AutomationSummary, VendorResult
from services.config_manager import ConfigManager
from utils.logger import get_logger

logger = get_logger(__name__)


def is_playwright_browser_installed() -> tuple[bool, str]:
    """
    Check if Playwright browsers are installed.

    Returns:
        Tuple of (is_installed, error_message)
    """
    try:
        # Check if chromium executable exists in expected location
        import platform
        home = Path.home()

        if platform.system() == "Windows":
            playwright_path = home / "AppData" / "Local" / "ms-playwright"
        else:
            playwright_path = home / ".cache" / "ms-playwright"

        if not playwright_path.exists():
            return False, "Playwright browsers not installed. Run: playwright install chromium"

        # Check for any chromium folder
        chromium_folders = list(playwright_path.glob("chromium-*"))
        if not chromium_folders:
            return False, "Chromium browser not installed. Run: playwright install chromium"

        return True, ""
    except Exception as e:
        logger.warning(f"Could not check Playwright installation: {e}")
        return True, ""  # Assume installed, let it fail naturally if not


def detect_playwright_error(error_message: str) -> tuple[bool, str]:
    """
    Detect if an error is related to Playwright browser installation.

    Returns:
        Tuple of (is_playwright_error, user_friendly_message)
    """
    error_lower = str(error_message).lower()

    if "executable doesn't exist" in error_lower or "browsertype.launch" in error_lower:
        return True, (
            "Playwright browser not installed. "
            "Please run 'playwright install chromium' in terminal and try again."
        )

    if "playwright" in error_lower and "install" in error_lower:
        return True, (
            "Playwright needs to be updated. "
            "Please run 'playwright install' in terminal and try again."
        )

    return False, str(error_message)


class UsernameConflictDialog(ctk.CTkToplevel):
    """Dialog for resolving username conflicts in Certified Credit"""

    def __init__(self, parent, display_name: str, attempted_username: str):
        super().__init__(parent)
        self.title("Username Conflict")
        self.geometry("450x280")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)
        self.grab_set()

        self.result = None

        # Main container
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Warning icon and message
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 15))

        warning_label = ctk.CTkLabel(
            header_frame,
            text="⚠️",
            font=ctk.CTkFont(size=32)
        )
        warning_label.pack(side="left", padx=(0, 10))

        msg_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        msg_frame.pack(side="left", fill="x", expand=True)

        title_label = ctk.CTkLabel(
            msg_frame,
            text="Username Already Taken",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        title_label.pack(anchor="w")

        detail_label = ctk.CTkLabel(
            msg_frame,
            text=f"Username '{attempted_username}' is already in use\nfor {display_name}",
            font=ctk.CTkFont(size=13),
            text_color="gray",
            anchor="w",
            justify="left"
        )
        detail_label.pack(anchor="w")

        # Username entry
        entry_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        entry_frame.pack(fill="x", pady=15)

        entry_label = ctk.CTkLabel(
            entry_frame,
            text="Enter alternative username:",
            font=ctk.CTkFont(size=13)
        )
        entry_label.pack(anchor="w", pady=(0, 5))

        self.username_entry = ctk.CTkEntry(entry_frame, width=380, height=35)
        self.username_entry.pack(fill="x")
        self.username_entry.insert(0, attempted_username)
        self.username_entry.select_range(0, 'end')
        self.username_entry.focus()

        # Bind Enter key to submit
        self.username_entry.bind('<Return>', lambda e: self._on_submit())

        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(20, 0))

        skip_btn = ctk.CTkButton(
            btn_frame,
            text="Skip This Vendor",
            command=self._on_skip,
            width=150,
            height=38,
            fg_color="gray",
            hover_color="#555555"
        )
        skip_btn.pack(side="left")

        submit_btn = ctk.CTkButton(
            btn_frame,
            text="Try This Username",
            command=self._on_submit,
            width=150,
            height=38,
            fg_color="green",
            hover_color="#006400"
        )
        submit_btn.pack(side="right")

        # Wait for window to close
        self.protocol("WM_DELETE_WINDOW", self._on_skip)

    def _on_submit(self):
        """User chose to try a new username"""
        new_username = self.username_entry.get().strip()
        if new_username:
            self.result = new_username
            self.destroy()

    def _on_skip(self):
        """User chose to skip this vendor"""
        self.result = None
        self.destroy()

    def get_result(self) -> Optional[str]:
        """
        Wait for dialog to close and return result

        Returns:
            New username string, or None if user chose to skip
        """
        self.wait_window()
        return self.result


class AutomationStatusTab:
    """Automation Status tab implementation"""

    def __init__(
        self,
        parent: ctk.CTkFrame,
        config_manager: ConfigManager,
        on_view_summary: Optional[Callable] = None
    ):
        self.parent = parent
        self.config_manager = config_manager
        self.on_view_summary = on_view_summary

        self.current_user: Optional[EntraUser] = None
        self.vendors: List[VendorConfig] = []
        self.vendor_status: Dict[str, Dict[str, Any]] = {}
        self.automation_summary: Optional[AutomationSummary] = None

        # Create UI
        self._create_ui()

        logger.info("Automation Status tab initialized")

    def _create_ui(self):
        """Create UI components"""
        # Main container with scrollbar
        self.main_scroll = ctk.CTkScrollableFrame(self.parent)
        self.main_scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Header section
        self._create_header_section()

        # Vendors status section
        self.vendors_container = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.vendors_container.pack(fill="both", expand=True, pady=(10, 0))

        # Action buttons section
        self._create_actions_section()

    def _create_header_section(self):
        """Create header section"""
        header_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))

        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="Automation Status",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(anchor="w")

        # Subtitle
        self.subtitle_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        )
        self.subtitle_label.pack(anchor="w", pady=(5, 0))

    def _create_actions_section(self):
        """Create action buttons section"""
        self.actions_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.actions_frame.pack(fill="x", pady=(20, 0))

        # View Summary button (hidden initially)
        self.done_btn = ctk.CTkButton(
            self.actions_frame,
            text="View Summary \u2192",
            command=self._on_view_summary_clicked,
            width=180,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="green",
            hover_color="#006400"
        )
        # Don't pack yet - will show when automation completes

    def start_automation(self, user: EntraUser, vendors: List[VendorConfig]):
        """
        Start automation for selected vendors

        Args:
            user: EntraUser object
            vendors: List of VendorConfig objects to provision
        """
        logger.info(f"Starting automation for {user.display_name} with {len(vendors)} vendor(s)")

        self.current_user = user
        self.vendors = vendors

        # Initialize automation summary
        self.automation_summary = AutomationSummary(
            user=user,
            start_time=datetime.now()
        )

        # Update header
        self.subtitle_label.configure(
            text=f"Creating accounts for {user.display_name} in {len(vendors)} vendor system(s)"
        )

        # Clear previous status
        for widget in self.vendors_container.winfo_children():
            widget.destroy()

        # Create vendor status cards
        for vendor in vendors:
            self._create_vendor_status_card(vendor)

        # Start automation in background thread
        thread = threading.Thread(target=self._run_automation_thread, daemon=True)
        thread.start()

    def _create_vendor_status_card(self, vendor: VendorConfig):
        """Create a status card for a vendor"""
        card = ctk.CTkFrame(self.vendors_container)
        card.pack(fill="x", pady=10)
        card.vendor_name = vendor.name  # Store vendor name for lookup

        # Header with vendor name
        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 10))

        vendor_label = ctk.CTkLabel(
            header_frame,
            text=vendor.display_name,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        vendor_label.pack(side="left")

        status_label = ctk.CTkLabel(
            header_frame,
            text="⏳ Starting...",
            font=ctk.CTkFont(size=13),
            text_color="orange",
            anchor="e"
        )
        status_label.pack(side="right")

        # Progress bar
        progress_bar = ctk.CTkProgressBar(card, mode="indeterminate")
        progress_bar.pack(fill="x", padx=20, pady=(0, 10))
        progress_bar.start()

        # Messages area
        messages_frame = ctk.CTkFrame(card)
        messages_frame.pack(fill="x", padx=20, pady=(0, 15))

        messages_text = ctk.CTkTextbox(messages_frame, height=150, state="disabled")
        messages_text.pack(fill="x")

        # Store widget references
        self.vendor_status[vendor.name] = {
            'card': card,
            'status_label': status_label,
            'progress_bar': progress_bar,
            'messages_text': messages_text,
            'status': 'running'
        }

    def _run_automation_thread(self):
        """Run automation in background thread"""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Run automation
            loop.run_until_complete(self._run_automation())

        except Exception as e:
            logger.error(f"Error in automation thread: {e}")
        finally:
            loop.close()

    async def _run_automation(self):
        """Run automation for all vendors"""
        logger.info("Running automation...")

        # Check if Playwright browsers are installed before starting
        is_installed, install_error = is_playwright_browser_installed()
        if not is_installed:
            logger.error(f"Playwright check failed: {install_error}")
            # Mark all vendors as failed with the same error
            for vendor in self.vendors:
                self._add_vendor_message(vendor.name, f"✗ {install_error}", color="red")
                self._update_vendor_status(vendor.name, "error", "✗ Setup Required")

                # Create vendor result for summary
                vendor_result = VendorResult(
                    vendor_name=vendor.name,
                    display_name=vendor.display_name,
                    success=False,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    errors=[install_error]
                )
                self.automation_summary.vendor_results.append(vendor_result)

            self._on_automation_complete()
            return

        for vendor in self.vendors:
            logger.info(f"Processing vendor: {vendor.name}")

            try:
                # Update status
                self._update_vendor_status(vendor.name, "running", "⚙️ Running automation...")

                # Import and run vendor automation module
                if vendor.name == "AccountChek":
                    await self._run_accountchek_automation(vendor)
                elif vendor.name == "BankVOD":
                    await self._run_bankvod_automation(vendor)
                elif vendor.name == "ClearCapital":
                    await self._run_clearcapital_automation(vendor)
                elif vendor.name == "DataVerify":
                    await self._run_dataverify_automation(vendor)
                elif vendor.name == "CertifiedCredit":
                    await self._run_certifiedcredit_automation(vendor)
                elif vendor.name == "PartnersCredit":
                    await self._run_partnerscredit_automation(vendor)
                elif vendor.name == "TheWorkNumber":
                    await self._run_theworknumber_automation(vendor)
                elif vendor.name == "MMI":
                    await self._run_mmi_automation(vendor)
                elif vendor.name == "Experience":
                    await self._run_experience_automation(vendor)
                else:
                    # Unknown vendor
                    self._add_vendor_message(vendor.name, f"✗ Unknown vendor: {vendor.name}")
                    self._update_vendor_status(vendor.name, "error", "✗ Error")

            except Exception as e:
                logger.error(f"Error processing vendor {vendor.name}: {e}")
                # Check if this is a Playwright installation error
                is_pw_error, friendly_msg = detect_playwright_error(str(e))
                self._add_vendor_message(vendor.name, f"✗ Error: {friendly_msg}", color="red")
                self._update_vendor_status(vendor.name, "error", "✗ Failed")

        # All done
        logger.info("Automation complete")
        self._on_automation_complete()

    async def _run_accountchek_automation(self, vendor: VendorConfig):
        """Run AccountChek automation"""
        vendor_result = VendorResult(
            vendor_name=vendor.name,
            display_name=vendor.display_name,
            success=False,
            start_time=datetime.now()
        )

        try:
            # Import automation module
            from automation.vendors.accountchek import provision_user

            # Get config path
            vendor_mappings = self.config_manager.get_enabled_vendors()
            accountchek_mapping = next(
                (m for m in vendor_mappings if m['vendor_name'] == 'AccountChek'),
                None
            )

            if not accountchek_mapping:
                raise Exception("AccountChek mapping not found in config")

            # Build config path
            config_dir = self.config_manager.project_root
            config_path = config_dir / accountchek_mapping['vendor_config']

            logger.info(f"Using config: {config_path}")

            # Add status message
            self._add_vendor_message(vendor.name, "Starting AccountChek automation...")

            # Run automation (no API key = uses keyword matching fallback)
            result = await provision_user(self.current_user, str(config_path), api_key=None)

            # Display results
            logger.info(f"AccountChek result: {result}")

            # Add messages
            for msg in result.get('messages', []):
                self._add_vendor_message(vendor.name, msg)

            # Add warnings
            for warning in result.get('warnings', []):
                self._add_vendor_message(vendor.name, warning, color="orange")

            # Add AI suggestions if available
            if 'ai_suggestions' in result:
                ai_sug = result['ai_suggestions']
                if 'role' in ai_sug:
                    role_info = ai_sug['role']
                    self._add_vendor_message(
                        vendor.name,
                        f"🤖 AI Role Suggestion: {role_info['suggested_role']} "
                        f"({role_info['confidence']:.0%} confidence)",
                        color="cyan"
                    )

            # Capture results for summary
            vendor_result.messages = result.get('messages', [])
            vendor_result.warnings = result.get('warnings', [])
            vendor_result.errors = result.get('errors', [])

            # Add errors to UI
            for error in vendor_result.errors:
                self._add_vendor_message(vendor.name, f"✗ {error}", color="red")

            # Update result and status
            vendor_result.success = result['success']
            if result['success']:
                self._update_vendor_status(vendor.name, "success", "✓ Complete")
            else:
                self._update_vendor_status(vendor.name, "error", "✗ Failed")

        except Exception as e:
            logger.error(f"AccountChek automation error: {e}")
            vendor_result.errors.append(str(e))
            self._add_vendor_message(vendor.name, f"✗ Error: {str(e)}", color="red")
            self._update_vendor_status(vendor.name, "error", "✗ Failed")

        finally:
            vendor_result.end_time = datetime.now()
            self.automation_summary.vendor_results.append(vendor_result)

    async def _run_bankvod_automation(self, vendor: VendorConfig):
        """Run BankVOD automation"""
        vendor_result = VendorResult(
            vendor_name=vendor.name,
            display_name=vendor.display_name,
            success=False,
            start_time=datetime.now()
        )

        try:
            # Import automation module
            from automation.vendors.bankvod import provision_user

            # Get config path
            vendor_mappings = self.config_manager.get_enabled_vendors()
            bankvod_mapping = next(
                (m for m in vendor_mappings if m['vendor_name'] == 'BankVOD'),
                None
            )

            if not bankvod_mapping:
                raise Exception("BankVOD mapping not found in config")

            # Build config path
            config_dir = self.config_manager.project_root
            config_path = config_dir / bankvod_mapping['vendor_config']

            logger.info(f"Using config: {config_path}")

            # Add status message
            self._add_vendor_message(vendor.name, "Starting BankVOD automation...")

            # Run automation (no API key needed for BankVOD)
            result = await provision_user(self.current_user, str(config_path), api_key=None)

            # Display results
            logger.info(f"BankVOD result: {result}")

            # Add messages
            for msg in result.get('messages', []):
                self._add_vendor_message(vendor.name, msg)

            # Add warnings
            for warning in result.get('warnings', []):
                self._add_vendor_message(vendor.name, warning, color="orange")

            # Capture results for summary
            vendor_result.messages = result.get('messages', [])
            vendor_result.warnings = result.get('warnings', [])
            vendor_result.errors = result.get('errors', [])

            # Add errors to UI
            for error in vendor_result.errors:
                self._add_vendor_message(vendor.name, f"✗ {error}", color="red")

            # Update result and status
            vendor_result.success = result['success']
            if result['success']:
                self._update_vendor_status(vendor.name, "success", "✓ Complete")
            else:
                self._update_vendor_status(vendor.name, "error", "✗ Failed")

        except Exception as e:
            logger.error(f"BankVOD automation error: {e}")
            vendor_result.errors.append(str(e))
            self._add_vendor_message(vendor.name, f"✗ Error: {str(e)}", color="red")
            self._update_vendor_status(vendor.name, "error", "✗ Failed")

        finally:
            vendor_result.end_time = datetime.now()
            self.automation_summary.vendor_results.append(vendor_result)

    async def _run_clearcapital_automation(self, vendor: VendorConfig):
        """Run ClearCapital automation with username conflict handling"""
        vendor_result = VendorResult(
            vendor_name=vendor.name,
            display_name=vendor.display_name,
            success=False,
            start_time=datetime.now()
        )

        # Store for dialog result communication between threads
        dialog_result_holder = {'result': None, 'ready': threading.Event()}

        async def handle_username_conflict(display_name: str, attempted_username: str) -> Optional[str]:
            """
            Callback to prompt user when username is taken.
            Shows a dialog on the main thread and waits for the response.
            """
            logger.info(f"Username conflict detected for {display_name}: {attempted_username}")
            dialog_result_holder['ready'].clear()
            dialog_result_holder['result'] = None

            def show_dialog():
                """Show dialog on main UI thread"""
                try:
                    dialog = UsernameConflictDialog(
                        self.parent,
                        display_name=display_name,
                        attempted_username=attempted_username
                    )
                    dialog_result_holder['result'] = dialog.get_result()
                except Exception as e:
                    logger.error(f"Dialog error: {e}")
                    dialog_result_holder['result'] = None
                finally:
                    dialog_result_holder['ready'].set()

            # Schedule dialog on main thread
            self.parent.after(0, show_dialog)

            # Wait for dialog result (with timeout)
            dialog_result_holder['ready'].wait(timeout=300)  # 5 minute timeout

            result = dialog_result_holder['result']
            if result:
                logger.info(f"User provided alternate username: {result}")
            else:
                logger.info("User chose to skip ClearCapital")

            return result

        try:
            # Import automation module
            from automation.vendors.clearcapital import provision_user

            # Get config path
            vendor_mappings = self.config_manager.get_enabled_vendors()
            clearcapital_mapping = next(
                (m for m in vendor_mappings if m['vendor_name'] == 'ClearCapital'),
                None
            )

            if not clearcapital_mapping:
                raise Exception("ClearCapital mapping not found in config")

            # Build config path
            config_dir = self.config_manager.project_root
            config_path = config_dir / clearcapital_mapping['vendor_config']

            logger.info(f"Using config: {config_path}")

            # Add status message
            self._add_vendor_message(vendor.name, "Starting ClearCapital automation...")

            # Run automation with username conflict callback
            result = await provision_user(
                self.current_user,
                str(config_path),
                api_key=None,
                on_username_conflict=handle_username_conflict
            )

            # Display results
            logger.info(f"ClearCapital result: {result}")

            # Add messages
            for msg in result.get('messages', []):
                self._add_vendor_message(vendor.name, msg)

            # Add warnings
            for warning in result.get('warnings', []):
                self._add_vendor_message(vendor.name, warning, color="orange")

            # Capture results for summary
            vendor_result.messages = result.get('messages', [])
            vendor_result.warnings = result.get('warnings', [])
            vendor_result.errors = result.get('errors', [])

            # Add errors to UI
            for error in vendor_result.errors:
                self._add_vendor_message(vendor.name, f"✗ {error}", color="red")

            # Update result and status
            vendor_result.success = result['success']
            if result['success']:
                self._update_vendor_status(vendor.name, "success", "✓ Complete")
            else:
                self._update_vendor_status(vendor.name, "error", "✗ Failed")

        except Exception as e:
            logger.error(f"ClearCapital automation error: {e}")
            vendor_result.errors.append(str(e))
            self._add_vendor_message(vendor.name, f"✗ Error: {str(e)}", color="red")
            self._update_vendor_status(vendor.name, "error", "✗ Failed")

        finally:
            vendor_result.end_time = datetime.now()
            self.automation_summary.vendor_results.append(vendor_result)

    async def _run_dataverify_automation(self, vendor: VendorConfig):
        """Run DataVerify automation"""
        vendor_result = VendorResult(
            vendor_name=vendor.name,
            display_name=vendor.display_name,
            success=False,
            start_time=datetime.now()
        )

        try:
            # Import automation module
            from automation.vendors.dataverify import provision_user

            # Get config path
            vendor_mappings = self.config_manager.get_enabled_vendors()
            dataverify_mapping = next(
                (m for m in vendor_mappings if m['vendor_name'] == 'DataVerify'),
                None
            )

            if not dataverify_mapping:
                raise Exception("DataVerify mapping not found in config")

            # Build config path
            config_dir = self.config_manager.project_root
            config_path = config_dir / dataverify_mapping['vendor_config']

            logger.info(f"Using config: {config_path}")

            # Add status message
            self._add_vendor_message(vendor.name, "Starting DataVerify automation...")

            # Run automation (no API key needed for DataVerify)
            result = await provision_user(self.current_user, str(config_path), api_key=None)

            # Display results
            logger.info(f"DataVerify result: {result}")

            # Add messages
            for msg in result.get('messages', []):
                self._add_vendor_message(vendor.name, msg)

            # Add warnings
            for warning in result.get('warnings', []):
                self._add_vendor_message(vendor.name, warning, color="orange")

            # Capture results for summary
            vendor_result.messages = result.get('messages', [])
            vendor_result.warnings = result.get('warnings', [])
            vendor_result.errors = result.get('errors', [])

            # Add errors to UI
            for error in vendor_result.errors:
                self._add_vendor_message(vendor.name, f"✗ {error}", color="red")

            # Update result and status
            vendor_result.success = result['success']
            if result['success']:
                self._update_vendor_status(vendor.name, "success", "✓ Complete")
            else:
                self._update_vendor_status(vendor.name, "error", "✗ Failed")

        except Exception as e:
            logger.error(f"DataVerify automation error: {e}")
            vendor_result.errors.append(str(e))
            self._add_vendor_message(vendor.name, f"✗ Error: {str(e)}", color="red")
            self._update_vendor_status(vendor.name, "error", "✗ Failed")

        finally:
            vendor_result.end_time = datetime.now()
            self.automation_summary.vendor_results.append(vendor_result)

    async def _run_certifiedcredit_automation(self, vendor: VendorConfig):
        """Run Certified Credit automation with username conflict handling"""
        vendor_result = VendorResult(
            vendor_name=vendor.name,
            display_name=vendor.display_name,
            success=False,
            start_time=datetime.now()
        )

        # Store for dialog result communication between threads
        dialog_result_holder = {'result': None, 'ready': threading.Event()}

        async def handle_username_conflict(display_name: str, attempted_username: str) -> Optional[str]:
            """
            Callback to prompt user when username is taken.
            Shows a dialog on the main thread and waits for the response.
            """
            logger.info(f"Username conflict detected for {display_name}: {attempted_username}")
            dialog_result_holder['ready'].clear()
            dialog_result_holder['result'] = None

            def show_dialog():
                """Show dialog on main UI thread"""
                try:
                    dialog = UsernameConflictDialog(
                        self.parent,
                        display_name=display_name,
                        attempted_username=attempted_username
                    )
                    dialog_result_holder['result'] = dialog.get_result()
                except Exception as e:
                    logger.error(f"Error showing username conflict dialog: {e}")
                    dialog_result_holder['result'] = None
                finally:
                    dialog_result_holder['ready'].set()

            # Schedule dialog on main thread
            self.parent.after(0, show_dialog)

            # Wait for dialog result (with timeout)
            while not dialog_result_holder['ready'].wait(timeout=0.1):
                await asyncio.sleep(0.1)

            result = dialog_result_holder['result']
            if result:
                logger.info(f"User provided alternative username: {result}")
            else:
                logger.info("User chose to skip CertifiedCredit")

            return result

        try:
            # Import automation module
            from automation.vendors.certifiedcredit import provision_user

            # Get config path
            vendor_mappings = self.config_manager.get_enabled_vendors()
            certifiedcredit_mapping = next(
                (m for m in vendor_mappings if m['vendor_name'] == 'CertifiedCredit'),
                None
            )

            if not certifiedcredit_mapping:
                raise Exception("Certified Credit mapping not found in config")

            # Build config path
            config_dir = self.config_manager.project_root
            config_path = config_dir / certifiedcredit_mapping['vendor_config']

            # Add status message
            self._add_vendor_message(vendor.name, "Starting Certified Credit automation...")

            # Run automation with username conflict callback
            result = await provision_user(
                self.current_user,
                str(config_path),
                api_key=None,
                on_username_conflict=handle_username_conflict
            )

            # Display results
            for msg in result.get('messages', []):
                self._add_vendor_message(vendor.name, msg)

            for warning in result.get('warnings', []):
                self._add_vendor_message(vendor.name, warning, color="orange")

            # Capture results for summary
            vendor_result.messages = result.get('messages', [])
            vendor_result.warnings = result.get('warnings', [])
            vendor_result.errors = result.get('errors', [])

            # Add errors to UI
            for error in vendor_result.errors:
                self._add_vendor_message(vendor.name, f"✗ {error}", color="red")

            # Update result and status
            vendor_result.success = result['success']
            if result['success']:
                self._update_vendor_status(vendor.name, "success", "✓ Complete")
            else:
                self._update_vendor_status(vendor.name, "error", "✗ Failed")

        except Exception as e:
            logger.error(f"Certified Credit automation error: {e}")
            vendor_result.errors.append(str(e))
            self._add_vendor_message(vendor.name, f"✗ Error: {str(e)}", color="red")
            self._update_vendor_status(vendor.name, "error", "✗ Failed")

        finally:
            vendor_result.end_time = datetime.now()
            self.automation_summary.vendor_results.append(vendor_result)

    async def _run_partnerscredit_automation(self, vendor: VendorConfig):
        """Run Partners Credit automation"""
        vendor_result = VendorResult(
            vendor_name=vendor.name,
            display_name=vendor.display_name,
            success=False,
            start_time=datetime.now()
        )

        try:
            from automation.vendors.partnerscredit import provision_user

            # Get config path
            vendor_mappings = self.config_manager.get_enabled_vendors()
            partnerscredit_mapping = next(
                (m for m in vendor_mappings if m['vendor_name'] == 'PartnersCredit'),
                None
            )

            if not partnerscredit_mapping:
                raise Exception("Partners Credit vendor mapping not found")

            # Build config path
            config_dir = self.config_manager.project_root
            config_path = config_dir / partnerscredit_mapping['vendor_config']

            logger.info(f"Using config: {config_path}")

            # Add status message
            self._add_vendor_message(vendor.name, "Starting Partners Credit automation...")

            # Run automation (no API key needed for Partners Credit)
            result = await provision_user(self.current_user, str(config_path), api_key=None)

            # Display results
            for msg in result.get('messages', []):
                self._add_vendor_message(vendor.name, msg)

            for warning in result.get('warnings', []):
                self._add_vendor_message(vendor.name, warning, color="orange")

            # Capture results for summary
            vendor_result.messages = result.get('messages', [])
            vendor_result.warnings = result.get('warnings', [])
            vendor_result.errors = result.get('errors', [])

            # Add errors to UI
            for error in vendor_result.errors:
                self._add_vendor_message(vendor.name, f"✗ {error}", color="red")

            # Update result and status
            vendor_result.success = result['success']
            if result['success']:
                self._update_vendor_status(vendor.name, "success", "✓ Complete")
            else:
                self._update_vendor_status(vendor.name, "error", "✗ Failed")

        except Exception as e:
            logger.error(f"Partners Credit automation error: {e}")
            vendor_result.errors.append(str(e))
            self._add_vendor_message(vendor.name, f"✗ Error: {str(e)}", color="red")
            self._update_vendor_status(vendor.name, "error", "✗ Failed")

        finally:
            vendor_result.end_time = datetime.now()
            self.automation_summary.vendor_results.append(vendor_result)

    async def _run_theworknumber_automation(self, vendor: VendorConfig):
        """Run The Work Number automation"""
        vendor_result = VendorResult(
            vendor_name=vendor.name,
            display_name=vendor.display_name,
            success=False,
            start_time=datetime.now()
        )

        try:
            from automation.vendors.theworknumber import provision_user

            # Get config path
            vendor_mappings = self.config_manager.get_enabled_vendors()
            theworknumber_mapping = next(
                (m for m in vendor_mappings if m['vendor_name'] == 'TheWorkNumber'),
                None
            )

            if not theworknumber_mapping:
                raise Exception("The Work Number vendor mapping not found")

            # Build config path
            config_dir = self.config_manager.project_root
            config_path = config_dir / theworknumber_mapping['vendor_config']

            logger.info(f"Using config: {config_path}")

            # Add status message
            self._add_vendor_message(vendor.name, "Starting The Work Number automation...")

            # Run automation
            result = await provision_user(self.current_user, str(config_path))

            # Display results
            for msg in result.get('messages', []):
                self._add_vendor_message(vendor.name, msg)

            for warning in result.get('warnings', []):
                self._add_vendor_message(vendor.name, warning, color="orange")

            # Capture results for summary
            vendor_result.messages = result.get('messages', [])
            vendor_result.warnings = result.get('warnings', [])
            vendor_result.errors = result.get('errors', [])

            # Add errors to UI
            for error in vendor_result.errors:
                self._add_vendor_message(vendor.name, f"✗ {error}", color="red")

            # Update result and status
            vendor_result.success = result['success']
            if result['success']:
                self._update_vendor_status(vendor.name, "success", "✓ Complete")
            else:
                self._update_vendor_status(vendor.name, "error", "✗ Failed")

        except Exception as e:
            logger.error(f"The Work Number automation error: {e}")
            vendor_result.errors.append(str(e))
            self._add_vendor_message(vendor.name, f"✗ Error: {str(e)}", color="red")
            self._update_vendor_status(vendor.name, "error", "✗ Failed")

        finally:
            vendor_result.end_time = datetime.now()
            self.automation_summary.vendor_results.append(vendor_result)

    async def _run_mmi_automation(self, vendor: VendorConfig):
        """Run MMI (Mortgage Market Intelligence) automation"""
        vendor_result = VendorResult(
            vendor_name=vendor.name,
            display_name=vendor.display_name,
            success=False,
            start_time=datetime.now()
        )

        try:
            from automation.vendors.mmi import provision_user

            # Get config path
            vendor_mappings = self.config_manager.get_enabled_vendors()
            mmi_mapping = next(
                (m for m in vendor_mappings if m['vendor_name'] == 'MMI'),
                None
            )

            if not mmi_mapping:
                raise Exception("MMI vendor mapping not found")

            # Build config path
            config_dir = self.config_manager.project_root
            config_path = config_dir / mmi_mapping['vendor_config']

            logger.info(f"Using config: {config_path}")

            # Add status message
            self._add_vendor_message(vendor.name, "Starting MMI automation...")

            # Run automation
            result = await provision_user(self.current_user, str(config_path))

            # Display results
            for msg in result.get('messages', []):
                self._add_vendor_message(vendor.name, msg)

            for warning in result.get('warnings', []):
                self._add_vendor_message(vendor.name, warning, color="orange")

            # Capture results for summary
            vendor_result.messages = result.get('messages', [])
            vendor_result.warnings = result.get('warnings', [])
            vendor_result.errors = result.get('errors', [])

            # Add errors to UI
            for error in vendor_result.errors:
                self._add_vendor_message(vendor.name, f"✗ {error}", color="red")

            # Update result and status
            vendor_result.success = result['success']
            if result['success']:
                self._update_vendor_status(vendor.name, "success", "✓ Complete")
            else:
                self._update_vendor_status(vendor.name, "error", "✗ Failed")

        except Exception as e:
            logger.error(f"MMI automation error: {e}")
            vendor_result.errors.append(str(e))
            self._add_vendor_message(vendor.name, f"✗ Error: {str(e)}", color="red")
            self._update_vendor_status(vendor.name, "error", "✗ Failed")

        finally:
            vendor_result.end_time = datetime.now()
            self.automation_summary.vendor_results.append(vendor_result)

    async def _run_experience_automation(self, vendor: VendorConfig):
        """Run Experience.com automation"""
        vendor_result = VendorResult(
            vendor_name=vendor.name,
            display_name=vendor.display_name,
            success=False,
            start_time=datetime.now()
        )

        try:
            from automation.vendors.experience import provision_user

            # Get config path
            vendor_mappings = self.config_manager.get_enabled_vendors()
            experience_mapping = next(
                (m for m in vendor_mappings if m['vendor_name'] == 'Experience'),
                None
            )

            if not experience_mapping:
                raise Exception("Experience vendor mapping not found")

            # Build config path
            config_dir = self.config_manager.project_root
            config_path = config_dir / experience_mapping['vendor_config']

            logger.info(f"Using config: {config_path}")

            # Add status message
            self._add_vendor_message(vendor.name, "Starting Experience.com automation...")

            # Run automation
            result = await provision_user(self.current_user, str(config_path))

            # Display results
            for msg in result.get('messages', []):
                self._add_vendor_message(vendor.name, msg)

            for warning in result.get('warnings', []):
                self._add_vendor_message(vendor.name, warning, color="orange")

            # Capture widget code and profile URL if available
            if result.get('widget_code'):
                self._add_vendor_message(vendor.name, f"Widget Code captured ({len(result['widget_code'])} chars)")
            if result.get('profile_url'):
                self._add_vendor_message(vendor.name, f"Profile URL: {result['profile_url']}")

            # Capture results for summary
            vendor_result.messages = result.get('messages', [])
            vendor_result.warnings = result.get('warnings', [])
            vendor_result.errors = result.get('errors', [])

            # Add errors to UI
            for error in vendor_result.errors:
                self._add_vendor_message(vendor.name, f"✗ {error}", color="red")

            # Update result and status
            vendor_result.success = result['success']
            if result['success']:
                self._update_vendor_status(vendor.name, "success", "✓ Complete")
            else:
                self._update_vendor_status(vendor.name, "error", "✗ Failed")

        except Exception as e:
            logger.error(f"Experience automation error: {e}")
            vendor_result.errors.append(str(e))
            self._add_vendor_message(vendor.name, f"✗ Error: {str(e)}", color="red")
            self._update_vendor_status(vendor.name, "error", "✗ Failed")

        finally:
            vendor_result.end_time = datetime.now()
            self.automation_summary.vendor_results.append(vendor_result)

    def _update_vendor_status(self, vendor_name: str, status: str, status_text: str):
        """Update vendor status in UI (thread-safe)"""
        def update():
            if vendor_name not in self.vendor_status:
                return

            widgets = self.vendor_status[vendor_name]
            widgets['status'] = status
            widgets['status_label'].configure(text=status_text)

            # Update status color
            if status == "success":
                widgets['status_label'].configure(text_color="green")
                widgets['progress_bar'].stop()
                widgets['progress_bar'].set(1.0)
            elif status == "error":
                widgets['status_label'].configure(text_color="red")
                widgets['progress_bar'].stop()
                widgets['progress_bar'].set(0.0)
            elif status == "running":
                widgets['status_label'].configure(text_color="orange")

        # Schedule UI update on main thread
        self.parent.after(0, update)

    def _add_vendor_message(self, vendor_name: str, message: str, color: str = "white"):
        """Add a message to vendor status (thread-safe)"""
        def update():
            if vendor_name not in self.vendor_status:
                return

            text_widget = self.vendor_status[vendor_name]['messages_text']
            text_widget.configure(state="normal")
            text_widget.insert("end", f"{message}\n")
            text_widget.see("end")
            text_widget.configure(state="disabled")

        # Schedule UI update on main thread
        self.parent.after(0, update)

    def _on_automation_complete(self):
        """Handle automation completion"""
        def update():
            logger.info("All automation tasks complete")

            # Set end time on summary
            if self.automation_summary:
                self.automation_summary.end_time = datetime.now()

            # Show done button
            self.done_btn.pack(side="right", padx=20)

            # Update subtitle
            success_count = sum(1 for v in self.vendor_status.values() if v['status'] == 'success')
            error_count = sum(1 for v in self.vendor_status.values() if v['status'] == 'error')

            if error_count == 0:
                self.subtitle_label.configure(
                    text=f"✓ All {success_count} vendor account(s) created successfully!"
                )
            else:
                self.subtitle_label.configure(
                    text=f"Completed with {success_count} success(es) and {error_count} error(s)"
                )

        # Schedule UI update on main thread
        self.parent.after(0, update)

    def _on_view_summary_clicked(self):
        """Handle View Summary button click"""
        logger.info("Navigating to summary tab")
        if self.on_view_summary and self.automation_summary:
            self.on_view_summary(self.automation_summary)

    def clear(self):
        """Clear automation status"""
        self.current_user = None
        self.vendors = []
        self.vendor_status = {}

        # Clear UI
        for widget in self.vendors_container.winfo_children():
            widget.destroy()

        self.subtitle_label.configure(text="")
        self.done_btn.pack_forget()
