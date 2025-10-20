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
from typing import List, Dict, Any, Optional
from pathlib import Path
from models.user import EntraUser
from models.vendor import VendorConfig
from services.config_manager import ConfigManager
from utils.logger import get_logger

logger = get_logger(__name__)


class AutomationStatusTab:
    """Automation Status tab implementation"""

    def __init__(
        self,
        parent: ctk.CTkFrame,
        config_manager: ConfigManager
    ):
        self.parent = parent
        self.config_manager = config_manager

        self.current_user: Optional[EntraUser] = None
        self.vendors: List[VendorConfig] = []
        self.vendor_status: Dict[str, Dict[str, Any]] = {}

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

        # Done button (hidden initially)
        self.done_btn = ctk.CTkButton(
            self.actions_frame,
            text="Done",
            command=self._on_done_clicked,
            width=150,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="green",
            hover_color="dark green"
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

        for vendor in self.vendors:
            logger.info(f"Processing vendor: {vendor.name}")

            try:
                # Update status
                self._update_vendor_status(vendor.name, "running", "⚙️ Running automation...")

                # Import and run vendor automation module
                if vendor.name == "AccountChek":
                    await self._run_accountchek_automation(vendor)
                else:
                    # Unknown vendor
                    self._add_vendor_message(vendor.name, f"✗ Unknown vendor: {vendor.name}")
                    self._update_vendor_status(vendor.name, "error", "✗ Error")

            except Exception as e:
                logger.error(f"Error processing vendor {vendor.name}: {e}")
                self._add_vendor_message(vendor.name, f"✗ Error: {str(e)}")
                self._update_vendor_status(vendor.name, "error", "✗ Failed")

        # All done
        logger.info("Automation complete")
        self._on_automation_complete()

    async def _run_accountchek_automation(self, vendor: VendorConfig):
        """Run AccountChek automation"""
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

            # Add errors
            for error in result.get('errors', []):
                self._add_vendor_message(vendor.name, f"✗ {error}", color="red")

            # Update final status
            if result['success']:
                self._update_vendor_status(vendor.name, "success", "✓ Complete")
            else:
                self._update_vendor_status(vendor.name, "error", "✗ Failed")

        except Exception as e:
            logger.error(f"AccountChek automation error: {e}")
            self._add_vendor_message(vendor.name, f"✗ Error: {str(e)}", color="red")
            self._update_vendor_status(vendor.name, "error", "✗ Failed")

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

    def _on_done_clicked(self):
        """Handle done button click"""
        logger.info("Automation session complete")
        # TODO: Navigate back to user search or show summary

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
