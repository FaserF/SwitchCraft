import flet as ft
import threading
import logging

from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.services.addon_service import AddonService
from switchcraft.utils.i18n import i18n
from pathlib import Path
from switchcraft.gui_modern.utils.view_utils import ViewMixin

logger = logging.getLogger(__name__)

class ModernWingetView(ft.Row, ViewMixin):
    def __init__(self, page: ft.Page):
        """
        Initialize the ModernWingetView attached to the given Flet page.

        Attempts to load the Winget addon helper and, if absent, configures a centered prompt with a button to navigate to the Addon Manager. If the helper is available, initializes UI state (search results pane, details pane, results count), builds the filter dropdown, search field, search button, and the left/right layout panes with an initial instruction in the results area. Binds search and action handlers and stores the current package state.

        Parameters:
            page (ft.Page): The Flet page instance used for rendering, navigation, and snack messages.
        """
        super().__init__(expand=True)
        self.app_page = page
        self.winget = None

        # Try to load helper
        winget_mod = AddonService().import_addon_module("winget", "utils.winget")
        if winget_mod:
            try:
                token = SwitchCraftConfig.get_secure_value("GitHubToken")
                self.winget = winget_mod.WingetHelper(github_token=token)
            except Exception as ex:
                logger.warning(f"Failed to initialize WingetHelper with token: {ex}")
                # Fallback to no-token init
                try:
                    self.winget = winget_mod.WingetHelper()
                except Exception:
                    pass

        self.current_pkg = None

        if not self.winget:
            def go_to_addons(e):
                # Navigate to Addon Manager (tab index 16)
                """
                Navigate the app to the Addon Manager tab or show a manual-navigation prompt.

                If the page exposes a `switchcraft_app.goto_tab` method, calls it with index 16 to switch to the Addon Manager.
                Otherwise displays an orange snackbar instructing the user to navigate to the Addons tab manually and updates the page.

                Parameters:
                    e: Event object from the UI control (unused).
                """
                if hasattr(page, 'switchcraft_app') and hasattr(page.switchcraft_app, 'goto_tab'):
                    page.switchcraft_app.goto_tab(16)
                else:
                    page.snack_bar = ft.SnackBar(ft.Text(i18n.get("please_navigate_manually") or "Please navigate to Addons tab manually"), bgcolor="ORANGE")
                    page.snack_bar.open = True
                    page.update()

            self.controls = [
                ft.Column([
                    ft.Icon(ft.Icons.EXTENSION_OFF, color="orange", size=50),
                    ft.Text(i18n.get("winget_addon_not_installed") or "Winget Addon not installed.", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text(i18n.get("addon_install_hint") or "Install the addon to enable this feature.", size=14, color="ON_SURFACE_VARIANT"),
                    ft.Container(height=10),
                    ft.FilledButton(
                        content=ft.Row([ft.Icon(ft.Icons.EXTENSION), ft.Text(i18n.get("btn_go_to_addons") or "Go to Addon Manager")], alignment=ft.MainAxisAlignment.CENTER),
                        bgcolor="BLUE_700",
                        color="WHITE",
                        on_click=go_to_addons
                    )
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)
            ]
            self.alignment = ft.MainAxisAlignment.CENTER
            return


        # State
        self.search_results = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        self.details_area = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        self.results_count = ft.Text("", size=12, color="GREY_500")

        # Filter dropdown
        self.filter_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("all", i18n.get("winget_filter_all") or "All Fields"),
                ft.dropdown.Option("name", i18n.get("winget_filter_name") or "Name"),
                ft.dropdown.Option("id", i18n.get("winget_filter_id") or "Package ID"),
                ft.dropdown.Option("publisher", i18n.get("winget_filter_publisher") or "Publisher"),
            ],
            value="all",
            width=130,
            height=48,
            text_size=14,
            content_padding=ft.Padding(10, 0, 10, 0),
            border_radius=8,
        )

        self.search_field = ft.TextField(
            hint_text=i18n.get("winget_search_hint") or "Search apps...",
            expand=True,
            height=48,
            text_size=14,
            content_padding=ft.Padding(12, 0, 12, 0),
            border_radius=8,
            on_submit=self._run_search
        )

        btn_search = ft.IconButton(
            icon=ft.Icons.SEARCH_ROUNDED,
            icon_color="BLUE_400",
            tooltip=i18n.get("search") or "Search",
            on_click=self._run_search
        )

        # Left Pane with filter row
        left_pane = ft.Container(
            content=ft.Column([
                ft.Text(i18n.get("winget_explorer_title") or "Winget Explorer", size=18, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [self.filter_dropdown, self.search_field, btn_search],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                self.results_count,
                ft.Divider(height=10, thickness=1),
                self.search_results
            ], expand=True),
            width=420,
            padding=15,
            bgcolor="SURFACE_CONTAINER_HIGHEST" if hasattr(getattr(ft, "colors", None), "SURFACE_CONTAINER_HIGHEST") else "GREY_900",
            border_radius=15,
            margin=ft.Margin.only(left=20, top=20, bottom=20, right=10)
        )

        # Right Pane - store as instance variable so we can update it
        # Start with visible=False to show instruction, will be set to True when details are loaded
        self.right_pane = ft.Container(
            content=self.details_area,
            expand=True,
            padding=20,
            margin=ft.Margin.only(right=20, top=20, bottom=20, left=10),
            visible=False  # Initially hidden until details are loaded
        )

        # Initial instruction
        self.search_results.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.SEARCH, size=40, color="GREY_600"),
                    ft.Text(i18n.get("winget_search_instruction") or "Enter a search term to start.",
                            color="GREY_600", text_align=ft.TextAlign.CENTER)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20,
                alignment=ft.Alignment(0, 0)
            )
        )

        self.controls = [left_pane, self.right_pane]

    def _run_search(self, e):
        """
        Initiates a package search for the current query, updates the UI to show progress, and asynchronously displays results or an error/timeout message.

        Performs a search using the winget helper for the text currently in the search field, clears previous results, shows a searching indicator, and starts a background thread that:
        - waits up to 60 seconds for the search to complete,
        - on success updates the results list via _show_list,
        - on timeout replaces the progress indicator with a localized timeout message,
        - on error replaces the progress indicator with a localized error message.

        Parameters:
            e: Event object from the UI action that triggered the search (may be None).
        """
        query = self.search_field.value
        if not query:
            return

        filter_by = self.filter_dropdown.value or "all"
        self.results_count.value = ""
        self.search_results.controls.clear()
        self.search_results.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.ProgressRing(width=40, height=40),
                    ft.Text(i18n.get("winget_searching") or "Searching...", size=16),
                    ft.Text(f"'{query}'", size=12, color="GREY_500")
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                alignment=ft.Alignment(0, 0),
                expand=True,
                padding=40
            )
        )
        try:
            self.page.update()
        except Exception:
            pass

        def _search():
            """
            Perform a winget package search on a background thread and update the UI with results, a timeout message, or an error display.

            This helper launches a background search for the current query and:
            - waits up to 60 seconds for the search to complete,
            - on success passes the results to self._show_list(filtered_by, query),
            - on timeout replaces self.search_results with a localized timeout message,
            - on exception replaces self.search_results with a localized error message and logs the error.
            The function updates the page when the UI is modified.

            Returns:
                None
            """
            try:
                result_holder = {"data": None, "error": None}

                def target():
                    try:
                        result_holder["data"] = self.winget.search_packages(query)
                    except Exception as e:
                        result_holder["error"] = e

                t = threading.Thread(target=target)
                t.start()
                t.join(timeout=60)  # Increased to 60 seconds to allow PowerShell/API/CLI fallbacks

                if t.is_alive():
                    logger.warning(f"Winget search timeout after 60s for query: {query}")
                    self.search_results.controls.clear()
                    self.search_results.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.WARNING, color="ORANGE", size=40),
                                ft.Text(i18n.get("winget_search_timeout") or "Search is taking too long...", color="ORANGE"),
                                ft.Text(i18n.get("winget_search_timeout_hint") or "Try a more specific search term or check your internet connection.", size=12, color="GREY_500")
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                            alignment=ft.Alignment(0, 0),
                            padding=40
                        )
                    )
                    try:
                        self.page.update()
                    except Exception:
                        pass
                    return

                if result_holder["error"]:
                    raise result_holder["error"]

                # Always call _show_list, even if data is empty
                # Route through _run_ui_update for thread safety (this runs in background thread)
                data = result_holder["data"] if result_holder["data"] is not None else []
                def _update_list():
                    self._show_list(data, filter_by, query)
                self._run_ui_update(_update_list)
            except Exception as ex:
                logger.error(f"Winget search error: {ex}")
                self.search_results.controls.clear()
                self.search_results.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.ERROR, color="RED", size=40),
                            ft.Text(f"{i18n.get('error_prefix') or 'Error:'} {ex}", color="RED")
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                        alignment=ft.Alignment(0, 0),
                        padding=40
                    )
                )
                try:
                    self.page.update()
                except Exception:
                    pass

        threading.Thread(target=_search, daemon=True).start()

    def _show_list(self, results, filter_by="all", query=""):
        """
        Populate the search results pane with matching Winget packages and update the results count.

        Filters the provided package list by `filter_by` ("all", "name", "id", or "publisher") when `query` is present, updates the visible results count text, and renders a ListTile for each package (attempting to use a package logo when available). Each rendered tile is bound to load the package details when clicked and the view is refreshed.

        Parameters:
            results (iterable[dict] | None): Iterable of package short-info dictionaries (expected keys: 'Id', 'Name', 'Version').
            filter_by (str): Which field to filter on; one of "all", "name", "id", or "publisher". Defaults to "all".
            query (str): Case-insensitive query string used when a non-"all" filter is selected. If empty, no filtering is applied.
        """
        # Ensure results is a list
        if results is None:
            results = []

        logger.debug(f"Showing Winget results: count={len(results)}, filter={filter_by}, query='{query}'")
        self.search_results.controls.clear()

        # Filter results based on selected filter
        if results and filter_by != "all" and query:
            query_lower = query.lower()
            filtered_results = []
            for item in results:
                if filter_by == "name" and query_lower in item.get('Name', '').lower():
                    filtered_results.append(item)
                elif filter_by == "id" and query_lower in item.get('Id', '').lower():
                    filtered_results.append(item)
                elif filter_by == "publisher":
                    # Publisher is in ID prefix (before the dot)
                    pkg_id = item.get('Id', '')
                    if '.' in pkg_id and query_lower in pkg_id.split('.')[0].lower():
                        filtered_results.append(item)
            results = filtered_results

        # Update results count
        count = len(results) if results else 0
        self.results_count.value = (i18n.get("apps_found") or "Found {0} apps").format(count) if count != 1 else (i18n.get("app_found") or "Found 1 app")

        if not results:
            self.search_results.controls.append(ft.Text(i18n.get("winget_no_results") or "No results found."))
        else:
            for item in results:
                # Try to get logo from winstall.app or manifest
                pkg_id = item.get('Id', '')
                logo_url = None
                if pkg_id:
                    # Try winstall.app logo API
                    try:
                        logo_url = f"https://cdn.winstall.app/packages/{pkg_id.replace('.', '/')}/icon.png"
                    except Exception:
                        pass

                leading_widget = ft.Icon(ft.Icons.APPS)
                if logo_url:
                    try:
                        leading_widget = ft.Image(src=logo_url, width=40, height=40, fit=ft.ImageFit.CONTAIN, error_content=ft.Icon(ft.Icons.APPS))
                    except Exception:
                        pass

                tile = ft.ListTile(
                    leading=leading_widget,
                    title=ft.Text(item.get('Name', i18n.get("unknown") or "Unknown")),
                    subtitle=ft.Text(f"{item.get('Id', '')} - {item.get('Version', '')}"),
                )
                # Capture item in lambda default arg and wrap with safe handler
                # Note: _safe_event_handler expects a handler that takes an event, so we create a wrapper
                def make_click_handler(pkg_item):
                    def handler(e):
                        try:
                            logger.info(f"Tile clicked for package: {pkg_item.get('Id', 'Unknown')}")
                            # Force run on UI thread via task safe wrapper
                            self._run_task_safe(lambda: self._load_details(pkg_item))
                        except Exception as ex:
                            logger.exception(f"Error in tile click handler for {pkg_item.get('Id', 'Unknown')}: {ex}")
                            self._show_error_view(ex, f"Load details for {pkg_item.get('Id', 'Unknown')}")
                    return handler
                tile.on_click = self._safe_event_handler(make_click_handler(item), f"Load details for {item.get('Id', 'Unknown')}")
                self.search_results.controls.append(tile)
        self.update()

    def _load_details(self, short_info):
        # Validate input first
        if not short_info or not short_info.get('Id'):
            logger.error("_load_details called with invalid short_info")
            self._show_error_view(Exception("Invalid package information"), "Load details")
            return

        logger.info(f"Loading details for package: {short_info.get('Id', 'Unknown')}")

        # Create new loading area immediately - use _run_task_safe to ensure UI updates happen on main thread
        def _show_loading():
            try:
                loading_area = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
                loading_area.controls.append(ft.ProgressBar())
                loading_area.controls.append(ft.Text(i18n.get("loading_package_details") or "Loading package details...", color="GREY_500", italic=True))
                self.details_area = loading_area

                # CRITICAL: Re-assign content to force container refresh
                self.right_pane.content = self.details_area
                self.right_pane.visible = True

                # Update UI - CORRECT ORDER: Parent first
                self.right_pane.update()
                # self.details_area.update() # Not needed if parent updated with new content
                self.update()
                if hasattr(self, 'app_page'):
                    self.app_page.update()
                logger.debug("Loading UI displayed successfully")
            except Exception as ex:
                logger.error(f"Error showing loading UI: {ex}", exc_info=True)

        self._run_task_safe(_show_loading)

        def _fetch():
            try:
                package_id = short_info.get('Id', 'Unknown')
                logger.info(f"Fetching package details for: {package_id}")
                logger.debug(f"Starting get_package_details call for {package_id}")

                # Check if winget is available
                if not self.winget:
                    raise Exception("Winget helper is not available. Please install the Winget addon.")

                try:
                    full = self.winget.get_package_details(package_id)
                except Exception as get_ex:
                    logger.error(f"get_package_details raised exception for {package_id}: {get_ex}", exc_info=True)
                    raise  # Re-raise to be caught by outer except

                logger.debug(f"Raw package details received: {list(full.keys()) if full else 'empty'}")
                logger.debug(f"Package details type: {type(full)}, length: {len(full) if isinstance(full, dict) else 'N/A'}")

                if full is None:
                    logger.warning(f"get_package_details returned None for {package_id}")
                    full = {}
                elif not full:
                    logger.warning(f"get_package_details returned empty dict for {package_id}. Using short info only.")
                    full = {}
                    # Don't raise exception, just use what we have

                merged = {**short_info, **full}
                self.current_pkg = merged
                logger.info(f"Package details fetched (partial/full), showing UI for: {merged.get('Name', 'Unknown')}")

                 # Update UI using run_task to marshal back to main thread
                def _show_ui():
                    try:
                        self._show_details_ui(merged)
                    except Exception as ex:
                        logger.exception(f"Error in _show_details_ui: {ex}")
                        self._show_error_view(ex, f"Show details UI for {package_id}")

                self._run_ui_update(_show_ui)

            except Exception as ex:
                package_id = short_info.get('Id', 'Unknown')
                logger.exception(f"Critical error in _fetch loop for {package_id}: {ex}")
                # Even in critical error, try to show at least the basic info if we can't show full details?
                # But here we probably really failed.

                error_msg = str(ex)
                if "timeout" in error_msg.lower():
                    error_msg = "Request timed out. Please check your connection and try again."

                # Update UI using run_task to marshal back to main thread
                def _show_error_ui():
                    error_area = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
                    error_area.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.ERROR, color="RED", size=40),
                                ft.Text(f"Error: {error_msg}", color="red", size=14, selectable=True),
                                ft.Text("Please check your connection and try again.", color="GREY_500", size=12, italic=True)
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                            padding=20,
                            alignment=ft.Alignment(0, 0)
                        )
                    )
                    self.details_area = error_area
                    self.right_pane.content = self.details_area
                    self.right_pane.visible = True
                    try:
                        self.details_area.update()
                        self.right_pane.update()
                        self.update()
                    except Exception as e:
                        logger.warning(f"Failed to update error UI after exception: {e}")

                self._run_ui_update(_show_error_ui)


        threading.Thread(target=_fetch, daemon=True).start()

    def _run_ui_update(self, ui_func):
        """
        Helper method to marshal UI updates to the main thread using run_task.

        Delegates to ViewMixin._run_task_safe for consistency.

        Parameters:
            ui_func (callable): Function that performs UI updates. Must be callable with no arguments.
        """
        self._run_task_safe(ui_func)

    def _show_details_ui(self, info):
        """
        Render detailed package information into the view's details_area and update the UI.

        Renders a header (including a fetched CDN logo when available), version badge, description, publisher/author, license, tags (up to 10), relevant external links (homepage, publisher site, privacy, release notes, GitHub manifest, winstall.app), and action buttons for copy/install/deploy. Uses localized labels from i18n where available and calls self.update() after composing the UI.

        Parameters:
            info (dict): Package metadata used to populate the details view. Common keys:
                - Id: package identifier (used for logo, winstall and manifest links)
                - Name: display name
                - Version: version string
                - Description / description: long description text
                - Publisher / publisher / Author / author: publisher or author name
                - License / license and LicenseUrl / license url: license text or URL
                - Tags / tags: comma- or newline-separated tags
                - Homepage / homepage, PublisherUrl / publisher url, PrivacyUrl / privacy url,
                  ReleaseNotesUrl / release notes url, ManifestUrl: URLs surfaced as link buttons

        Side effects:
            - Mutates self.details_area.controls.
            - Calls self.update() to refresh the UI.
            - May call self._open_url, self._copy_install_command, self._install_local, or self._open_deploy_menu via button callbacks.
        """
        logger.info(f"_show_details_ui called for package: {info.get('Name', 'Unknown')}")

        # Create a new Column to build the details
        detail_controls = []

        # Try to get logo
        pkg_id = info.get('Id', '')
        logo_url = None
        if pkg_id:
            try:
                logo_url = f"https://cdn.winstall.app/packages/{pkg_id.replace('.', '/')}/icon.png"
            except Exception:
                pass

        # Header Section with Logo - use icon placeholder first, load image async
        header_row = ft.Row(
            [
                ft.Icon(ft.Icons.APPS, size=64),
                ft.Column([
                    ft.Text(info.get('Name', i18n.get("unknown") or "Unknown"), size=28, weight=ft.FontWeight.BOLD),
                    ft.Text(info.get('Id', ''), color="ON_SURFACE_VARIANT", size=14)
                ], spacing=4, expand=True)
            ],
            spacing=15,
            vertical_alignment=ft.CrossAxisAlignment.START
        )
        detail_controls.append(header_row)

        # Version Badge
        version = info.get('Version', i18n.get("unknown") or "Unknown")
        detail_controls.append(
            ft.Container(
                content=ft.Text(f"v{version}", color="WHITE", size=12),
                bgcolor="BLUE_700",
                padding=ft.Padding(8, 4, 8, 4),
                border_radius=4,
                margin=ft.Margin(0, 8, 0, 8)
            )
        )

        detail_controls.append(ft.Divider())

        # Description Section (prominent like winstall.app)
        description = info.get('Description') or info.get('description')
        if description:
            detail_controls.append(ft.Text(i18n.get("field_about") or "About", size=18, weight=ft.FontWeight.BOLD))
            detail_controls.append(
                ft.Container(
                    content=ft.Text(description, size=14, selectable=True),
                    padding=ft.Padding(0, 8, 0, 16)
                )
            )

        # Publisher/Author Info
        publisher = info.get('Publisher') or info.get('publisher')
        author = info.get('Author') or info.get('author')
        if publisher or author:
            pub_text = publisher or author
            detail_controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.BUSINESS, size=16, color="GREY_500"),
                    ft.Text(f"{i18n.get('field_publisher') or 'Publisher'}: ", weight=ft.FontWeight.BOLD, size=14),
                    ft.Text(pub_text, size=14)
                ], spacing=4)
            )

        # License Section
        license_val = info.get('License') or info.get('license')
        license_url = info.get('LicenseUrl') or info.get('license url')
        if license_val or license_url:
            license_row = [
                ft.Icon(ft.Icons.GAVEL, size=16, color="GREY_500"),
                ft.Text(f"{i18n.get('field_license') or 'License'}: ", weight=ft.FontWeight.BOLD, size=14),
            ]
            if license_url:
                license_row.append(ft.TextButton(
                    content=ft.Text(license_val or i18n.get("field_view_license") or "View License"),
                    on_click=lambda e, url=license_url: self._open_url(url)
                ))
            else:
                license_row.append(ft.Text(license_val, size=14))
            detail_controls.append(ft.Row(license_row, spacing=4))

        # Tags Section
        tags = info.get('Tags') or info.get('tags')
        if tags:
            tag_list = tags.split('\n') if '\n' in tags else tags.split(',') if ',' in tags else [tags]
            tag_chips = []
            for tag in tag_list[:10]:  # Limit to 10 tags
                tag = tag.strip()
                if tag:
                    tag_chips.append(
                        ft.Container(
                            content=ft.Text(tag, size=11, color="BLUE_700"),
                            bgcolor="BLUE_50" if hasattr(getattr(ft, "colors", None), "BLUE_50") else "BLUE_900",
                            padding=ft.Padding(8, 4, 8, 4),
                            border_radius=12
                        )
                    )
            if tag_chips:
                detail_controls.append(ft.Container(height=8))
                detail_controls.append(
                    ft.Row([
                        ft.Icon(ft.Icons.LABEL, size=16, color="GREY_500"),
                        ft.Text(f"{i18n.get('field_tags') or 'Tags'}: ", weight=ft.FontWeight.BOLD, size=14),
                    ], spacing=4)
                )
                detail_controls.append(ft.Row(tag_chips, wrap=True, spacing=6))

        detail_controls.append(ft.Container(height=12))

        # Links Section
        detail_controls.append(ft.Text(i18n.get("field_links") or "Links", size=16, weight=ft.FontWeight.BOLD))

        # Homepage
        homepage = info.get('Homepage') or info.get('homepage')
        if homepage:
            detail_controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.HOME, size=16, color="BLUE_400"),
                    ft.TextButton(content=ft.Text(i18n.get("field_homepage") or "Homepage"), on_click=lambda e, url=homepage: self._open_url(url))
                ], spacing=4)
            )

        # Publisher URL
        pub_url = info.get('PublisherUrl') or info.get('publisher url')
        if pub_url:
            detail_controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.BUSINESS, size=16, color="BLUE_400"),
                    ft.TextButton(content=ft.Text(i18n.get("field_publisher_website") or "Publisher Website"), on_click=lambda e, url=pub_url: self._open_url(url))
                ], spacing=4)
            )

        # Privacy URL
        privacy_url = info.get('PrivacyUrl') or info.get('privacy url')
        if privacy_url:
            detail_controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.PRIVACY_TIP, size=16, color="BLUE_400"),
                    ft.TextButton(content=ft.Text(i18n.get("field_privacy_policy") or "Privacy Policy"), on_click=lambda e, url=privacy_url: self._open_url(url))
                ], spacing=4)
            )

        # Release Notes URL
        release_notes_url = info.get('ReleaseNotesUrl') or info.get('release notes url')
        if release_notes_url:
            detail_controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.NEW_RELEASES, size=16, color="BLUE_400"),
                    ft.TextButton(content=ft.Text(i18n.get("field_release_notes") or "Release Notes"), on_click=lambda e, url=release_notes_url: self._open_url(url))
                ], spacing=4)
            )

        # Manifest Link (GitHub)
        manifest = info.get('ManifestUrl')
        if not manifest and info.get('Id'):
            pkg_id = info.get('Id')
            try:
                parts = pkg_id.split('.', 1)
                if len(parts) >= 2:
                    publisher_part = parts[0]
                    first_char = publisher_part[0].lower()
                    manifest = f"https://github.com/microsoft/winget-pkgs/tree/master/manifests/{first_char}/{publisher_part}/{parts[1]}"
                else:
                    manifest = f"https://github.com/microsoft/winget-pkgs/tree/master/manifests/{pkg_id[0].lower()}/{pkg_id}"
            except (IndexError, ValueError):
                pass

        if manifest:
            detail_controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.CODE, size=16, color="BLUE_400"),
                    ft.TextButton(content=ft.Text(i18n.get("field_view_manifest_github") or "View Manifest on GitHub"), on_click=lambda e, url=manifest: self._open_url(url))
                ], spacing=4)
            )

        # Winstall.app link
        pkg_id = info.get('Id')
        if pkg_id:
            winstall_url = f"https://winstall.app/apps/{pkg_id}"
            detail_controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.WEB, size=16, color="PURPLE_400"),
                    ft.TextButton(content=ft.Text(i18n.get("field_view_winstall") or "View on winstall.app"), on_click=lambda e, url=winstall_url: self._open_url(url))
                ], spacing=4)
            )

        detail_controls.append(ft.Divider())

        # Actions
        btn_copy = ft.FilledButton(content=ft.Row([ft.Icon(ft.Icons.COPY), ft.Text(i18n.get("btn_copy_command") or "Copy Command")], alignment=ft.MainAxisAlignment.CENTER), bgcolor="GREY_700", color="WHITE")
        btn_copy.on_click = lambda e, i=info: self._copy_install_command(i)

        btn_local = ft.FilledButton(content=ft.Row([ft.Icon(ft.Icons.DOWNLOAD), ft.Text(i18n.get("btn_install_locally") or "Install Locally")], alignment=ft.MainAxisAlignment.CENTER), bgcolor="GREEN", color="WHITE")
        btn_local.on_click = self._install_local

        btn_deploy = ft.FilledButton(content=ft.Row([ft.Icon(ft.Icons.CLOUD_UPLOAD), ft.Text(i18n.get("btn_deploy_package") or "Deploy / Package...")], alignment=ft.MainAxisAlignment.CENTER), bgcolor="BLUE", color="WHITE")
        btn_deploy.on_click = lambda e: self._open_deploy_menu(info)

        detail_controls.append(ft.Row([btn_copy, btn_local, btn_deploy], wrap=True, spacing=8))

        # Tip
        detail_controls.append(ft.Container(height=20))
        detail_controls.append(ft.Text(i18n.get("winget_tip_autoupdate") or "Tip: Use SwitchCraft Winget-AutoUpdate to keep apps fresh!", color="ON_SURFACE_VARIANT", italic=True))

        # CRITICAL: Create a NEW Column instance with all controls
        # This forces Flet to recognize the change
        new_details_area = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        new_details_area.controls = detail_controls

        # CRITICAL: Re-assign both details_area and right_pane.content
        self.details_area = new_details_area
        self.right_pane.content = self.details_area
        self.right_pane.visible = True

        # Force update of all UI components - MUST update in correct order
        logger.info(f"Updating UI components for package details: {info.get('Name', 'Unknown')}")
        logger.debug(f"Details area has {len(self.details_area.controls)} controls")
        logger.debug(f"Right pane visible: {self.right_pane.visible}, content type: {type(self.right_pane.content)}")

        try:
            # Update right pane container - CRITICAL for visibility
            self.right_pane.update()
            logger.debug("right_pane.update() called successfully")
        except Exception as ex:
            logger.error(f"Error updating right_pane: {ex}", exc_info=True)

        try:
            # Then update the row (this view)
            self.update()
            logger.debug("self.update() called successfully")
        except Exception as ex:
            logger.error(f"Error updating view: {ex}", exc_info=True)

        # Finally update the page - this is often needed for Flet to recognize changes
        if hasattr(self, 'app_page') and self.app_page:
            try:
                self.app_page.update()
                logger.debug("app_page.update() called successfully")
            except Exception as ex:
                logger.error(f"Error updating app_page: {ex}", exc_info=True)

        logger.info(f"Package details UI update complete for: {info.get('Name', 'Unknown')}")

        logger.info(f"Package details UI updated for: {info.get('Name', 'Unknown')}")

        logger.info(f"Details UI displayed for package: {info.get('Name', 'Unknown')}")

        # Load image asynchronously AFTER UI is rendered and new Column is created
        # Find the header_row in the new details_area
        if logo_url:
            def _load_image_async():
                try:
                    img = ft.Image(src=logo_url, width=64, height=64, fit=ft.ImageFit.CONTAIN, error_content=ft.Icon(ft.Icons.APPS, size=64))
                    # Find header_row in the new details_area (first Row control)
                    def _replace():
                        try:
                            # Find the first Row in details_area (should be header_row)
                            for control in self.details_area.controls:
                                if isinstance(control, ft.Row) and len(control.controls) > 0:
                                    # Check if first control is an Icon
                                    if isinstance(control.controls[0], ft.Icon):
                                        control.controls[0] = img
                                        control.update()
                                        self.details_area.update()
                                        self.right_pane.update()
                                        if hasattr(self, 'app_page'):
                                            self.app_page.update()
                                        break
                        except Exception as ex:
                            logger.debug(f"Failed to replace header icon: {ex}")

                    if hasattr(self, 'app_page') and hasattr(self.app_page, 'run_task'):
                        # Wrap sync function in async wrapper for run_task
                        async def async_replace():
                            _replace()
                        self.app_page.run_task(async_replace)
                    else:
                        _replace()
                except Exception as ex:
                    logger.debug(f"Failed to load logo: {ex}")

            threading.Thread(target=_load_image_async, daemon=True).start()

    def _replace_header_icon(self, header_row, image):
        """Replace the icon in header_row with the loaded image."""
        try:
            if len(header_row.controls) >= 2 and isinstance(header_row.controls[0], ft.Icon):
                header_row.controls[0] = image
                header_row.update()
                if hasattr(self, 'app_page'):
                    self.app_page.update()
        except Exception as ex:
            logger.debug(f"Failed to replace header icon: {ex}")

    def _copy_install_command(self, info):
        """Copy the winget install command to clipboard."""
        pkg_id = info.get('Id', '')
        command = f"winget install --id {pkg_id} --accept-package-agreements --accept-source-agreements"
        self._copy_to_clipboard(command)
        self._show_snack(f"Copied: {command}", "GREEN_700")

    def _open_url(self, url: str):
        """Open URL in default browser."""
        try:
            self._launch_url(url)
        except Exception as ex:
            logger.error(f"Failed to open URL: {ex}")

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard."""
        try:
            import pyperclip
            pyperclip.copy(text)
        except ImportError:
            # Fallback for systems without pyperclip
            try:
                import subprocess
                subprocess.run(['clip'], input=text.encode('utf-8'), check=True)
            except Exception:
                pass

    def _open_deploy_menu(self, info):
        """
        Open a modal dialog that lets the user choose a deployment method for the given package.

        Displays a centered alert dialog titled "Deploy <Name>" with three deployment options:
        - Winget-AutoUpdate (opens WAU info via _deploy_wau),
        - Download & Package (downloads installer and prepares a package via _deploy_package),
        - Create Install Script (generates a PowerShell install script via _deploy_script).

        The dialog closes before invoking the selected handler. Dialog text and descriptions use i18n lookups when available. The dialog is assigned to self.app_page.dialog, opened, and the page is updated.

        Parameters:
            info (dict): Package metadata dictionary expected to contain at least the 'Name' key used in the dialog title.
        """
        def close_dlg(e):
            self.app_page.dialog.open = False
            self.app_page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(f"Deploy {info.get('Name')}", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.Text(i18n.get("winget_deploy_select_method") or "Select a deployment method:", size=16),
                ft.Container(height=10),

                ft.FilledButton(
                    content=ft.Row([ft.Icon(ft.Icons.UPDATE), ft.Text("Winget-AutoUpdate (WAU)")], alignment=ft.MainAxisAlignment.CENTER),
                    style=ft.ButtonStyle(bgcolor="GREEN", color="WHITE"),
                    on_click=lambda e: [close_dlg(e), self._deploy_wau(info)], width=250),
                ft.Text(i18n.get("winget_deploy_wau_desc") or "Best for keeping apps updated automatically.", size=12, italic=True),

                ft.Container(height=5),
                ft.FilledButton(
                    content=ft.Row([ft.Icon(ft.Icons.ARCHIVE), ft.Text("Download & Package")], alignment=ft.MainAxisAlignment.CENTER),
                    style=ft.ButtonStyle(bgcolor="BLUE", color="WHITE"),
                    on_click=lambda e: [close_dlg(e), self._deploy_package(info)], width=250),
                ft.Text(i18n.get("winget_deploy_package_desc") or "Download installer and prepare for Intune.", size=12, italic=True),

                ft.Container(height=5),
                ft.FilledButton(
                    content=ft.Row([ft.Icon(ft.Icons.CODE), ft.Text("Create Install Script")], alignment=ft.MainAxisAlignment.CENTER),
                    style=ft.ButtonStyle(bgcolor="GREY_700", color="WHITE"),
                    on_click=lambda e: [close_dlg(e), self._deploy_script(info)], width=250),
                ft.Text(i18n.get("winget_deploy_script_desc") or "Generate PowerShell script for deployment.", size=12, italic=True),
            ], height=300, width=400, alignment=ft.MainAxisAlignment.CENTER),
            actions=[ft.TextButton("Cancel", on_click=close_dlg)],
        )
        self.app_page.dialog = dlg
        dlg.open = True
        self.app_page.update()

    def _deploy_wau(self, info):
        self._launch_url("https://github.com/Romanitho/Winget-AutoUpdate")
        self._show_snack("WAU info opened in browser.")


    def _deploy_package(self, info):
        import tempfile
        import shutil
        import subprocess

        pkg_id = info.get('Id')
        self._show_snack(f"Downloading {pkg_id} for packaging...", "BLUE")

        def _bg():
            try:
                tmp_dir = tempfile.mkdtemp()
                # Run winget download
                # Note: 'winget download' requires a newer winget version, but user has it if using SwitchCraft
                cmd = ['winget', 'download', '--id', pkg_id, '--dir', tmp_dir, '--accept-source-agreements', '--accept-package-agreements', '--silent']

                # Hide CMD window on Windows
                import sys
                kwargs = {}
                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    kwargs['startupinfo'] = startupinfo

                subprocess.run(cmd, check=True, **kwargs)

                # Find file
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

                    self._show_snack(f"Downloaded to {dest}", "GREEN")
                    # TODO: Maybe auto-switch to Analyzer?
                else:
                    self._show_snack("Download success but no installer found?", "ORANGE")

                shutil.rmtree(tmp_dir)

            except Exception as ex:
                self._show_snack(f"Download failed: {ex}", "RED")

        threading.Thread(target=_bg, daemon=True).start()

    def _deploy_script(self, info):
        self._create_script_click(None) # Re-use existing simple script or enhance it?
        # Enhancing existing method to be more advanced is better.

    def _install_local(self, e):
        """
        Initiates a local installation of the currently selected package using winget, prompting to restart the app with elevated (administrator) privileges if required.

        If no package is selected, the function does nothing. If the current process is not running with administrator rights, a confirmation dialog is shown offering to restart the application elevated; accepting will attempt to relaunch the application as administrator and exit the current process. If running as administrator, the function builds a winget install command for the selected package and launches it in a new command prompt window. User-facing status is reported via snack messages for start, success, and failure conditions.
        """
        import sys
        if not self.current_pkg:
            return

        # Check against Web/Linux
        # self.app_page might be the Flet page
        if getattr(self.app_page, 'web', False) or sys.platform != 'win32':
             self._show_snack("Install Locally is only supported on Windows Desktop App.", "ORANGE")
             return

        # Admin check
        is_admin = False
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            pass

        if not is_admin:
            def on_restart_confirm(e):
                """
                Request elevation and restart the current application process with Administrator privileges.

                Attempts to close UI dialog, flush logging, perform a brief cleanup and garbage collection, then relaunch the current Python executable with the same command-line arguments using a Windows elevation (runas) request. If the elevated process is started, the current process exits. On failure, a red snack is shown with the error message.

                Parameters:
                    e: The event object from the confirmation button click that triggered the restart.
                """
                restart_dlg.open = False
                self.app_page.update()
                try:
                    import sys
                    import time
                    import gc
                    import logging

                    # 1. Close all file handles and release resources
                    try:
                        logging.shutdown()
                    except Exception:
                        pass

                    # 2. Force garbage collection
                    gc.collect()

                    # 3. Small delay to allow file handles to be released
                    time.sleep(0.2)

                    executable = sys.executable
                    params = f'"{sys.argv[0]}"'
                    if len(sys.argv) > 1:
                        params += " " + " ".join(f'"{a}"' for a in sys.argv[1:])

                    # 4. Launch as admin
                    if sys.platform == 'win32':
                        ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 1)
                    else:
                        raise NotImplementedError("Elevation not supported on this platform")

                    # 5. Give the new process a moment to start
                    time.sleep(0.3)

                    # 6. Exit
                    sys.exit(0)
                except Exception as ex:
                    self._show_snack(f"Failed to elevate: {ex}", "RED")

            restart_dlg = ft.AlertDialog(
                title=ft.Text(i18n.get("admin_required_title") or "Admin Rights Required"),
                content=ft.Text(i18n.get("admin_required_msg") or "Local testing requires administrative privileges. Would you like to restart SwitchCraft as Administrator?"),
                actions=[
                    ft.TextButton(i18n.get("btn_cancel") or "Cancel", on_click=lambda _: setattr(restart_dlg, "open", False) or self.app_page.update()),
                    ft.FilledButton(content=ft.Text(i18n.get("btn_restart_admin") or "Restart as Admin"), bgcolor="RED_700", color="WHITE", on_click=on_restart_confirm),
                ],
            )
            self.app_page.open(restart_dlg)
            return

        pkg_id = self.current_pkg.get('Id')
        cmd = f"winget install --id {pkg_id} --silent --accept-package-agreements --accept-source-agreements"

        def _run():
            import subprocess
            import sys
            self._show_snack(f"Starting install for {pkg_id}...", "BLUE")
            try:
                # Use list format instead of shell=True to avoid CMD window
                cmd_list = ['winget', 'install', '--id', pkg_id, '--silent', '--accept-package-agreements', '--accept-source-agreements']

                # Hide CMD window on Windows
                kwargs = {}
                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    kwargs['startupinfo'] = startupinfo

                # Run in background without showing window
                subprocess.Popen(cmd_list, **kwargs)
            except Exception as ex:
                self._show_snack(f"Failed to start install: {ex}", "RED")

        _run()

    def _create_script_click(self, e):
        if not self.current_pkg:
            return
        default_name = f"Install-{self.current_pkg.get('Name', 'App')}.ps1"
        default_name = "".join(x for x in default_name if x.isalnum() or x in "-_.")

        path = FilePickerHelper.save_file(dialog_title="Save Winget Script", file_name=default_name, allowed_extensions=["ps1"])
        if path:
            script_content = f"""<#
.NOTES
Generated by SwitchCraft via Winget Integration
App: {self.current_pkg.get('Name')}
ID: {self.current_pkg.get('Id')}
#>
$PackageId = "{self.current_pkg.get('Id')}"
$LogPath = "$env:ProgramData\\Microsoft\\IntuneManagementExtension\\Logs\\Winget-$PackageId.log"

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
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(script_content)
                self._show_snack(f"Script saved to {path}", "GREEN")
            except Exception as ex:
                self._show_snack(f"Save failed: {ex}", "RED")
