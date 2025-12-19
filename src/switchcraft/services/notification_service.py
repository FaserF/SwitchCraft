
import logging
import threading
import sys
import ctypes

logger = logging.getLogger(__name__)

# Try winotify first for better Windows toast support
_WINOTIFY_AVAILABLE = False
try:
    from winotify import Notification, audio
    _WINOTIFY_AVAILABLE = True
except ImportError:
    pass

# Fallback to plyer
_PLYER_AVAILABLE = False
try:
    from plyer import notification
    _PLYER_AVAILABLE = True
except (ImportError, NotImplementedError):
    pass

if not _WINOTIFY_AVAILABLE and not _PLYER_AVAILABLE:
    logger.warning("No notification provider found (winotify or plyer). Notifications may be limited.")


class NotificationService:
    """
    Service to handle system notifications.
    Uses winotify for Windows 10/11 toast notifications with click support.
    Falls back to plyer or PowerShell when winotify is unavailable.
    """

    APP_NAME = "SwitchCraft"
    APP_ICON = None  # Path to .ico if available, set by app.py
    _app_window = None  # Reference to main app window for focus

    @classmethod
    def set_app_window(cls, window):
        """Set reference to main app window for focus on notification click."""
        cls._app_window = window

    @staticmethod
    def _is_app_foreground() -> bool:
        """Check if the app window is currently in the foreground."""
        if sys.platform != "win32":
            return True  # Assume foreground on non-Windows

        try:
            # Get current foreground window
            foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()
            # Get our process ID
            current_pid = ctypes.windll.kernel32.GetCurrentProcessId()
            # Get PID of foreground window
            foreground_pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(foreground_hwnd, ctypes.byref(foreground_pid))
            return foreground_pid.value == current_pid
        except Exception:
            return True  # Assume foreground on error

    @staticmethod
    def _bring_app_to_front():
        """Bring the app window to the foreground."""
        if NotificationService._app_window:
            try:
                # Schedule on main thread
                NotificationService._app_window.after(0, lambda: [
                    NotificationService._app_window.deiconify(),
                    NotificationService._app_window.lift(),
                    NotificationService._app_window.focus_force()
                ])
            except Exception as e:
                logger.warning(f"Failed to bring app to front: {e}")

    @staticmethod
    def send_notification(title: str, message: str, timeout: int = 10):
        """
        Sends a desktop notification.
        If app is in background, uses system notification center.
        If app is in foreground, notification still shows but app stays visible.
        """
        def _notify():
            full_title = f"{NotificationService.APP_NAME}: {title}"
            # is_foreground = NotificationService._is_app_foreground()

            # Always send system notification (it will appear in action center)
            if sys.platform == "win32" and _WINOTIFY_AVAILABLE:
                try:
                    toast = Notification(
                        app_id=NotificationService.APP_NAME,
                        title=full_title,
                        msg=message,
                        duration="short"
                    )

                    # Add click action to bring app to front
                    toast.add_actions(label="Open App", launch="")

                    # Set audio
                    toast.set_audio(audio.Default, loop=False)

                    toast.show()

                    # If not in foreground, the notification will appear
                    # When clicked, Windows will activate the app
                    return
                except Exception as e:
                    logger.warning(f"Winotify failed: {e}. Trying fallback...")

            # Fallback to plyer
            if _PLYER_AVAILABLE:
                try:
                    notification.notify(
                        title=full_title,
                        message=message,
                        app_name=NotificationService.APP_NAME,
                        app_icon=NotificationService.APP_ICON,
                        timeout=timeout
                    )
                    return
                except Exception as e:
                    logger.warning(f"Plyer failed: {e}. Trying PowerShell...")

            # Final fallback: PowerShell
            if sys.platform == "win32":
                NotificationService._send_powershell_notification(title, message)
            else:
                logger.warning(f"Notification suppressed (no provider): {title} - {message}")

        # Run in thread to avoid blocking
        threading.Thread(target=_notify, daemon=True).start()

    @staticmethod
    def _send_powershell_notification(title, message):
        """Uses PowerShell to show a notification on Windows."""
        import subprocess
        try:
            # Escape quotes for PowerShell
            safe_title = title.replace('"', '`"').replace("'", "`'")
            safe_message = message.replace('"', '`"').replace("'", "`'")

            ps_script = f"""
            [void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")
            $objNotifyIcon = New-Object System.Windows.Forms.NotifyIcon
            $objNotifyIcon.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon((Get-Process -Id $pid).Path)
            $objNotifyIcon.BalloonTipIcon = "Info"
            $objNotifyIcon.BalloonTipText = "{safe_message}"
            $objNotifyIcon.BalloonTipTitle = "{NotificationService.APP_NAME}: {safe_title}"
            $objNotifyIcon.Visible = $True
            $objNotifyIcon.ShowBalloonTip(10000)
            Start-Sleep -s 2
            $objNotifyIcon.Dispose()
            """
            subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception as e:
            logger.error(f"PowerShell notification failed: {e}")
