import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class HistoryService:
    def __init__(self):
        self.history_file = self._get_history_path()

    def _get_history_path(self):
        app_data = os.getenv('APPDATA')
        if not app_data:
            return Path("history.json") # Fallback

        dir_path = Path(app_data) / "FaserF" / "SwitchCraft"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path / "history.json"

    def get_history(self):
        """Get all history items, sorted by date (newest first)."""
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                 data = json.load(f)
                 return sorted(data, key=lambda x: x.get('timestamp', ''), reverse=True)
        except json.JSONDecodeError:
            logger.warning(f"History file corrupted (JSON error): {self.history_file}. Resetting.")
            return []
        except Exception:
            logger.exception(f"Unexpected error loading history from {self.history_file}")
            return []

    def get_recent(self, limit=5):
        """Get the most recent N history items formatted for display."""
        history = self.get_history()
        result = []
        for item in history[:limit]:
            # Format for home view
            title = item.get('filename') or item.get('product') or 'Unknown'
            action = item.get('status', 'Analyzed')
            ts = item.get('timestamp', '')
            try:
                ts_display = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                ts_display = ts
            result.append({
                'title': f"{title} - {action}",
                'action': action,
                'timestamp': ts_display
            })
        return result

    def add_entry(self, entry):
        """Add a new analysis entry."""
        history = self.get_history()

        # Add timestamp
        entry['timestamp'] = datetime.now().isoformat()

        # Avoid duplicates (by filepath and size maybe? simplified by filename for now)
        # Actually duplicates are fine if re-analyzed.

        history.insert(0, entry)

        # Limit size (e.g. last 100)
        if len(history) > 100:
            history = history[:100]

        self._save(history)

    def clear(self):
        self._save([])

    def _save(self, data):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            logger.exception("Failed to save history")
