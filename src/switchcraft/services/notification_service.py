import logging
import uuid
from datetime import datetime
from typing import List, Dict, Callable
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class NotificationService:
    _instance = None
    _listeners: List[Callable] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotificationService, cls).__new__(cls)
            cls._instance.notifications = []
            cls._instance._load_notifications()
        return cls._instance

    def _get_storage_path(self):
        app_data = os.getenv('APPDATA')
        if app_data:
             path = Path(app_data) / "FaserF" / "SwitchCraft" / "notifications.json"
        else:
             path = Path.home() / ".switchcraft" / "notifications.json"

        # Ensure dir exists
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _load_notifications(self):
        try:
            path = self._get_storage_path()
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Restore timestamp objects
                    for n in data:
                        if isinstance(n.get("timestamp"), str):
                            try:
                                n["timestamp"] = datetime.fromisoformat(n["timestamp"])
                            except:
                                n["timestamp"] = datetime.now()
                    self.notifications = data
        except Exception as e:
            logger.error(f"Failed to load notifications: {e}")

    def _save_notifications(self):
        try:
            path = self._get_storage_path()
            # Serialize dates
            data_to_save = []
            for n in self.notifications:
                item = n.copy()
                if isinstance(item.get("timestamp"), datetime):
                    item["timestamp"] = item["timestamp"].isoformat()
                data_to_save.append(item)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save notifications: {e}")

    def add_notification(self, title: str, message: str, type: str = "info", notify_system: bool = None, data: Dict = None):
        """
        Adds a notification.
        type: info, success, warning, error
        notify_system: If True, triggers OS toast (if supported by GUI).
                       If None, defaults to True for 'error' and 'warning', False otherwise.
        """

        # Determine priority/system notification
        if notify_system is None:
            notify_system = type in ["error", "warning"]

        notif = {
            "id": str(uuid.uuid4()),
            "title": title,
            "message": message,
            "type": type,
            "timestamp": datetime.now(),
            "read": False,
            "notify_system": notify_system,
            "data": data or {}
        }
        self.notifications.insert(0, notif)
        self._save_notifications()
        self._notify_listeners()
        return notif

    def mark_read(self, notif_id: str):
        for n in self.notifications:
            if n["id"] == notif_id:
                n["read"] = True
                break
        self._save_notifications()
        self._notify_listeners()

    def mark_all_read(self):
        for n in self.notifications:
            n["read"] = True
        self._save_notifications()
        self._notify_listeners()

    def clear_all(self):
        self.notifications.clear()
        self._save_notifications()
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
