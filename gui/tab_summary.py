"""
Tab 4: Summary

Displays automation results summary with:
- Completion message
- Per-vendor result cards with expandable screenshots
- Generate PDF button
"""

import customtkinter as ctk
from tkinter import filedialog
from typing import Optional, Callable
from datetime import datetime
from pathlib import Path

from models.automation_result import AutomationSummary, VendorResult
from services.config_manager import ConfigManager
from services.pdf_generator import PDFGenerator
from utils.logger import get_logger

logger = get_logger(__name__)


class SummaryTab:
    """Summary tab implementation"""

    def __init__(
        self,
        parent: ctk.CTkFrame,
        config_manager: ConfigManager,
        on_new_automation: Optional[Callable] = None
    ):
        self.parent = parent
        self.config_manager = config_manager
        self.on_new_automation = on_new_automation
        self.automation_summary: Optional[AutomationSummary] = None

        # Create UI
        self._create_ui()

        logger.info("Summary tab initialized")

    def _create_ui(self):
        """Create UI components"""
        # Main container with scrollbar
        self.main_scroll = ctk.CTkScrollableFrame(self.parent)
        self.main_scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Header section
        self._create_header_section()

        # Stats section (success/failure counts)
        self.stats_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.stats_frame.pack(fill="x", pady=(0, 20))

        # Vendor results container
        self.vendors_container = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.vendors_container.pack(fill="both", expand=True, pady=(0, 20))

        # Action buttons section
        self._create_actions_section()

        # Show "no summary" message initially
        self._show_no_summary()

    def _create_header_section(self):
        """Create header section"""
        header_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))

        # Title
        self.title_label = ctk.CTkLabel(
            header_frame,
            text="Automation Complete",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.pack(anchor="w")

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

        # Generate PDF button
        self.pdf_btn = ctk.CTkButton(
            self.actions_frame,
            text="Generate PDF Report",
            command=self._on_generate_pdf_clicked,
            width=200,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1f538d",
            hover_color="#163d66"
        )
        # Don't pack yet - will show when summary is loaded

        # New Automation button
        self.new_btn = ctk.CTkButton(
            self.actions_frame,
            text="Start New Automation",
            command=self._on_new_automation_clicked,
            width=180,
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color="gray",
            hover_color="#555555"
        )
        # Don't pack yet

    def _show_no_summary(self):
        """Show 'no summary' placeholder"""
        self.no_summary_label = ctk.CTkLabel(
            self.vendors_container,
            text="No Automation Summary\n\nComplete an automation to see results here.",
            font=ctk.CTkFont(size=16),
            text_color="gray"
        )
        self.no_summary_label.pack(expand=True, pady=100)

    def load_summary(self, summary: AutomationSummary):
        """Load automation summary for display"""
        logger.info(f"Loading summary for {summary.user.display_name}")

        self.automation_summary = summary

        # Clear existing content
        for widget in self.vendors_container.winfo_children():
            widget.destroy()
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        # Update header
        self.title_label.configure(text="Automation Complete")
        self.subtitle_label.configure(
            text=f"Provisioning for {summary.user.display_name} - "
                 f"{summary.success_count} of {len(summary.vendor_results)} successful"
        )

        # Display stats
        self._display_stats()

        # Display vendor results
        for vendor_result in summary.vendor_results:
            self._create_vendor_result_card(vendor_result)

        # Show action buttons
        self.pdf_btn.pack(side="right", padx=20)
        self.new_btn.pack(side="right", padx=(0, 10))

        logger.info("Summary loaded successfully")

    def _display_stats(self):
        """Display summary statistics"""
        summary = self.automation_summary

        # Stats container
        stats_card = ctk.CTkFrame(self.stats_frame)
        stats_card.pack(fill="x", pady=10)

        stats_inner = ctk.CTkFrame(stats_card, fg_color="transparent")
        stats_inner.pack(fill="x", padx=20, pady=15)

        # Success count
        success_frame = ctk.CTkFrame(stats_inner, fg_color="transparent")
        success_frame.pack(side="left", padx=(0, 40))

        success_count_label = ctk.CTkLabel(
            success_frame,
            text=str(summary.success_count),
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="green"
        )
        success_count_label.pack()

        success_text_label = ctk.CTkLabel(
            success_frame,
            text="Successful",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        success_text_label.pack()

        # Failure count
        failure_frame = ctk.CTkFrame(stats_inner, fg_color="transparent")
        failure_frame.pack(side="left", padx=(0, 40))

        failure_count_label = ctk.CTkLabel(
            failure_frame,
            text=str(summary.failure_count),
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="red" if summary.failure_count > 0 else "gray"
        )
        failure_count_label.pack()

        failure_text_label = ctk.CTkLabel(
            failure_frame,
            text="Failed",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        failure_text_label.pack()

        # Duration
        duration_frame = ctk.CTkFrame(stats_inner, fg_color="transparent")
        duration_frame.pack(side="left")

        duration_seconds = summary.total_duration_seconds
        if duration_seconds >= 60:
            duration_text = f"{int(duration_seconds // 60)}m {int(duration_seconds % 60)}s"
        else:
            duration_text = f"{int(duration_seconds)}s"

        duration_count_label = ctk.CTkLabel(
            duration_frame,
            text=duration_text,
            font=ctk.CTkFont(size=36, weight="bold")
        )
        duration_count_label.pack()

        duration_text_label = ctk.CTkLabel(
            duration_frame,
            text="Total Time",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        duration_text_label.pack()

    def _create_vendor_result_card(self, vendor_result: VendorResult):
        """Create a vendor result card"""
        card = ctk.CTkFrame(self.vendors_container)
        card.pack(fill="x", pady=10)

        # Header with vendor name and status
        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 10))

        # Status icon and vendor name
        status_icon = "\u2713" if vendor_result.success else "\u2717"
        status_color = "green" if vendor_result.success else "red"

        status_label = ctk.CTkLabel(
            header_frame,
            text=status_icon,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=status_color
        )
        status_label.pack(side="left", padx=(0, 10))

        vendor_label = ctk.CTkLabel(
            header_frame,
            text=vendor_result.display_name,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        vendor_label.pack(side="left")

        # Duration on the right
        if vendor_result.duration_seconds > 0:
            duration_label = ctk.CTkLabel(
                header_frame,
                text=f"{vendor_result.duration_seconds:.1f}s",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            )
            duration_label.pack(side="right")

        # Errors section (only show if there are errors)
        if vendor_result.errors:
            errors_frame = ctk.CTkFrame(card)
            errors_frame.pack(fill="x", padx=20, pady=(0, 10))

            errors_label = ctk.CTkLabel(
                errors_frame,
                text="Errors:",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="red"
            )
            errors_label.pack(anchor="w", padx=10, pady=(10, 5))

            for error in vendor_result.errors:
                error_item = ctk.CTkLabel(
                    errors_frame,
                    text=f"  \u2022 {error}",
                    font=ctk.CTkFont(size=11),
                    text_color="red",
                    anchor="w"
                )
                error_item.pack(anchor="w", padx=10)

            # Add bottom padding
            ctk.CTkLabel(errors_frame, text="", height=5).pack()

        # Screenshot thumbnail (placeholder or actual)
        screenshot_frame = ctk.CTkFrame(card, fg_color="transparent")
        screenshot_frame.pack(fill="x", padx=20, pady=(0, 15))

        if vendor_result.screenshot_path and Path(vendor_result.screenshot_path).exists():
            # Create clickable thumbnail
            self._create_screenshot_thumbnail(screenshot_frame, vendor_result.screenshot_path)
        else:
            # Placeholder
            placeholder_frame = ctk.CTkFrame(screenshot_frame, fg_color="#3a3a3a", height=80, width=150)
            placeholder_frame.pack(anchor="w")
            placeholder_frame.pack_propagate(False)

            placeholder_label = ctk.CTkLabel(
                placeholder_frame,
                text="[Screenshot\nPlaceholder]",
                font=ctk.CTkFont(size=10),
                text_color="gray"
            )
            placeholder_label.pack(expand=True)

    def _create_screenshot_thumbnail(self, parent, screenshot_path: str):
        """Create a clickable screenshot thumbnail"""
        try:
            from PIL import Image

            # Load and resize image for thumbnail
            img = Image.open(screenshot_path)
            img.thumbnail((200, 150))

            # Convert to CTkImage
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(200, 150))

            # Create clickable label
            thumb_label = ctk.CTkLabel(
                parent,
                text="",
                image=ctk_img,
                cursor="hand2"
            )
            thumb_label.pack(anchor="w")
            thumb_label.image = ctk_img  # Keep reference

            # Bind click event
            thumb_label.bind("<Button-1>", lambda e: self._show_full_image(screenshot_path))

            # "Click to expand" text
            expand_hint = ctk.CTkLabel(
                parent,
                text="Click to expand",
                font=ctk.CTkFont(size=10),
                text_color="gray"
            )
            expand_hint.pack(anchor="w")

        except Exception as e:
            logger.error(f"Error loading screenshot: {e}")
            error_label = ctk.CTkLabel(
                parent,
                text="[Screenshot unavailable]",
                font=ctk.CTkFont(size=11),
                text_color="gray"
            )
            error_label.pack(anchor="w")

    def _show_full_image(self, image_path: str):
        """Show full-size image in a popup window"""
        try:
            from PIL import Image

            # Create popup window
            popup = ctk.CTkToplevel(self.parent)
            popup.title("Screenshot")
            popup.geometry("1000x700")
            popup.grab_set()  # Make modal

            # Load full image
            img = Image.open(image_path)

            # Resize to fit window while maintaining aspect ratio
            max_width, max_height = 980, 650
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)

            # Display image
            img_label = ctk.CTkLabel(popup, text="", image=ctk_img)
            img_label.pack(expand=True, pady=10)
            img_label.image = ctk_img  # Keep reference

            # Close button
            close_btn = ctk.CTkButton(
                popup,
                text="Close",
                command=popup.destroy,
                width=100
            )
            close_btn.pack(pady=10)

        except Exception as e:
            logger.error(f"Error showing full image: {e}")

    def _on_generate_pdf_clicked(self):
        """Handle Generate PDF button click"""
        if not self.automation_summary:
            return

        logger.info("Generating PDF report")

        # Create suggested filename
        user_name = self.automation_summary.user.display_name.replace(" ", "_")
        date_str = datetime.now().strftime("%Y%m%d")
        suggested_filename = f"{user_name}_VendorProvisioning_{date_str}.pdf"

        # Open save dialog
        file_path = filedialog.asksaveasfilename(
            title="Save PDF Report",
            defaultextension=".pdf",
            initialfile=suggested_filename,
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )

        if not file_path:
            logger.info("PDF save cancelled by user")
            return

        try:
            # Generate PDF
            generator = PDFGenerator()
            generator.generate_report(self.automation_summary, file_path)

            logger.info(f"PDF saved to: {file_path}")

            # Show success message
            self._show_success_message(f"PDF saved to:\n{file_path}")

        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            self._show_error_message(f"Error generating PDF: {str(e)}")

    def _show_success_message(self, message: str):
        """Show success popup"""
        popup = ctk.CTkToplevel(self.parent)
        popup.title("Success")
        popup.geometry("400x150")
        popup.grab_set()

        msg_label = ctk.CTkLabel(
            popup,
            text=message,
            font=ctk.CTkFont(size=14)
        )
        msg_label.pack(expand=True, pady=20)

        ok_btn = ctk.CTkButton(popup, text="OK", command=popup.destroy, width=100)
        ok_btn.pack(pady=(0, 20))

    def _show_error_message(self, message: str):
        """Show error popup"""
        popup = ctk.CTkToplevel(self.parent)
        popup.title("Error")
        popup.geometry("400x150")
        popup.grab_set()

        msg_label = ctk.CTkLabel(
            popup,
            text=message,
            font=ctk.CTkFont(size=14),
            text_color="red"
        )
        msg_label.pack(expand=True, pady=20)

        ok_btn = ctk.CTkButton(popup, text="OK", command=popup.destroy, width=100)
        ok_btn.pack(pady=(0, 20))

    def _on_new_automation_clicked(self):
        """Handle New Automation button click"""
        logger.info("Starting new automation")
        if self.on_new_automation:
            self.on_new_automation()

    def clear(self):
        """Clear the summary"""
        self.automation_summary = None

        # Clear UI
        for widget in self.vendors_container.winfo_children():
            widget.destroy()
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        self.subtitle_label.configure(text="")
        self.pdf_btn.pack_forget()
        self.new_btn.pack_forget()

        # Show placeholder
        self._show_no_summary()
