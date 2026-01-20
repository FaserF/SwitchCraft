import flet as ft
import logging
import asyncio
import inspect
import traceback

logger = logging.getLogger(__name__)

class ViewMixin:
    """Mixin for common view functionality."""

    def _show_error_view(self, error: Exception, context: str = None):
        """
        Show a CrashDumpView for runtime errors in event handlers.

        This method should be called when an unhandled exception occurs
        during event handling (e.g., in on_click, on_submit callbacks).

        Parameters:
            error: The Exception that occurred
            context: Optional context string describing where the error occurred
        """
        try:
            import traceback as tb
            from switchcraft.gui_modern.views.crash_view import CrashDumpView

            page = getattr(self, "app_page", None)
            if not page:
                try:
                    page = self.page
                except (RuntimeError, AttributeError):
                    logger.error(f"Cannot show error view: page not available")
                    return

            if not page:
                logger.error(f"Cannot show error view: page is None")
                return

            # Get traceback
            tb_str = tb.format_exc()
            if context:
                tb_str = f"Context: {context}\n\n{tb_str}"

            # Log the error
            error_msg = f"Runtime error in {context or 'event handler'}: {error}"
            logger.error(error_msg, exc_info=True)

            # Create crash view
            crash_view = CrashDumpView(page, error=error, traceback_str=tb_str)

            # Try to replace current view content with crash view
            # This works if the view is a Column/Row/Container
            try:
                if hasattr(self, 'controls') and isinstance(self.controls, list):
                    # Clear existing controls and add crash view
                    self.controls.clear()
                    self.controls.append(crash_view)
                    self.update()
                elif hasattr(self, 'content'):
                    # Replace content
                    self.content = crash_view
                    self.update()
                else:
                    # Fallback: try to add to page directly
                    page.clean()
                    page.add(crash_view)
                    page.update()
            except Exception as e:
                logger.error(f"Failed to show error view in UI: {e}", exc_info=True)
                # Last resort: try to add directly to page
                try:
                    page.clean()
                    page.add(crash_view)
                    page.update()
                except Exception as e2:
                    logger.error(f"Failed to add error view to page: {e2}", exc_info=True)
        except Exception as e:
            logger.error(f"Critical error in _show_error_view: {e}", exc_info=True)

    def _safe_event_handler(self, handler, context: str = None):
        """
        Wrap an event handler to catch and display exceptions in CrashDumpView.

        Usage:
            button = ft.Button("Click", on_click=self._safe_event_handler(self._my_handler, "button click"))

        Parameters:
            handler: The event handler function to wrap
            context: Optional context string for error messages

        Returns:
            A wrapped function that catches exceptions and shows them in CrashDumpView
        """
        def wrapped_handler(e):
            try:
                return handler(e)
            except Exception as ex:
                handler_name = getattr(handler, '__name__', 'unknown')
                error_context = context or f"event handler '{handler_name}'"
                self._show_error_view(ex, error_context)
        return wrapped_handler

    def _show_snack(self, msg, color="GREEN"):
        """Show a snackbar message on the page using modern API."""
        try:
            page = getattr(self, "app_page", None)
            if not page:
                try:
                    page = self.page
                except (RuntimeError, AttributeError):
                    logger.warning(f"Failed to show snackbar: page not available (RuntimeError/AttributeError)")
                    return
            if not page:
                logger.warning(f"Failed to show snackbar: page is None")
                return

            page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
            # Use newer API for showing snackbar
            page.open(page.snack_bar)
        except Exception as e:
            logger.warning(f"Failed to show snackbar: {e}", exc_info=True)

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
    def _run_task_safe(self, func):
        """
        Safely run a function via page.run_task, wrapping sync functions in async wrappers.

        This helper ensures that both sync and async functions can be passed to run_task
        without causing TypeError: handler must be a coroutine function.

        If run_task is unavailable (e.g., in tests or older Flet builds), falls back
        to a direct call to preserve behavior.

        Parameters:
            func: A callable (sync or async function)

        Returns:
            bool: True if task was executed (scheduled or called directly), False otherwise
        """
        import inspect

        try:
            page = getattr(self, "app_page", None)
            if not page:
                try:
                    page = self.page
                except (RuntimeError, AttributeError):
                    # No page available, try direct call as fallback
                    try:
                        func()
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to execute function directly (no page): {e}", exc_info=True)
                        return False
            if not page:
                # No page available, try direct call as fallback
                try:
                    func()
                    return True
                except Exception as e:
                    logger.warning(f"Failed to execute function directly (page None): {e}", exc_info=True)
                    return False

            # Check if run_task is available
            if hasattr(page, 'run_task'):
                # Check if function is already async
                if inspect.iscoroutinefunction(func):
                    try:
                        page.run_task(func)
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to run async task: {e}", exc_info=True)
                        # Fallback: try direct call
                        try:
                            func()
                            return True
                        except Exception as e2:
                            logger.error(f"Failed to execute async function directly: {e2}", exc_info=True)
                            return False
                else:
                    # Wrap sync function in async wrapper
                    async def async_wrapper():
                        try:
                            func()
                        except Exception as e:
                            logger.error(f"Error in async wrapper for sync function: {e}", exc_info=True)
                            raise
                    try:
                        page.run_task(async_wrapper)
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to run task (sync wrapped): {e}", exc_info=True)
                        # Fallback: try direct call
                        try:
                            func()
                            return True
                        except Exception as e2:
                            logger.error(f"Failed to execute sync function directly: {e2}", exc_info=True)
                            return False
            else:
                # run_task not available, fall back to direct call
                try:
                    func()
                    return True
                except Exception as e:
                    logger.warning(f"Failed to execute function directly (no run_task): {e}", exc_info=True)
                    return False
        except Exception as ex:
            logger.error(f"Failed to run task safely: {ex}", exc_info=True)
            # Fallback: try direct call
            try:
                func()
                return True
            except Exception as e:
                logger.error(f"Failed to execute function in final fallback: {e}", exc_info=True)
                return False

    def _open_dialog_safe(self, dlg):
        """
        Safely open a dialog, ensuring it's added to the page first.
        This prevents "Control must be added to the page first" errors.

        Parameters:
            dlg: The AlertDialog to open

        Returns:
            bool: True if dialog was opened successfully, False otherwise
        """
        try:
            page = getattr(self, "app_page", None)
            if not page:
                try:
                    page = self.page
                except (RuntimeError, AttributeError):
                    logger.error("Cannot open dialog: page not available (RuntimeError/AttributeError)")
                    return False
            if not page:
                logger.error("Cannot open dialog: page is None")
                return False

            # Ensure dialog is set on page before opening
            if not hasattr(page, 'dialog') or page.dialog is None:
                page.dialog = dlg

            # Use page.open() if available (newer Flet API)
            if hasattr(page, 'open') and callable(getattr(page, 'open')):
                try:
                    page.open(dlg)
                except Exception as e:
                    logger.warning(f"Failed to open dialog via page.open(): {e}, trying fallback", exc_info=True)
                    # Fallback to manual assignment
                    page.dialog = dlg
                    dlg.open = True
            else:
                # Fallback to manual assignment
                page.dialog = dlg
                dlg.open = True

            try:
                page.update()
            except Exception as e:
                logger.warning(f"Failed to update page after opening dialog: {e}", exc_info=True)

            return True
        except Exception as e:
            logger.error(f"Error opening dialog: {e}", exc_info=True)
            return False

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
                except Exception as e:
                    logger.warning(f"Failed to close dialog via page.close(): {e}", exc_info=True)
            elif hasattr(page, "close_dialog"):
                try:
                    page.close_dialog()
                except Exception as e:
                    logger.warning(f"Failed to close dialog via page.close_dialog(): {e}", exc_info=True)

            try:
                page.update()
            except Exception as e:
                logger.warning(f"Failed to update page after closing dialog: {e}", exc_info=True)
        except Exception as e:
            logger.warning(f"Failed to close dialog: {e}", exc_info=True)

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

        # Check if task_func is a coroutine function
        is_coroutine = inspect.iscoroutinefunction(task_func)
        is_fallback_coroutine = inspect.iscoroutinefunction(fallback_func) if fallback_func else False

        # Branch up front: use run_task only for coroutines, avoid exception-driven flow
        if hasattr(page, 'run_task') and is_coroutine:
            # Use run_task for coroutine functions (async)
            try:
                page.run_task(task_func)
                return True
            except Exception as ex:
                logger.exception(f"Error in run_task for coroutine: {ex}")
                # Fallback: handle coroutine functions properly
                try:
                    try:
                        loop = asyncio.get_running_loop()
                        # Store task reference and add exception handling to avoid silent failures
                        task = asyncio.create_task(fallback_func())
                        # Add exception handler to catch and log exceptions from the task
                        def handle_task_exception(task):
                            try:
                                task.result()
                            except Exception as task_ex:
                                logger.exception(f"Exception in async fallback task: {task_ex}")
                                if error_msg:
                                    self._show_snack(error_msg, "RED")
                        task.add_done_callback(handle_task_exception)
                    except RuntimeError:
                        asyncio.run(fallback_func())
                    return True
                except Exception as ex2:
                    logger.exception(f"Error in fallback execution: {ex2}")
                    if error_msg:
                        self._show_snack(error_msg, "RED")
                    return False
        elif not is_coroutine:
            # For sync functions, try task_func first, then fallback on exception
            try:
                task_func()
                return True
            except Exception as ex:
                logger.exception(f"Error in task_func for sync function: {ex}")
                # Fallback to fallback_func as recovery path
                try:
                    fallback_func()
                    return True
                except Exception as ex2:
                    logger.exception(f"Error in fallback execution of sync function: {ex2}")
                    if error_msg:
                        self._show_snack(error_msg, "RED")
                    return False
        else:
            # No run_task available, handle coroutine functions properly
            try:
                if is_fallback_coroutine:
                    # Fallback is async, need to run it
                    try:
                        loop = asyncio.get_running_loop()
                        # Store task reference and add exception handling to avoid silent failures
                        task = asyncio.create_task(fallback_func())
                        # Add exception handler to catch and log exceptions from the task
                        def handle_task_exception(task):
                            try:
                                task.result()
                            except Exception as task_ex:
                                logger.exception(f"Exception in async fallback task: {task_ex}")
                                if error_msg:
                                    self._show_snack(error_msg, "RED")
                        task.add_done_callback(handle_task_exception)
                    except RuntimeError:
                        asyncio.run(fallback_func())
                else:
                    fallback_func()
                return True
            except Exception as ex:
                logger.exception(f"Error in direct execution: {ex}")
                if error_msg:
                    self._show_snack(error_msg, "RED")
                return False