import logging
import uuid
from datetime import datetime
from typing import List, Dict, Callable

logger = logging.getLogger(__name__)

class NotificationService:
    _instance = None
    _listeners: List[Callable] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotificationService, cls).__new__(cls)
            cls._instance.notifications = []
        return cls._instance

    def add_notification(self, title: str, message: str, type: str = "info"):
        """
        Adds a notification.
        type: info, success, warning, error
        """
        notif = {
            "id": str(uuid.uuid4()),
            "title": title,
            "message": message,
            "type": type,
            "timestamp": datetime.now(),
            "read": False
        }
        self.notifications.insert(0, notif)
        self._notify_listeners()
        return notif

    def mark_read(self, notif_id: str):
        for n in self.notifications:
            if n["id"] == notif_id:
                n["read"] = True
                break
        self._notify_listeners()

    def mark_all_read(self):
        for n in self.notifications:
            n["read"] = True
        self._notify_listeners()

    def clear_all(self):
        self.notifications.clear()
        self._notify_listeners()

    def get_unread_count(self) -> int:
        return sum(1 for n in self.notifications if not n["read"])

    def get_notifications(self) -> List[Dict]:
        return self.notifications

    def add_listener(self, callback: Callable):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self):
        for callback in self._listeners:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in notification listener: {e}")

    # --- Legacy Static Method ---
    @staticmethod
    def set_app_window(window):
        """Legacy: No-op for backwards compatibility with legacy GUI."""
        logger.debug("NotificationService.set_app_window() called (legacy no-op)")
        pass
