
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from plyer import notification
    _PLYER_AVAILABLE = True
except ImportError:
    logger.warning("plyer module not found. Notifications will be disabled.")
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
        Sends a desktop notification.
        """
        if not _PLYER_AVAILABLE:
            logger.debug(f"Notification suppressed (plyer missing): {title} - {message}")
            return

        def _notify():
            try:
                notification.notify(
                    title=f"{NotificationService.APP_NAME}: {title}",
                    message=message,
                    app_name=NotificationService.APP_NAME,
                    app_icon=NotificationService.APP_ICON,
                    timeout=timeout
                )
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")

        # Run in a separate thread to avoid blocking the GUI/Main thread
        threading.Thread(target=_notify, daemon=True).start()
