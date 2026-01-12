import customtkinter as ctk
import threading
import logging
from switchcraft.services.intune_service import IntuneService
from switchcraft.utils.config import SwitchCraftConfig

logger = logging.getLogger(__name__)

class IntuneStoreView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.intune_service = IntuneService()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_ui()

    def setup_ui(self):
        # Master Layout: Left (List) vs Right (Details)
        self.panes = ctk.CTkFrame(self, fg_color="transparent")
        self.panes.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.panes.grid_columnconfigure(0, weight=1)
        self.panes.grid_columnconfigure(1, weight=2)
        self.panes.grid_rowconfigure(0, weight=1)

        # Helper to check credentials
        tenant_id = SwitchCraftConfig.get_value("GraphTenantId")
        client_id = SwitchCraftConfig.get_value("GraphClientId")
        client_secret = SwitchCraftConfig.get_secure_value("GraphClientSecret")

        if not (tenant_id and client_id and client_secret):
             ctk.CTkLabel(self.panes, text="Intune Not Configured", font=ctk.CTkFont(size=24, weight="bold"), text_color="orange").pack(pady=20)
             ctk.CTkLabel(self.panes, text="Please configure Microsoft Graph API credentials in Settings.").pack(pady=(0,20))
             return

        # === Left Pane ===
        left_pane = ctk.CTkFrame(self.panes)
        left_pane.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_pane.grid_rowconfigure(2, weight=1)
        left_pane.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left_pane, text="Intune Store", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, pady=10)

        # Search
        search_frame = ctk.CTkFrame(left_pane, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.entry_search = ctk.CTkEntry(search_frame, placeholder_text="Search Intune Apps...")
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_search.bind("<Return>", lambda e: self._perform_search())

        ctk.CTkButton(search_frame, text="Search", width=60, command=self._perform_search).pack(side="right")

        # Results
        self.results_scroll = ctk.CTkScrollableFrame(left_pane)
        self.results_scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # === Right Pane ===
        self.right_pane = ctk.CTkFrame(self.panes)
        self.right_pane.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.right_pane.grid_columnconfigure(0, weight=1)

        self.lbl_details_title = ctk.CTkLabel(self.right_pane, text="Select an App", font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl_details_title.pack(pady=20)

        self.details_content = ctk.CTkScrollableFrame(self.right_pane, fg_color="transparent")
        self.details_content.pack(fill="both", expand=True, padx=10, pady=10)

    def _get_token(self):
        tenant_id = SwitchCraftConfig.get_value("GraphTenantId")
        client_id = SwitchCraftConfig.get_value("GraphClientId")
        client_secret = SwitchCraftConfig.get_secure_value("GraphClientSecret")
        if not (tenant_id and client_id and client_secret):
            return None
        return self.intune_service.authenticate(tenant_id, client_id, client_secret)

    def _perform_search(self):
        query = self.entry_search.get()

        for w in self.results_scroll.winfo_children():
            w.destroy()

        loader = ctk.CTkLabel(self.results_scroll, text="Searching...", text_color="gray")
        loader.pack(pady=20)
        self.update()

        def _bg():
            try:
                token = self._get_token()
                if not token:
                    self.after(0, lambda: self._show_error("Intune not configured."))
                    return

                if query:
                    apps = self.intune_service.search_apps(token, query)
                else:
                    apps = self.intune_service.list_apps(token)

                self.after(0, lambda: self._update_list(apps))
            except Exception as ex:
                self.after(0, lambda: self._show_error(str(ex)))

        threading.Thread(target=_bg, daemon=True).start()

    def _show_error(self, msg):
        for w in self.results_scroll.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.results_scroll, text=f"Error: {msg}", text_color="red", wraplength=200).pack(pady=20)

    def _update_list(self, apps):
        for w in self.results_scroll.winfo_children():
            w.destroy()

        if not apps:
            ctk.CTkLabel(self.results_scroll, text="No apps found.").pack(pady=20)
            return

        for app in apps:
            name = app.get("displayName", "Unknown")
            publisher = app.get("publisher", "")
            btn = ctk.CTkButton(
                self.results_scroll,
                text=f"{name}\n{publisher}",
                anchor="w",
                fg_color="transparent",
                border_width=1,
                text_color=("black", "white"),
                command=lambda a=app: self._show_details(a)
            )
            btn.pack(fill="x", pady=2)

    def _show_details(self, app):
        for w in self.details_content.winfo_children():
            w.destroy()

        self.lbl_details_title.configure(text=app.get("displayName", "Unknown"))

        def add_row(lbl, val):
            if not val: return
            f = ctk.CTkFrame(self.details_content, fg_color="transparent")
            f.pack(fill="x", pady=1)
            ctk.CTkLabel(f, text=f"{lbl}:", font=ctk.CTkFont(weight="bold"), width=100, anchor="w").pack(side="left")
            ctk.CTkLabel(f, text=str(val), anchor="w", wraplength=400).pack(side="left", fill="x", expand=True)

        add_row("ID", app.get("id"))
        add_row("Publisher", app.get("publisher"))
        add_row("Owner", app.get("owner"))
        add_row("Created", app.get("createdDateTime"))

        ctk.CTkLabel(self.details_content, text="Description", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 0))
        ctk.CTkLabel(self.details_content, text=app.get("description", "No description"), anchor="w", wraplength=500, justify="left").pack(fill="x")
