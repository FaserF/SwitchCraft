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
    def __init__(self, parent, show_update_callback, intune_service, on_winget_toggle=None):
        super().__init__(parent)
        self.show_update_callback = show_update_callback
        self.intune_service = intune_service
        self.on_winget_toggle = on_winget_toggle

        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_ui()

    def setup_ui(self):
        """Setup the Settings view with Tabs."""
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Tabs
        self.tab_general = self.tabview.add(i18n.get("settings_title") or "General")
        self.tab_updates = self.tabview.add(i18n.get("settings_hdr_update") or "Updates")
        self.tab_deploy = self.tabview.add(i18n.get("deployment_title") or "Deployment")
        self.tab_help = self.tabview.add(i18n.get("help_title") or "Help") # Fixed key

        for tab in [self.tab_general, self.tab_updates, self.tab_deploy, self.tab_help]:
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        self._setup_tab_general(self.tab_general)
        self._setup_tab_updates(self.tab_updates)
        self._setup_tab_deploy(self.tab_deploy)
        self._setup_tab_help(self.tab_help)

    def _setup_tab_general(self, parent):
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(scroll, text=i18n.get("settings_title"), font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)

        # Winget Toggle
        frame_winget = ctk.CTkFrame(scroll)
        frame_winget.pack(fill="x", padx=10, pady=10)

        self.winget_var = ctk.BooleanVar(value=SwitchCraftConfig.get_value("EnableWinget", True))
        def toggle_winget():
            val = self.winget_var.get()
            SwitchCraftConfig.set_user_preference("EnableWinget", val)
            if self.on_winget_toggle:
                self.on_winget_toggle(val)

        ctk.CTkSwitch(frame_winget, text=i18n.get("settings_enable_winget"), variable=self.winget_var, command=toggle_winget).pack(pady=10, padx=10)

        # Language Selector
        frame_lang = ctk.CTkFrame(scroll)
        frame_lang.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(frame_lang, text=i18n.get("settings_language")).pack(side="left", padx=5)

        lang_var = ctk.StringVar(value=SwitchCraftConfig.get_value("Language", "en"))
        def change_lang(val):
            SwitchCraftConfig.set_user_preference("Language", val)
            messagebox.showinfo(i18n.get("restart_required"), i18n.get("restart_required_msg"))

        ctk.CTkOptionMenu(frame_lang, values=["en", "de"], command=change_lang, variable=lang_var).pack(side="right", padx=5)

        # Theme Selector
        frame_theme = ctk.CTkFrame(scroll)
        frame_theme.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(frame_theme, text=i18n.get("settings_theme")).pack(side="left", padx=5)

        theme_var = ctk.StringVar(value=SwitchCraftConfig.get_value("Theme", "System"))
        def change_theme(val):
            SwitchCraftConfig.set_user_preference("Theme", val)
            ctk.set_appearance_mode(val)

        ctk.CTkOptionMenu(frame_theme, values=["System", "Dark", "Light"], command=change_theme, variable=theme_var).pack(side="right", padx=5)

        # AI Configuration
        self._setup_ai_config(scroll)

    def _setup_tab_updates(self, parent):
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(scroll, text=i18n.get("settings_hdr_update"), font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)

        # Update Channel
        frame_channel = ctk.CTkFrame(scroll)
        frame_channel.pack(fill="x", padx=10, pady=10)

        lbl = ctk.CTkLabel(frame_channel, text=i18n.get("settings_channel") or "Update Channel", font=ctk.CTkFont(weight="bold"))
        lbl.pack(pady=5)

        self.channel_opt = ctk.CTkSegmentedButton(
            frame_channel,
            values=["Stable", "Beta", "Dev"],
            command=self.change_update_channel
        )
        # Load current
        current_channel = self._get_registry_value("UpdateChannel")
        if not current_channel:
            v_low = __version__.lower()
            if "dev" in v_low: current_channel = "dev"
            elif "beta" in v_low: current_channel = "beta"
            else: current_channel = "stable"

        channel_map = {"stable": "Stable", "beta": "Beta", "dev": "Dev"}
        self.channel_opt.set(channel_map.get(current_channel, "Stable"))
        self.channel_opt.pack(pady=5)

        channel_desc = ctk.CTkLabel(
            frame_channel,
            text=i18n.get("settings_channel_desc"),
            text_color="gray",
            font=ctk.CTkFont(size=11),
            wraplength=350
        )
        channel_desc.pack(pady=2)

        # Check Updates Button
        # Changelog Display
        frame_log = ctk.CTkFrame(scroll)
        frame_log.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame_log, text=i18n.get("changelog") or "Changelog (Installed)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=2)

        self.changelog_box = ctk.CTkTextbox(frame_log, height=150)
        self.changelog_box.pack(fill="x", padx=5, pady=5)
        self.changelog_box.insert("0.0", "Loading...")
        self.changelog_box.configure(state="disabled")

        # Check Updates Button
        ctk.CTkButton(scroll, text=i18n.get("check_updates"), command=self.show_update_callback).pack(pady=10)

        # Async fetch changelog
        self.after(100, self._fetch_changelog)

    def _fetch_changelog(self):
        import threading
        def fetch():
            try:
                # Use current channel
                channel = self._get_registry_value("UpdateChannel") or "stable"
                checker = UpdateChecker(channel=channel)
                # This fetches latest info
                checker.check_for_updates()

                note = checker.release_notes or i18n.get("no_changelog")

                # Check version mismatch logic
                header = f"Version: {checker.latest_version}\n"
                if checker.latest_version != __version__:
                     header += f"(NOTE: You are running {__version__}, showing changelog for latest {checker.channel} release)\n"

                header += "-" * 40 + "\n\n"
                full_text = header + note

                self.after(0, lambda: self._update_changelog_ui(full_text))
            except Exception as e:
                self.after(0, lambda: self._update_changelog_ui(f"Failed to load changelog: {e}"))

        threading.Thread(target=fetch, daemon=True).start()

    def _update_changelog_ui(self, text):
        self.changelog_box.configure(state="normal")
        self.changelog_box.delete("0.0", "end")
        self.changelog_box.insert("0.0", text)
        self.changelog_box.configure(state="disabled")

    def _setup_tab_deploy(self, parent):
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        # Intune / Graph
        self._setup_intune_settings(scroll)

        # Signing
        self._setup_signing_settings(scroll)

        # Paths
        self._setup_path_settings(scroll)

        # Tools
        self._setup_tool_settings(scroll)

        # Templates
        self._setup_template_settings(scroll)

    def _setup_tab_help(self, parent):
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        # Help Links
        frame_links = ctk.CTkFrame(scroll)
        frame_links.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame_links, text="Resources", font=ctk.CTkFont(weight="bold")).pack(pady=5)

        def open_url(url):
            webbrowser.open(url)

        btn_grid = ctk.CTkFrame(frame_links, fg_color="transparent")
        btn_grid.pack(fill="x", pady=5)

        ctk.CTkButton(btn_grid, text="README", command=lambda: open_url("https://github.com/FaserF/SwitchCraft/blob/main/README.md")).pack(side="left", padx=5, expand=True)
        ctk.CTkButton(btn_grid, text="Issues", command=lambda: open_url("https://github.com/FaserF/SwitchCraft/issues")).pack(side="left", padx=5, expand=True)
        ctk.CTkButton(btn_grid, text="Project", command=lambda: open_url("https://github.com/FaserF/SwitchCraft")).pack(side="left", padx=5, expand=True)

        # Addon Manager
        self._setup_addon_manager(scroll)

        # Debug Console
        self._setup_debug_console(scroll)

        # About
        frame_about = ctk.CTkFrame(scroll)
        frame_about.pack(fill="x", padx=10, pady=20)

        ctk.CTkLabel(frame_about, text=f"SwitchCraft v{__version__}", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
        ctk.CTkLabel(frame_about, text=i18n.get("brought_by")).pack()

        # Debug Hint
        debug_hint = ctk.CTkLabel(
            scroll,
            text=i18n.get("settings_debug_hint"),
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        debug_hint.pack(pady=10)


    # --- Sub-components (Refactored to accept 'parent') ---

    def _setup_ai_config(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame, text=i18n.get("settings_hdr_ai") or "AI Config", font=ctk.CTkFont(weight="bold")).pack(pady=5)

        # Provider
        row1 = ctk.CTkFrame(frame, fg_color="transparent")
        row1.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(row1, text=i18n.get("settings_ai_provider")).pack(side="left")

        self.ai_provider = ctk.CTkOptionMenu(
            row1,
            values=["local", "openai", "gemini"],
            command=self._on_ai_provider_change
        )
        self.ai_provider.set(SwitchCraftConfig.get_value("AIProvider", "local"))
        self.ai_provider.pack(side="right")

        # API Key
        row2 = ctk.CTkFrame(frame, fg_color="transparent")
        row2.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(row2, text=i18n.get("settings_ai_key")).pack(side="left")

        self.ai_key = ctk.CTkEntry(row2, show="*", width=200)
        # Load key logic (omitted for brevity, handled by secure store)
        # self.ai_key.insert(0, ...)
        self.ai_key.pack(side="right")

        # Save Button specifically for AI? Or global?
        # For now rely on manual edits or global save if we add one.

        self.privacy_lbl = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=10), text_color="gray")
        self.privacy_lbl.pack(pady=5)
        self._update_privacy_text(SwitchCraftConfig.get_value("AIProvider", "local"))

    def _update_privacy_text(self, provider):
        if provider == "local":
            self.privacy_lbl.configure(text=i18n.get("privacy_note_local"))
        else:
            self.privacy_lbl.configure(text=i18n.get("privacy_note_cloud", provider=provider))

    def _on_ai_provider_change(self, value):
        self._save_manual_config("AIProvider", value)
        self._update_privacy_text(value)


    def _setup_signing_settings(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame, text=i18n.get("settings_hdr_signing") or "Signing", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=5)

        self.sign_var = ctk.BooleanVar(value=SwitchCraftConfig.get_value("SignScripts", False))
        self.sign_switch = ctk.CTkSwitch(
            frame,
            text=i18n.get("signing_enabled"),
            variable=self.sign_var,
            command=self.toggle_sign
        )
        self.sign_switch.grid(row=1, column=0, sticky="w", padx=5, pady=5)

        self.cert_entry_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.cert_entry_frame.grid(row=2, column=0, sticky="ew", padx=5)

        ctk.CTkLabel(self.cert_entry_frame, text=i18n.get("lbl_cert_path")).pack(side="left")

        self.cert_path_entry = ctk.CTkEntry(self.cert_entry_frame, width=250)
        self.cert_path_entry.pack(side="left", padx=5, expand=True, fill="x")

        self.cert_browse_btn = ctk.CTkButton(self.cert_entry_frame, text=i18n.get("btn_browse"), width=80, command=self.browse_cert)
        self.cert_browse_btn.pack(side="left")

        # Reset Cert Button (to clear auto-detected cert and re-enable manual entry)
        self.cert_reset_btn = ctk.CTkButton(self.cert_entry_frame, text="X", width=30, fg_color="red", command=self.reset_cert)
        self.cert_reset_btn.pack(side="left", padx=2)

        # Load initial state
        saved_cert = SwitchCraftConfig.get_value("CodeSigningCertPath", "")
        saved_thumb = SwitchCraftConfig.get_value("CodeSigningCertThumbprint", "")

        if saved_thumb:
            self.cert_path_entry.insert(0, f"Store-Cert: {saved_thumb}")
            self.cert_path_entry.configure(state="disabled")
            # Try to fetch subject name for better display if possible
            self.cert_info_lbl = ctk.CTkLabel(frame, text=f"Active: {saved_thumb}", text_color="green", font=ctk.CTkFont(size=11))
            self.cert_info_lbl.grid(row=3, column=0, sticky="w", padx=20)
        elif saved_cert:
            self.cert_path_entry.insert(0, saved_cert)
            self.cert_info_lbl = ctk.CTkLabel(
                frame,
                text=f"Active File: {Path(saved_cert).name}",
                text_color="green",
                font=ctk.CTkFont(size=11)
            )
            self.cert_info_lbl.grid(row=3, column=0, sticky="w", padx=20)
        else:
            self.cert_info_lbl = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=11))
            self.cert_info_lbl.grid(row=3, column=0, sticky="w", padx=20)

        if not self.sign_var.get():
            self._toggle_cert_entry(False)

    def _get_signing_certs(self):
        """PowerShell to list CodeSigning certs from Cert:\\CurrentUser\\My"""
        import subprocess
        try:
            cmd = [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert | Select-Object Subject, Thumbprint | ConvertTo-Json"
            ]
            # Use startupinfo to hide window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            proc = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                if isinstance(data, dict): return [data]
                if isinstance(data, list): return data
            return []
        except Exception as e:
            logger.error(f"Cert Scan failed: {e}")
            return []

    def toggle_sign(self):
        enabled = self.sign_var.get()
        SwitchCraftConfig.set_user_preference("SignScripts", enabled)

        if enabled:
            # Smart Detection
            current_path = self.cert_path_entry.get()
            # If empty or disabled (maybe previously set), check store
            if not current_path or "Store-Cert" in current_path:
                 certs = self._get_signing_certs()
                 if len(certs) == 1:
                     # Auto-select single cert
                     c = certs[0]
                     subj = c.get("Subject","").split(",")[0]
                     thumb = c.get("Thumbprint")
                     self.cert_path_entry.configure(state="normal")
                     self.cert_path_entry.delete(0, "end")
                     self.cert_path_entry.insert(0, f"Store-Cert: {subj} ({thumb})")
                     self.cert_path_entry.configure(state="disabled")
                     SwitchCraftConfig.set_user_preference("CodeSigningCertThumbprint", thumb)
                     SwitchCraftConfig.set_user_preference("CodeSigningCertPath", "") # Clear path preference
                 elif len(certs) > 1:
                     # Prompt user (Simple dialog or log)
                     # For now, just enable the field and let them browse or maybe show a dialog in future
                     # Or we can show a input dialog asking for number
                     titles = [f"{i+1}: {c.get('Subject').split(',')[0]}" for i,c in enumerate(certs)]
                     selection = ctk.CTkInputDialog(text="Multiple Certificates Found:\n" + "\n".join(titles) + "\n\nEnter Number:", title="Select Certificate").get_input()
                     if selection and selection.isdigit():
                         idx = int(selection) - 1
                         if 0 <= idx < len(certs):
                             c = certs[idx]
                             thumb = c.get("Thumbprint")
                             subj = c.get('Subject').split(',')[0]
                             self.cert_path_entry.configure(state="normal")
                             self.cert_path_entry.delete(0, "end")
                             self.cert_path_entry.insert(0, f"Store-Cert: {subj} ({thumb})")
                             self.cert_path_entry.configure(state="disabled")
                             SwitchCraftConfig.set_user_preference("CodeSigningCertThumbprint", thumb)
                             SwitchCraftConfig.set_user_preference("CodeSigningCertPath", "")
                 else:
                     # 0 found -> Manual
                     self._toggle_cert_entry(True)
            else:
                 self._toggle_cert_entry(True)
        else:
            self._toggle_cert_entry(False)

    def _toggle_cert_entry(self, state):
        self.cert_path_entry.configure(state="normal" if state else "disabled")
        self.cert_browse_btn.configure(state="normal" if state else "disabled")

    def reset_cert(self):
        """Clear cert selection to allow re-scan or manual entry."""
        self.cert_path_entry.configure(state="normal")
        self.cert_path_entry.delete(0, "end")
        SwitchCraftConfig.set_user_preference("CodeSigningCertThumbprint", "")
        SwitchCraftConfig.set_user_preference("CodeSigningCertPath", "")
        # Trigger toggle logic again to re-scan if enabled, or leave empty for browse
        # If enabled, maybe we want to force manual mode?
        # Just leave it empty enabled.

    def browse_cert(self):
        file_path = ctk.filedialog.askopenfilename(filetypes=[("PFX Certificate", "*.pfx")])
        if file_path:
            self.cert_path_entry.configure(state="normal")
            self.cert_path_entry.delete(0, "end")
            self.cert_path_entry.insert(0, file_path)
            self.cert_path_entry.configure(state="disabled") # Keep it read-only to avoid manual typos? Or allow edit?
            # Actually, standard behavior is usually editable.
            # But here we used disabled for Store-Cert.
            SwitchCraftConfig.set_user_preference("CodeSigningCertPath", file_path)
            SwitchCraftConfig.set_user_preference("CodeSigningCertThumbprint", "")

    def _setup_path_settings(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame, text=i18n.get("settings_hdr_directories") or "Directories", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=5)

        # Git Repo
        ctk.CTkLabel(frame, text=i18n.get("lbl_git_path")).grid(row=1, column=0, sticky="w", padx=5)
        self.git_entry = ctk.CTkEntry(frame, width=300)
        self.git_entry.insert(0, SwitchCraftConfig.get_value("GitRepoPath", ""))
        self.git_entry.grid(row=1, column=1, padx=5)

        def save_git():
            SwitchCraftConfig.set_user_preference("GitRepoPath", self.git_entry.get())
            messagebox.showinfo(i18n.get("settings_saved"), i18n.get("settings_saved"))

        ctk.CTkButton(frame, text=i18n.get("btn_save"), width=60, command=save_git).grid(row=1, column=2, padx=5)

    def _setup_tool_settings(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame, text=i18n.get("settings_hdr_tools") or "External Tools", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=5)

        ctk.CTkLabel(frame, text=i18n.get("lbl_intune_tool_path")).grid(row=1, column=0, sticky="w", padx=5)
        self.tool_entry = ctk.CTkEntry(frame, width=300)
        self.tool_entry.insert(0, str(self.intune_service.tool_path) if self.intune_service else "")
        self.tool_entry.grid(row=1, column=1, padx=5)

    def _setup_intune_settings(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame, text=i18n.get("settings_hdr_integrations") or "Integrations", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5)

        # Grid for inputs
        auth_grid = ctk.CTkFrame(frame, fg_color="transparent")
        auth_grid.pack(fill="x", pady=5)
        auth_grid.grid_columnconfigure(1, weight=1)

        def create_auth_field(row, label, key, show=""):
            ctk.CTkLabel(auth_grid, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=2)
            entry = ctk.CTkEntry(auth_grid, show=show)
            entry.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
            entry.insert(0, SwitchCraftConfig.get_value(key, ""))
            # Save on focus out or save button? Let's do Save Button.
            return entry

        self.entry_tenant = create_auth_field(0, "Tenant ID:", "GraphTenantId")
        self.entry_client = create_auth_field(1, "Client ID:", "GraphClientId")
        self.entry_secret = create_auth_field(2, "Client Secret:", "GraphClientSecret", show="*")

        # Save Button
        def save_auth():
            t = self.entry_tenant.get().strip()
            c = self.entry_client.get().strip()
            s = self.entry_secret.get().strip()

            SwitchCraftConfig.set_user_preference("GraphTenantId", t)
            SwitchCraftConfig.set_user_preference("GraphClientId", c)
            SwitchCraftConfig.set_user_preference("GraphClientSecret", s)

            messagebox.showinfo(i18n.get("settings_verify_success_title"), i18n.get("settings_saved"))

        btn_box = ctk.CTkFrame(frame, fg_color="transparent")
        btn_box.pack(fill="x", pady=5)

        ctk.CTkButton(btn_box, text=i18n.get("btn_save"), command=save_auth).pack(side="left", padx=5)
        ctk.CTkButton(btn_box, text=i18n.get("btn_verify_save"), command=self._verify_save_intune).pack(side="left", padx=5)

    def _verify_save_intune(self):
        # Implementation of verification logic
        pass

    def _setup_template_settings(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame, text=i18n.get("settings_hdr_template") or "Templates", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5)

        ctk.CTkLabel(frame, text=i18n.get("lbl_custom_template") or "Custom Intune Template (.ps1):").pack(anchor="w", padx=5, pady=(5,0))

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=5, pady=5)

        self.template_entry = ctk.CTkEntry(row, width=300)
        self.template_entry.pack(side="left", fill="x", expand=True, padx=5)

        current_tpl = SwitchCraftConfig.get_value("CustomTemplatePath", "")
        if current_tpl:
            self.template_entry.insert(0, current_tpl)
        else:
            self.template_entry.insert(0, "(Default)")
        self.template_entry.configure(state="disabled")

        def browse_template():
             path = ctk.filedialog.askopenfilename(filetypes=[("PowerShell Script", "*.ps1")])
             if path:
                 SwitchCraftConfig.set_user_preference("CustomTemplatePath", path)
                 self.template_entry.configure(state="normal")
                 self.template_entry.delete(0, "end")
                 self.template_entry.insert(0, path)
                 self.template_entry.configure(state="disabled")

        def reset_template():
             SwitchCraftConfig.set_user_preference("CustomTemplatePath", "")
             self.template_entry.configure(state="normal")
             self.template_entry.delete(0, "end")
             self.template_entry.insert(0, "(Default)")
             self.template_entry.configure(state="disabled")

        ctk.CTkButton(row, text=i18n.get("btn_browse"), width=80, command=browse_template).pack(side="left", padx=5)
        ctk.CTkButton(row, text="Reset", width=60, fg_color="red", command=reset_template).pack(side="left", padx=5)

        ctk.CTkLabel(frame, text=i18n.get("template_help") or "Select a custom .ps1 template to use for Intune wrapping. Leave empty for default.",
                     text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10)

    def _setup_debug_console(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=10)
        # Debug console switch...

    def _get_registry_value(self, key):
        # Mock or real usage
        return "stable"

    def change_update_channel(self, value):
        # ...
        pass

    def _setup_addon_manager(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame, text=i18n.get("addon_manager_title") or "Addon Manager", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)

        # List of Addons
        addons = [
            {"id": "advanced", "name": "Advanced Features (Intune, Brute Force)", "desc": "Adds deep analysis and Intune integration."},
            {"id": "winget", "name": "Winget Integration", "desc": "adds Winget search capabilities."},
            {"id": "ai", "name": "AI Assistant", "desc": "Adds AI chat and analysis assistance."}
        ]

        # Use AddonService to check status
        from switchcraft.services.addon_service import AddonService

        for addon in addons:
            row = ctk.CTkFrame(frame)
            row.pack(fill="x", padx=5, pady=2)

            is_installed = AddonService.is_addon_installed(addon["id"])
            status_color = "green" if is_installed else "orange"
            status_text = "Installed" if is_installed else "Not Installed"

            ctk.CTkLabel(row, text=addon["name"], font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=status_text, text_color=status_color).pack(side="right", padx=10)

            if not is_installed:
                 ctk.CTkButton(row, text=i18n.get("btn_download"), width=80,
                               command=lambda id=addon["id"]: self._install_addon(id)).pack(side="right", padx=5)

    def _install_addon(self, addon_id):
        from switchcraft.services.addon_service import AddonService
        # In a real app, this would show progress. For MVP, we simulate or open link if failing.
        messagebox.showinfo("Download", f"Downloading addon {addon_id}...\n(This will happen in background in final version)")
        # Trigger service
        if AddonService.install_addon(addon_id):
             messagebox.showinfo("Success", f"Addon {addon_id} installed! Please restart.")
        else:
             webbrowser.open("https://github.com/FaserF/SwitchCraft/releases/latest")

    def _save_manual_config(self, key, value):
        SwitchCraftConfig.set_user_preference(key, value)
