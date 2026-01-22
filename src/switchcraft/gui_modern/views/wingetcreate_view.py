"""
WingetCreate View - GUI for creating and updating Winget manifests.

This view provides a user-friendly interface for the wingetcreate CLI tool,
allowing users to:
- Create new manifests for packages (wingetcreate new)
- Update existing manifests (wingetcreate update)
- Configure all parameters via GUI
- Save manifests to SwitchCraft subdirectory
"""

import flet as ft
import logging
import subprocess
import threading
import os
import sys
from pathlib import Path
from switchcraft.utils.i18n import i18n
from switchcraft.gui_modern.utils.flet_compat import create_tabs
from switchcraft.gui_modern.utils.view_utils import ViewMixin


logger = logging.getLogger(__name__)


def ensure_manifest_dir():
    """Get the SwitchCraft manifest directory, creating it if needed."""

    app_data = os.getenv('APPDATA', os.path.expanduser('~'))
    base = Path(app_data) / "FaserF" / "SwitchCraft" / "winget-manifests"
    base.mkdir(parents=True, exist_ok=True)
    return base


class WingetCreateView(ft.Column, ViewMixin):
    """GUI for wingetcreate CLI to create and update Winget manifests."""

    def __init__(self, page: ft.Page):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO)
        self.app_page = page
        self.manifest_dir = ensure_manifest_dir()

        self._build_ui()

    def _build_ui(self):
        """Build the main UI."""
        # Tab body container
        self.tab_body = ft.Container(expand=True)

        def on_tab_change(e):
            idx = int(e.control.selected_index)
            if idx == 0:
                self.tab_body.content = self._build_new_tab()
            else:
                self.tab_body.content = self._build_update_tab()
            self.tab_body.update()

        tabs = create_tabs(
            selected_index=0,
            animation_duration=300,
            expand=True,
            on_change=on_tab_change,
            tabs=[
                ft.Tab(
                    label=i18n.get("wingetcreate_new") or "New Manifest",
                    icon=ft.Icons.ADD_CIRCLE_OUTLINE
                ),
                ft.Tab(
                    label=i18n.get("wingetcreate_update") or "Update Manifest",
                    icon=ft.Icons.UPDATE
                )
            ]
        )

        # Initial tab content
        self.tab_body.content = self._build_new_tab()

        self.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.TERMINAL, size=32, color="BLUE_400"),
                        ft.Column([
                            ft.Text(
                                i18n.get("wingetcreate_title") or "WingetCreate Manager",
                                size=28,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Text(
                                i18n.get("wingetcreate_subtitle") or
                                "Create and update Winget package manifests",
                                size=16,
                                color="GREY_400"
                            )
                        ], spacing=5)
                    ], spacing=15),
                    ft.Container(height=5),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.INFO_OUTLINE, size=18, color="BLUE_300"),
                            ft.Container(
                                content=ft.Text(
                                    i18n.get("wingetcreate_info", path=str(self.manifest_dir)) or
                                    f"Manifests are saved to: {self.manifest_dir}",
                                    size=12,
                                    color="GREY_400"
                                ),
                                expand=True,
                                width=None
                            ),
                            ft.IconButton(
                                ft.Icons.FOLDER_OPEN,
                                icon_size=18,
                                tooltip=i18n.get("open_folder") or "Open Folder",
                                on_click=self._open_manifest_dir
                            )
                        ], spacing=10, wrap=False),
                        padding=10,
                        bgcolor="BLACK12",
                        border_radius=8
                    ),
                    ft.Divider(height=20),
                    tabs,
                    self.tab_body
                ], expand=True, spacing=10),
                padding=20,
                expand=True
            )
        ]

    def _build_new_tab(self):
        """Build the 'New Manifest' tab."""
        # Installer URLs (multiple)
        self.new_urls = ft.TextField(
            label=i18n.get("installer_urls") or "Installer URLs",
            hint_text="https://example.com/app-x64.exe\nhttps://example.com/app-x86.exe",
            multiline=True,
            min_lines=3,
            max_lines=5,
            border_radius=8
        )

        # Package ID
        self.new_package_id = ft.TextField(
            label=i18n.get("package_id") or "Package ID",
            hint_text="Publisher.AppName",
            border_radius=8
        )

        # Version
        self.new_version = ft.TextField(
            label=i18n.get("version") or "Version",
            hint_text="1.0.0",
            border_radius=8,
            width=150
        )

        # Publisher
        self.new_publisher = ft.TextField(
            label=i18n.get("publisher") or "Publisher",
            hint_text="Publisher Name",
            border_radius=8
        )

        # App Name
        self.new_app_name = ft.TextField(
            label=i18n.get("app_name") or "Application Name",
            hint_text="My Application",
            border_radius=8
        )

        # License
        self.new_license = ft.TextField(
            label=i18n.get("license") or "License",
            hint_text="MIT, GPL-3.0, Proprietary, etc.",
            border_radius=8
        )

        # Short Description
        self.new_description = ft.TextField(
            label=i18n.get("short_description") or "Short Description",
            hint_text="A brief description of the application",
            border_radius=8
        )

        # Homepage
        self.new_homepage = ft.TextField(
            label=i18n.get("homepage") or "Homepage URL",
            hint_text="https://example.com",
            border_radius=8
        )

        # Installer Type
        self.new_installer_type = ft.Dropdown(
            label=i18n.get("installer_type") or "Installer Type",
            options=[
                ft.dropdown.Option("", i18n.get("auto_detect") or "Auto-Detect"),
                ft.dropdown.Option("exe", "EXE"),
                ft.dropdown.Option("msi", "MSI"),
                ft.dropdown.Option("msix", "MSIX"),
                ft.dropdown.Option("inno", "Inno Setup"),
                ft.dropdown.Option("nullsoft", "NSIS"),
                ft.dropdown.Option("wix", "WiX"),
                ft.dropdown.Option("burn", "Burn"),
                ft.dropdown.Option("portable", "Portable"),
                ft.dropdown.Option("zip", "ZIP"),
            ],
            value="",
            width=200
        )

        # Silent switches
        self.new_silent_args = ft.TextField(
            label=i18n.get("silent_switches") or "Silent Install Switches",
            hint_text="/S /VERYSILENT",
            border_radius=8
        )

        # Scope
        self.new_scope = ft.Dropdown(
            label=i18n.get("install_scope") or "Install Scope",
            options=[
                ft.dropdown.Option("", i18n.get("auto_detect") or "Auto-Detect"),
                ft.dropdown.Option("user", "User"),
                ft.dropdown.Option("machine", "Machine"),
            ],
            value="",
            width=150
        )

        # Architecture
        self.new_arch = ft.Dropdown(
            label=i18n.get("architecture") or "Architecture",
            options=[
                ft.dropdown.Option("", i18n.get("auto_detect") or "Auto-Detect"),
                ft.dropdown.Option("x64", "x64"),
                ft.dropdown.Option("x86", "x86"),
                ft.dropdown.Option("arm64", "ARM64"),
                ft.dropdown.Option("neutral", "Neutral"),
            ],
            value="",
            width=150
        )

        # GitHub Token (optional, for auto-submit)
        self.new_github_token = ft.TextField(
            label=i18n.get("github_token") or "GitHub Token (optional)",
            hint_text="ghp_xxxxxxxxxxxx",
            password=True,
            can_reveal_password=True,
            border_radius=8
        )

        # Submit PR checkbox
        self.new_submit_pr = ft.Checkbox(
            label=i18n.get("submit_pr") or "Submit Pull Request to winget-pkgs",
            value=False
        )

        # Status and buttons
        self.new_status = ft.Text("")
        self.new_output = ft.TextField(
            label=i18n.get("output") or "Output",
            multiline=True,
            min_lines=8,
            max_lines=12,
            read_only=True,
            text_style=ft.TextStyle(font_family="Consolas", size=11),
            border_radius=8
        )

        return ft.Container(
            content=ft.Column([
                ft.Text(
                    i18n.get("create_new_manifest") or "Create New Winget Manifest",
                    size=20,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Container(height=10),

                # Row 1: URLs
                self.new_urls,

                # Row 2: Package ID, Version
                ft.Row([self.new_package_id, self.new_version], spacing=15),

                # Row 3: Publisher, App Name
                ft.Row([self.new_publisher, self.new_app_name], spacing=15),

                # Row 4: License, Homepage
                ft.Row([self.new_license, self.new_homepage], spacing=15),

                # Row 5: Description
                self.new_description,

                # Row 6: Installer Type, Scope, Arch
                ft.Row([
                    self.new_installer_type,
                    self.new_scope,
                    self.new_arch
                ], spacing=15),

                # Row 7: Silent switches
                self.new_silent_args,

                ft.Divider(height=20),

                # GitHub options
                ft.Text(
                    i18n.get("github_options") or "GitHub Integration (Optional)",
                    weight=ft.FontWeight.BOLD
                ),
                ft.Row([self.new_github_token, self.new_submit_pr], spacing=15),

                ft.Container(height=15),

                # Buttons
                ft.Row([
                    ft.ElevatedButton(
                        text=i18n.get("generate_manifest") or "Generate Manifest",
                        icon=ft.Icons.BUILD,
                        bgcolor="BLUE_700",
                        color="WHITE",
                        on_click=self._generate_new_manifest
                    ),
                    ft.ElevatedButton(
                        text=i18n.get("validate_manifest") or "Validate",
                        icon=ft.Icons.CHECK_CIRCLE,
                        on_click=self._validate_manifest
                    ),
                    self.new_status
                ], spacing=15),

                ft.Container(height=10),
                self.new_output

            ], spacing=10, scroll=ft.ScrollMode.AUTO),
            padding=20,
            expand=True
        )

    def _build_update_tab(self):
        """Build the 'Update Manifest' tab."""
        # Package ID to update
        self.upd_package_id = ft.TextField(
            label=i18n.get("package_id") or "Package ID",
            hint_text="Microsoft.VisualStudioCode",
            border_radius=8,
            expand=True
        )

        # New URL(s)
        self.upd_urls = ft.TextField(
            label=i18n.get("new_installer_urls") or "New Installer URL(s)",
            hint_text="https://example.com/app-v2.0.0-x64.exe",
            multiline=True,
            min_lines=2,
            max_lines=4,
            border_radius=8
        )

        # New Version
        self.upd_version = ft.TextField(
            label=i18n.get("new_version") or "New Version",
            hint_text="2.0.0",
            border_radius=8,
            width=150
        )

        # GitHub Token
        self.upd_github_token = ft.TextField(
            label=i18n.get("github_token") or "GitHub Token",
            hint_text="Required for update",
            password=True,
            can_reveal_password=True,
            border_radius=8
        )

        # Submit PR
        self.upd_submit_pr = ft.Checkbox(
            label=i18n.get("submit_pr") or "Submit Pull Request",
            value=True
        )

        # Status
        self.upd_status = ft.Text("")
        self.upd_output = ft.TextField(
            label=i18n.get("output") or "Output",
            multiline=True,
            min_lines=8,
            max_lines=12,
            read_only=True,
            text_style=ft.TextStyle(font_family="Consolas", size=11),
            border_radius=8
        )

        return ft.Container(
            content=ft.Column([
                ft.Text(
                    i18n.get("update_existing_manifest") or "Update Existing Winget Package",
                    size=20,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Container(height=5),
                ft.Text(
                    i18n.get("update_manifest_desc") or
                    "Update an existing package in the winget-pkgs repository with a new version.",
                    size=14,
                    color="GREY_400"
                ),
                ft.Container(height=15),

                # Package ID
                ft.Row([self.upd_package_id], spacing=15),

                # New URLs
                self.upd_urls,

                # Version and Token
                ft.Row([self.upd_version, self.upd_github_token], spacing=15),

                # Submit PR
                self.upd_submit_pr,

                ft.Container(height=15),

                # Buttons
                ft.Row([
                    ft.ElevatedButton(
                        text=i18n.get("update_manifest") or "Update Manifest",
                        icon=ft.Icons.UPDATE,
                        bgcolor="GREEN_700",
                        color="WHITE",
                        on_click=self._update_manifest
                    ),
                    self.upd_status
                ], spacing=15),

                ft.Container(height=10),
                self.upd_output

            ], spacing=10, scroll=ft.ScrollMode.AUTO),
            padding=20,
            expand=True
        )

    def _generate_new_manifest(self, e):
        """Generate a new manifest using wingetcreate new."""
        urls = self.new_urls.value.strip()
        if not urls:
            self._show_snack(
                i18n.get("urls_required") or "At least one installer URL is required",
                "RED"
            )
            return

        self.new_status.value = i18n.get("generating") or "Generating..."
        self.new_status.color = "BLUE"
        self.new_output.value = ""
        self.update()

        def _bg():
            try:
                # Build command
                cmd = ["wingetcreate", "new"]

                # Add URLs (first positional args)
                for url in urls.split("\n"):
                    url = url.strip()
                    if url:
                        cmd.append(url)

                # Add optional parameters
                if self.new_package_id.value:
                    cmd.extend(["--id", self.new_package_id.value])
                if self.new_version.value:
                    cmd.extend(["--version", self.new_version.value])
                if self.new_publisher.value:
                    cmd.extend(["--publisher", self.new_publisher.value])
                if self.new_app_name.value:
                    cmd.extend(["--name", self.new_app_name.value])
                if self.new_license.value:
                    cmd.extend(["--license", self.new_license.value])
                if self.new_description.value:
                    cmd.extend(["--description", self.new_description.value])
                if self.new_homepage.value:
                    cmd.extend(["--home", self.new_homepage.value])
                if self.new_installer_type.value:
                    cmd.extend(["--installer-type", self.new_installer_type.value])
                if self.new_silent_args.value:
                    cmd.extend(["--silent", self.new_silent_args.value])

                if self.new_scope.value:
                    cmd.extend(["--scope", self.new_scope.value])
                if self.new_arch.value:
                    cmd.extend(["--arch", self.new_arch.value])

                # Output directory
                cmd.extend(["--output", str(self.manifest_dir)])

                # Submit PR?
                # Submit PR?
                env = os.environ.copy()
                if self.new_submit_pr.value and self.new_github_token.value:
                    # Pass token via environment variable instead of CLI argument for security
                    env["WINGET_CREATE_GITHUB_TOKEN"] = self.new_github_token.value
                    cmd.append("--submit")

                # Run command
                self.new_output.value = f"Running: {' '.join(cmd[:3])}...\n\n"
                self.update()

                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    kwargs = {"startupinfo": startupinfo, "env": env}
                else:
                    kwargs = {"env": env}

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    **kwargs
                )

                output = result.stdout + "\n" + result.stderr
                self.new_output.value += output

                if result.returncode == 0:
                    self.new_status.value = i18n.get("manifest_created") or "Manifest created!"
                    self.new_status.color = "GREEN"
                else:
                    self.new_status.value = i18n.get("manifest_failed") or "Failed"
                    self.new_status.color = "RED"

            except FileNotFoundError:
                self.new_status.value = "wingetcreate not found"
                self.new_status.color = "RED"
                self.new_output.value = (
                    "Error: wingetcreate is not installed or not in PATH.\n\n"
                    "Install it via:\n"
                    "winget install Microsoft.WingetCreate\n\n"
                    "Or download from:\n"
                    "https://github.com/microsoft/winget-create/releases"
                )
            except subprocess.TimeoutExpired:
                self.new_status.value = "Timeout"
                self.new_status.color = "RED"
                self.new_output.value += "\n\nOperation timed out after 120 seconds."
            except Exception as ex:
                self.new_status.value = f"Error: {ex}"
                self.new_status.color = "RED"
                logger.error(f"WingetCreate error: {ex}")
            finally:
                self.update()

        threading.Thread(target=_bg, daemon=True).start()

    def _update_manifest(self, e):
        """Update an existing manifest using wingetcreate update."""
        pkg_id = self.upd_package_id.value.strip()
        urls = self.upd_urls.value.strip()

        if not pkg_id or not urls:
            self._show_snack(
                i18n.get("package_id_and_urls_required") or
                "Package ID and new URLs are required",
                "RED"
            )
            return

        self.upd_status.value = i18n.get("updating") or "Updating..."
        self.upd_status.color = "BLUE"
        self.upd_output.value = ""
        self.update()

        def _bg():
            try:
                # Build command
                cmd = ["wingetcreate", "update", pkg_id]

                # Add URLs
                for url in urls.split("\n"):
                    url = url.strip()
                    if url:
                        cmd.extend(["--urls", url])

                # Version
                if self.upd_version.value:
                    cmd.extend(["--version", self.upd_version.value])

                # Output directory
                cmd.extend(["--output", str(self.manifest_dir)])

                # Submit PR?
                if self.upd_submit_pr.value and self.upd_github_token.value:
                    # Token passed via env var for security
                    cmd.append("--submit")

                # Run command
                self.upd_output.value = f"Running: wingetcreate update {pkg_id}...\n\n"
                self.update()

                env = os.environ.copy()
                if self.upd_github_token.value:
                    env["WINGET_CREATE_GITHUB_TOKEN"] = self.upd_github_token.value

                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    kwargs = {"startupinfo": startupinfo}
                else:
                    kwargs = {}

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=env,
                    **kwargs
                )

                output = result.stdout + "\n" + result.stderr
                self.upd_output.value += output

                if result.returncode == 0:
                    self.upd_status.value = i18n.get("manifest_updated") or "Manifest updated!"
                    self.upd_status.color = "GREEN"
                else:
                    self.upd_status.value = i18n.get("update_failed") or "Failed"
                    self.upd_status.color = "RED"

            except FileNotFoundError:
                self.upd_status.value = "wingetcreate not found"
                self.upd_status.color = "RED"
                self.upd_output.value = (
                    "Error: wingetcreate is not installed.\n\n"
                    "Install via: winget install Microsoft.WingetCreate"
                )
            except subprocess.TimeoutExpired:
                self.upd_status.value = "Timeout"
                self.upd_status.color = "RED"
            except Exception as ex:
                self.upd_status.value = f"Error: {ex}"
                self.upd_status.color = "RED"
                logger.error(f"WingetCreate update error: {ex}")
            finally:
                self.update()

        threading.Thread(target=_bg, daemon=True).start()

    def _validate_manifest(self, e):
        """Validate manifests in the output directory."""
        self.new_status.value = i18n.get("validating") or "Validating..."
        self.new_status.color = "BLUE"
        self.update()

        def _bg():
            try:
                cmd = ["winget", "validate", str(self.manifest_dir)]

                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    kwargs = {"startupinfo": startupinfo}
                else:
                    kwargs = {}

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    **kwargs
                )

                output = result.stdout + "\n" + result.stderr
                self.new_output.value = f"Validation Result:\n\n{output}"

                if result.returncode == 0:
                    self.new_status.value = i18n.get("validation_passed") or "Validation passed!"
                    self.new_status.color = "GREEN"
                else:
                    self.new_status.value = i18n.get("validation_failed") or "Validation failed"
                    self.new_status.color = "RED"

            except Exception as ex:
                self.new_status.value = f"Error: {ex}"
                self.new_status.color = "RED"
            finally:
                self.update()

        threading.Thread(target=_bg, daemon=True).start()

    def _open_manifest_dir(self, e):
        """Open the manifest directory in file explorer."""
        try:
            path = str(self.manifest_dir)
            self._open_path(path)
        except Exception as ex:
            logger.error(f"Failed to open manifest dir: {ex}")
