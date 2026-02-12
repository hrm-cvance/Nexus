"""
Tab 2: Account Provisioning

Shows selected user details and vendors to provision:
- User summary panel with profile information and groups
- Auto-detected vendors based on group membership
- Vendor selection cards
- Field mapping preview
- Start Automation button
"""

import customtkinter as ctk
from typing import List, Optional, Callable
from models.user import EntraUser
from models.vendor import VendorConfig
from services.config_manager import ConfigManager
from utils.logger import get_logger

logger = get_logger(__name__)


class AccountProvisioningTab:
    """Account Provisioning tab implementation"""

    def __init__(
        self,
        parent: ctk.CTkFrame,
        config_manager: ConfigManager,
        on_start_automation: Callable
    ):
        self.parent = parent
        self.config_manager = config_manager
        self.on_start_automation = on_start_automation

        self.current_user: Optional[EntraUser] = None
        self.detected_vendors: List[VendorConfig] = []
        self.selected_vendors: List[str] = []

        # Create UI
        self._create_ui()

        logger.info("Account Provisioning tab initialized")

    def _create_ui(self):
        """Create UI components"""
        # Main container with scrollbar
        main_scroll = ctk.CTkScrollableFrame(self.parent)
        main_scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Show "no user selected" message initially
        self.no_user_frame = ctk.CTkFrame(main_scroll)
        self.no_user_frame.pack(fill="both", expand=True, padx=20, pady=20)

        no_user_label = ctk.CTkLabel(
            self.no_user_frame,
            text="No User Selected\n\nPlease select a user from the User Search tab",
            font=ctk.CTkFont(size=16),
            text_color="gray"
        )
        no_user_label.pack(expand=True, pady=100)

        # Create frames for when user is loaded (hidden initially)
        self.user_content_frame = ctk.CTkFrame(main_scroll, fg_color="transparent")
        # Don't pack yet

        # User summary section
        self._create_user_summary_section()

        # Vendors section
        self._create_vendors_section()

        # Action buttons section
        self._create_actions_section()

    def _create_user_summary_section(self):
        """Create user summary section"""
        summary_frame = ctk.CTkFrame(self.user_content_frame)
        summary_frame.pack(fill="x", padx=0, pady=(0, 20))

        # Title
        title_label = ctk.CTkLabel(
            summary_frame,
            text="Selected User",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(padx=20, pady=(15, 10), anchor="w")

        # User info container
        self.user_info_container = ctk.CTkFrame(summary_frame, fg_color="transparent")
        self.user_info_container.pack(fill="x", padx=20, pady=(0, 15))

    def _create_vendors_section(self):
        """Create vendors section"""
        vendors_frame = ctk.CTkFrame(self.user_content_frame)
        vendors_frame.pack(fill="x", padx=0, pady=(0, 20))

        # Title with count
        title_container = ctk.CTkFrame(vendors_frame, fg_color="transparent")
        title_container.pack(fill="x", padx=20, pady=(15, 10))

        title_label = ctk.CTkLabel(
            title_container,
            text="Vendor Accounts",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(side="left")

        self.vendors_count_label = ctk.CTkLabel(
            title_container,
            text="",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.vendors_count_label.pack(side="left", padx=(10, 0))

        # Info message
        info_label = ctk.CTkLabel(
            vendors_frame,
            text="Auto-detected vendors are pre-selected based on group membership",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        info_label.pack(padx=20, pady=(0, 10), anchor="w")

        # Vendors container
        self.vendors_container = ctk.CTkFrame(vendors_frame, fg_color="transparent")
        self.vendors_container.pack(fill="x", padx=20, pady=(0, 15))

    def _create_actions_section(self):
        """Create action buttons section"""
        actions_frame = ctk.CTkFrame(self.user_content_frame, fg_color="transparent")
        actions_frame.pack(fill="x", padx=0, pady=(0, 20))

        # Start Automation button
        self.start_btn = ctk.CTkButton(
            actions_frame,
            text="Start Automation →",
            command=self._on_start_automation_clicked,
            width=200,
            height=45,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="green",
            hover_color="dark green"
        )
        self.start_btn.pack(side="right", padx=20)

        # Cancel button
        cancel_btn = ctk.CTkButton(
            actions_frame,
            text="← Back to Search",
            command=self._on_back_clicked,
            width=150,
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color="gray",
            hover_color="dark gray"
        )
        cancel_btn.pack(side="right", padx=(0, 10))

    def load_user(self, user: EntraUser):
        """
        Load user and detect applicable vendors

        Args:
            user: EntraUser with full details including groups
        """
        logger.info(f"Loading user for provisioning: {user.display_name}")

        self.current_user = user

        # Hide "no user" message, show content
        self.no_user_frame.pack_forget()
        self.user_content_frame.pack(fill="both", expand=True)

        # Display user info
        self._display_user_info()

        # Detect and display vendors
        self._detect_vendors()
        self._display_vendors()

        logger.info(f"User loaded with {len(self.detected_vendors)} vendor(s) detected")

    def _display_user_info(self):
        """Display user information"""
        # Clear existing content
        for widget in self.user_info_container.winfo_children():
            widget.destroy()

        user = self.current_user

        # User details grid
        details_frame = ctk.CTkFrame(self.user_info_container)
        details_frame.pack(fill="x", pady=10)

        # Column 1
        col1 = ctk.CTkFrame(details_frame, fg_color="transparent")
        col1.pack(side="left", fill="both", expand=True, padx=15, pady=15)

        self._add_user_field(col1, "Name", user.display_name)
        self._add_user_field(col1, "Email", user.email)
        if user.employee_id:
            self._add_user_field(col1, "Employee ID", user.employee_id)

        # Column 2
        col2 = ctk.CTkFrame(details_frame, fg_color="transparent")
        col2.pack(side="left", fill="both", expand=True, padx=15, pady=15)

        if user.job_title:
            self._add_user_field(col2, "Job Title", user.job_title)
        if user.department:
            self._add_user_field(col2, "Department", user.department)
        if user.office_location:
            self._add_user_field(col2, "Office", user.office_location)

        # Groups section
        if user.groups:
            groups_frame = ctk.CTkFrame(self.user_info_container)
            groups_frame.pack(fill="x", pady=(10, 0))

            groups_label = ctk.CTkLabel(
                groups_frame,
                text=f"Group Memberships ({len(user.groups)})",
                font=ctk.CTkFont(size=13, weight="bold")
            )
            groups_label.pack(padx=15, pady=(10, 5), anchor="w")

            # Make textbox much taller for many groups, and scrollable
            groups_text = ctk.CTkTextbox(groups_frame, height=200)
            groups_text.pack(fill="x", padx=15, pady=(0, 10))

            # Sort groups alphabetically and insert
            sorted_groups = sorted(user.groups, key=lambda g: g.display_name.lower())
            for group in sorted_groups:
                groups_text.insert("end", f"• {group.display_name}\n")

            groups_text.configure(state="disabled")

    def _add_user_field(self, parent, label: str, value: str):
        """Add a user field to the display"""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="x", pady=5)

        label_widget = ctk.CTkLabel(
            container,
            text=f"{label}:",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        label_widget.pack(anchor="w")

        value_widget = ctk.CTkLabel(
            container,
            text=value,
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        value_widget.pack(anchor="w")

    def _detect_vendors(self):
        """Load all enabled vendors; auto-select those matching user's groups"""
        self.detected_vendors = []
        self.selected_vendors = []

        user_groups = self.current_user.groups if self.current_user else []
        logger.info(f"User has {len(user_groups)} groups")
        if user_groups:
            logger.debug(f"User groups: {[g.display_name for g in user_groups]}")

        # Get all enabled vendor mappings
        mappings = self.config_manager.get_enabled_vendors()
        logger.info(f"Loading {len(mappings)} enabled vendor(s)")

        # Build vendor configs for ALL enabled vendors
        for mapping in mappings:
            group_name = mapping.get('entra_group_name')
            is_member = (
                self.current_user is not None
                and self.current_user.is_member_of(group_name)
            )

            if is_member:
                logger.info(f"✓ MATCH: User is member of '{group_name}' - auto-selecting {mapping.get('vendor_name')}")
            else:
                logger.info(f"✗ NO MATCH: '{group_name}' - showing {mapping.get('vendor_name')} unchecked")

            vendor = VendorConfig(
                name=mapping.get('vendor_name'),
                display_name=mapping.get('vendor_display_name'),
                entra_group_name=group_name,
                is_auto_detected=is_member,
                is_selected=is_member
            )
            self.detected_vendors.append(vendor)
            if is_member:
                self.selected_vendors.append(vendor.name)

        auto_count = len(self.selected_vendors)
        logger.info(f"Loaded {len(self.detected_vendors)} vendor(s), {auto_count} auto-selected")

    def _display_vendors(self):
        """Display vendor cards — all enabled vendors shown, auto-detected ones pre-checked"""
        # Clear existing content
        for widget in self.vendors_container.winfo_children():
            widget.destroy()

        # Update count to show how many were auto-detected
        auto_count = sum(1 for v in self.detected_vendors if v.is_auto_detected)
        self.vendors_count_label.configure(
            text=f"({auto_count} auto-detected)"
        )

        # Create vendor cards for all enabled vendors
        for vendor in self.detected_vendors:
            self._create_vendor_card(vendor)

        # Show disabled vendor cards (grayed out, e.g. Experience.com)
        disabled_mappings = self.config_manager.get_disabled_vendors()
        for mapping in disabled_mappings:
            self._create_disabled_vendor_card(mapping)

        # Enable start button if vendors are selected
        self._update_start_button()

    def _create_vendor_card(self, vendor: VendorConfig):
        """Create a vendor selection card"""
        card = ctk.CTkFrame(self.vendors_container)
        card.pack(fill="x", pady=2)

        # Checkbox and vendor info container
        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.pack(fill="x", padx=15, pady=8)

        # Checkbox for selection
        checkbox_var = ctk.BooleanVar(value=vendor.is_selected)
        checkbox = ctk.CTkCheckBox(
            content_frame,
            text="",
            variable=checkbox_var,
            command=lambda v=vendor, var=checkbox_var: self._on_vendor_toggled(v, var)
        )
        checkbox.pack(side="left", padx=(0, 10))

        # Vendor info
        info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)

        name_label = ctk.CTkLabel(
            info_frame,
            text=vendor.display_name,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        name_label.pack(anchor="w")

        group_label = ctk.CTkLabel(
            info_frame,
            text=f"Group: {vendor.entra_group_name}",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w"
        )
        group_label.pack(anchor="w")

        # Auto-detected badge
        if vendor.is_auto_detected:
            badge = ctk.CTkLabel(
                content_frame,
                text="AUTO-DETECTED",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="green"
            )
            badge.pack(side="right", padx=(10, 0))

    def _create_disabled_vendor_card(self, mapping: dict):
        """Create a grayed-out vendor card for a disabled vendor"""
        card = ctk.CTkFrame(self.vendors_container, fg_color="#2b2b2b")
        card.pack(fill="x", pady=2)

        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.pack(fill="x", padx=15, pady=8)

        # Disabled checkbox (unchecked, non-interactive)
        checkbox = ctk.CTkCheckBox(
            content_frame,
            text="",
            state="disabled"
        )
        checkbox.pack(side="left", padx=(0, 10))

        # Vendor info (grayed out)
        info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)

        name_label = ctk.CTkLabel(
            info_frame,
            text=mapping.get('vendor_display_name', mapping.get('vendor_name', '')),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#666666",
            anchor="w"
        )
        name_label.pack(anchor="w")

        group_label = ctk.CTkLabel(
            info_frame,
            text=f"Group: {mapping.get('entra_group_name', '')}",
            font=ctk.CTkFont(size=11),
            text_color="#555555",
            anchor="w"
        )
        group_label.pack(anchor="w")

        # "DISABLED" badge
        badge = ctk.CTkLabel(
            content_frame,
            text="DISABLED",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#666666"
        )
        badge.pack(side="right", padx=(10, 0))

    def _on_vendor_toggled(self, vendor: VendorConfig, var: ctk.BooleanVar):
        """Handle vendor checkbox toggle"""
        is_selected = var.get()
        vendor.is_selected = is_selected

        if is_selected:
            if vendor.name not in self.selected_vendors:
                self.selected_vendors.append(vendor.name)
        else:
            if vendor.name in self.selected_vendors:
                self.selected_vendors.remove(vendor.name)

        logger.info(f"Vendor {vendor.name} {'selected' if is_selected else 'deselected'}")
        self._update_start_button()

    def _update_start_button(self):
        """Update start button state based on selections"""
        if self.selected_vendors:
            self.start_btn.configure(state="normal")
            count = len(self.selected_vendors)
            self.start_btn.configure(text=f"Start Automation → ({count} vendor{'s' if count > 1 else ''})")
        else:
            self.start_btn.configure(state="disabled")
            self.start_btn.configure(text="Start Automation →")

    def _on_start_automation_clicked(self):
        """Handle start automation button click"""
        if not self.current_user or not self.selected_vendors:
            return

        logger.info(f"Starting automation for {len(self.selected_vendors)} vendor(s)")

        # Get selected vendor configs
        selected_vendor_configs = [v for v in self.detected_vendors if v.is_selected]

        # Call callback with user and vendors
        self.on_start_automation(self.current_user, selected_vendor_configs)

    def _on_back_clicked(self):
        """Handle back button click"""
        logger.info("Returning to user search")
        # TODO: Switch back to tab 1
        # This will be implemented when we wire up the tab switching

    def clear(self):
        """Clear the current user and vendors"""
        self.current_user = None
        self.detected_vendors = []
        self.selected_vendors = []

        # Show "no user" message
        self.user_content_frame.pack_forget()
        self.no_user_frame.pack(fill="both", expand=True, padx=20, pady=20)
