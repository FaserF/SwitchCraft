import customtkinter as ctk
import hashlib
import threading
from pathlib import Path
from tkinter import messagebox
from switchcraft.services.winget_manifest_service import WingetManifestService

class ManifestDialog(ctk.CTkToplevel):
    def __init__(self, parent, installer_info):
        super().__init__(parent)
        self.title("Create Winget Manifest")
        self.geometry("600x700")
        self.info = installer_info
        self.service = WingetManifestService()

        self.output_dir = None
        self.manifest_path = None

        self._setup_ui()
        self._prefill_data()

    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)

        # Scrollable Content
        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # Helper variables
        self.vars = {}

        # Fields
        self._add_field("Package Identifier", "PackageIdentifier", placeholder="Publisher.Package")
        self._add_field("Publisher", "Publisher")
        self._add_field("Package Name", "PackageName")
        self._add_field("Package Version", "PackageVersion")
        self._add_field("Publisher URL", "PublisherUrl")
        self._add_field("Short Description", "ShortDescription")
        self._add_field("License", "License", "Proprietary")
        self._add_field("Installer URL", "InstallerUrl", placeholder="https://example.com/setup.exe")
        self._add_field("Installer Type", "InstallerType", placeholder="exe, msi, nullsoft, inno...")

        # SHA256 (ReadOnly, calculated)
        self.sha_label = ctk.CTkLabel(self.scroll, text="Installer SHA256: Calculating...", text_color="orange")
        self.sha_label.pack(anchor="w", padx=10, pady=(10,0))
        self.sha_val = ctk.CTkEntry(self.scroll, state="readonly", width=400)
        self.sha_val.pack(fill="x", padx=10, pady=5)

        # Calculate SHA in background
        threading.Thread(target=self._calc_sha, daemon=True).start()

        # Action Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(btn_frame, text="Generate Manifest", fg_color="green", command=self._generate).pack(side="right", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", command=self.destroy).pack(side="right")

    def _add_field(self, label, key, default="", placeholder=""):
        frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        frame.pack(fill="x", pady=2)
        ctk.CTkLabel(frame, text=label, width=140, anchor="w").pack(side="left", padx=5)
        var = ctk.StringVar(value=default)
        self.vars[key] = var
        entry = ctk.CTkEntry(frame, textvariable=var, placeholder_text=placeholder)
        entry.pack(side="left", fill="x", expand=True, padx=5)

    def _prefill_data(self):
        # Infer data from Analysis Info
        if self.info.product_name:
            self.vars["PackageName"].set(self.info.product_name)
        if self.info.product_version:
            self.vars["PackageVersion"].set(self.info.product_version)
        if self.info.manufacturer:
            self.vars["Publisher"].set(self.info.manufacturer)
            # Guess ID
            safe_pub = "".join(x for x in self.info.manufacturer if x.isalnum())
            safe_name = "".join(x for x in (self.info.product_name or "App") if x.isalnum())
            self.vars["PackageIdentifier"].set(f"{safe_pub}.{safe_name}")

        normalized_type = self.info.installer_type.lower()
        if "msi" in normalized_type:
            self.vars["InstallerType"].set("msi")
        elif "inno" in normalized_type:
            self.vars["InstallerType"].set("inno")
        elif "nullsoft" in normalized_type or "nsis" in normalized_type:
            self.vars["InstallerType"].set("nullsoft")
        elif "installshield" in normalized_type:
            self.vars["InstallerType"].set("installshield")
        else:
            self.vars["InstallerType"].set("exe")

    def _calc_sha(self):
        try:
            path = Path(self.info.file_path)
            h = hashlib.sha256()
            with open(path, "rb") as f:
                while chunk := f.read(8192):
                    h.update(chunk)
            sha = h.hexdigest().upper()
            self.sha_val.configure(state="normal")
            self.sha_val.delete(0, "end")
            self.sha_val.insert(0, sha)
            self.sha_val.configure(state="readonly")
            self.sha_label.configure(text="Installer SHA256: Ready", text_color="green")
        except Exception as e:
            self.sha_label.configure(text=f"Error: {e}", text_color="red")

    def _generate(self):
        # Collect Data
        data = {k: v.get() for k, v in self.vars.items()}
        data["Installers"] = [{
            "InstallerUrl": data.pop("InstallerUrl"),
            "InstallerSha256": self.sha_val.get(),
            "InstallerType": data.pop("InstallerType"),
            "Architecture": "x64", # Defaulting to x64 for now
            "Scope": "machine",
            "InvestorSilentSwitches": self.info.install_switches
        }]

        # Silent Switches Override if available
        if self.info.install_switches:
            data["Installers"][0]["InstallerSwitches"] = {
                "Silent": " ".join(self.info.install_switches),
                "SilentWithProgress": " ".join(self.info.install_switches)
            }

        try:
            manifest_dir = self.service.generate_manifests(data)
            self.manifest_path = manifest_dir

            # Validate
            validation = self.service.validate_manifest(manifest_dir)

            if validation["valid"]:
                if messagebox.askyesno("Success", f"Manifests created! Validation PASSED.\nLocation: {manifest_dir}\n\nView Next Steps?"):
                    self._show_next_steps(manifest_dir)
                    self.destroy()
            else:
                top = ctk.CTkToplevel(self)
                top.title("Validation Failed")
                top.geometry("600x400")
                ctk.CTkLabel(top, text="Manifest created but Validation Failed", text_color="red").pack(pady=10)
                tb = ctk.CTkTextbox(top)
                tb.pack(fill="both", expand=True)
                tb.insert("0.0", validation["output"])
                ctk.CTkButton(top, text="Open Folder Anyway", command=lambda: self._show_next_steps(manifest_dir)).pack(pady=10)

        except Exception as e:
            messagebox.showerror("Generation Error", str(e))

    def _show_next_steps(self, manifest_dir):
        # Open folder
        import os
        os.startfile(manifest_dir)

        # Show Wizard
        top = ctk.CTkToplevel(self.master)
        top.title("Winget Submission Workflow")
        top.geometry("700x600")

        step_text = f"""
## Next Steps to Submit to Winget

1. **Fork the Winget Repo**
   - Go to [winget-pkgs](https://github.com/microsoft/winget-pkgs) and click Fork.

2. **Clone your Fork**
   - `git clone https://github.com/YOUR_USER/winget-pkgs.git`

3. **Create Branch**
   - `git checkout -b new-package-{self.vars['PackageIdentifier'].get()}`

4. **Copy Manifests**
   - The manifest files are currently in:
     `{manifest_dir}`
   - Copy this ENTIRE FOLDER to your cloned repo under `manifests` attempting to match the folder structure.
     (e.g. `winget-pkgs/manifests/m/MyPub/MyApp/1.0.0`)

5. **Commit & Push**
   - `git add .`
   - `git commit -m "New package: {self.vars['PackageIdentifier'].get()}"`
   - `git push origin`

6. **Create Pull Request**
   - Go to your GitHub fork and click "Compare & pull request".
   - The Winget bot will run automated tests.
"""

        lbl = ctk.CTkLabel(top, text="🚀 Ready for Submission!", font=ctk.CTkFont(size=20, weight="bold"))
        lbl.pack(pady=10)

        tb = ctk.CTkTextbox(top, font=("Consolas", 12))
        tb.pack(fill="both", expand=True, padx=20, pady=10)
        tb.insert("0.0", step_text)

        ctk.CTkButton(top, text="Open Folder", command=lambda: os.startfile(manifest_dir)).pack(side="left", padx=20, pady=20)
        ctk.CTkButton(top, text="Close", command=top.destroy).pack(side="right", padx=20, pady=20)
