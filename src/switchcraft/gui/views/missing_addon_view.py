import customtkinter as ctk
import webbrowser
from switchcraft.utils.i18n import i18n
from switchcraft.services.addon_service import AddonService
from tkinter import messagebox
import threading

class MissingAddonView(ctk.CTkFrame):
    def __init__(self, parent, app, addon_id, addon_name, description):
        super().__init__(parent)
        self.app = app
        self.addon_id = addon_id
        self.addon_name = addon_name
        self.description = description

        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=0, column=0)

        # Icon or large text
        ctk.CTkLabel(container, text="🧩", font=ctk.CTkFont(size=64)).pack(pady=(0, 20))

        ctk.CTkLabel(container,
                     text=i18n.get("addon_missing_title_fmt", name=self.addon_name) or f"{self.addon_name} Missing",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(pady=10)

        ctk.CTkLabel(container,
                     text=self.description,
                     font=ctk.CTkFont(size=14),
                     text_color="gray").pack(pady=10)

        self.status_label = ctk.CTkLabel(container, text="", text_color="orange")
        self.status_label.pack(pady=5)

        self.btn_install = ctk.CTkButton(container,
                                         text=i18n.get("btn_install_addon", name=self.addon_name) or f"Install {self.addon_name}",
                                         font=ctk.CTkFont(size=16, weight="bold"),
                                         height=40,
                                         command=self._install_addon)
        self.btn_install.pack(pady=20)

    def _install_addon(self):
        self.btn_install.configure(state="disabled")
        self.status_label.configure(text=i18n.get("status_downloading") or "Downloading & Installing...", text_color="cyan")

        def _target():
            success = AddonService.install_addon(self.addon_id)
            if success:
                self.after(0, lambda: self.status_label.configure(text=i18n.get("status_installed_restart") or "Installed! Restart required.", text_color="green"))
                # Trigger App Restart Logic
                if hasattr(self.app, '_show_restart_countdown'):
                    self.after(0, self.app._show_restart_countdown)
                else:
                    self.after(0, lambda: messagebox.showinfo("Success", i18n.get("restart_required_msg")))
            else:
                self.after(0, lambda: self.status_label.configure(text="Installation Failed.", text_color="red"))
                self.after(0, lambda: self.btn_install.configure(state="normal"))
                # Fallback
                self.after(0, lambda: self._offer_manual_download())

        threading.Thread(target=_target, daemon=True).start()

    def _offer_manual_download(self):
        if messagebox.askyesno("Error", i18n.get("addon_install_failed_manual") or "Installation failed. Open download page?"):
             webbrowser.open("https://github.com/FaserF/SwitchCraft/releases/latest")
