"""
Tab 1: User Search

Provides Microsoft authentication and user search functionality:
- Authentication panel with sign-in button
- User search with multiple search types
- Search results table
"""

import customtkinter as ctk
import threading
from typing import Callable, Optional, List

from services.auth_service import AuthService, AuthenticationError
from services.graph_api import GraphAPIClient, SearchType, GraphAPIError
from services.config_manager import ConfigManager
from models.user import EntraUser
from utils.logger import get_logger

logger = get_logger(__name__)


class UserSearchTab:
    """User Search tab implementation"""

    def __init__(
        self,
        parent: ctk.CTkFrame,
        auth_service: AuthService,
        graph_client: GraphAPIClient,
        config_manager: ConfigManager,
        on_user_selected: Callable
    ):
        self.parent = parent
        self.auth_service = auth_service
        self.graph_client = graph_client
        self.config_manager = config_manager
        self.on_user_selected = on_user_selected

        self.scopes = config_manager.get('microsoft.scopes')
        self.search_results: List[EntraUser] = []
        self.selected_user: Optional[EntraUser] = None

        # Create UI
        self._create_ui()

        # Check if already authenticated
        if self.auth_service.is_authenticated():
            self._on_sign_in_success()

        logger.info("User Search tab initialized")

    def _create_ui(self):
        """Create UI components"""
        # Main container
        main_frame = ctk.CTkFrame(self.parent)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Create sections
        self._create_auth_section(main_frame)
        self._create_search_section(main_frame)
        self._create_results_section(main_frame)

    def _create_auth_section(self, parent):
        """Create authentication section"""
        auth_frame = ctk.CTkFrame(parent)
        auth_frame.pack(fill="x", padx=0, pady=(0, 20))

        # Title
        title_label = ctk.CTkLabel(
            auth_frame,
            text="Microsoft Sign-In",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(padx=20, pady=(15, 10), anchor="w")

        # Status and button container
        status_frame = ctk.CTkFrame(auth_frame, fg_color="transparent")
        status_frame.pack(fill="x", padx=20, pady=(0, 15))

        # Status indicator with colored dot
        indicator_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        indicator_frame.pack(side="left", padx=(0, 20))

        # Colored status dot (canvas)
        self.status_dot = ctk.CTkCanvas(
            indicator_frame,
            width=12,
            height=12,
            bg="#2b2b2b",
            highlightthickness=0
        )
        self.status_dot.pack(side="left", padx=(0, 8))
        self.status_circle = self.status_dot.create_oval(2, 2, 10, 10, fill="gray", outline="")

        # Status text
        self.status_label = ctk.CTkLabel(
            indicator_frame,
            text="Not Connected",
            font=ctk.CTkFont(size=14)
        )
        self.status_label.pack(side="left")

        # Sign in button
        self.sign_in_btn = ctk.CTkButton(
            status_frame,
            text="🔑 Sign In with Microsoft",
            command=self._on_sign_in_clicked,
            width=200,
            height=35,
            font=ctk.CTkFont(size=14)
        )
        self.sign_in_btn.pack(side="left")

        # Sign out button (hidden initially)
        self.sign_out_btn = ctk.CTkButton(
            status_frame,
            text="Sign Out",
            command=self._on_sign_out_clicked,
            width=100,
            height=35,
            fg_color="gray"
        )
        # Don't pack yet - will show after sign-in

    def _create_search_section(self, parent):
        """Create user search section"""
        self.search_frame = ctk.CTkFrame(parent)
        self.search_frame.pack(fill="x", padx=0, pady=(0, 20))

        # Title
        title_label = ctk.CTkLabel(
            self.search_frame,
            text="User Search",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(padx=20, pady=(15, 10), anchor="w")

        # Search controls
        controls_frame = ctk.CTkFrame(self.search_frame, fg_color="transparent")
        controls_frame.pack(fill="x", padx=20, pady=(0, 15))

        # Search type dropdown
        ctk.CTkLabel(controls_frame, text="Search By:").pack(side="left", padx=(0, 10))

        self.search_type_var = ctk.StringVar(value="Display Name")
        self.search_type_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.search_type_var,
            values=["Display Name", "Email", "First Name", "Last Name", "Employee ID"],
            width=150
        )
        self.search_type_dropdown.pack(side="left", padx=(0, 20))

        # Search entry
        self.search_entry = ctk.CTkEntry(
            controls_frame,
            placeholder_text="Enter search query...",
            width=400,
            height=35
        )
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self._on_search_clicked())

        # Search button
        self.search_btn = ctk.CTkButton(
            controls_frame,
            text="🔍 Search",
            command=self._on_search_clicked,
            width=100,
            height=35
        )
        self.search_btn.pack(side="left")

        # Disable search controls initially
        self._set_search_enabled(False)

    def _create_results_section(self, parent):
        """Create search results section"""
        # Results container frame
        results_container = ctk.CTkFrame(parent)
        results_container.pack(fill="both", expand=True, padx=0, pady=0)

        # Results frame (holds title and scrollable results)
        results_frame = ctk.CTkFrame(results_container)
        results_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Title with result count
        title_frame = ctk.CTkFrame(results_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(15, 10))

        self.results_title_label = ctk.CTkLabel(
            title_frame,
            text="Search Results",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.results_title_label.pack(side="left")

        self.results_count_label = ctk.CTkLabel(
            title_frame,
            text="",
            font=ctk.CTkFont(size=14)
        )
        self.results_count_label.pack(side="left", padx=(10, 0))

        # Results scrollable frame
        self.results_scroll = ctk.CTkScrollableFrame(results_frame, height=300)
        self.results_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # Button frame at bottom (outside scrollable area) - always visible
        self.button_frame = ctk.CTkFrame(results_container, height=70)
        self.button_frame.pack(fill="x", padx=0, pady=0)
        self.button_frame.pack_propagate(False)

        # Select user button (hidden initially, but in fixed position)
        self.select_user_btn = ctk.CTkButton(
            self.button_frame,
            text="Select User →",
            command=self._on_select_user_clicked,
            width=150,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        # Don't pack yet

    def _set_search_enabled(self, enabled: bool):
        """Enable/disable search controls"""
        state = "normal" if enabled else "disabled"
        self.search_entry.configure(state=state)
        self.search_btn.configure(state=state)
        self.search_type_dropdown.configure(state=state)

    def _on_sign_in_clicked(self):
        """Handle sign-in button click"""
        logger.info("Sign-in button clicked")
        self.sign_in_btn.configure(state="disabled", text="Signing in...")
        self.status_dot.itemconfig(self.status_circle, fill="yellow")
        self.status_label.configure(text="Connecting...")

        # Perform authentication in background thread
        def authenticate():
            try:
                self.auth_service.sign_in_interactive(self.scopes)
                # Update UI in main thread
                self.parent.after(0, self._on_sign_in_success)
            except AuthenticationError as e:
                logger.error(f"Authentication failed: {e}")
                self.parent.after(0, lambda: self._on_sign_in_error(str(e)))

        thread = threading.Thread(target=authenticate, daemon=True)
        thread.start()

    def _on_sign_in_success(self):
        """Handle successful sign-in"""
        username = self.auth_service.get_current_username()
        logger.info(f"Sign-in successful: {username}")

        self.status_dot.itemconfig(self.status_circle, fill="green")
        self.status_label.configure(text=f"Connected as: {username}")
        self.sign_in_btn.pack_forget()
        self.sign_out_btn.pack(side="left")

        # Enable search
        self._set_search_enabled(True)

    def _on_sign_in_error(self, error_message: str):
        """Handle sign-in error"""
        self.status_dot.itemconfig(self.status_circle, fill="red")
        self.status_label.configure(text="Sign-in failed")
        self.sign_in_btn.configure(state="normal", text="🔑 Sign In with Microsoft")

        # Show error dialog
        self._show_error("Authentication Error", error_message)

    def _on_sign_out_clicked(self):
        """Handle sign-out button click"""
        logger.info("Sign-out button clicked")
        self.auth_service.sign_out()

        # Update UI
        self.status_dot.itemconfig(self.status_circle, fill="gray")
        self.status_label.configure(text="Not Connected")
        self.sign_out_btn.pack_forget()
        self.sign_in_btn.pack(side="left")
        self.sign_in_btn.configure(state="normal", text="🔑 Sign In with Microsoft")

        # Disable search and clear results
        self._set_search_enabled(False)
        self._clear_results()

    def _on_search_clicked(self):
        """Handle search button click"""
        query = self.search_entry.get().strip()
        if not query:
            self._show_error("Search Error", "Please enter a search query")
            return

        # Map UI search type to SearchType enum
        search_type_map = {
            "Display Name": SearchType.DISPLAY_NAME,
            "Email": SearchType.EMAIL,
            "First Name": SearchType.FIRST_NAME,
            "Last Name": SearchType.LAST_NAME,
            "Employee ID": SearchType.EMPLOYEE_ID
        }
        search_type = search_type_map[self.search_type_var.get()]

        logger.info(f"Searching for: {query} (type: {search_type.value})")

        # Disable search during operation
        self.search_btn.configure(state="disabled", text="Searching...")
        self._clear_results()

        # Perform search in background thread
        def search():
            try:
                results = self.graph_client.search_users(query, search_type)
                self.parent.after(0, lambda: self._on_search_success(results))
            except GraphAPIError as e:
                logger.error(f"Search failed: {e}")
                self.parent.after(0, lambda: self._on_search_error(str(e)))

        thread = threading.Thread(target=search, daemon=True)
        thread.start()

    def _on_search_success(self, results: List[EntraUser]):
        """Handle successful search"""
        self.search_results = results
        logger.info(f"Search returned {len(results)} result(s)")

        # Update results count
        self.results_count_label.configure(text=f"({len(results)} found)")

        # Display results
        self._display_results(results)

        # Re-enable search
        self.search_btn.configure(state="normal", text="🔍 Search")

    def _on_search_error(self, error_message: str):
        """Handle search error"""
        self.search_btn.configure(state="normal", text="🔍 Search")
        self._show_error("Search Error", error_message)

    def _display_results(self, results: List[EntraUser]):
        """Display search results"""
        self._clear_results()

        if not results:
            no_results_label = ctk.CTkLabel(
                self.results_scroll,
                text="No users found",
                font=ctk.CTkFont(size=14)
            )
            no_results_label.pack(pady=20)
            return

        # Create result cards
        for user in results:
            self._create_user_card(user)

    def _create_user_card(self, user: EntraUser):
        """Create a user result card"""
        card = ctk.CTkFrame(self.results_scroll, cursor="hand2")
        card.pack(fill="x", padx=5, pady=5)

        # Make card and all children selectable
        def select_handler(e):
            self._select_user(user)

        card.bind("<Button-1>", select_handler)

        # User info
        info_frame = ctk.CTkFrame(card, fg_color="transparent", cursor="hand2")
        info_frame.pack(fill="x", padx=15, pady=10)
        info_frame.bind("<Button-1>", select_handler)

        # Name
        name_label = ctk.CTkLabel(
            info_frame,
            text=user.display_name,
            font=ctk.CTkFont(size=14, weight="bold"),
            cursor="hand2"
        )
        name_label.pack(anchor="w")
        name_label.bind("<Button-1>", select_handler)

        # Email
        email_label = ctk.CTkLabel(
            info_frame,
            text=user.email,
            font=ctk.CTkFont(size=12),
            cursor="hand2"
        )
        email_label.pack(anchor="w")
        email_label.bind("<Button-1>", select_handler)

        # Job title and department
        if user.job_title or user.department:
            details = f"{user.job_title or ''}"
            if user.department:
                details += f" - {user.department}"
            details_label = ctk.CTkLabel(
                info_frame,
                text=details,
                font=ctk.CTkFont(size=11),
                text_color="gray",
                cursor="hand2"
            )
            details_label.pack(anchor="w")
            details_label.bind("<Button-1>", select_handler)

        # Store user reference
        card.user = user

    def _select_user(self, user: EntraUser):
        """Select a user from results"""
        logger.info(f"User clicked: {user.display_name}")
        self.selected_user = user

        # Highlight selected card
        for widget in self.results_scroll.winfo_children():
            if hasattr(widget, 'user'):
                if widget.user == user:
                    widget.configure(border_width=2, border_color="white")
                else:
                    widget.configure(border_width=0)

        # Show select button (right-aligned in button frame with padding)
        self.select_user_btn.pack(side="right", padx=20, pady=15)

    def _on_select_user_clicked(self):
        """Handle select user button click"""
        if self.selected_user:
            logger.info(f"Loading full details for: {self.selected_user.display_name}")

            # Load full user details including groups
            def load_details():
                try:
                    full_user = self.graph_client.get_user_details(self.selected_user.id)
                    self.parent.after(0, lambda: self.on_user_selected(full_user))
                except Exception as e:
                    logger.error(f"Failed to load user details: {e}")
                    self.parent.after(0, lambda: self._show_error("Error", f"Failed to load user details: {str(e)}"))

            thread = threading.Thread(target=load_details, daemon=True)
            thread.start()

    def _clear_results(self):
        """Clear search results"""
        for widget in self.results_scroll.winfo_children():
            widget.destroy()
        self.results_count_label.configure(text="")
        self.search_results = []
        self.selected_user = None
        self.select_user_btn.pack_forget()

    def _show_error(self, title: str, message: str):
        """Show error dialog"""
        error_window = ctk.CTkToplevel(self.parent)
        error_window.title(title)
        error_window.geometry("400x200")

        label = ctk.CTkLabel(
            error_window,
            text=message,
            wraplength=350,
            font=ctk.CTkFont(size=12)
        )
        label.pack(padx=20, pady=30)

        close_btn = ctk.CTkButton(
            error_window,
            text="OK",
            command=error_window.destroy,
            width=100
        )
        close_btn.pack(pady=10)
