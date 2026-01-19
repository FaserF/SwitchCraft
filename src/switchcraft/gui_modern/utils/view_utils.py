import flet as ft
import logging

logger = logging.getLogger(__name__)

class ViewMixin:
    """Mixin for common view functionality."""

    def _show_snack(self, msg, color="GREEN"):
        """Show a snackbar message on the page using modern API."""
        try:
            page = getattr(self, "app_page", None)
            if not page:
                try:
                    page = self.page
                except (RuntimeError, AttributeError):
                    return
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
            page = getattr(self, "app_page", None)
            if not page:
                try:
                    page = self.page
                except (RuntimeError, AttributeError):
                    return
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

    def _run_task_with_fallback(self, task_func, fallback_func=None, error_msg=None):
        """
        Execute a task function on the main thread using run_task, with fallback handling.

        This helper consolidates the common pattern of:
        1. Try run_task if available
        2. Fallback to direct call if run_task fails or is unavailable
        3. Provide error handling and user feedback

        Parameters:
            task_func (callable): Function to execute on main thread (no arguments)
            fallback_func (callable, optional): Function to call if run_task fails.
                                                If None, task_func is called directly.
            error_msg (str, optional): Error message to show if all attempts fail.

        Returns:
            bool: True if task was executed successfully, False otherwise
        """
        # Try app_page first (commonly used in views)
        page = getattr(self, "app_page", None)
        # If not available, try page property (but catch RuntimeError if control not added to page)
        if not page:
            try:
                # Direct access to page property (not getattr) to catch RuntimeError
                page = self.page
            except (RuntimeError, AttributeError):
                # Control not added to page yet (common in tests)
                page = None
        if not page:
            logger.warning("No page available for run_task")
            return False

        if fallback_func is None:
            fallback_func = task_func

        if hasattr(page, 'run_task'):
            try:
                page.run_task(task_func)
                return True
            except Exception as ex:
                logger.exception(f"Error in run_task: {ex}")
                # Fallback: try direct call
                try:
                    fallback_func()
                    return True
                except Exception as ex2:
                    logger.exception(f"Error in fallback execution: {ex2}")
                    if error_msg:
                        self._show_snack(error_msg, "RED")
                    return False
        else:
            # No run_task, try direct call
            try:
                fallback_func()
                return True
            except Exception as ex:
                logger.exception(f"Error in direct execution: {ex}")
                if error_msg:
                    self._show_snack(error_msg, "RED")
                return False