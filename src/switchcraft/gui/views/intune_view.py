import customtkinter as ctk
import logging
import threading
import os
from pathlib import Path
from tkinter import messagebox
from switchcraft.utils.i18n import i18n
from switchcraft.utils.config import SwitchCraftConfig

logger = logging.getLogger(__name__)

class IntuneView(ctk.CTkFrame):
    def __init__(self, parent, intune_service, notification_service):
        super().__init__(parent)
        self.intune_service = intune_service
        self.notification_service = notification_service

        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_ui()

    def setup_ui(self):
        """Setup the dedicated Intune Utility tab."""
        # Main Layout
        self.frame_intune = ctk.CTkFrame(self)
        self.frame_intune.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.frame_intune.grid_columnconfigure(0, weight=1)
        self.frame_intune.grid_rowconfigure(0, weight=0) # Status
        self.frame_intune.grid_rowconfigure(1, weight=0) # Activation
        self.frame_intune.grid_rowconfigure(2, weight=0) # Form
        self.frame_intune.grid_rowconfigure(3, weight=1) # Log/Output

        self._refresh_intune_status()

    def _refresh_intune_status(self):
        # Clear previous
        for widget in self.frame_intune.winfo_children():
            widget.destroy()

        # Check if tool exists
        if self.intune_service.is_tool_available():
            self._show_intune_form()
        else:
            self._show_intune_activation()

    def _show_intune_activation(self):
        # Activation / Download UI
        frame = ctk.CTkFrame(self.frame_intune, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text=i18n.get("intune_tool_missing_title"), font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        ctk.CTkLabel(frame, text=i18n.get("intune_tool_missing_desc")).pack(pady=5)

        ctk.CTkButton(frame, text=i18n.get("intune_btn_download"), command=self._activate_intune_tool).pack(pady=20)

        self.lbl_activation_status = ctk.CTkLabel(frame, text="", text_color="gray")
        self.lbl_activation_status.pack(pady=5)

    def _activate_intune_tool(self):
        self.lbl_activation_status.configure(text=i18n.get("intune_status_downloading"))

        def _download():
            if self.intune_service.download_tool():
                self.after(0, self._refresh_intune_status)
            else:
                self.after(0, lambda: self.lbl_activation_status.configure(text=i18n.get("intune_status_dl_failed"), text_color="red"))

        threading.Thread(target=_download, daemon=True).start()

    def _show_intune_form(self):
        # Header
        ctk.CTkLabel(self.frame_intune, text=i18n.get("intune_header"), font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, pady=10, sticky="w", padx=20)

        # Form Frame
        form = ctk.CTkFrame(self.frame_intune)
        form.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        form.grid_columnconfigure(1, weight=1)

        # 1. Setup File
        ctk.CTkLabel(form, text=i18n.get("intune_lbl_setup")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_intune_setup = ctk.CTkEntry(form)
        self.entry_intune_setup.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(form, text=i18n.get("browse"), width=50, command=self._browse_intune_setup).grid(row=0, column=2, padx=10, pady=10)

        # 2. Source Folder
        ctk.CTkLabel(form, text=i18n.get("intune_lbl_source")).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.entry_intune_source = ctk.CTkEntry(form)
        self.entry_intune_source.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(form, text=i18n.get("browse"), width=50, command=lambda: self._browse_folder(self.entry_intune_source)).grid(row=1, column=2, padx=10, pady=10)

        # 3. Output Folder
        ctk.CTkLabel(form, text=i18n.get("intune_lbl_output")).grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.entry_intune_output = ctk.CTkEntry(form)
        self.entry_intune_output.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(form, text=i18n.get("browse"), width=50, command=lambda: self._browse_folder(self.entry_intune_output)).grid(row=2, column=2, padx=10, pady=10)

        # 4. Quiet
        self.var_intune_quiet = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(form, text=i18n.get("intune_chk_quiet"), variable=self.var_intune_quiet).grid(row=3, column=1, padx=10, pady=10, sticky="w")

        # Create Button
        # Create Button
        ctk.CTkButton(self.frame_intune, text=i18n.get("intune_btn_create"), fg_color="green", hover_color="darkgreen", height=40, font=ctk.CTkFont(size=16, weight="bold"), command=self._run_intune_creation).grid(row=4, column=0, padx=20, pady=20, sticky="ew")

        # Upload Button Area
        upload_frame = ctk.CTkFrame(self.frame_intune, fg_color="transparent")
        upload_frame.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="ew")

        # Check config
        tenant_id = SwitchCraftConfig.get_value("IntuneTenantID")
        client_id = SwitchCraftConfig.get_value("IntuneClientId")
        client_secret = SwitchCraftConfig.get_value("IntuneClientSecret")

        is_configured = tenant_id and client_id and client_secret

        btn_state = "normal" if is_configured else "disabled"
        btn_color = "#0066CC" if is_configured else "gray"

        self.btn_upload = ctk.CTkButton(
            upload_frame,
            text="☁️ Upload to Intune (Graph API)",
            fg_color=btn_color,
            state=btn_state,
            height=35,
            command=self._run_upload
        )
        self.btn_upload.pack(fill="x")

        if not is_configured:
            ctk.CTkLabel(upload_frame, text="Configure App Registration in Settings to enable upload.", text_color="gray", font=ctk.CTkFont(size=10)).pack(pady=2)



        # Log Toggle and Area
        self.frame_log_container = ctk.CTkFrame(self.frame_intune, fg_color="transparent")
        self.frame_log_container.grid(row=6, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.frame_intune.grid_rowconfigure(6, weight=1)

        self.btn_toggle_log = ctk.CTkButton(self.frame_log_container, text="Show Terminal Output", width=150, fg_color="gray", command=self._toggle_log)
        self.btn_toggle_log.pack(anchor="w", pady=(0, 5))

        self.txt_intune_log = ctk.CTkTextbox(self.frame_log_container, height=150)
        # Hidden by default - we don't pack it yet.

    def _toggle_log(self):
        if self.txt_intune_log.winfo_ismapped():
            self.txt_intune_log.pack_forget()
            self.btn_toggle_log.configure(text="Show Terminal Output")
        else:
            self.txt_intune_log.pack(fill="both", expand=True)
            self.btn_toggle_log.configure(text="Hide Terminal Output")

    def _browse_intune_setup(self):
        f = ctk.filedialog.askopenfilename(title=i18n.get("intune_browse_setup_title"))
        if f:
            self.entry_intune_setup.delete(0, "end")
            self.entry_intune_setup.insert(0, f)
            # Auto-fill source/output if empty
            if not self.entry_intune_source.get():
                self.entry_intune_source.insert(0, str(Path(f).parent))
            if not self.entry_intune_output.get():
                self.entry_intune_output.insert(0, str(Path(f).parent))

    def _browse_folder(self, entry_widget):
        d = ctk.filedialog.askdirectory()
        if d:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, d)

    def _run_intune_creation(self):
        s_setup = self.entry_intune_setup.get()
        s_source = self.entry_intune_source.get()
        s_output = self.entry_intune_output.get()
        b_quiet = self.var_intune_quiet.get()

        if not s_setup or not s_source or not s_output:
            messagebox.showerror("Error", i18n.get("intune_err_missing"))
            return

        # Prepare Log
        if not self.txt_intune_log.winfo_ismapped():
            # Optional: Auto-show on run? User said "Standardmäßig versteckt".
            # Let's keep it hidden unless user opens it, but status updates help.
            self.btn_toggle_log.configure(text="Show Terminal Output (Running...)")

        self.txt_intune_log.delete("0.0", "end")
        self.txt_intune_log.insert("end", i18n.get("intune_start_creation") + "\n")

        def _log_callback(line):
            self.after(0, lambda: self.txt_intune_log.insert("end", line))
            # Auto-scroll
            self.after(0, lambda: self.txt_intune_log.see("end"))

        def _process():
            try:
                # Pass callback for streaming
                self.intune_service.create_intunewin(
                    source_folder=s_source,
                    setup_file=s_setup,
                    output_folder=s_output,
                    quiet=b_quiet,
                    progress_callback=_log_callback
                )
                self.after(0, lambda: self.txt_intune_log.insert("end", "\nDONE!"))
                self.after(0, lambda: messagebox.showinfo("Success", i18n.get("intune_pkg_success", path=s_output)))
                self.notification_service.send_notification("Package Created", f"Created .intunewin package in {s_output}")

                # Reset button text if hidden
                if not self.txt_intune_log.winfo_ismapped():
                     self.after(0, lambda: self.btn_toggle_log.configure(text="Show Terminal Output"))

                # Open Explorer
                try:
                    os.startfile(s_output)
                except Exception:
                    pass
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self.txt_intune_log.insert("end", f"ERROR: {err_msg}\n"))
                self.after(0, lambda: messagebox.showerror("Failed", err_msg))

        threading.Thread(target=_process, daemon=True).start()

    def _run_upload(self):
        s_setup = self.entry_intune_setup.get()
        s_output = self.entry_intune_output.get()

        if not s_output:
            messagebox.showerror("Error", "Please select output folder first (where .intunewin is/will be).")
            return

        # Find .intunewin
        # Assuming filename logic from IntuneWinAppUtil: setup.exe -> setup.intunewin
        # Or check if any .intunewin exists?
        # Ideally we know the exact file.
        # If user just ran Create, we might know. But usually tool outputs [SetupFileName].intunewin

        setup_name = Path(s_setup).name
        possible_intunewin = Path(s_output) / (setup_name + ".intunewin")

        if not possible_intunewin.exists():
            # Try removing extension from setup name
            possible_intunewin = Path(s_output) / (Path(s_setup).stem + ".intunewin")

        if not possible_intunewin.exists():
             messagebox.showerror("Error", f"Could not find .intunewin file in {s_output}. Please create it first.")
             return

        self.txt_intune_log.delete("0.0", "end")
        self.txt_intune_log.insert("end", f"Starting upload for {possible_intunewin.name}...\n")

        def _process_upload():
            tenant_id = SwitchCraftConfig.get_value("IntuneTenantID")
            client_id = SwitchCraftConfig.get_value("IntuneClientId")
            client_secret = SwitchCraftConfig.get_value("IntuneClientSecret")

            try:
                self.after(0, lambda: self.txt_intune_log.insert("end", "Authenticating...\n"))
                token = self.intune_service.authenticate(tenant_id, client_id, client_secret)

                # Metadata (Simplified for now, user can edit in portal)
                app_info = {
                    "displayName": possible_intunewin.stem,
                    "description": "Uploaded via SwitchCraft",
                    "publisher": "SwitchCraft User",
                    "installCommandLine": "install.cmd",
                    "uninstallCommandLine": "uninstall.cmd",
                    "developer": "",
                    "informationUrl": None,
                    "privacyInformationUrl": None,
                    "notes": "Packaged by SwitchCraft"
                }

                # Apply Context Metadata if available
                if hasattr(self, 'current_metadata') and self.current_metadata:
                    meta = self.current_metadata
                    if meta.get("Name"):
                        app_info["displayName"] = meta.get("Name")
                    if meta.get("description"):
                        app_info["description"] = meta.get("description")
                    if meta.get("publisher"):
                        app_info["publisher"] = meta.get("publisher")
                    if meta.get("author"):
                        app_info["developer"] = meta.get("author")
                    if meta.get("homepage"):
                        app_info["informationUrl"] = meta.get("homepage")
                    if meta.get("license_url"):
                        app_info["notes"] += f"\nLicense: {meta.get('license_url')}"

                    # Detect Command Line if Script
                    if str(possible_intunewin).lower().endswith(".ps1.intunewin") or str(setup_name).lower().endswith(".ps1"):
                         base_cmd = f"powershell.exe -ExecutionPolicy Bypass -File \"{setup_name}\""
                         app_info["installCommandLine"] = base_cmd + " -InstallMode Install"
                         app_info["uninstallCommandLine"] = base_cmd + " -InstallMode Uninstall"

                def progress_cb(p, msg):
                     self.after(0, lambda: self.txt_intune_log.insert("end", f"{int(p*100)}% - {msg}\n"))

                self.intune_service.upload_win32_app(token, possible_intunewin, app_info, progress_callback=progress_cb)
                self.notification_service.send_notification("Upload Complete", f"{possible_intunewin.name} uploaded successfully!")

            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: messagebox.showerror("Upload Failed", err_msg))
                self.after(0, lambda: self.txt_intune_log.insert("end", f"ERROR: {err_msg}\n"))
                self.notification_service.send_notification("Upload Failed", err_msg)

        threading.Thread(target=_process_upload, daemon=True).start()

    def prefill_form(self, setup_path, metadata=None):
        """Pre-fills the form from an external request."""
        self.current_metadata = metadata
        path = Path(setup_path)
        if hasattr(self, 'entry_intune_setup'):
            self.entry_intune_setup.delete(0, "end")
            self.entry_intune_setup.insert(0, str(path))

            self.entry_intune_source.delete(0, "end")
            self.entry_intune_source.insert(0, str(path.parent))

            self.entry_intune_output.delete(0, "end")
            self.entry_intune_output.insert(0, str(path.parent))
