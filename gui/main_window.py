"""
Main Window - Nexus GUI Application

Main application window with tabbed interface:
- Tab 1: User Search
- Tab 2: Account Provisioning (placeholder)
- Tab 3: Automation Status (placeholder)
- Tab 4: Settings (placeholder)
"""

import os
import sys
import ctypes
import customtkinter as ctk
from services.config_manager import ConfigManager

# Set Windows AppUserModelID so the taskbar shows our icon instead of Python's
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("HighlandMortgage.Nexus.1.0")
except Exception:
    pass
from services.auth_service import AuthService
from services.graph_api import GraphAPIClient
from services.keyvault_service import KeyVaultService
from services.msal_credential_adapter import MSALCredentialAdapter
from gui.tab_search import UserSearchTab
from gui.tab_provisioning import AccountProvisioningTab
from gui.tab_automation import AutomationStatusTab
from gui.tab_summary import SummaryTab
from utils.logger import get_logger

logger = get_logger(__name__)

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class NexusMainWindow(ctk.CTk):
    """Main application window"""

    def __init__(self, config_manager: ConfigManager, version: str = ""):
        super().__init__()

        self.config_manager = config_manager
        self.app_version = version
        logger.info("Initializing Nexus Main Window")

        # Validate configuration
        is_valid, errors = config_manager.validate_configuration()
        if not is_valid:
            logger.error(f"Configuration errors: {errors}")
            self._show_config_error(errors)
            return

        # Initialize services
        self._initialize_services()

        # Set up window
        title = f"Nexus v{self.app_version} - Automated Vendor Account Provisioning" if self.app_version else "Nexus - Automated Vendor Account Provisioning"
        self.title(title)

        # Set window icon using Win32 API for proper multi-size support.
        # Tkinter's iconbitmap() only loads one size from the ICO.
        # Windows needs WM_SETICON with ICON_SMALL (title bar) and ICON_BIG (taskbar)
        # so it picks the correct resolution frame from the multi-size ICO.
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_path = os.path.join(base_path, "assets", "nexus.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)  # Fallback for Tk internals
            self.after(200, lambda: self._set_window_icons(icon_path))

        # Set minimum window size
        self.minsize(1200, 900)

        # Set initial size and center on screen
        window_width = 1400
        window_height = 950
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Create UI
        self._create_header()
        self._create_tabs()

        logger.info("Main window initialized successfully")

    def _initialize_services(self):
        """Initialize authentication and API services"""
        logger.info("Initializing services")

        # Get configuration
        tenant_id = self.config_manager.get('microsoft.tenant_id')
        client_id = self.config_manager.get('microsoft.client_id')
        redirect_uri = self.config_manager.get('microsoft.redirect_uri')
        scopes = self.config_manager.get('microsoft.scopes')
        vault_url = self.config_manager.get('azure_keyvault.vault_url')

        # Initialize authentication service
        self.auth_service = AuthService(
            tenant_id=tenant_id,
            client_id=client_id,
            redirect_uri=redirect_uri
        )

        # Initialize Graph API client
        self.graph_client = GraphAPIClient(
            auth_service=self.auth_service,
            scopes=scopes
        )

        # Initialize Key Vault service with MSAL credential adapter
        # This allows using the same user sign-in for both Graph API and Key Vault
        try:
            # Create credential adapter that uses MSAL tokens
            msal_credential = MSALCredentialAdapter(
                auth_service=self.auth_service,
                scopes=["https://vault.azure.net/.default"]
            )

            # Initialize Key Vault with the MSAL credential
            self.keyvault_service = KeyVaultService(
                vault_url=vault_url,
                credential=msal_credential,
                skip_connection_test=True  # Skip test initially, will authenticate when user signs in
            )
            logger.info("Key Vault service initialized with interactive browser authentication")

        except Exception as e:
            logger.warning(f"Could not initialize Key Vault service: {e}")
            self.keyvault_service = None

        logger.info("Services initialized")

    def _create_header(self):
        """Create header with title and status"""
        header_frame = ctk.CTkFrame(self, height=60, corner_radius=0)
        header_frame.pack(fill="x", padx=0, pady=0)
        header_frame.pack_propagate(False)

        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="NEXUS",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(side="left", padx=20, pady=10)

        # Subtitle
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Automated Vendor Account Provisioning",
            font=ctk.CTkFont(size=14)
        )
        subtitle_label.pack(side="left", padx=0, pady=10)

    def _create_tabs(self):
        """Create tab view"""
        # Create tab view
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Add tabs
        self.tabview.add("User Search")
        self.tabview.add("Account Provisioning")
        self.tabview.add("Automation Status")
        self.tabview.add("Summary")

        # Initialize Tab 1: User Search
        self.tab_search = UserSearchTab(
            parent=self.tabview.tab("User Search"),
            auth_service=self.auth_service,
            graph_client=self.graph_client,
            config_manager=self.config_manager,
            on_user_selected=self._on_user_selected
        )

        # Initialize Tab 2: Account Provisioning
        self.tab_provisioning = AccountProvisioningTab(
            parent=self.tabview.tab("Account Provisioning"),
            config_manager=self.config_manager,
            on_start_automation=self._on_start_automation
        )

        # Initialize Tab 3: Automation Status
        self.tab_automation = AutomationStatusTab(
            parent=self.tabview.tab("Automation Status"),
            config_manager=self.config_manager,
            on_view_summary=self._on_view_summary
        )

        # Initialize Tab 4: Summary
        self.tab_summary = SummaryTab(
            parent=self.tabview.tab("Summary"),
            config_manager=self.config_manager,
            on_new_automation=self._on_new_automation
        )

    def _create_placeholder_tab(self, parent, tab_name):
        """Create placeholder for tabs not yet implemented"""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        label = ctk.CTkLabel(
            frame,
            text=f"{tab_name}\n\nComing soon...",
            font=ctk.CTkFont(size=18)
        )
        label.pack(expand=True)

    def _on_user_selected(self, user):
        """Callback when user is selected from search"""
        logger.info(f"User selected: {user.display_name}")

        # Load user in provisioning tab
        self.tab_provisioning.load_user(user)

        # Switch to Account Provisioning tab
        self.tabview.set("Account Provisioning")

    def _on_start_automation(self, user, vendors):
        """Callback when automation is started"""
        logger.info(f"Starting automation for {user.display_name} with {len(vendors)} vendor(s)")

        # Switch to Automation Status tab and start automation
        self.tabview.set("Automation Status")

        # Start the automation
        self.tab_automation.start_automation(user, vendors)

    def _on_view_summary(self, automation_summary):
        """Callback when View Summary is clicked from Automation tab"""
        logger.info(f"Viewing summary for {automation_summary.user.display_name}")

        # Load summary in summary tab
        self.tab_summary.load_summary(automation_summary)

        # Switch to Summary tab
        self.tabview.set("Summary")

    def _on_new_automation(self):
        """Callback when Start New Automation is clicked from Summary tab"""
        logger.info("Starting new automation session")

        # Clear summary tab
        self.tab_summary.clear()

        # Clear automation tab
        self.tab_automation.clear()

        # Switch to User Search tab
        self.tabview.set("User Search")

    def _show_config_error(self, errors: list):
        """Show configuration error dialog"""
        error_window = ctk.CTkToplevel(self)
        error_window.title("Configuration Error")
        error_window.geometry("500x300")

        label = ctk.CTkLabel(
            error_window,
            text="Configuration Errors:",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        label.pack(padx=20, pady=20)

        for error in errors:
            error_label = ctk.CTkLabel(error_window, text=f"• {error}")
            error_label.pack(padx=20, pady=5)

        close_btn = ctk.CTkButton(
            error_window,
            text="Close",
            command=error_window.destroy
        )
        close_btn.pack(padx=20, pady=20)

    def _set_window_icons(self, icon_path):
        """Set window icons using Win32 API for proper multi-size ICO support.

        LoadImage reads the ICO file and picks the best frame for the requested
        size. SendMessage with WM_SETICON tells Windows which icon to use for
        the title bar (ICON_SMALL) and taskbar/Alt+Tab (ICON_BIG) independently.
        """
        try:
            self.iconbitmap(icon_path)  # Reapply for Tk internals

            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())

            # LoadImage flags
            IMAGE_ICON = 1
            LR_LOADFROMFILE = 0x0010
            LR_DEFAULTSIZE = 0x0040

            # WM_SETICON constants
            WM_SETICON = 0x0080
            ICON_SMALL = 0
            ICON_BIG = 1

            # Get system icon sizes (respects DPI scaling)
            sm_cxsmicon = ctypes.windll.user32.GetSystemMetrics(49)  # SM_CXSMICON
            sm_cxicon = ctypes.windll.user32.GetSystemMetrics(11)    # SM_CXICON

            # Load small icon (title bar) — Windows picks best frame for this size
            hicon_small = ctypes.windll.user32.LoadImageW(
                0, icon_path, IMAGE_ICON,
                sm_cxsmicon, sm_cxsmicon, LR_LOADFROMFILE
            )

            # Load big icon (taskbar, Alt+Tab) — Windows picks best frame for this size
            hicon_big = ctypes.windll.user32.LoadImageW(
                0, icon_path, IMAGE_ICON,
                sm_cxicon, sm_cxicon, LR_LOADFROMFILE
            )

            if hicon_small:
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
            if hicon_big:
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)

            logger.info(f"Window icons set via Win32 API (small={sm_cxsmicon}px, big={sm_cxicon}px)")
        except Exception as e:
            logger.warning(f"Win32 icon set failed, falling back to iconbitmap: {e}")

    def run(self):
        """Run the application"""
        logger.info("Starting Nexus GUI")
        self.mainloop()
