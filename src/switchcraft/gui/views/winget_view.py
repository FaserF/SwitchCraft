import customtkinter as ctk
from tkinter import messagebox
import threading
import logging
import shutil
import tempfile
import webbrowser
from pathlib import Path

from switchcraft.utils.i18n import i18n
# from switchcraft.utils.winget import WingetHelper # Moved to Addon

logger = logging.getLogger(__name__)

class WingetView(ctk.CTkFrame):
    def __init__(self, parent, winget_helper, intune_service, notification_service):
        super().__init__(parent)
        self.winget_helper = winget_helper
        self.intune_service = intune_service
        self.notification_service = notification_service
        self.main_app = parent

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_ui()

    def setup_ui(self):
        # Master Layout
        self.panes = ctk.CTkFrame(self, fg_color="transparent")
        self.panes.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.panes.grid_columnconfigure(0, weight=1) # List
        self.panes.grid_columnconfigure(1, weight=2) # Details
        self.panes.grid_rowconfigure(0, weight=1)

        # === Left Pane: Search ===
        left_pane = ctk.CTkFrame(self.panes)
        left_pane.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_pane.grid_rowconfigure(2, weight=1)
        left_pane.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left_pane, text="Winget Store", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, pady=10)

        # Search Bar
        search_frame = ctk.CTkFrame(left_pane, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text=i18n.get("winget_search_placeholder"))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.search_entry.bind("<Return>", lambda e: self._perform_search())

        ctk.CTkButton(search_frame, text=i18n.get("winget_search_btn"), width=40, command=self._perform_search).pack(side="right")

        # Results List
        self.results_scroll = ctk.CTkScrollableFrame(left_pane)
        self.results_scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # === Right Pane: Details ===
        self.right_pane = ctk.CTkFrame(self.panes)
        self.right_pane.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.right_pane.grid_columnconfigure(0, weight=1)

        self.lbl_details_title = ctk.CTkLabel(self.right_pane, text=i18n.get("manual_select"), font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl_details_title.pack(pady=20)

        self.details_content = ctk.CTkScrollableFrame(self.right_pane, fg_color="transparent")
        self.details_content.pack(fill="both", expand=True, padx=10, pady=10)

        # Initial empty state
        self.lbl_empty_state = ctk.CTkLabel(self.details_content, text=i18n.get("winget_search_placeholder"))
        self.lbl_empty_state.pack(pady=20)

        if not self.winget_helper:
            err_bg = ctk.CTkFrame(self.panes, fg_color="#DC3545", height=30)
            err_bg.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
            ctk.CTkLabel(err_bg, text="Winget Addon not loaded. Please reinstall addons.", text_color="white").pack()
            self.search_entry.configure(state="disabled")

    def _perform_search(self):
        query = self.search_entry.get().strip()
        if not query:
            return

        for w in self.results_scroll.winfo_children():
            w.destroy()

        loader = ctk.CTkLabel(self.results_scroll, text=i18n.get("winget_searching"), text_color="gray")
        loader.pack(pady=20)
        self.update()

        def _search_thread():
            error_msg = None
            results = []
            try:
                results = self.winget_helper.search_packages(query)
            except Exception as e:
                error_msg = str(e)

            self.after(0, lambda: self._display_results(results, error=error_msg))

        threading.Thread(target=_search_thread, daemon=True).start()

    def _display_results(self, results, error=None):
        for w in self.results_scroll.winfo_children():
            w.destroy()

        if error:
            err_label = ctk.CTkLabel(self.results_scroll, text=f"Error: {error}", text_color="red", wraplength=250)
            err_label.pack(pady=20, padx=10)
            return

        if not results:
            ctk.CTkLabel(self.results_scroll, text=i18n.get("winget_no_results")).pack(pady=20)
            return

        for app in results:
            # Clickable logic
            display_text = f"{app['Name']} ({app['Version']})\nID: {app['Id']}"
            b = ctk.CTkButton(self.results_scroll, text=display_text, anchor="w", fg_color="transparent", border_width=1,
                              text_color=("black", "white"),
                              command=lambda a=app: self._load_details(a))
            b.pack(fill="x", pady=2)

    def _load_details(self, app_info):
        for w in self.details_content.winfo_children():
            w.destroy()
        self.lbl_details_title.configure(text=app_info["Name"])

        loader = ctk.CTkLabel(self.details_content, text=i18n.get("winget_loading"), text_color="gray")
        loader.pack(pady=20)

        def _fetch():
            details = self.winget_helper.get_package_details(app_info["Id"])
            full_info = {**app_info, **details}
            self.after(0, lambda: self._show_full_details(full_info))

        threading.Thread(target=_fetch, daemon=True).start()

    def _show_full_details(self, info):
        for w in self.details_content.winfo_children():
            w.destroy()

        def add_row(lbl, val, link=False):
            if not val:
                return
            f = ctk.CTkFrame(self.details_content, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=lbl + ":", font=ctk.CTkFont(weight="bold"), width=100, anchor="w").pack(side="left")
            if link:
                ctk.CTkButton(f, text=val, fg_color="transparent", text_color="#3B8ED0", anchor="w", hover=False, height=20,
                              command=lambda: webbrowser.open(val)).pack(side="left", fill="x", expand=True)
            else:
                if len(val) > 50:
                    t = ctk.CTkTextbox(f, height=60, fg_color="transparent", wrap="word")
                    t.insert("0.0", val)
                    t.configure(state="disabled")
                    t.pack(side="left", fill="x", expand=True)
                else:
                    ctk.CTkLabel(f, text=val, anchor="w", wraplength=400).pack(side="left", fill="x", expand=True)

        add_row("Publisher", info.get("publisher"))
        add_row("Description", info.get("description"))
        add_row("Homepage", info.get("homepage"), link=True)
        add_row("License", info.get("license"))
        add_row("License URL", info.get("license_url"), link=True)
        add_row("Installer Type", info.get("installer_type"))
        add_row("SHA256", info.get("sha256"))

        # Actions
        ctk.CTkLabel(self.details_content, text=i18n.get("winget_actions"), font=ctk.CTkFont(weight="bold", size=14)).pack(pady=(20, 10))

        actions_frame = ctk.CTkFrame(self.details_content)
        actions_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkButton(actions_frame, text=i18n.get("winget_install_local"), fg_color="green",
                      command=lambda: self._install_local(info)).pack(side="left", padx=10, pady=10, expand=True)

        ctk.CTkButton(actions_frame, text=i18n.get("winget_deploy_intune"), fg_color="#0066CC",
                      command=lambda: self._deploy_menu(info)).pack(side="right", padx=10, pady=10, expand=True)

    def _install_local(self, info):
        scope = "machine"
        if messagebox.askyesno(i18n.get("winget_install_scope_title"), i18n.get("winget_install_scope_msg")):
            scope = "machine"
        else:
            scope = "user"

        cmd = f"winget install --id {info['Id']} --scope {scope} --accept-package-agreements --accept-source-agreements"

        top = ctk.CTkToplevel(self)
        top.title(i18n.get("winget_dl_title"))
        lbl = ctk.CTkLabel(top, text=f"{i18n.get('winget_dl_title')} {info['Name']}...")
        lbl.pack(pady=20, padx=20)

        def _run():
            success = self.winget_helper.install_package(info['Id'], scope)
            if success:
                self.after(0, lambda: messagebox.showinfo(i18n.get("winget_install_success_title"), f"{info['Name']} {i18n.get('winget_install_success_msg')}"))
            else:
                self.after(0, lambda: messagebox.showerror(i18n.get("winget_install_failed_title"), f"{i18n.get('winget_install_failed_msg')}"))
            self.after(0, top.destroy)

        threading.Thread(target=_run, daemon=True).start()

    def _deploy_menu(self, info):
        dialog = ctk.CTkToplevel(self)
        dialog.title(i18n.get("winget_deploy_dialog_title"))
        dialog.geometry("450x400")

        ctk.CTkLabel(dialog, text=f"{i18n.get('winget_deploy_dialog_title')} {info['Name']}", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        ctk.CTkLabel(dialog, text=i18n.get("winget_deploy_select_method")).pack(pady=5)

        # 1. WAU
        def _method_wau():
            dialog.destroy()
            self._deploy_wau_promo(info)

        btn1 = ctk.CTkButton(dialog, text=i18n.get("winget_method_wau"), fg_color="green", command=_method_wau)
        btn1.pack(pady=(10, 5), fill="x", padx=20)
        ctk.CTkLabel(dialog, text=i18n.get("winget_method_wau_desc"), font=ctk.CTkFont(size=10)).pack(pady=(0, 10))

        # 2. Package
        def _method_package():
            dialog.destroy()
            self._deploy_package_start(info)

        btn2 = ctk.CTkButton(dialog, text=i18n.get("winget_method_pkg"), fg_color="#0066CC", command=_method_package)
        btn2.pack(pady=5, fill="x", padx=20)
        ctk.CTkLabel(dialog, text=i18n.get("winget_method_pkg_desc"), font=ctk.CTkFont(size=10)).pack(pady=(0, 10))

        # 3. Direct Script
        def _method_direct():
            dialog.destroy()
            self._deploy_direct_script(info)

        btn3 = ctk.CTkButton(dialog, text=i18n.get("winget_method_script"), fg_color="gray", command=_method_direct)
        btn3.pack(pady=5, fill="x", padx=20)
        ctk.CTkLabel(dialog, text=i18n.get("winget_method_script_desc"), font=ctk.CTkFont(size=10)).pack(pady=(0, 10))

    def _deploy_wau_promo(self, info):
        webbrowser.open("https://github.com/Romanitho/Winget-AutoUpdate")
        messagebox.showinfo(i18n.get("winget_wau_info_title"), i18n.get("winget_wau_info_msg"))

    def _deploy_direct_script(self, info):
        script_content = f"""<#
.NOTES
Generated by SwitchCraft via Winget Integration
App: {info['Name']}
ID: {info['Id']}
#>
$PackageId = "{info['Id']}"
$LogPath = "$env:ProgramData\\Microsoft\\IntuneManagementExtension\\Logs\\Winget-{info['Id']}.log"

Start-Transcript -Path $LogPath -Force

Write-Host "Installing $PackageId via Winget..."
$winget = Get-Command winget -ErrorAction SilentlyContinue
if (!$winget) {{
    Write-Error "Winget not found!"
    exit 1
}}

& winget install --id $PackageId --accept-package-agreements --accept-source-agreements --scope machine
$err = $LASTEXITCODE

Stop-Transcript
exit $err
"""
        tmp = tempfile.mkdtemp()
        script_path = Path(tmp) / "install.ps1"
        script_path.write_text(script_content, encoding="utf-8")

        save_path = ctk.filedialog.asksaveasfilename(defaultextension=".ps1", initialfile=f"Install-{info['Id']}.ps1", title=i18n.get("winget_create_script_btn"))
        if save_path:
            shutil.copy(script_path, save_path)
            shutil.rmtree(tmp)
            if messagebox.askyesno(i18n.get("winget_script_saved", path=""), i18n.get("winget_script_saved", path="Script saved") + "\n\nPackage Now?"):
                self.main_app.show_intune_tab(save_path, metadata=info)

    def _deploy_package_start(self, info):
        top = ctk.CTkToplevel(self)
        top.title(i18n.get("winget_dl_title"))
        ctk.CTkLabel(top, text=f"{i18n.get('winget_dl_title')} {info['Name']}...").pack(pady=20, padx=20)

        def _dl():
            tmp_dir = tempfile.mkdtemp()
            cmd = ["winget", "download", "--id", info["Id"], "--dir", tmp_dir, "--accept-source-agreements", "--accept-package-agreements"]
            import subprocess
            proc = subprocess.run(cmd, capture_output=True, text=True)

            if proc.returncode == 0:
                files = list(Path(tmp_dir).glob("*.*"))
                installer = None
                for f in files:
                    if f.suffix.lower() in [".exe", ".msi"]:
                        installer = f
                        break

                if installer:
                    dest_dir = Path.home() / "Downloads" / "SwitchCraft_Winget"
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest = dest_dir / installer.name
                    shutil.copy(installer, dest)

                    self.after(0, lambda: self._on_download_complete(dest, info))
                else:
                    self.after(0, lambda: messagebox.showerror(i18n.get("winget_dl_error_title"), i18n.get("winget_dl_error_no_file")))
            else:
                 self.after(0, lambda: messagebox.showerror(i18n.get("winget_dl_failed_title"), proc.stderr))
            self.after(0, top.destroy)

        threading.Thread(target=_dl, daemon=True).start()

    def _on_download_complete(self, filepath, info):
        if messagebox.askyesno(i18n.get("winget_dl_complete_title"), i18n.get("winget_dl_complete_msg", path=filepath)):
            self.main_app.start_analysis_tab(str(filepath))
