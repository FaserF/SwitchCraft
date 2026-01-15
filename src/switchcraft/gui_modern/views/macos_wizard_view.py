"""
MacOS Package Wizard - Deploy DMG/PKG files via Intune Shell Scripts.

Supports both URL downloads and local file selection.
"""

import flet as ft
from switchcraft.services.intune_service import IntuneService
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.i18n import i18n
from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper
from switchcraft.gui_modern.utils.flet_compat import create_tabs
import logging
import threading

from pathlib import Path
import shlex

logger = logging.getLogger(__name__)


class MacOSWizardView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page
        self.intune_service = IntuneService()

        # State

        self.local_file_path = None
        self.generated_script = ""

        self._init_ui()

    def _init_ui(self):
        self.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Text(
                        i18n.get("macos_wizard_title") or "MacOS Package Wizard",
                        size=28,
                        weight=ft.FontWeight.BOLD
                    ),
                    ft.Text(
                        i18n.get("macos_wizard_subtitle") or
                        "Deploy DMG/PKG files via Intune Shell Scripts",
                        size=16,
                        color="GREY_400"
                    ),
                    ft.Divider(height=20),
                    self._build_content()
                ], expand=True, spacing=10),
                padding=20,
                expand=True
            )
        ]

    def _build_content(self):
        # Tab body container
        self.source_tab_body = ft.Container(expand=True)

        # URL input
        self.url_field = ft.TextField(
            label=i18n.get("download_url_dmg_pkg") or "Download URL (DMG or PKG)",
            hint_text="https://example.com/installer.dmg",
            expand=True,
            border_radius=8
        )

        # File path display
        self.file_path_text = ft.Text(
            i18n.get("no_file_selected") or "No file selected",
            size=14,
            italic=True,
            color="GREY_400"
        )

        # URL Tab content
        url_content = ft.Column([
            ft.Icon(ft.Icons.CLOUD_DOWNLOAD, size=50, color="BLUE_400"),
            ft.Text(
                i18n.get("download_from_web") or "Download from Web",
                size=18,
                weight=ft.FontWeight.BOLD
            ),
            ft.Container(height=10),
            self.url_field
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)

        # Local File Tab content
        local_content = ft.Column([
            ft.Icon(ft.Icons.FOLDER_OPEN, size=50, color="GREEN_400"),
            ft.Text(
                i18n.get("select_local_file") or "Select Local File",
                size=18,
                weight=ft.FontWeight.BOLD
            ),
            ft.Container(height=10),
            ft.Button(
                i18n.get("browse_file") or "Browse...",
                icon=ft.Icons.FILE_OPEN,
                on_click=self._pick_local_file
            ),
            self.file_path_text
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)

        def on_source_change(e):
            idx = int(e.control.selected_index)
            if idx == 0:
                self.source_tab_body.content = url_content
            else:
                self.source_tab_body.content = local_content
            self.source_tab_body.update()

        source_tabs = create_tabs(
            selected_index=0,
            animation_duration=300,
            on_change=on_source_change,
            tabs=[
                ft.Tab(
                    label=i18n.get("download_url") or "Download URL",
                    icon=ft.Icons.LINK
                ),
                ft.Tab(
                    label=i18n.get("local_file") or "Local File",
                    icon=ft.Icons.COMPUTER
                )
            ]
        )

        self.source_tab_body.content = url_content

        # App Details
        self.app_name = ft.TextField(
            label=i18n.get("app_name_label") or "App Name",
            hint_text="My Application",
            border_radius=8,
            expand=True
        )
        self.bundle_id = ft.TextField(
            label=i18n.get("bundle_id_label") or "Bundle ID (e.g. com.example.app)",
            hint_text="com.example.myapp",
            border_radius=8,
            expand=True
        )

        # Generate button
        self.gen_btn = ft.Button(
            i18n.get("generate_installer_script") or "Generate Installer Script",
            icon=ft.Icons.BUILD,
            bgcolor="BLUE_700",
            color="WHITE",
            on_click=self._generate_script
        )

        # Script preview
        self.preview_field = ft.TextField(
            label=i18n.get("generated_shell_script") or "Generated Shell Script",
            multiline=True,
            min_lines=12,
            max_lines=18,
            read_only=False,
            text_style=ft.TextStyle(font_family="Consolas", size=11),
            border_radius=8
        )

        # Upload button
        self.upload_btn = ft.Button(
            i18n.get("upload_to_intune") or "Upload to Intune",
            icon=ft.Icons.CLOUD_UPLOAD,
            bgcolor="GREEN_700",
            color="WHITE",
            disabled=True,
            on_click=self._upload_to_intune
        )
        self.status_txt = ft.Text("")

        return ft.Container(
            content=ft.Column([
                ft.Text(
                    i18n.get("step_source_info") or "Step 1: Source Info",
                    weight=ft.FontWeight.BOLD,
                    size=16
                ),
                source_tabs,
                self.source_tab_body,
                ft.Container(height=10),
                ft.Row([self.app_name, self.bundle_id], spacing=15),
                ft.Container(height=10),
                self.gen_btn,
                ft.Divider(height=20),
                ft.Text(
                    i18n.get("step_review_script") or "Step 2: Review Script",
                    weight=ft.FontWeight.BOLD,
                    size=16
                ),
                self.preview_field,
                ft.Container(height=10),
                ft.Row([self.upload_btn, self.status_txt], spacing=15)
            ], spacing=10, scroll=ft.ScrollMode.AUTO),
            padding=10,
            expand=True
        )

    def _pick_local_file(self, e):
        """Pick a local DMG or PKG file."""
        path = FilePickerHelper.pick_file(allowed_extensions=["dmg", "pkg"])
        if path:
            self.local_file_path = path
            self.file_path_text.value = path
            self.file_path_text.color = "GREEN"

            # Try to auto-fill app name from filename
            if not self.app_name.value:
                filename = Path(path).stem
                # Clean up common patterns
                clean_name = filename.replace("-", " ").replace("_", " ")
                self.app_name.value = clean_name.title()

            self.update()

    def _generate_script(self, e):
        url = self.url_field.value.strip()
        local_file = self.local_file_path
        name = self.app_name.value.strip()

        # Validate
        if not name:
            self._show_snack(
                i18n.get("url_and_name_required") or "URL/File and App Name are required",
                "RED"
            )
            return

        if not url and not local_file:
            self._show_snack(
                i18n.get("url_and_name_required") or "URL/File and App Name are required",
                "RED"
            )
            return

        # Determine source
        if local_file:
            # For local file, we need to upload it first or use a different approach
            # For now, we'll generate a script that assumes the file is copied alongside
            source_type = "local"
            filename = Path(local_file).name
            download_section = f'''# Local file deployment
# Ensure {shlex.quote(filename)} is copied to the same location as this script
FILENAME="{shlex.quote(filename)}"
FILEPATH="$(dirname "$0")/$FILENAME"
'''
        else:
            source_type = "url"
            filename = url.split("/")[-1] or "installer"
            download_section = f'''# Download from URL
DOWNLOAD_URL="{shlex.quote(url)}"
TEMP_DIR=$(mktemp -d)
FILENAME=$(basename "$DOWNLOAD_URL")
FILEPATH="$TEMP_DIR/$FILENAME"

echo "Downloading {shlex.quote(name)}..."
curl -L -o "$FILEPATH" "$DOWNLOAD_URL"
'''

        # Template for DMG/PKG installation
        script = f'''#!/bin/bash
# Auto-generated by SwitchCraft for {shlex.quote(name)}
# Source: {"Local file" if source_type == "local" else shlex.quote(url)}

APP_NAME="{shlex.quote(name)}"
{download_section}

# Check extension
EXT="${{FILENAME##*.}}"

if [[ "$EXT" == "dmg" ]]; then
    echo "Mounting DMG..."
    MOUNTPOINT=$(hdiutil attach "$FILEPATH" -nobrowse -readonly | tail -n 1 | awk '{{print $NF}}' | tr -d '\\n')

    echo "Copying .app to /Applications..."
    # Find .app in mountpoint
    APP_PATH=$(find "$MOUNTPOINT" -maxdepth 1 -name "*.app" -print -quit)

    if [[ -n "$APP_PATH" ]]; then
        cp -R "$APP_PATH" /Applications/
        echo "Installed to /Applications/$(basename "$APP_PATH")"
    else
        echo "Error: No .app found in DMG"
        exit 1
    fi

    echo "Unmounting..."
    hdiutil detach "$MOUNTPOINT"
elif [[ "$EXT" == "pkg" ]]; then
    echo "Installing PKG..."
    installer -pkg "$FILEPATH" -target /
else
    echo "Unknown format: $EXT"
    exit 1
fi
'''

        if source_type == "url":
            script += '''
echo "Cleaning up..."
rm -rf "$TEMP_DIR"
'''

        script += '''
echo "Done."
exit 0
'''

        self.generated_script = script
        self.preview_field.value = script
        self.upload_btn.disabled = False
        self.update()

    def _upload_to_intune(self, e):
        # Authenticate
        tenant = SwitchCraftConfig.get_value("IntuneTenantID")
        client = SwitchCraftConfig.get_value("IntuneClientID")
        secret = SwitchCraftConfig.get_secure_value("IntuneClientSecret")

        if not all([tenant, client, secret]):
            self._show_snack(
                i18n.get("intune_creds_missing") or "Intune Credentials missing in Settings",
                "RED"
            )
            return

        self.status_txt.value = i18n.get("uploading") or "Uploading..."
        self.status_txt.color = "BLUE"
        self.upload_btn.disabled = True
        self.update()

        def _bg():
            try:
                token = self.intune_service.authenticate(tenant, client, secret)
                self.intune_service.upload_macos_shell_script(
                    token,
                    f"Install {self.app_name.value}",
                    f"Auto-generated installer for {self.app_name.value}",
                    self.preview_field.value
                )
                self.status_txt.value = (
                    i18n.get("upload_success_macos") or
                    "Success! Script Uploaded to MacOS > Shell Scripts."
                )
                self.status_txt.color = "GREEN"
            except Exception as ex:
                self.status_txt.value = f"Error: {ex}"
                self.status_txt.color = "RED"
                logger.error(f"MacOS upload failed: {ex}")
            finally:
                self.upload_btn.disabled = False
                self.update()

        threading.Thread(target=_bg, daemon=True).start()

    def _show_snack(self, msg, color="GREEN"):
        try:
            self.app_page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
            self.app_page.snack_bar.open = True
            self.app_page.update()
        except Exception:
            pass
