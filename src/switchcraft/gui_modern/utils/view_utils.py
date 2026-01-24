import flet as ft
from switchcraft import IS_WEB
import logging
import asyncio
import inspect

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
            import traceback
            from switchcraft.gui_modern.views.crash_view import CrashDumpView

            page = getattr(self, "app_page", None)
            if not page:
                try:
                    page = self.page
                except (RuntimeError, AttributeError):
                    logger.error("Cannot show error view: page not available")
                    return

            if not page:
                logger.error("Cannot show error view: page is None")
                return

            # Get traceback from the exception object
            try:
                tb_lines = traceback.TracebackException.from_exception(error).format()
                tb_str = ''.join(tb_lines)
            except Exception as tb_ex:
                # Fallback if traceback extraction fails
                tb_str = f"{type(error).__name__}: {error}\n(Unable to extract full traceback: {tb_ex})"

            if context:
                tb_str = f"Context: {context}\n\n{tb_str}"

            # Log the error with exception info
            error_msg = f"Runtime error in {context or 'event handler'}: {error}"
            logger.error(error_msg, exc_info=error)

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
                    logger.warning("Failed to show snackbar: page not available (RuntimeError/AttributeError)")
                    return
            if not page:
                logger.warning("Failed to show snackbar: page is None")
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
    def _launch_url(self, url: str):
        """
        Launches a URL using the best available method for the environment.
        On Desktop, prefers webbrowser.open for better OS integration.
        In Web/WASM, uses page.launch_url.
        """
        if not url:
            return

        logger.info(f"Launching URL: {url}")

        # Determine environment
        page = getattr(self, "app_page", None)
        if not page:
            try:
                page = self.page
            except (RuntimeError, AttributeError):
                pass

        is_web = getattr(page, "web", False) if page else False

        # On Desktop, webbrowser.open is usually more reliable than page.launch_url
        if not is_web:
            try:
                import webbrowser
                logger.info(f"Desktop mode: Using webbrowser.open for: {url}")
                if webbrowser.open(url):
                    return
                logger.warning("webbrowser.open returned False, trying page.launch_url fallback")
            except Exception as e:
                logger.debug(f"webbrowser.open failed: {e}")

        if page:
            try:
                # Flet's launch_url
                logger.info(f"Using page.launch_url for: {url}")
                page.launch_url(url)
                return
            except Exception as e:
                logger.error(f"page.launch_url failed: {e}")

        # Final fallback for any case where previous attempts failed
        try:
            import webbrowser
            logger.info(f"Final fallback: Using webbrowser.open for: {url}")
            webbrowser.open(url)
        except Exception as e:
            logger.error(f"Failed to launch URL in any mode: {e}")
            self._show_snack(f"Could not open URL: {e}", "RED")

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
                        # Check if func is async and handle accordingly
                        if inspect.iscoroutinefunction(func):
                            try:
                                loop = asyncio.get_running_loop()
                                asyncio.create_task(func())
                            except RuntimeError:
                                # No running loop, use asyncio.run
                                asyncio.run(func())
                        else:
                            func()
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to execute function directly (no page): {e}", exc_info=True)
                        return False
            if not page:
                # No page available, try direct call as fallback
                try:
                    # Check if func is async and handle accordingly
                    if inspect.iscoroutinefunction(func):
                        try:
                            loop = asyncio.get_running_loop()
                            asyncio.create_task(func())
                        except RuntimeError:
                            # No running loop, use asyncio.run
                            asyncio.run(func())
                    else:
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
                        logger.warning(f"Failed to run async task via run_task: {e}", exc_info=True)
                        # Fallback for async function when run_task fails
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(func() if inspect.iscoroutine(func) else func())
                            return True
                        except RuntimeError:
                            asyncio.run(func() if inspect.iscoroutine(func) else func())
                            return True
                else:
                    # For sync functions, wrap in async wrapper
                    try:
                        async def async_wrapper():
                            try:
                                func()
                            except Exception as e:
                                logger.error(f"Error in async wrapper for sync function: {e}", exc_info=True)
                        page.run_task(async_wrapper)
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to run wrapped sync task via run_task: {e}", exc_info=True)
                        # Fallback: call sync directly
                        try:
                            func()
                            return True
                        except Exception as e2:
                            logger.error(f"Sync fallback failed: {e2}")
                            return False
            else:
                # No run_task available, handle async/sync accordingly
                try:
                    if inspect.iscoroutinefunction(func):
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(func())
                        except RuntimeError:
                            asyncio.run(func())
                    else:
                        func()
                    return True
                except Exception as e:
                    logger.warning(f"Fallback execution failed: {e}", exc_info=True)
                    return False
        except Exception as e:
            logger.error(f"Critical failure in _run_task_safe: {e}", exc_info=True)
            return False

    def _run_in_background(self, target, *args, **kwargs):
        """
        Run a function in the background, handling web/desktop differences.
        On Desktop: Starts a new daemon thread.
        On Web: Uses page.run_task (which is async safe in WASM).

        Parameters:
            target: The function to run
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
        """
        import threading

        page = getattr(self, "app_page", None) or getattr(self, "page", None)

        if IS_WEB and page and hasattr(page, "run_task"):
            logger.debug(f"Web mode: Running '{target.__name__}' as async task")
            async def async_wrapper():
                try:
                    # If target is async, await it, else call it
                    if inspect.iscoroutinefunction(target):
                        await target(*args, **kwargs)
                    else:
                        target(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in background task: {e}", exc_info=True)

            page.run_task(async_wrapper)
        else:
            if IS_WEB:
                logger.warning("Web mode detected but page.run_task not available. Falling back to sync call.")
                # Fallback to sync call if run_task is missing on web (shouldn't happen)
                target(*args, **kwargs)
            else:
                # Desktop: Use traditional threading
                logger.debug(f"Desktop mode: Starting thread for '{target.__name__}'")
                threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True).start()

    def _open_dialog_safe(self, dlg):
        """
        Open a dialog safely across Flet versions and environments.
        Prioritizes modern 'page.open(dlg)' API, falls back to legacy 'page.dialog = dlg'.
        """
        page = getattr(self, "app_page", None)
        if not page:
            try:
                page = self.page
            except (RuntimeError, AttributeError):
                pass

        if not page:
             logger.warning("Cannot open dialog: Page not found")
             return False

        try:
            # Method 1: Modern API (Preferred)
            if hasattr(page, 'open'):
                try:
                    logger.debug("Attempting to open dialog using page.open()...")
                    page.open(dlg)
                    page.update()
                    logger.info("Dialog opened successfully using page.open()")
                    return True
                except Exception as e:
                    logger.warning(f"page.open(dlg) failed: {e}. Falling back to legacy mode.")

            # Method 2: Legacy API (Fallback)
            logger.debug("Attempting to open dialog using legacy page.dialog...")
            page.dialog = dlg
            if hasattr(dlg, 'open'):
                dlg.open = True
            page.update()
            logger.info("Dialog opened using legacy page.dialog mode")
            return True

        except Exception as e:
            logger.error(f"Failed to open dialog in any mode: {e}", exc_info=True)
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
                try:
                    dialog.update()
                except:
                    pass

            # Use modern API if available
            if hasattr(page, "close") and dialog:
                try:
                    page.close(dialog)
                except Exception as e:
                    logger.warning(f"Failed to close dialog via page.close(): {e}")

            # Legacy logic or fallback
            if hasattr(page, "dialog") and page.dialog == dialog:
                page.dialog = None

            try:
                page.update()
            except Exception as e:
                logger.debug(f"Page update after dialog close failed (ignored): {e}")
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
        # Assign fallback_func before page check so it can be used in fallback path
        if fallback_func is None:
            fallback_func = task_func

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
            logger.warning("No page available for run_task, using fallback")
            # Execute fallback even without page
            try:
                is_fallback_coroutine = inspect.iscoroutinefunction(fallback_func) if fallback_func else False
                if is_fallback_coroutine:
                    try:
                        loop = asyncio.get_running_loop()
                        task = asyncio.create_task(fallback_func())
                        def handle_task_exception(task):
                            try:
                                task.result()
                            except Exception as task_ex:
                                logger.exception(f"Exception in async fallback task (no page): {task_ex}")
                                if error_msg:
                                    self._show_snack(error_msg, "RED")
                        task.add_done_callback(handle_task_exception)
                    except RuntimeError:
                        asyncio.run(fallback_func())
                else:
                    fallback_func()
                return True
            except Exception as ex:
                logger.exception(f"Error in fallback execution (no page): {ex}")
                if error_msg:
                    self._show_snack(error_msg, "RED")
                return False

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
                    # Check if fallback_func is async and handle accordingly
                    if is_fallback_coroutine:
                        try:
                            loop = asyncio.get_running_loop()
                            task = asyncio.create_task(fallback_func())
                            def handle_task_exception(task):
                                try:
                                    task.result()
                                except Exception as task_ex:
                                    logger.exception(f"Exception in async fallback task (sync path): {task_ex}")
                                    if error_msg:
                                        self._show_snack(error_msg, "RED")
                            task.add_done_callback(handle_task_exception)
                        except RuntimeError:
                            asyncio.run(fallback_func())
                    else:
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