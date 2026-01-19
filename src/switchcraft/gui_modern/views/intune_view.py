import flet as ft
import threading
import logging
import os
from pathlib import Path

from switchcraft.services.intune_service import IntuneService
from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.i18n import i18n
from switchcraft.gui_modern.utils.flet_compat import create_tabs
from switchcraft.gui_modern.utils.view_utils import ViewMixin

logger = logging.getLogger(__name__)

class ModernIntuneView(ft.Column, ViewMixin):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page
        self.intune_service = IntuneService()

        # Check Tool Availability
        if not self.intune_service.is_tool_available():
            btn_dl = ft.Button(i18n.get("btn_download_tool") or "Download Intune Tool")
            btn_dl.on_click = lambda e: self._show_snack("Download feature coming soon")

            self.controls = [
                ft.Column([
                    ft.Icon(ft.Icons.WARNING_AMBER, size=50, color="orange"),
                    ft.Text("IntuneWinAppUtil not found.", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text("This tool is required to package applications."),
                    btn_dl
                ], alignment=ft.MainAxisAlignment.CENTER)
            ]
            self.alignment = ft.MainAxisAlignment.CENTER
            self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
            return

        # Main Layout: Tabs
        self.packager_content = self._build_packager_tab()
        self.uploader_content = self._build_uploader_tab()
        self.tab_body = ft.Container(content=self.packager_content, expand=True)

        def on_tab_change(e):
             idx = int(e.control.selected_index)
             if idx == 0:
                 self.tab_body.content = self.packager_content
             else:
                 self.tab_body.content = self.uploader_content
             self.tab_body.update()

        self.tabs = create_tabs(
            selected_index=0,
            animation_duration=300,
            on_change=on_tab_change,
            tabs=[
                ft.Tab(
                    label=i18n.get("tab_packager") or "Packager",
                    icon=ft.Icons.INVENTORY_2
                ),
                ft.Tab(
                    label=i18n.get("tab_uploader") or "Uploader & Update",
                    icon=ft.Icons.CLOUD_UPLOAD
                ),
            ],
            expand=False
        )

        self.controls = [
            ft.Text(i18n.get("intune_manager_title") or "Intune Manager", size=28, weight=ft.FontWeight.BOLD),
            ft.Text(i18n.get("intune_manager_desc") or "Package and Upload Win32 Apps", color="GREY"),
            ft.Divider(),
            self.tabs,
            self.tab_body
        ]

    # --- Packager Tab ---
    def _build_packager_tab(self):
        self.log_view = ft.ListView(expand=True, spacing=5, auto_scroll=True)

        self.setup_field = ft.TextField(label=i18n.get("lbl_setup_file") or "Setup File (.exe/.msi)", expand=True)
        self.source_field = ft.TextField(label=i18n.get("lbl_source_folder") or "Source Folder", expand=True)
        self.output_field = ft.TextField(label=i18n.get("lbl_output_folder") or "Output Folder", expand=True)
        self.quiet_check = ft.Checkbox(label=i18n.get("lbl_quiet_mode") or "Quiet Mode (No UI)", value=True)

        # Helpers
        def pick_setup_file(e):
            path = FilePickerHelper.pick_file(allowed_extensions=["exe", "msi", "ps1", "bat", "cmd", "vbs", "wsf", "msp"])
            if path:
                self.setup_field.value = path
                parent = os.path.dirname(path)
                if not self.source_field.value:
                    self.source_field.value = parent
                if not self.output_field.value:
                    self.output_field.value = parent
                self.update()

        def pick_folder(e, field):
            path = FilePickerHelper.pick_directory()
            if path:
                field.value = path
                self.update()

        def create_file_row():
            btn = ft.IconButton(ft.Icons.FILE_OPEN, on_click=pick_setup_file)
            return ft.Row([self.setup_field, btn])

        def create_folder_row(field):
            btn = ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=lambda e: pick_folder(e, field))
            return ft.Row([field, btn])

        btn_create = ft.Button(
            i18n.get("btn_create_intunewin") or "Create .intunewin",
            style=ft.ButtonStyle(
                bgcolor="GREEN_700",
                color="WHITE",
            ),
            height=50,
            on_click=self._run_creation
        )

        return ft.Container(
            content=ft.Column([
                ft.Text(i18n.get("packager_title") or "Create Package", size=20, weight=ft.FontWeight.BOLD),
                create_file_row(),
                create_folder_row(self.source_field),
                create_folder_row(self.output_field),
                self.quiet_check,
                btn_create,
                ft.Divider(),
                ft.Text(i18n.get("lbl_logs") or "Logs:", weight=ft.FontWeight.BOLD),
                ft.Container(content=self.log_view, expand=True, bgcolor="BLACK", padding=10, border_radius=5)
            ], expand=True, spacing=15),
            padding=20
        )

    # --- Uploader Tab ---
    def _build_uploader_tab(self):
        # Credentials
        """
        Builds the "Uploader & Update" tab UI used for uploading .intunewin packages to Intune and managing supersedence.

        The tab includes connection controls (tenant/client credential usage and a Connect button), file and app metadata fields (file, display name, publisher, description, install/uninstall commands), upload controls (status text and an Upload button), and supersedence tools (search field, progress indicator, results dropdown, copy-metadata button, and an uninstall-previous-version switch). Long-running actions (authentication, search, metadata fetch, file picking, and upload) are started on background threads and update the UI when complete.

        Returns:
            ft.Container: A Flet container holding the uploader tab layout and interactive controls.
        """
        self.tenant_id = SwitchCraftConfig.get_value("IntuneTenantID", "")
        self.client_id = SwitchCraftConfig.get_value("IntuneClientID", "")
        self.client_secret = SwitchCraftConfig.get_secure_value("IntuneClientSecret") or ""

        # UI Elements
        self.up_file_field = ft.TextField(label=i18n.get("lbl_intunewin_file") or ".intunewin File", expand=True)
        self.up_display_name = ft.TextField(label=i18n.get("lbl_display_name") or "Display Name", expand=True)
        self.up_description = ft.TextField(label=i18n.get("lbl_description") or "Description", multiline=True, min_lines=2)
        self.up_publisher = ft.TextField(label=i18n.get("lbl_publisher") or "Publisher")
        self.up_install_cmd = ft.TextField(label=i18n.get("lbl_install_cmd") or "Install Command")
        self.up_uninstall_cmd = ft.TextField(label=i18n.get("lbl_uninstall_cmd") or "Uninstall Command")

        self.up_status = ft.Text(i18n.get("status_not_connected") or "Not connected", color="GREY")
        self.btn_upload = ft.Button(
            i18n.get("btn_upload_intune") or "Upload to Intune",
            icon=ft.Icons.CLOUD_UPLOAD,
            disabled=True,
            on_click=self._run_upload
        )

        # Supersedence UI
        self.search_supersede_field = ft.TextField(label=i18n.get("lbl_search_replace") or "Search App to Replace/Update", height=40, expand=True)
        self.supersede_search_progress = ft.ProgressBar(visible=False, width=300)
        self.supersede_options = ft.Dropdown(label=i18n.get("lbl_select_app") or "Select App", options=[], visible=False)
        self.supersede_copy_btn = ft.Button(
            i18n.get("btn_copy_metadata") or "Copy Metadata",
            icon=ft.Icons.COPY,
            disabled=True,
            visible=False,
            on_click=self._copy_metadata_from_supersedence
        )
        self.supersede_uninstall_sw = ft.Switch(label=i18n.get("lbl_uninstall_prev") or "Uninstall previous version?", value=True)
        self.supersede_status_text = ft.Text("", size=12, italic=True)

        # Connect Logic
        def connect(e):
            self.up_status.value = "Connecting..."
            self.update()
            def _bg():
                try:
                    if not self.tenant_id or not self.client_id or not self.client_secret:
                        def update_fail_creds():
                            self.up_status.value = "Missing Credentials (check Settings)"
                            self.up_status.color = "RED"
                            self.update()
                        self.app_page.run_task(update_fail_creds)
                        return

                    auth_token = self.intune_service.authenticate(self.tenant_id, self.client_id, self.client_secret)

                    def update_success():
                        self.token = auth_token
                        self.up_status.value = "Connected"
                        self.up_status.color = "GREEN"
                        self.btn_upload.disabled = False
                        self.update()
                    self.app_page.run_task(update_success)

                except Exception as ex:
                    error_msg = str(ex)  # Capture error message for use in nested function
                    def update_error():
                        self.up_status.value = f"Connection Failed: {error_msg}"
                        self.up_status.color = "RED"
                        self.update()
                    self.app_page.run_task(update_error)
                except BaseException:
                    # Catch all exceptions including KeyboardInterrupt to prevent unhandled thread exceptions
                    logger.exception("Unexpected error in connection background thread")

            threading.Thread(target=_bg, daemon=True).start()

        btn_connect = ft.Button(i18n.get("btn_connect") or "Connect", on_click=connect)

        # Supersedence Logic
        def search_apps(e):
            """
            Searches Intune for apps matching the supersedence query and updates the uploader UI with progress, results, and status.

            Runs the network search in a background thread. While searching, shows a progress indicator and hides results; on success caches found apps, populates the supersedence dropdown with labeled options, and updates the status text and colors; on failure updates the status with an error message and hides result controls. If the user is not connected or the query is empty, shows an appropriate snack message and returns without starting a search.

            Parameters:
                e: Event object from the UI interaction that triggered the search (may be None or unused).
            """
            if not hasattr(self, 'token'):
                self._show_snack(i18n.get("connect_first") or "Connect first", "RED")
                return
            query = self.search_supersede_field.value
            if not query:
                self._show_snack(i18n.get("enter_search_query") or "Please enter a search query", "ORANGE")
                return

            # Show loading indicator
            self.supersede_status_text.value = i18n.get("searching") or "Searching..."
            self.supersede_search_progress.visible = True
            self.supersede_options.visible = False
            self.supersede_copy_btn.visible = False
            self.update()

            def _bg():
                """
                Perform the supersedence app search and apply results to the UI.

                Executes intune_service.search_apps(self.token, query), logs the outcome, and updates UI elements:
                - hides the progress indicator,
                - when no apps are found sets the status text to "No apps found" (localized), hides options and copy button,
                - when apps are found caches them in self.found_apps, populates self.supersede_options with descriptive labels, and sets a localized found count and green status.

                UI updates are scheduled via self.app_page.run_task when available; on exceptions the updates are applied directly. Any exceptions during the search are logged and reported to the UI with a localized error message and red status.
                """
                try:
                    logger.info(f"Searching for apps with query: {query}")
                    apps = self.intune_service.search_apps(self.token, query)
                    logger.info(f"Search returned {len(apps) if apps else 0} apps")

                    def update_results():
                        self.supersede_search_progress.visible = False

                        if not apps:
                            self.supersede_status_text.value = i18n.get("no_apps_found") or "No apps found"
                            self.supersede_status_text.color = "GREY"
                            self.supersede_options.visible = False
                            self.supersede_copy_btn.visible = False
                        else:
                            self.found_apps = {app['id']: app for app in apps}
                            options = [ft.dropdown.Option(
                                app['id'],
                                f"{app.get('displayName', i18n.get('unknown') or 'Unknown')} ({app.get('appVersion', app.get('version', i18n.get('unknown') or 'Unknown'))})"
                            ) for app in apps]

                            self.supersede_options.options = options
                            self.supersede_options.visible = True
                            self.supersede_status_text.value = (i18n.get("found_apps") or "Found {count} apps").format(count=len(apps))
                            self.supersede_status_text.color = "GREEN"
                        self.update()

                    # Use run_task if available, otherwise update directly
                    try:
                        self.app_page.run_task(update_results)
                    except Exception:
                        update_results()

                except Exception as ex:
                    logger.exception(f"Error searching apps: {ex}")
                    error_msg = str(ex)  # Capture error message for use in nested function
                    def update_error():
                        self.supersede_search_progress.visible = False
                        self.supersede_status_text.value = f"{i18n.get('search_error') or 'Search Error'}: {error_msg}"
                        self.supersede_status_text.color = "RED"
                        self.supersede_options.visible = False
                        self.supersede_copy_btn.visible = False
                        self.update()

                    try:
                        self.app_page.run_task(update_error)
                    except Exception:
                        update_error()

            threading.Thread(target=_bg, daemon=True).start()

        def on_app_select(e):
            """
            Handle selection of an app from the supersedence results and populate UI fields.

            Sets the selected_supersede_id from the dropdown, enables and shows the Copy Metadata button,
            then either auto-fills metadata from cached app data or triggers a fetch of full app details.
            Requests a UI refresh after updating state.
            """
            self.selected_supersede_id = self.supersede_options.value
            self.supersede_copy_btn.disabled = False
            self.supersede_copy_btn.visible = True

            # Automatically copy metadata when app is selected
            if self.selected_supersede_id and hasattr(self, 'found_apps') and self.selected_supersede_id in self.found_apps:
                # Use cached app data if available
                app_data = self.found_apps[self.selected_supersede_id]
                self._auto_fill_from_app(app_data)
            else:
                # Fetch full details if not in cache
                self._copy_metadata_from_supersedence(None)

            self.update()

        self.supersede_options.on_change = on_app_select

        def pick_intunewin(e):
            """
            Prompt the user to select a `.intunewin` file, set the upload file field to the chosen path, and attempt to extract and apply metadata from the package.

            Parameters:
                e: Event object from the UI click/activation (unused).
            """
            path = FilePickerHelper.pick_file(allowed_extensions=["intunewin"])
            if path:
                self.up_file_field.value = path
                # Try to extract info from intunewin file automatically
                self._extract_info_from_intunewin(path)
                self.update()

        btn_pick = ft.IconButton(ft.Icons.FILE_OPEN, on_click=pick_intunewin)

        return ft.Container(
            content=ft.ListView([
                ft.Text(i18n.get("upload_title") or "Upload & Update App", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([btn_connect, self.up_status]),
                ft.Divider(),

                ft.Text(i18n.get("hdr_supersedence") or "Update Existing App (Supersedence)", weight=ft.FontWeight.BOLD, color="BLUE"),
                ft.Row([self.search_supersede_field, ft.IconButton(ft.Icons.SEARCH, on_click=search_apps)]),
                ft.Container(
                    content=ft.Column([
                        self.supersede_search_progress,
                        self.supersede_status_text
                    ], tight=True, spacing=5),
                ),
                self.supersede_options,
                self.supersede_copy_btn,
                self.supersede_uninstall_sw,
                ft.Divider(),

                ft.Text(i18n.get("hdr_app_details") or "New App Details", weight=ft.FontWeight.BOLD),
                ft.Row([self.up_file_field, btn_pick]),
                self.up_display_name,
                self.up_publisher,
                self.up_description,
                ft.Row([self.up_install_cmd, self.up_uninstall_cmd]),

                ft.Container(height=10),
                self.btn_upload
            ], spacing=15, padding=10),
            padding=20,
            expand=True
        )

    def _auto_fill_from_app(self, app_data):
        """
        Populate uploader UI fields from provided Intune app metadata and refresh the view.

        Populates display name, description, publisher, and install/uninstall command fields when those keys are present in app_data. If the uploader's selected .intunewin file exists on disk, attempts to extract and apply additional metadata from that file. Errors are logged and do not propagate.

        Parameters:
            app_data (dict): Intune app metadata; expected keys include 'displayName', 'description', 'publisher', 'installCommandLine', and 'uninstallCommandLine'.
        """
        try:
            # Fill basic fields
            if app_data.get("displayName"):
                self.up_display_name.value = app_data.get("displayName", "")
            if app_data.get("description"):
                self.up_description.value = app_data.get("description", "")
            if app_data.get("publisher"):
                self.up_publisher.value = app_data.get("publisher", "")

            # Fill commands
            if app_data.get("installCommandLine"):
                self.up_install_cmd.value = app_data.get("installCommandLine", "")
            if app_data.get("uninstallCommandLine"):
                self.up_uninstall_cmd.value = app_data.get("uninstallCommandLine", "")

            # Try to extract info from .intunewin file if available
            intunewin_path = self.up_file_field.value
            if intunewin_path and Path(intunewin_path).exists():
                self._extract_info_from_intunewin(intunewin_path)

            self.update()
        except Exception as ex:
            logger.warning(f"Error auto-filling from app data: {ex}")

    def _extract_info_from_intunewin(self, intunewin_path):
        """
        Populate UI fields from metadata found inside a .intunewin archive.

        Reads manifest or metadata files inside the provided .intunewin (ZIP) file and, if an `applicationInfo` object is present, fills the view's display name, publisher, and description fields only when those fields are currently empty. Parsing errors and other failures are logged at debug level and do not raise exceptions.

        Parameters:
            intunewin_path (str | pathlib.Path): Filesystem path to the .intunewin archive to inspect.
        """
        try:
            import zipfile
            import json

            # .intunewin files are ZIP archives
            with zipfile.ZipFile(intunewin_path, 'r') as zip_ref:
                # Look for detection.xml or metadata files
                file_list = zip_ref.namelist()

                # Try to find detection.xml or IntuneWinAppUtil metadata
                for file_name in file_list:
                    if 'detection.xml' in file_name.lower():
                        try:
                            detection_content = zip_ref.read(file_name).decode('utf-8')
                            # Parse XML to extract info if needed
                            # For now, we'll focus on the manifest if available
                        except Exception:
                            pass

                    # Look for manifest or metadata JSON
                    if 'manifest' in file_name.lower() or 'metadata' in file_name.lower():
                        try:
                            if file_name.endswith('.json'):
                                manifest_content = zip_ref.read(file_name).decode('utf-8')
                                manifest_data = json.loads(manifest_content)

                                # Extract available info
                                if not self.up_display_name.value and manifest_data.get("applicationInfo", {}).get("name"):
                                    self.up_display_name.value = manifest_data["applicationInfo"]["name"]
                                if not self.up_publisher.value and manifest_data.get("applicationInfo", {}).get("publisher"):
                                    self.up_publisher.value = manifest_data["applicationInfo"]["publisher"]
                                if not self.up_description.value and manifest_data.get("applicationInfo", {}).get("description"):
                                    self.up_description.value = manifest_data["applicationInfo"]["description"]
                        except Exception as ex:
                            logger.debug(f"Failed to parse manifest from intunewin: {ex}")
        except Exception as ex:
            logger.debug(f"Failed to extract info from intunewin file: {ex}")

    def _copy_metadata_from_supersedence(self, e):
        """
        Copy metadata from the selected supersedence app into the uploader fields.

        Fetches full app details for the currently selected supersedence app in a background thread, populates available uploader fields (display name, description, publisher, install/uninstall commands), attempts to extract additional metadata from the chosen .intunewin file if present, updates the supersedence status text and color, and shows a confirmation snack on success. On failure, updates the supersedence status with an error message.

        Parameters:
            e: Event or click payload that triggered the action (may be None). The function does not use this value except to match the caller signature.
        """
        app_id = self.supersede_options.value if self.supersede_options.value else (self.selected_supersede_id if hasattr(self, 'selected_supersede_id') else None)
        if not app_id:
            return

        self.supersede_status_text.value = i18n.get("fetching_details") or "Fetching details..."
        self.update()

        def _bg():
            """
            Fetch full Intune app details and apply them to the uploader UI.

            Fetches detailed app metadata for the currently selected app, fills uploader fields
            (display name, description, publisher, install/uninstall commands) when those
            fields are empty, attempts to extract additional metadata from a selected
            .intunewin file if present, updates the supersede status text to indicate
            success and shows a success snack. On failure, logs the error and updates the
            supersede status text to indicate the copy failed.
            """
            try:
                # Get full details if needed, or use cached search result
                # Search result is usually summary, get_app_details is better
                full_app = self.intune_service.get_app_details(self.token, app_id)

                def update_ui():
                    # Fill all available fields
                    self.up_display_name.value = full_app.get("displayName", "") or self.up_display_name.value or ""
                    self.up_description.value = full_app.get("description", "") or self.up_description.value or ""
                    self.up_publisher.value = full_app.get("publisher", "") or self.up_publisher.value or ""
                    self.up_install_cmd.value = full_app.get("installCommandLine", "") or self.up_install_cmd.value or ""
                    self.up_uninstall_cmd.value = full_app.get("uninstallCommandLine", "") or self.up_uninstall_cmd.value or ""

                    # Try to extract additional info from .intunewin if available
                    intunewin_path = self.up_file_field.value
                    if intunewin_path and Path(intunewin_path).exists():
                        self._extract_info_from_intunewin(intunewin_path)

                    self.supersede_status_text.value = i18n.get("metadata_copied") or "Metadata copied!"
                    self.supersede_status_text.color = "GREEN"
                    self.update()
                    self._show_snack((i18n.get("metadata_copied_from") or "Metadata copied from {name}").format(name=full_app.get("displayName", "")), "GREEN")

                # Use page.update() directly instead of run_task to avoid coroutine requirement
                if hasattr(self.app_page, 'run_task'):
                    try:
                        self.app_page.run_task(update_ui)
                    except TypeError:
                        # If run_task requires async, use update directly
                        update_ui()
                else:
                    update_ui()

            except Exception as ex:
                logger.exception(f"Error copying metadata: {ex}")
                error_msg = str(ex)  # Capture error message for use in nested function
                def update_error():
                    self.supersede_status_text.value = f"{i18n.get('copy_failed') or 'Copy Failed'}: {error_msg}"
                    self.supersede_status_text.color = "RED"
                    self.update()
                if hasattr(self.app_page, 'run_task'):
                    try:
                        self.app_page.run_task(update_error)
                    except TypeError:
                        update_error()
                else:
                    update_error()
        threading.Thread(target=_bg, daemon=True).start()

    def _log(self, msg):
        """
        Append a line to the view's log panel and refresh the UI.

        The provided `msg` is added to `self.log_view` as a monospace, green-styled text entry and the view is refreshed. If the page exposes `run_task`, the UI update is scheduled through it; otherwise the update is performed immediately.

        Parameters:
            msg (str): The log message to append.
        """
        def _update_ui():
            self.log_view.controls.append(ft.Text(msg, font_family="Consolas", size=12, color="GREEN_400"))
            self.update()
        if hasattr(self.app_page, 'run_task'):
            try:
                self.app_page.run_task(_update_ui)
            except TypeError:
                _update_ui()
        else:
            _update_ui()

    def _run_creation(self, e):
        # ... logic mainly same as before ...
        """
        Create a .intunewin package from the configured setup, source, and output fields, run the creation in a background thread, and present success or error feedback in the UI.

        Validates that the setup file, source folder, and output folder are provided; logs a starting message, invokes the packager via the Intune service with progress forwarded to the view's log, and runs the work on a background thread. On success, attempts to locate the created .intunewin file, opens a dialog showing its location with an "Open Folder" action (which opens Windows Explorer when available), and updates the UI. On failure, logs the exception and shows an error snack.

        Parameters:
            e: The UI event that triggered this action (click event; value is not used by the method).
        """
        setup = self.setup_field.value
        source = self.source_field.value
        output = self.output_field.value
        quiet = self.quiet_check.value

        if not setup or not source or not output:
            self._show_snack(i18n.get("fill_all_fields") or "Please fill all fields", "RED")
            return

        self._log(i18n.get("starting_creation") or "Starting creation...")
        # ... (rest of creation logic similar to previous implementation)
        # simplified for brevity in this replacement block, but need to keep full logic

        def _bg():
            """
            Execute the Intune packaging operation, report progress, and present the resulting package location.

            This background task calls the Intune service to create a .intunewin package from the provided setup file and source/output folders, forwarding progress lines to the view's logger. On success it attempts to locate the produced .intunewin file, shows an alert dialog with the package path and an "Open Folder" action that opens the file explorer to the package. On failure it logs the exception and shows a failure snack message.
            """
            try:
                self.intune_service.create_intunewin(
                    source_folder=source,
                    setup_file=setup,
                    output_folder=output,
                    quiet=quiet,
                    progress_callback=lambda line: self._log(line.strip())
                )
                self._log("DONE! Package created successfully.")

                # Feedback logic verified in previous step
                possible_names = [
                    os.path.basename(setup) + ".intunewin",
                    os.path.splitext(os.path.basename(setup))[0] + ".intunewin"
                ]
                output_file = str(output) # Fallback
                for name in possible_names:
                     f = os.path.join(output, name)
                     if os.path.exists(f):
                         output_file = f
                         break

                def open_folder(e):
                    import subprocess
                    if os.name == 'nt':
                        # Use normpath to ensure backslashes
                        safe_path = os.path.normpath(output_file)
                        # Quote the path in the argument if it has spaces?
                        # subprocess.run handles list args by quoting if needed usually,
                        # but /select,path is tricky as it is one arg for explorer.
                        # However, explorer /select,"path" works.
                        # subprocess will quote individual args.
                        # We need to pass the whole string "/select,path" as one arg if we want explorer to receive it?
                        # Actually explorer expects: explorer /select,path
                        # If we pass ["explorer", "/select," + safe_path] it might be quoted as "/select,path" which is fine.
                        proc = subprocess.run(['explorer', f'/select,{safe_path}'])
                        # Wait for process to complete to avoid ResourceWarning
                        try:
                            proc.wait(timeout=5.0)
                        except Exception:
                            pass
                    dlg.open = False
                    self.app_page.update()

                dlg = ft.AlertDialog(
                    title=ft.Text(i18n.get("package_created_title") or "Package Created!", color="GREEN"),
                    content=ft.Text(f"{i18n.get('location')}: {output_file}"),
                    actions=[ft.Button(i18n.get("open_folder") or "Open Folder", on_click=open_folder)]
                )
                def show_dialog():
                    self.app_page.open(dlg)
                if hasattr(self.app_page, 'run_task'):
                    try:
                        self.app_page.run_task(show_dialog)
                    except TypeError:
                        show_dialog()
                else:
                    show_dialog()

            except Exception as ex:
                self._log(f"ERROR: {ex}")
                self._show_snack(f"Failed: {ex}", "RED")

        threading.Thread(target=_bg, daemon=True).start()

    def _run_upload(self, e):
        # Upload Logic
        path = self.up_file_field.value
        if not path or not os.path.exists(path):
            self._show_snack("Invalid File", "RED")
            return

        app_info = {
            "displayName": self.up_display_name.value,
            "description": self.up_description.value,
            "publisher": self.up_publisher.value,
            "installCommandLine": self.up_install_cmd.value,
            "uninstallCommandLine": self.up_uninstall_cmd.value
        }

        child_supersede = self.supersede_options.value
        uninstall_prev = self.supersede_uninstall_sw.value

        self.up_status.value = "Uploading..."
        self.up_status.color = "BLUE"
        self.btn_upload.disabled = True
        self.update()

        def _bg():
            try:
                def update_progress(pct, msg):
                    def _u():
                        self.up_status.value = f"{int(pct*100)}% - {msg}"
                        self.update()
                    self.app_page.run_task(_u)

                # 1. Upload
                new_app_id = self.intune_service.upload_win32_app(
                    self.token,
                    path,
                    app_info,
                    progress_callback=update_progress
                )

                # 2. Add Supersedence if selected
                if child_supersede:
                    def update_sup():
                        self.up_status.value = "Adding Supersedence..."
                        self.update()
                    self.app_page.run_task(update_sup)

                    self.intune_service.add_supersedence(self.token, new_app_id, child_supersede, uninstall_prev=uninstall_prev)

                def update_done():
                    self.up_status.value = "Upload Complete!"
                    self.up_status.color = "GREEN"
                    self.btn_upload.disabled = False
                    self.update()
                    self._show_success_dialog(new_app_id)
                self.app_page.run_task(update_done)

            except Exception as ex:
                logger.error(f"Upload failed: {ex}")
                error_msg = str(ex)  # Capture error message for use in nested function
                def update_fail():
                    self.up_status.value = f"Error: {error_msg}"
                    self.up_status.color = "RED"
                    self.btn_upload.disabled = False
                    self.update()
                self.app_page.run_task(update_fail)

        threading.Thread(target=_bg, daemon=True).start()

    def _show_success_dialog(self, app_id):
        dlg = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color="GREEN"), ft.Text("Upload Successful")]),
            content=ft.Text(f"App ID: {app_id}\nSupersedence configured if selected."),
            actions=[ft.TextButton("Close", on_click=lambda e: setattr(dlg, "open", False) or self.app_page.update())]
        )
        self.app_page.open(dlg)