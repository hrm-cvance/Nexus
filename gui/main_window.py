"""
Main Window - Nexus GUI Application

Main application window with tabbed interface:
- Tab 1: User Search
- Tab 2: Account Provisioning (placeholder)
- Tab 3: Automation Status (placeholder)
- Tab 4: Settings (placeholder)
"""

import customtkinter as ctk
from services.config_manager import ConfigManager
from services.auth_service import AuthService
from services.graph_api import GraphAPIClient
from services.keyvault_service import KeyVaultService
from services.msal_credential_adapter import MSALCredentialAdapter
from gui.tab_search import UserSearchTab
from gui.tab_provisioning import AccountProvisioningTab
from gui.tab_automation import AutomationStatusTab
from utils.logger import get_logger

logger = get_logger(__name__)

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class NexusMainWindow(ctk.CTk):
    """Main application window"""

    def __init__(self, config_manager: ConfigManager):
        super().__init__()

        self.config_manager = config_manager
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
        self.title("Nexus - Automated Vendor Account Provisioning")

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
        self.tabview.add("Settings")

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
            config_manager=self.config_manager
        )

        # Placeholders for other tabs
        self._create_placeholder_tab(self.tabview.tab("Settings"), "Settings")

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

    def run(self):
        """Run the application"""
        logger.info("Starting Nexus GUI")
        self.mainloop()
