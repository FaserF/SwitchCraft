import flet as ft
import logging

logger = logging.getLogger(__name__)

class ViewMixin:
    """Mixin for common view functionality."""

    def _show_snack(self, msg, color="GREEN"):
        """Show a snackbar message on the page using modern API."""
        try:
            page = getattr(self, "app_page", getattr(self, "page", None))
            if not page:
                return

            page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
            # Use newer API for showing snackbar
            page.open(page.snack_bar)
        except Exception as e:
            logger.debug(f"Failed to show snackbar: {e}")

    def _open_path(self, path):
        """Cross-platform path opener (Folder or File)."""
        import os
        import platform
        import subprocess
        import webbrowser

        try:
            if not os.path.exists(path):
                self._show_snack(f"Path does not exist: {path}", "RED")
                return

            system = platform.system()
            if system == "Windows":
                os.startfile(path)
            elif system == "Darwin": # macOS
                subprocess.run(["open", path], check=True)
            else: # Linux
                subprocess.run(["xdg-open", path], check=True)
        except Exception as e:
            logger.debug(f"Default opener failed, falling back to webbrowser: {e}")
            try:
                from pathlib import Path
                uri = Path(path).as_uri()
                webbrowser.open(uri)
            except Exception as e2:
                self._show_snack(f"Failed to open path: {path}", "RED")
                logger.error(f"Failed to open path: {e2}")
    def _close_dialog(self, dialog=None):
        """Close a dialog on the page."""
        try:
            page = getattr(self, "app_page", getattr(self, "page", None))
            if not page:
                return

            if dialog:
                dialog.open = False
                dialog.update()

            # Fallback for older Flet or to ensure it's removed from overlay
            if hasattr(page, "close"):
                try:
                    page.close(dialog)
                except Exception:
                    pass
            elif hasattr(page, "close_dialog"):
                try:
                    page.close_dialog()
                except Exception:
                    pass

            page.update()
        except Exception as e:
            logger.debug(f"Failed to close dialog: {e}")
