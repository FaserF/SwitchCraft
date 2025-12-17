
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from plyer import notification
    _PLYER_AVAILABLE = True
except (ImportError, NotImplementedError):
    logger.warning("plyer module not found or not supported. Notifications will be disabled.")
    _PLYER_AVAILABLE = False

class NotificationService:
    """
    Service to handle system notifications using plyer.
    """

    APP_NAME = "SwitchCraft"
    APP_ICON = None # Path to .ico if available

    @staticmethod
    def send_notification(title: str, message: str, timeout: int = 10):
        """
        Sends a desktop notification. Uses plyer if available, falls back to PowerShell on Windows.
        """
        def _notify():
            if _PLYER_AVAILABLE:
                try:
                    notification.notify(
                        title=f"{NotificationService.APP_NAME}: {title}",
                        message=message,
                        app_name=NotificationService.APP_NAME,
                        app_icon=NotificationService.APP_ICON,
                        timeout=timeout
                    )
                    return
                except Exception as e:
                    logger.warning(f"Plyer notification failed: {e}. Attempting fallback...")

            # Fallback for Windows
            import sys
            if sys.platform == "win32":
                NotificationService._send_powershell_notification(title, message)
            else:
                logger.warning(f"Notification suppressed (no provider): {title} - {message}")

        # Run in a separate thread to avoid blocking the GUI/Main thread
        threading.Thread(target=_notify, daemon=True).start()

    @staticmethod
    def _send_powershell_notification(title, message):
        """Uses PowerShell to show a notification on Windows."""
        import subprocess
        try:
            # PowerShell script to show a balloon tip/toast
            # Note: Modern toast requires AppUserModelID set (which we do in app.py)
            # This is a simple fallback using Windows.Forms
            ps_script = f"""
            [void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")
            $objNotifyIcon = New-Object System.Windows.Forms.NotifyIcon
            $objNotifyIcon.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon((Get-Process -Id $pid).Path)
            $objNotifyIcon.BalloonTipIcon = "Info"
            $objNotifyIcon.BalloonTipText = "{message}"
            $objNotifyIcon.BalloonTipTitle = "{NotificationService.APP_NAME}: {title}"
            $objNotifyIcon.Visible = $True
            $objNotifyIcon.ShowBalloonTip(10000)
            Start-Sleep -s 2 # Wait for balloon to show
            $objNotifyIcon.Dispose()
            """
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            logger.error(f"PowerShell notification failed: {e}")
