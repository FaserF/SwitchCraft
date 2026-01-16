import flet as ft
import traceback

class CrashDumpView(ft.Container):
    def __init__(self, page: ft.Page, error: Exception, traceback_str: str = None):
        """
        Initialize a crash view container that displays an error message, selectable traceback, and action buttons for copying, closing, or reloading the application.
        
        Displays a prominent error icon and title, a short explanatory subtext, a styled expandable error block containing the error message and the traceback (both selectable), and action buttons: "Copy Error" (copies traceback to clipboard), "Close App" (force-exits the process), and "Reload App" (attempts to restart the application). If `traceback_str` is not provided, the current traceback is captured automatically.
        
        Parameters:
            page: The flet Page used for UI updates, clipboard access, and reload/close actions.
            error: The Exception instance whose message will be shown in the error block.
            traceback_str: Optional preformatted traceback text to display; when omitted, the current traceback is obtained via traceback.format_exc().
        """
        super().__init__(expand=True)
        self.app_page = page
        self.bgcolor = "#1a1a1a" # Dark background like BSOD but modern
        self.padding = 30

        if not traceback_str:
            traceback_str = traceback.format_exc()

        self._traceback_str = traceback_str
        self.content = ft.Column(
            controls=[
                ft.Icon(ft.Icons.ERROR_OUTLINE, color="RED_400", size=64),
                ft.Text("Something went wrong", size=32, weight=ft.FontWeight.BOLD, color="WHITE"),
                ft.Text("An unexpected error occurred while loading this view.", size=16, color="GREY_400"),
                ft.Container(height=20),
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"Error: {str(error)}", color="RED_200", weight=ft.FontWeight.BOLD, selectable=True),
                        ft.Divider(color="GREY_700"),
                        ft.Text(traceback_str, font_family="Consolas", size=12, color="WHITE", selectable=True)
                    ], scroll=ft.ScrollMode.AUTO),
                    bgcolor="#2d2d2d",
                    padding=15,
                    border_radius=8,
                    expand=True
                ),
                ft.Container(height=20),
                ft.Row([
                    ft.FilledButton("Copy Error", icon=ft.Icons.COPY, on_click=self._copy_error),
                    ft.FilledButton("Close App", icon=ft.Icons.CLOSE, on_click=self._close_app, style=ft.ButtonStyle(bgcolor="RED_900", color="WHITE")),
                    ft.FilledButton("Reload App", icon=ft.Icons.REFRESH, on_click=lambda e: self._reload_app(page)),
                ], alignment=ft.MainAxisAlignment.END)
            ],
            expand=True
        )

    def _copy_error(self, e):
        error_text = self._traceback_str if hasattr(self, '_traceback_str') else "No traceback available."

        success = False
        # Try Pyperclip first (more reliable for desktop clipboard)
        try:
            import pyperclip
            pyperclip.copy(error_text)
            success = True
        except Exception:
            # Try Flet Native
            try:
                self.app_page.set_clipboard(error_text)
                success = True
            except Exception:
                # Log via logger if possible, but minimal deps here
                pass

        if success:
             try:
                 self.app_page.snack_bar = ft.SnackBar(ft.Text("Error details copied to clipboard"))
                 self.app_page.snack_bar.open = True
                 self.app_page.update()
             except Exception:
                 pass
        else:
             try:
                 self.app_page.snack_bar = ft.SnackBar(ft.Text("Failed to copy to clipboard"), bgcolor="RED")
                 self.app_page.snack_bar.open = True
                 self.app_page.update()
             except Exception:
                 pass

    def _close_app(self, e):
        """
        Initiates an immediate, forceful shutdown of the running process.
        
        If the provided event object has a triggering control, that control will be disabled
        and its label updated to indicate the app is closing. A background thread is then
        started to terminate the process after a short delay so the UI update can be shown.
        @param e: Event object from the triggering UI action; may contain a `control` attribute whose `disabled` and `text` properties will be modified if present.
        """
        import sys
        import ctypes
        import threading

        # Disable button to prevent multiple clicks
        if hasattr(e, 'control'):
            e.control.disabled = True
            e.control.text = "Closing..."
            try:
                self.app_page.update()
            except Exception:
                pass

        # Use a thread to force exit after a short delay to allow UI update
        def force_exit():
            """
            Forcefully terminate the running process after a short delay to allow UI updates.
            
            Sleeps for 0.1 seconds to give the UI a moment to update, then performs an immediate, non-interruptible exit: on Windows it attempts to call the Win32 ExitProcess(0) API and falls back to os._exit(0) if that fails; on other platforms it calls os._exit(0).
            """
            import time
            time.sleep(0.1)  # Small delay to allow UI to update
            # Nuclear option: Win32 ExitProcess - cannot be blocked
            if sys.platform == "win32":
                try:
                    ctypes.windll.kernel32.ExitProcess(0)
                except Exception:
                    # Fallback to os._exit
                    import os
                    os._exit(0)
            else:
                import os
                os._exit(0)

        # Run in background thread to avoid blocking
        threading.Thread(target=force_exit, daemon=False).start()

    def _reload_app(self, page):
        """
        Restart the application by launching a new process with a sanitized environment and then exiting the current process.
        
        This method updates the provided page to show a "Reloading..." message, performs cleanup (logging shutdown and garbage collection), removes PyInstaller-related environment entries, starts a detached new process using the current Python executable and appropriate arguments, waits briefly for startup, and then terminates the current process. If automatic restart fails, a snack bar with an error message is shown on the provided page.
        
        Parameters:
            page (ft.Page): The current Flet page used to display the "Reloading..." message and any error snack bar.
        """
        import sys
        import os
        import subprocess
        import time
        import gc
        import logging

        page.clean()
        page.add(ft.Text("Reloading...", size=20))
        page.update()

        # Robust Restart Logic with proper cleanup
        try:
            if getattr(sys, 'frozen', False):
                # Running as PyInstaller Bundle
                executable = sys.executable
                args = sys.argv[1:]
            else:
                # Running as Script
                executable = sys.executable
                args = sys.argv

            # 1. Close all file handles and release resources
            try:
                logging.shutdown()
            except Exception:
                pass

            # 2. Force garbage collection to close any remaining file handles
            gc.collect()

            # 3. Small delay to allow file handles to be released
            time.sleep(0.2)

            # 4. Prepare environment: remove PyInstaller's _MEIPASS
            env = os.environ.copy()
            for key in list(env.keys()):
                if key.startswith('_MEI'):
                    env.pop(key)
            env.pop('LD_LIBRARY_PATH', None)  # Linux related but good practice

            # 5. Launch new instance
            # Use DETACHED_PROCESS flag on Windows (0x00000008) to separate from current console/process group
            # Also close_fds=True to prevent handle inheritance (fixes _MEI cleanup issues)
            creationflags = 0
            if sys.platform == 'win32':
                creationflags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

            # Force CWD to the executable's directory to avoid locking the temp _MEI folder
            cwd = os.path.dirname(executable) if getattr(sys, 'frozen', False) else os.getcwd()

            # Launch new process BEFORE quitting current one
            subprocess.Popen(
                [executable] + args,
                close_fds=True,
                creationflags=creationflags,
                cwd=cwd,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # 6. Give the new process a moment to start
            time.sleep(0.3)

            # 7. Kill current instance
            sys.exit(0)
        except Exception as e:
            text = f"Failed to reload automatically: {e}\nPlease restart manually."
            try:
                page.show_snack_bar(ft.SnackBar(ft.Text(text)))
                page.update()
            except Exception:
                pass