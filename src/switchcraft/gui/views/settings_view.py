import customtkinter as ctk
import webbrowser
import sys
import logging
import json
import re
import os
from tkinter import messagebox
from switchcraft.utils.i18n import i18n
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.updater import UpdateChecker
from switchcraft import __version__

logger = logging.getLogger(__name__)

class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, show_update_callback, intune_service):
        super().__init__(parent)
        self.show_update_callback = show_update_callback
        self.intune_service = intune_service

        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_ui()

    def setup_ui(self):
        """Setup the Settings tab with TabView layout."""
        # Main Layout: TabView instead of single ScrollableFrame
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.tab_view.grid_columnconfigure(0, weight=1)

        # Create Tabs
        self.tab_general = self.tab_view.add("General")
        self.tab_updates = self.tab_view.add("Updates")
        self.tab_deploy = self.tab_view.add("Deployment")
        self.tab_help = self.tab_view.add("Help")

        # Configure Grids for Tabs
        for tab in [self.tab_general, self.tab_updates, self.tab_deploy, self.tab_help]:
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        # Create Scrollable Frames for each tab (Fixes cutoff issues)
        self.scroll_general = ctk.CTkScrollableFrame(self.tab_general, fg_color="transparent")
        self.scroll_general.pack(fill="both", expand=True)

        self.scroll_updates = ctk.CTkScrollableFrame(self.tab_updates, fg_color="transparent")
        self.scroll_updates.pack(fill="both", expand=True)

        self.scroll_deploy = ctk.CTkScrollableFrame(self.tab_deploy, fg_color="transparent")
        self.scroll_deploy.pack(fill="both", expand=True)

        self.scroll_help = ctk.CTkScrollableFrame(self.tab_help, fg_color="transparent")
        self.scroll_help.pack(fill="both", expand=True)

        # Populate Tabs
        self._setup_tab_general(self.scroll_general)
        self._setup_tab_updates(self.scroll_updates)
        self._setup_tab_deployment(self.scroll_deploy)
        self._setup_tab_help(self.scroll_help)

    def _setup_tab_general(self, parent):
        """General Settings: Winget, Paths, AI."""
        # Winget
        frame_gen = ctk.CTkFrame(parent)
        frame_gen.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame_gen, text=i18n.get("settings_hdr_integrations"), font=ctk.CTkFont(weight="bold")).pack(pady=5)

        self.winget_var = ctk.BooleanVar(value=SwitchCraftConfig.get_value("EnableWinget", True))
        def toggle_winget():
            SwitchCraftConfig.set_user_preference("EnableWinget", self.winget_var.get())
        ctk.CTkSwitch(frame_gen, text=i18n.get("settings_enable_winget", default="Enable Winget Integration"), variable=self.winget_var, command=toggle_winget).pack(pady=5)

        # Directories
        self._setup_path_settings(parent)

        # External Tools
        self._setup_tool_settings(parent)

        # AI Config
        self._setup_ai_config(parent)


    def _setup_tab_updates(self, parent):
        """Update Settings: Channel, Check Button."""
        frame_upd = ctk.CTkFrame(parent)
        frame_upd.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame_upd, text=i18n.get("settings_channel") or "Update Channel", font=ctk.CTkFont(weight="bold")).pack(pady=5)

        self.channel_opt = ctk.CTkSegmentedButton(
            frame_upd,
            values=["Stable", "Beta", "Dev"],
            command=self.change_update_channel
        )
        # Load current channel
        current_channel = self._get_registry_value("UpdateChannel")
        if not current_channel:
            start_ver = __version__.lower()
            if "dev" in start_ver: current_channel = "dev"
            elif "beta" in start_ver: current_channel = "beta"
            else: current_channel = "stable"

        channel_map = {"stable": "Stable", "beta": "Beta", "dev": "Dev"}
        self.channel_opt.set(channel_map.get(current_channel, "Stable"))
        self.channel_opt.pack(pady=5)

        ctk.CTkLabel(
            frame_upd,
            text=i18n.get("settings_channel_desc"),
            text_color="gray",
            font=ctk.CTkFont(size=11),
            wraplength=350
        ).pack(pady=5)

        # divider/spacing
        ctk.CTkFrame(frame_upd, height=2, fg_color="gray").pack(fill="x", padx=20, pady=10)

        # Check Button
        ctk.CTkButton(frame_upd, text=i18n.get("check_updates"), command=lambda: self.show_update_callback(show_no_update=True)).pack(pady=10)


    def _setup_tab_deployment(self, parent):
        """Deployment: Intune, Signing, Templates."""
        # Intune
        self._setup_intune_settings(parent)

        # Signing
        self._setup_signing_settings(parent)

        # Templates
        frame_tmpl = ctk.CTkFrame(parent)
        frame_tmpl.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame_tmpl, text=i18n.get("settings_tmpl_title"), font=ctk.CTkFont(weight="bold")).pack(pady=5)

        current_tmpl = SwitchCraftConfig.get_value("CustomTemplatePath")
        display_tmpl = current_tmpl if current_tmpl else i18n.get("settings_tmpl_default")

        self.tmpl_path_label = ctk.CTkLabel(frame_tmpl, text=display_tmpl, text_color="gray", wraplength=300)
        self.tmpl_path_label.pack(pady=2)

        def select_template():
            path = ctk.filedialog.askopenfilename(filetypes=[("PowerShell", "*.ps1")])
            if path:
                SwitchCraftConfig.set_user_preference("CustomTemplatePath", path)
                self.tmpl_path_label.configure(text=path)

        ctk.CTkButton(frame_tmpl, text=i18n.get("settings_tmpl_select"), command=select_template).pack(pady=5)

        def reset_template():
            SwitchCraftConfig.set_user_preference("CustomTemplatePath", "")
            self.tmpl_path_label.configure(text=i18n.get("settings_tmpl_default"))

        ctk.CTkButton(frame_tmpl, text=i18n.get("settings_tmpl_reset"), fg_color="transparent", border_width=1, command=reset_template).pack(pady=2)


    def _setup_tab_help(self, parent):
        """Help & About."""
        # Documentation
        frame_docs = ctk.CTkFrame(parent)
        frame_docs.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame_docs, text=i18n.get("settings_hdr_help"), font=ctk.CTkFont(weight="bold")).pack(pady=5)

        ctk.CTkButton(frame_docs, text=i18n.get("settings_btn_open_docs"),
                                command=lambda: webbrowser.open("https://github.com/FaserF/SwitchCraft/blob/main/README.md")).pack(pady=5, fill="x")

        ctk.CTkButton(frame_docs, text=i18n.get("settings_btn_get_help"), fg_color="transparent", border_width=1,
                                command=lambda: webbrowser.open("https://github.com/FaserF/SwitchCraft/issues")).pack(pady=5, fill="x")

        # Debug Console
        if sys.platform == 'win32':
             self._setup_debug_console(parent)

        # Link to View Templates (moved from main list)
        ctk.CTkButton(parent, text=i18n.get("settings_btn_view_tmpl"), fg_color="transparent", text_color="#3B8ED0", hover=False,
                         command=lambda: webbrowser.open("https://github.com/FaserF/SwitchCraft/tree/main/src/switchcraft/assets/templates")).pack(pady=5)

        # About
        frame_about = ctk.CTkFrame(parent, fg_color="transparent")
        frame_about.pack(fill="x", padx=10, pady=20)

        ctk.CTkLabel(frame_about, text="SwitchCraft", font=ctk.CTkFont(size=24, weight="bold")).pack()
        ctk.CTkLabel(frame_about, text=f"{i18n.get('about_version')}: {__version__}").pack()
        ctk.CTkLabel(frame_about, text=f"{i18n.get('about_dev')}: FaserF").pack()

        ctk.CTkButton(frame_about, text="GitHub: FaserF/SwitchCraft", fg_color="transparent", text_color="cyan", hover=False,
                              command=lambda: webbrowser.open("https://github.com/FaserF/SwitchCraft")).pack(pady=5)

        ctk.CTkLabel(parent, text=i18n.get("brought_by"), text_color="gray").pack(side="bottom", pady=10)

    def _setup_signing_settings(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame, text=i18n.get("settings_hdr_signing"), font=ctk.CTkFont(weight="bold")).pack(pady=5)

        self.sign_var = ctk.BooleanVar(value=SwitchCraftConfig.get_value("SignScripts", False))

        def _get_signing_certs():
            import subprocess
            try:
                # Get CodeSigning certs from CurrentUser\My
                cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                       "Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert | Select-Object Subject, Thumbprint | ConvertTo-Json"]
                # Use startupinfo to hide window
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                res = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
                if not res.stdout.strip(): return []

                try:
                    data = json.loads(res.stdout)
                except: return []

                if isinstance(data, dict): return [data]
                return data
            except Exception as e:
                logger.error(f"Cert Scan Error: {e}")
                return []

        def toggle_sign():
            enabled = self.sign_var.get()
            SwitchCraftConfig.set_user_preference("SignScripts", enabled)

            if enabled:
                self.cert_frame.pack(fill="x", padx=10, pady=5)

                # Check if we already have a valid config (Path OR Thumbprint)
                curr_path = SwitchCraftConfig.get_value("CertPath", "")
                curr_thumb = SwitchCraftConfig.get_value("CertThumbprint", "")

                # If nothing configured, try auto-detect
                if not curr_path and not curr_thumb:
                    certs = _get_signing_certs()
                    if len(certs) == 1:
                        # Auto-Select Single Cert
                        cert = certs[0]
                        thumb = cert.get("Thumbprint")
                        subj = cert.get("Subject")
                        SwitchCraftConfig.set_user_preference("CertThumbprint", thumb)
                        self.cert_path_entry.delete(0, "end")
                        self.cert_path_entry.insert(0, f"Auto-Cert: {subj} [{thumb}]")
                        self.cert_path_entry.configure(state="disabled") # Lock it to show it's managed
                        messagebox.showinfo("Certificate Found", f"Auto-selected signing certificate:\n{subj}")

                    elif len(certs) > 1:
                        # Multiple Certs - Ask User
                        # Simple Input Dialog for simplicity or custom dialog.
                        # For now, let's list them in a message box and ask to manual browse or we could implementation a selection window.
                        # Given constraints, let's just pick the first one but warn, OR fallback to manual mode where they can browse file.
                        # Better: Show a selection dialog.

                        cert_list = "\n".join([f"{i+1}. {c.get('Subject')}" for i, c in enumerate(certs)])
                        choice = ctk.CTkInputDialog(text=f"Multiple Certificates Found:\n{cert_list}\n\nEnter number to select:", title="Select Certificate").get_input()

                        if choice and choice.isdigit():
                            idx = int(choice) - 1
                            if 0 <= idx < len(certs):
                                cert = certs[idx]
                                thumb = cert.get("Thumbprint")
                                subj = cert.get("Subject")
                                SwitchCraftConfig.set_user_preference("CertThumbprint", thumb)
                                self.cert_path_entry.delete(0, "end")
                                self.cert_path_entry.insert(0, f"Store-Cert: {subj}")
                                self.cert_path_entry.configure(state="disabled")
                    else:
                         # 0 found, keep manual mode
                         pass
            else:
                self.cert_frame.pack_forget()

        ctk.CTkSwitch(frame, text=i18n.get("settings_enable_signing"), variable=self.sign_var, command=toggle_sign).pack(pady=5)

        self.cert_frame = ctk.CTkFrame(frame, fg_color="transparent")

        # Cert Path or Thumbprint Display
        ctk.CTkLabel(self.cert_frame, text=i18n.get("settings_lbl_cert_path")).pack(anchor="w")
        self.cert_path_entry = ctk.CTkEntry(self.cert_frame)
        self.cert_path_entry.pack(fill="x", pady=2)

        # Init Entry Value
        c_thumb = SwitchCraftConfig.get_value("CertThumbprint", "")
        c_path = SwitchCraftConfig.get_value("CertPath", "")

        if c_thumb:
             self.cert_path_entry.insert(0, f"Store-Cert: {c_thumb}")
             self.cert_path_entry.configure(state="disabled")
        elif c_path:
             self.cert_path_entry.insert(0, c_path)

        def save_cert_path(event=None):
            # Only save if enabled (search mode not active)
            if self.cert_path_entry.cget("state") != "disabled":
                 SwitchCraftConfig.set_user_preference("CertPath", self.cert_path_entry.get())
                 # Clear thumbprint if manually editing path
                 SwitchCraftConfig.set_user_preference("CertThumbprint", "")

        self.cert_path_entry.bind("<FocusOut>", save_cert_path)

        btn_frame = ctk.CTkFrame(self.cert_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=5)

        def browse_cert():
            # Reset to manual mode
            self.cert_path_entry.configure(state="normal")
            path = ctk.filedialog.askopenfilename(filetypes=[("PFX Certificate", "*.pfx")])
            if path:
                self.cert_path_entry.delete(0, "end")
                self.cert_path_entry.insert(0, path)
                SwitchCraftConfig.set_user_preference("CertPath", path)
                SwitchCraftConfig.set_user_preference("CertThumbprint", "") # Clear thumbprint

        ctk.CTkButton(btn_frame, text=i18n.get("settings_btn_browse"), width=100, command=browse_cert).pack(side="left", padx=5)

        # Clear / Reset Button
        def clear_cert():
            self.cert_path_entry.configure(state="normal")
            self.cert_path_entry.delete(0, "end")
            SwitchCraftConfig.set_user_preference("CertPath", "")
            SwitchCraftConfig.set_user_preference("CertThumbprint", "")

        ctk.CTkButton(btn_frame, text="Reset", width=60, fg_color="transparent", border_width=1, command=clear_cert).pack(side="left", padx=5)

        if self.sign_var.get():
             self.cert_frame.pack(fill="x", padx=10, pady=5)


    def _setup_intune_settings(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame, text=i18n.get("settings_hdr_intune_auth"), font=ctk.CTkFont(weight="bold")).pack(pady=5)

        link_doc = ctk.CTkButton(frame, text="Documentation (GitHub)", fg_color="transparent", text_color="#3B8ED0", hover=False, height=20,
                                 command=lambda: webbrowser.open("https://github.com/FaserF/SwitchCraft/blob/main/docs/SECURITY.md"))
        link_doc.pack(pady=(0, 10))

        self.ent_tenant = self._create_intune_entry(frame, "Tenant ID:", "IntuneTenantID")
        self.ent_client = self._create_intune_entry(frame, "Client ID (App ID):", "IntuneClientId")
        self.ent_secret = self._create_intune_entry(frame, "Client Secret:", "IntuneClientSecret", hide=True)

        # Verify & Save Button
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)

        self.btn_verify = ctk.CTkButton(btn_frame, text=i18n.get("settings_btn_verify_save"), fg_color="green", command=self._verify_and_save_intune)
        self.btn_verify.pack(pady=5, fill="x")

        self.lbl_verify_status = ctk.CTkLabel(frame, text="", text_color="gray")
        self.lbl_verify_status.pack(pady=2)

    def _create_intune_entry(self, parent, label, config_key, hide=False):
        ctk.CTkLabel(parent, text=label).pack(anchor="w", padx=10)
        entry = ctk.CTkEntry(parent, show="*" if hide else "")
        entry.pack(fill="x", padx=10, pady=(0, 5))
        # Try getting from keyring first, then registry
        val = SwitchCraftConfig.get_secret(config_key)
        if not val:
            val = SwitchCraftConfig.get_value(config_key, "")

        if val: entry.insert(0, val)
        return entry

    def _verify_and_save_intune(self):
        t_id = self.ent_tenant.get().strip()
        c_id = self.ent_client.get().strip()
        sec = self.ent_secret.get().strip()

        if not (t_id and c_id and sec):
            messagebox.showwarning("Incomplete", i18n.get("settings_verify_incomplete"))
            return

        self.btn_verify.configure(state="disabled", text=(i18n.get("settings_verify_validating") or "Verifying..."))
        self.lbl_verify_status.configure(text=i18n.get("settings_verify_progress"), text_color="blue")
        self.update()

        def _verify_thread():
            try:
                # Attempt Authentication
                token = self.intune_service.authenticate(t_id, c_id, sec)
                if token:
                    # Verify Permissions
                    is_valid, msg = self.intune_service.verify_graph_permissions(token)
                    if is_valid:
                        # Success - Save Config securely
                        # Tenant ID is public info, Registry is fine
                        SwitchCraftConfig.set_user_preference("IntuneTenantID", t_id)

                        # Client ID and Secret in Keyring
                        SwitchCraftConfig.set_secret("IntuneClientId", c_id)
                        SwitchCraftConfig.set_secret("IntuneClientSecret", sec)

                        # Clear potential plaintext form registry if exists (migration)
                        SwitchCraftConfig.set_user_preference("IntuneClientSecret", "")
                        SwitchCraftConfig.set_user_preference("IntuneClientId", "")

                        self.after(0, lambda: self._on_verify_success())

                        if "ok_with_warning" in msg:
                             clean_msg = msg.replace("ok_with_warning: ", "")
                             self.after(0, lambda: messagebox.showwarning(i18n.get("settings_verify_warning") or "Permission Warning", clean_msg))
                    else:
                        raise RuntimeError(f"Permissions missing: {msg}")
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: self._on_verify_fail(error_msg))

        import threading
        threading.Thread(target=_verify_thread, daemon=True).start()

    def _on_verify_success(self):
        self.btn_verify.configure(state="normal", text=i18n.get("settings_btn_verify_save"))
        self.lbl_verify_status.configure(text=i18n.get("settings_verify_success"), text_color="green")
        messagebox.showinfo(i18n.get("settings_verify_success_title"), i18n.get("settings_verify_success_msg"))

    def _on_verify_fail(self, error_msg):
        self.btn_verify.configure(state="normal", text=i18n.get("settings_btn_verify_save"))
        self.lbl_verify_status.configure(text=i18n.get("settings_verify_fail"), text_color="red")
        messagebox.showerror(i18n.get("settings_verify_fail"), i18n.get("settings_verify_fail_msg", error=error_msg))


    def _setup_path_settings(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame, text=i18n.get("settings_hdr_directories"), font=ctk.CTkFont(weight="bold")).pack(pady=5)

        ctk.CTkLabel(frame, text=i18n.get("settings_lbl_git_path")).pack(anchor="w", padx=10)

        path_frame = ctk.CTkFrame(frame, fg_color="transparent")
        path_frame.pack(fill="x", padx=10)

        self.git_path_entry = ctk.CTkEntry(path_frame)
        self.git_path_entry.pack(side="left", fill="x", expand=True, pady=2)
        val = SwitchCraftConfig.get_value("GitRepoPath", "")
        if val: self.git_path_entry.insert(0, val)

        def save_git(event=None):
             SwitchCraftConfig.set_user_preference("GitRepoPath", self.git_path_entry.get())

        self.git_path_entry.bind("<FocusOut>", save_git)

        def browse_git():
            path = ctk.filedialog.askdirectory()
            if path:
                self.git_path_entry.delete(0, "end")
                self.git_path_entry.insert(0, path)
                save_git()

        ctk.CTkButton(path_frame, text=i18n.get("settings_btn_browse"), width=80, command=browse_git).pack(side="right", padx=5)

    def _setup_tool_settings(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame, text=i18n.get("settings_hdr_tools"), font=ctk.CTkFont(weight="bold")).pack(pady=5)

        # IntuneWinAppUtil
        lbl = i18n.get("settings_lbl_tool_custom")
        ctk.CTkLabel(frame, text=lbl).pack(anchor="w", padx=10)

        tool_frame = ctk.CTkFrame(frame, fg_color="transparent")
        tool_frame.pack(fill="x", padx=10)

        self.tool_path_entry = ctk.CTkEntry(tool_frame)
        self.tool_path_entry.pack(side="left", fill="x", expand=True, pady=2)
        val = SwitchCraftConfig.get_value("IntuneToolPath", "")
        if not val:
            # Check default location
            default_path = os.path.join(os.getcwd(), "Bin", "IntuneWinAppUtil.exe")
            if os.path.exists(default_path):
                val = default_path
        if val: self.tool_path_entry.insert(0, val)

        def save_tool(event=None):
             SwitchCraftConfig.set_user_preference("IntuneToolPath", self.tool_path_entry.get())

        self.tool_path_entry.bind("<FocusOut>", save_tool)

        def browse_tool():
            path = ctk.filedialog.askopenfilename(filetypes=[("Executable", "*.exe")])
            if path:
                self.tool_path_entry.delete(0, "end")
                self.tool_path_entry.insert(0, path)
                save_tool()

        ctk.CTkButton(tool_frame, text=i18n.get("settings_btn_browse"), width=80, command=browse_tool).pack(side="right", padx=5)

        # Intune Groups
        ctk.CTkLabel(frame, text=i18n.get("settings_hdr_intune_groups"), font=ctk.CTkFont(weight="bold")).pack(pady=(15,5))

        grp_frame = ctk.CTkFrame(frame)
        grp_frame.pack(fill="x", padx=10, pady=5)

        self.group_scroll = ctk.CTkScrollableFrame(grp_frame, height=100)
        self.group_scroll.pack(fill="x", padx=5, pady=5)

        self.refresh_group_list()

        input_frame = ctk.CTkFrame(grp_frame, fg_color="transparent")
        input_frame.pack(fill="x", padx=5, pady=5)
        self.ent_grp_name = ctk.CTkEntry(input_frame, placeholder_text="Name (e.g. Testers)")
        self.ent_grp_name.pack(side="left", fill="x", expand=True, padx=(0,5))
        self.ent_grp_id = ctk.CTkEntry(input_frame, placeholder_text="Object ID (GUID)")
        self.ent_grp_id.pack(side="left", fill="x", expand=True, padx=(0,5))

        def get_groups():
            raw = SwitchCraftConfig.get_value("IntuneTestGroups", "[]")
            if isinstance(raw, str):
                try: return json.loads(raw)
                except: return []
            return raw if isinstance(raw, list) else []

        def save_groups(groups):
            SwitchCraftConfig.set_user_preference("IntuneTestGroups", json.dumps(groups))
            self.refresh_group_list()

        def add_grp():
            n = self.ent_grp_name.get().strip()
            i = self.ent_grp_id.get().strip()
            if n and i:
                 # GUID Validation
                 if not re.match(r"^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$", i):
                     messagebox.showwarning("Invalid ID", "Please enter a valid GUID (Object ID).")
                     return

                 current = get_groups()
                 current.append({"name": n, "id": i})
                 save_groups(current)
                 self.ent_grp_name.delete(0, "end")
                 self.ent_grp_id.delete(0, "end")

        ctk.CTkButton(input_frame, text=i18n.get("settings_btn_add"), width=50, command=add_grp).pack(side="right")

    def refresh_group_list(self):
        for widget in self.group_scroll.winfo_children():
            widget.destroy()

        raw = SwitchCraftConfig.get_value("IntuneTestGroups", "[]")
        groups = []
        if isinstance(raw, str):
            try: groups = json.loads(raw)
            except: pass
        elif isinstance(raw, list):
            groups = raw

        for idx, grp in enumerate(groups):
            row = ctk.CTkFrame(self.group_scroll, fg_color="transparent")
            row.pack(fill="x")
            ctk.CTkLabel(row, text=f"{grp.get('name')} ({grp.get('id')})").pack(side="left")
            def rem(x=idx):
                current = groups # Closure over reference? Need fresh load to be safe or copy
                # Safer to reload
                raw_curr = SwitchCraftConfig.get_value("IntuneTestGroups", "[]")
                curr = json.loads(raw_curr) if isinstance(raw_curr, str) else (raw_curr if isinstance(raw_curr, list) else [])

                if 0 <= x < len(curr):
                    curr.pop(x)
                    SwitchCraftConfig.set_user_preference("IntuneTestGroups", json.dumps(curr))
                    self.refresh_group_list()

            ctk.CTkButton(row, text="X", width=30, fg_color="red", command=rem).pack(side="right")



    def _setup_ai_config(self, parent):
        """AI Assistant Configuration."""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame, text=i18n.get("settings_ai_title"), font=ctk.CTkFont(weight="bold")).pack(pady=5)

        # Provider Selection
        ctk.CTkLabel(frame, text=i18n.get("settings_ai_provider")).pack(anchor="w", padx=10)

        self.ai_provider_var = ctk.StringVar(value=SwitchCraftConfig.get_value("AIProvider", "local"))

        provider_menu = ctk.CTkOptionMenu(
            frame,
            variable=self.ai_provider_var,
            values=["local", "openai", "gemini"],
            command=self._on_ai_provider_change
        )
        provider_menu.pack(fill="x", padx=10, pady=(0, 5))

        # Key Entry (Dynamic)
        self.ai_key_frame = ctk.CTkFrame(frame, fg_color="transparent")
        ctk.CTkLabel(self.ai_key_frame, text=i18n.get("settings_ai_key")).pack(anchor="w")
        self.ai_key_entry = ctk.CTkEntry(self.ai_key_frame, show="*")
        self.ai_key_entry.pack(fill="x")

        # Model Entry
        self.ai_model_frame = ctk.CTkFrame(frame, fg_color="transparent")
        ctk.CTkLabel(self.ai_model_frame, text=i18n.get("settings_ai_model")).pack(anchor="w")
        self.ai_model_entry = ctk.CTkEntry(self.ai_model_frame, placeholder_text="e.g. gpt-4o")
        v = SwitchCraftConfig.get_value("AIModel", "")
        if v: self.ai_model_entry.insert(0, v)
        self.ai_model_entry.pack(fill="x")

        # Save Button
        ctk.CTkButton(frame, text=i18n.get("settings_btn_save_ai"), command=self._save_ai_settings).pack(pady=10)

        # Initial State
        self._on_ai_provider_change(self.ai_provider_var.get())

    def _on_ai_provider_change(self, value):
        if value == "local":
            self.ai_key_frame.pack_forget()
            self.ai_model_frame.pack_forget()
        else:
            self.ai_key_frame.pack(fill="x", padx=10, pady=5)
            self.ai_model_frame.pack(fill="x", padx=10, pady=5)
            # Load specific key
            secret_key = "OPENAI_API_KEY" if value == "openai" else "GEMINI_API_KEY"
            val = SwitchCraftConfig.get_secret(secret_key)
            self.ai_key_entry.delete(0, "end")
            if val: self.ai_key_entry.insert(0, val)

    def _save_ai_settings(self):
        provider = self.ai_provider_var.get()
        SwitchCraftConfig.set_user_preference("AIProvider", provider)
        SwitchCraftConfig.set_user_preference("AIModel", self.ai_model_entry.get().strip())

        if provider != "local":
            secret_key = "OPENAI_API_KEY" if provider == "openai" else "GEMINI_API_KEY"
            key_val = self.ai_key_entry.get().strip()
            if key_val:
                SwitchCraftConfig.set_secret(secret_key, key_val)

        messagebox.showinfo("Saved", "AI Settings Saved. Please restart to apply changes.")

    def _setup_debug_console(self, parent):
        """Setup debug console toggle."""
        frame_debug = ctk.CTkFrame(parent)
        frame_debug.pack(fill="x", padx=10, pady=10)


        ctk.CTkLabel(frame_debug, text=i18n.get("settings_debug_title"), font=ctk.CTkFont(weight="bold")).pack(pady=5)

        self.debug_console_var = ctk.BooleanVar(value=False)

        def toggle_console():
             import ctypes
             kernel32 = ctypes.windll.kernel32
             if self.debug_console_var.get():
                 kernel32.AllocConsole()
                 sys.stdout = open("CONOUT$", "w")
                 sys.stderr = open("CONOUT$", "w")
                 print("SwitchCraft Debug Console [Enabled]")
             else:
                 try:
                     sys.stdout.close()
                     sys.stderr.close()
                     # Restore std streams to avoid errors
                     sys.stdout = sys.__stdout__
                     sys.stderr = sys.__stderr__
                 except: pass
                 kernel32.FreeConsole()

        ctk.CTkSwitch(frame_debug, text=i18n.get("settings_debug_console"), variable=self.debug_console_var, command=toggle_console).pack(pady=5)

    def change_update_channel(self, value):
        channel_map = {"Stable": "stable", "Beta": "beta", "Dev": "dev"}
        new_channel = channel_map.get(value, "stable")
        self._set_registry_value("UpdateChannel", new_channel)
        messagebox.showinfo("Saved", i18n.get("settings_saved", channel=value))

    def _get_registry_value(self, name, default=None):
        """Read a value from the Windows registry."""
        if sys.platform != 'win32':
            return default
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\FaserF\SwitchCraft', 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)
            return value
        except:
            return default

    def _set_registry_value(self, name, value, value_type=None):
        """Write a value to the Windows registry."""
        if sys.platform != 'win32':
            return
        try:
            import winreg
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\FaserF\SwitchCraft')
            if value_type is None:
                value_type = winreg.REG_SZ
            winreg.SetValueEx(key, name, 0, value_type, str(value))
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Failed to set registry {name}: {e}")
            messagebox.showerror("Registry Error", f"Could not save setting: {e}")

    def _run_update_check(self, show_no_update=False):
        # We need to call the callback provided by App, because App handles the dialog logic
        if self.show_update_callback:
            self.show_update_callback(show_no_update)
            return

        # Fallback if no callback (shouldn't happen with proper init)
        try:
            channel = SwitchCraftConfig.get_update_channel()
            checker = UpdateChecker(channel=channel)
            has_update, version, data = checker.check_for_updates()
            if has_update:
                messagebox.showinfo("Update Available", f"New version {version} is available!")
            elif show_no_update:
                channel_display = channel.capitalize()
                messagebox.showinfo(i18n.get("check_updates"), f"{i18n.get('up_to_date')}\n\n{i18n.get('about_version')}: {__version__}\nChannel: {channel_display}")
        except Exception as e:
             if show_no_update:
                messagebox.showerror(i18n.get("update_check_failed"), f"{i18n.get('could_not_check')}\n{e}")
