import customtkinter as ctk
import webbrowser
import sys
import logging
from tkinter import messagebox
from switchcraft.utils.i18n import i18n
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.updater import UpdateChecker
from switchcraft.utils.templates import TemplateGenerator
from switchcraft import __version__

logger = logging.getLogger(__name__)

class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, show_update_callback):
        super().__init__(parent)
        self.show_update_callback = show_update_callback

        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_ui()

    def setup_ui(self):
        """Setup the Settings tab."""
        self.settings_scroll = ctk.CTkScrollableFrame(self)
        self.settings_scroll.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.settings_scroll.grid_columnconfigure(0, weight=1)

        # Header
        ctk.CTkLabel(self.settings_scroll, text=i18n.get("settings_title"), font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)

        # Debug Hint
        debug_hint = ctk.CTkLabel(
            self.settings_scroll,
            text=i18n.get("settings_debug_hint"),
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        debug_hint.pack(pady=2)

        # Update Channel Selection
        frame_channel = ctk.CTkFrame(self.settings_scroll)
        frame_channel.pack(fill="x", padx=10, pady=10)

        channel_label = i18n.get("settings_channel") if "settings_channel" in i18n.translations.get(i18n.language, {}) else "Update Channel"
        lbl_channel = ctk.CTkLabel(frame_channel, text=channel_label, font=ctk.CTkFont(weight="bold"))
        lbl_channel.pack(pady=5)

        self.channel_opt = ctk.CTkSegmentedButton(
            frame_channel,
            values=["Stable", "Beta", "Dev"],
            command=self.change_update_channel
        )
        # Load current channel from registry
        current_channel = self._get_registry_value("UpdateChannel")
        if not current_channel:
            # Smart Detection
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

        # Template Selection
        frame_tmpl = ctk.CTkFrame(self.settings_scroll)
        frame_tmpl.pack(fill="x", padx=10, pady=10)

        lbl_tmpl = ctk.CTkLabel(frame_tmpl, text=i18n.get("settings_tmpl_title"), font=ctk.CTkFont(weight="bold"))
        lbl_tmpl.pack(pady=5)

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


        # --- NEW SETTINGS ---

        # Signing Settings
        self._setup_signing_settings()

        # Intune / Graph Settings
        self._setup_intune_settings()

        # Git / Path Settings
        self._setup_path_settings()


        # Help & Documentation
        frame_docs = ctk.CTkFrame(self.settings_scroll)
        frame_docs.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame_docs, text="Help & Support", font=ctk.CTkFont(weight="bold")).pack(pady=5)

        btn_docs = ctk.CTkButton(frame_docs, text="Open Documentation (README)",
                               command=lambda: webbrowser.open("https://github.com/FaserF/SwitchCraft/blob/main/README.md"))
        btn_docs.pack(pady=5, fill="x")

        btn_help = ctk.CTkButton(frame_docs, text="Get Help (GitHub Issues)", fg_color="transparent", border_width=1,
                               command=lambda: webbrowser.open("https://github.com/FaserF/SwitchCraft/issues"))
        btn_help.pack(pady=5, fill="x")

        # Debug Console Toggle (Windows Only)
        if sys.platform == 'win32':
             self._setup_debug_console()

        # Update Check Button
        frame_upd = ctk.CTkFrame(self.settings_scroll)
        frame_upd.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(frame_upd, text=i18n.get("check_updates"), command=lambda: self.show_update_callback(show_no_update=True)).pack(pady=10)

        # About
        frame_about = ctk.CTkFrame(self.settings_scroll, fg_color="transparent")
        frame_about.pack(fill="x", padx=10, pady=20)

        ctk.CTkLabel(frame_about, text="SwitchCraft", font=ctk.CTkFont(size=24, weight="bold")).pack()
        ctk.CTkLabel(frame_about, text=f"{i18n.get('about_version')}: {__version__}").pack()
        ctk.CTkLabel(frame_about, text=f"{i18n.get('about_dev')}: FaserF").pack()

        link = ctk.CTkButton(frame_about, text="GitHub: FaserF/SwitchCraft", fg_color="transparent", text_color="cyan", hover=False,
                             command=lambda: webbrowser.open("https://github.com/FaserF/SwitchCraft"))
        link.pack(pady=5)

        # Footer
        ctk.CTkLabel(self.settings_scroll, text=i18n.get("brought_by"), text_color="gray").pack(side="bottom", pady=10)

    def _setup_signing_settings(self):
        frame = ctk.CTkFrame(self.settings_scroll)
        frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame, text="PowerShell Signing", font=ctk.CTkFont(weight="bold")).pack(pady=5)

        self.sign_var = ctk.BooleanVar(value=SwitchCraftConfig.get_value("SignScripts", False))

        def toggle_sign():
            SwitchCraftConfig.set_user_preference("SignScripts", self.sign_var.get())
            if self.sign_var.get():
                self.cert_frame.pack(fill="x", padx=10, pady=5)
            else:
                self.cert_frame.pack_forget()

        ctk.CTkSwitch(frame, text="Enable Script Signing", variable=self.sign_var, command=toggle_sign).pack(pady=5)

        self.cert_frame = ctk.CTkFrame(frame, fg_color="transparent")
        if self.sign_var.get():
            self.cert_frame.pack(fill="x", padx=10, pady=5)

        # Cert Path
        ctk.CTkLabel(self.cert_frame, text="Certificate Path (.pfx):").pack(anchor="w")
        self.cert_path_entry = ctk.CTkEntry(self.cert_frame)
        self.cert_path_entry.pack(fill="x", pady=2)
        self.cert_path_entry.insert(0, SwitchCraftConfig.get_value("CertPath", ""))

        def save_cert_path(event=None):
            SwitchCraftConfig.set_user_preference("CertPath", self.cert_path_entry.get())

        self.cert_path_entry.bind("<FocusOut>", save_cert_path)

        btn_frame = ctk.CTkFrame(self.cert_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=5)

        def browse_cert():
            path = ctk.filedialog.askopenfilename(filetypes=[("PFX Certificate", "*.pfx")])
            if path:
                self.cert_path_entry.delete(0, "end")
                self.cert_path_entry.insert(0, path)
                save_cert_path()

        def auto_detect_cert():
             # Placeholder for auto-detect logic (calls a service)
             # For now, we simulate detection or just warn
             messagebox.showinfo("Auto Check", "Will attempt to auto-detect cert during generation if path is empty.")

        ctk.CTkButton(btn_frame, text="Browse...", width=100, command=browse_cert).pack(side="left", padx=5)
        # ctk.CTkButton(btn_frame, text="Auto-Detect", width=100, fg_color="gray", command=auto_detect_cert).pack(side="left", padx=5)


    def _setup_intune_settings(self):
        frame = ctk.CTkFrame(self.settings_scroll)
        frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame, text="Intune / Graph API", font=ctk.CTkFont(weight="bold")).pack(pady=5)

        def create_entry(label, key, hide=False):
            ctk.CTkLabel(frame, text=label).pack(anchor="w", padx=10)
            entry = ctk.CTkEntry(frame, show="*" if hide else "")
            entry.pack(fill="x", padx=10, pady=(0, 5))
            val = SwitchCraftConfig.get_value(key, "")
            if val: entry.insert(0, val)

            def save(event=None):
                SwitchCraftConfig.set_user_preference(key, entry.get())

            entry.bind("<FocusOut>", save)
            return entry

        create_entry("Tenant ID:", "IntuneTenantID")
        create_entry("Client ID (App ID):", "IntuneClientId")
        create_entry("Client Secret:", "IntuneClientSecret", hide=True)


    def _setup_path_settings(self):
        frame = ctk.CTkFrame(self.settings_scroll)
        frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame, text="Directories", font=ctk.CTkFont(weight="bold")).pack(pady=5)

        ctk.CTkLabel(frame, text="Standard Git Repo Path:").pack(anchor="w", padx=10)

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

        ctk.CTkButton(path_frame, text="Browse...", width=80, command=browse_git).pack(side="right", padx=5)

    def _setup_debug_console(self):
        frame_debug = ctk.CTkFrame(self.settings_scroll)
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
