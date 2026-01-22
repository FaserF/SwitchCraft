import flet as ft
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.i18n import i18n
from switchcraft.gui_modern.utils.view_utils import ViewMixin

import logging
from datetime import datetime
from pathlib import Path
import os
import sys
import threading

logger = logging.getLogger(__name__)


class LibraryView(ft.Column, ViewMixin):
    """Library view that displays recent .intunewin packages."""

    def __init__(self, page: ft.Page):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO)
        self.app_page = page
        self.all_files = []

        # Get configured directories to scan
        self.scan_dirs = self._get_scan_directories()

        # State
        self.search_val = ""

        # UI Components
        self.grid = ft.GridView(
            runs_count=5,
            max_extent=250,
            child_aspect_ratio=1.0,
            spacing=10,
            run_spacing=10,
            expand=True,
            padding=10
        )

        self.search_field = ft.TextField(
            hint_text=i18n.get("search_library") or "Search Library...",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            border_radius=8,
            on_change=self._on_search_change
        )

        self.dir_info = ft.Text(
            f"{i18n.get('scanning') or 'Scanning'}: {len(self.scan_dirs)} {i18n.get('directories') or 'directories'}",
            size=12,
            color="GREY_500"
        )

        self.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Column([
                            ft.Text(
                                i18n.get("intunewin_library_title") or "IntuneWin Library",
                                size=28,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Text(
                                i18n.get("intunewin_library_subtitle") or "Recent .intunewin packages",
                                size=16,
                                color="GREY_400"
                            ),
                        ], spacing=5),
                        ft.Container(expand=True),
                        ft.IconButton(
                            ft.Icons.FOLDER_OPEN,
                            tooltip=i18n.get("scan_directories") or "Configure scan directories",
                            on_click=self._safe_event_handler(self._show_dir_config, "Folder config button")
                        ),
                        ft.IconButton(
                            ft.Icons.REFRESH,
                            tooltip=i18n.get("btn_refresh") or "Refresh",
                            on_click=self._safe_event_handler(self._load_data, "Refresh button")
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=20),
                    ft.Row([self.search_field, self.dir_info], spacing=15),
                    ft.Container(height=10),
                    self.grid
                ], expand=True, spacing=10),
                padding=20,
                expand=True
            )
        ]

    def did_mount(self):
        self._load_data(None)

    def _get_scan_directories(self):
        """Get directories to scan for .intunewin files."""
        dirs = []

        # Check configured output folder from settings
        output_folder = SwitchCraftConfig.get_value("IntuneOutputFolder")
        if output_folder and os.path.isdir(output_folder):
            dirs.append(output_folder)

        # Common default locations
        user_home = Path.home()
        default_dirs = [
            user_home / "Downloads",
            user_home / "Documents",
            user_home / "Desktop",
        ]


        if sys.platform == "win32":
            default_dirs.extend([
                Path("C:/Temp"),
                Path("C:/IntuneWin"),
            ])

        for d in default_dirs:
            if d.exists() and d.is_dir():
                dirs.append(str(d))

        # Remove duplicates
        seen = set()
        unique_dirs = []
        is_windows = sys.platform == "win32"
        for d in dirs:
            d_normalized = os.path.normpath(d)
            key = d_normalized.lower() if is_windows else d_normalized
            if key not in seen:
                seen.add(key)
                unique_dirs.append(d)

        return unique_dirs[:5]  # Limit to 5 directories to avoid slow scanning

    def _load_data(self, e):
        """Load .intunewin files from scan directories."""
        logger.info("_load_data called - starting scan")
        try:
            # Update dir_info to show loading state - use _run_task_safe to avoid RuntimeError
            def update_loading():
                try:
                    self.dir_info.value = f"{i18n.get('scanning') or 'Scanning'}..."
                    self.dir_info.update()
                except (RuntimeError, AttributeError):
                    logger.debug("dir_info not attached to page yet, skipping update")
            self._run_task_safe(update_loading)

            # Run scanning in background thread to avoid blocking UI
            def scan_files():
                try:
                    logger.info("Scanning directories for .intunewin files...")
                    all_files = []

                    for scan_dir in self.scan_dirs:
                        try:
                            path = Path(scan_dir)
                            if not path.exists():
                                logger.debug(f"Scan directory does not exist: {scan_dir}")
                                continue

                            # Non-recursive scan of the directory
                            for file in path.glob("*.intunewin"):
                                if file.is_file():
                                    stat = file.stat()
                                    all_files.append({
                                        'path': str(file),
                                        'filename': file.name,
                                        'size': stat.st_size,
                                        'modified': datetime.fromtimestamp(stat.st_mtime),
                                        'directory': scan_dir
                                    })

                            # Also check one level down (common structure), limit to first 20 subdirs
                            try:
                                subdirs = [x for x in path.iterdir() if x.is_dir()]
                                for subdir in subdirs[:20]: # Limit subdirectory scan
                                    for file in subdir.glob("*.intunewin"):
                                        if file.is_file():
                                            stat = file.stat()
                                            all_files.append({
                                                'path': str(file),
                                                'filename': file.name,
                                                'size': stat.st_size,
                                                'modified': datetime.fromtimestamp(stat.st_mtime),
                                                'directory': str(subdir)
                                            })
                            except Exception as ex:
                                logger.debug(f"Error scanning subdirectories in {scan_dir}: {ex}")
                        except Exception as ex:
                            if isinstance(ex, PermissionError):
                                logger.debug(f"Permission denied scanning {scan_dir}")
                            else:
                                logger.warning(f"Failed to scan {scan_dir}: {ex}", exc_info=True)

                    # Sort by modification time (newest first)
                    all_files.sort(key=lambda x: x['modified'], reverse=True)

                    # Limit to 50 most recent files
                    all_files = all_files[:50]
                    logger.info(f"Found {len(all_files)} .intunewin files")

                    # Update UI on main thread
                    def update_ui():
                        try:
                            self.all_files = all_files
                            self.dir_info.value = f"{i18n.get('scanning') or 'Scanning'}: {len(self.scan_dirs)} {i18n.get('directories') or 'directories'} - {len(self.all_files)} {i18n.get('files_found') or 'files found'}"
                            self.dir_info.update()
                            self._refresh_grid()
                        except (RuntimeError, AttributeError) as e:
                            logger.debug(f"UI not ready for update: {e}")
                            # Try to refresh grid anyway
                            try:
                                self.all_files = all_files
                                self._refresh_grid()
                            except Exception:
                                pass
                    self._run_task_safe(update_ui)
                except Exception as ex:
                    logger.error(f"Error scanning library data: {ex}", exc_info=True)
                    def show_error():
                        try:
                            msg = f"Failed to load library: {ex}"
                            self._show_snack(msg, "RED")
                            self.dir_info.value = f"{i18n.get('error') or 'Error'}: {str(ex)[:50]}"
                            self.dir_info.update()
                        except (RuntimeError, AttributeError) as ex:
                            pass
                        logger.debug("Cannot update error UI: control not attached")
                    self._run_task_safe(show_error)

            # Start scanning in background thread
            threading.Thread(target=scan_files, daemon=True).start()
        except Exception as ex:
            logger.error(f"Error starting library scan: {ex}", exc_info=True)
            self._show_snack(f"Failed to start library scan: {ex}", "RED")

    def _on_search_change(self, e):
        self.search_val = e.control.value.lower()
        self._refresh_grid()

    def _refresh_grid(self):
        """Refresh the grid with current files and search filter."""
        try:
            self.grid.controls.clear()

            if not self.all_files:
                self.grid.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=60, color="GREY_500"),
                            ft.Text(
                                i18n.get("no_intunewin_files") or "No .intunewin files found",
                                size=16,
                                color="GREY_500"
                            ),
                            ft.Text(
                                i18n.get("scan_directories_hint") or "Check scan directories or create packages first",
                                size=12,
                                color="GREY_600"
                            )
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.Alignment(0, 0),
                        expand=True
                    )
                )
                try:
                    self.grid.update()
                    self.update()
                except (RuntimeError, AttributeError):
                    logger.debug("Grid not attached to page yet, skipping update")
                return

            # Filter files based on search
            filtered_files = []
            for item in self.all_files:
                name = item.get('filename', '').lower()
                if not self.search_val or self.search_val in name:
                    filtered_files.append(item)

            # Add tiles for filtered files or show "no results" message
            if not filtered_files:
                # Show empty state when search yields no results
                no_results = ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.SEARCH_OFF, size=48, color="GREY_500"),
                        ft.Text(i18n.get("no_results_found") or "No results found", size=16, color="GREY_500")
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    alignment=ft.alignment.center,
                    padding=40
                )
                self.grid.controls.append(no_results)
            else:
                for item in filtered_files:
                    self.grid.controls.append(self._create_tile(item))

            try:
                self.grid.update()
                self.update()
            except (RuntimeError, AttributeError) as e:
                logger.debug(f"Grid not attached to page yet: {e}")
        except Exception as ex:
            logger.error(f"Error refreshing grid: {ex}", exc_info=True)
            def show_error(err=ex):
                try:
                    self._show_snack(f"Failed to refresh grid: {err}", "RED")
                except (RuntimeError, AttributeError):
                    pass
            self._run_task_safe(show_error)

    def _create_tile(self, item):
        filename = item.get('filename', 'Unknown')
        size_bytes = item.get('size', 0)
        modified = item.get('modified', datetime.now())
        directory = item.get('directory', '')

        # Format size
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

        # Format date
        date_str = modified.strftime("%Y-%m-%d %H:%M")

        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.INVENTORY_2, size=40, color="BLUE_400"),
                ft.Text(
                    filename.replace('.intunewin', ''),
                    weight=ft.FontWeight.BOLD,
                    no_wrap=True,
                    tooltip=filename,
                    max_lines=2
                ),
                ft.Text(size_str, size=12, color="GREY_400"),
                ft.Container(expand=True),
                ft.Row([
                    ft.Text(date_str, size=10, color="GREY_500"),
                    ft.IconButton(
                        ft.Icons.FOLDER_OPEN,
                        icon_size=16,
                        tooltip=i18n.get("open_folder") or "Open Folder",
                        on_click=lambda e, p=item.get('path'): self._open_folder(p)
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], spacing=5),
            bgcolor="WHITE10",
            border=ft.Border.all(1, "WHITE10"),
            border_radius=10,
            padding=15,
            on_hover=lambda e: self._on_tile_hover(e),
            on_click=lambda e, item=item: self._on_tile_click(item)
        )

    def _on_tile_hover(self, e):
        e.control.bgcolor = "WHITE20" if e.data == "true" else "WHITE10"
        e.control.update()

    def _on_tile_click(self, item):
        # Show details in a dialog
        path = item.get('path', '')
        dlg = ft.AlertDialog(
            title=ft.Text(item.get('filename', 'Unknown')),
            content=ft.Column([
                ft.Text(f"📁 {i18n.get('location') or 'Location'}: {item.get('directory', '')}"),
                ft.Text(f"📏 {i18n.get('size') or 'Size'}: {item.get('size', 0) / (1024*1024):.2f} MB"),
                ft.Text(f"📅 {i18n.get('modified') or 'Modified'}: {item.get('modified', datetime.now()).strftime('%Y-%m-%d %H:%M')}"),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton(i18n.get("btn_cancel") or "Close", on_click=lambda e: self._close_dialog(dlg)),
                ft.FilledButton(
                    content=ft.Row([ft.Icon(ft.Icons.FOLDER_OPEN), ft.Text(i18n.get("open_folder") or "Open Folder")], alignment=ft.MainAxisAlignment.CENTER),
                    on_click=lambda e: (self._close_dialog(dlg), self._open_folder(path))
                )
            ]
        )

        if not self._open_dialog_safe(dlg):
            self._show_snack("Failed to open file details dialog", "RED")

    def _open_folder(self, path):
        """Open the folder containing the file."""
        try:
            folder = os.path.dirname(path)
            self._open_path(folder)
        except Exception as ex:
            logger.error(f"Failed to open folder: {ex}")

    def _show_dir_config(self, e):
        """Show dialog to configure scan directories."""
        try:
            # Refresh scan directories in case settings changed
            self.scan_dirs = self._get_scan_directories()

            dirs_text = "\n".join(self.scan_dirs) if self.scan_dirs else "(No directories configured)"

            dlg = ft.AlertDialog(
                title=ft.Text(i18n.get("scan_directories") or "Scan Directories"),
                content=ft.Column([
                    ft.Text(
                        i18n.get("scan_dirs_desc") or "The following directories are scanned for .intunewin files:",
                        size=14
                    ),
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Text(dirs_text, selectable=True, size=12),
                        bgcolor="BLACK12",
                        border_radius=8,
                        padding=10,
                        width=400
                    ),
                    ft.Container(height=10),
                    ft.Text(
                        i18n.get("scan_dirs_hint") or "Configure the default output folder in Settings > Directories",
                        size=12,
                        color="GREY_500",
                        italic=True
                    )
                ], tight=True, scroll=ft.ScrollMode.AUTO),
                actions=[
                    ft.TextButton(i18n.get("btn_cancel") or "Close", on_click=lambda e: self._close_dialog(dlg))
                ]
            )

            if not self._open_dialog_safe(dlg):
                self._show_snack("Failed to open directory configuration dialog", "RED")
        except Exception as ex:
            logger.error(f"Error showing directory config: {ex}", exc_info=True)
            self._show_snack(f"Failed to show directory config: {ex}", "RED")
