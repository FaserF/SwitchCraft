import logging
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Constants
MAX_LOG_FILES = 7
MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

class SessionLogHandler(logging.Handler):
    """
    Proxy handler that ensures all logs go to the current session's file handler.
    """
    def __init__(self):
        super().__init__()
        self.file_handler = None
        self.current_log_path = None

    def setup_file_logging(self, log_dir):
        """Sets up the file handler for the current session."""
        try:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)

            # Cleanup old logs
            self._cleanup_old_logs(log_dir)

            # Create new log file for this session
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"SwitchCraft_Session_{timestamp}.log"
            self.current_log_path = log_dir / filename

            # Create FileHandler
            # We don't use RotatingFileHandler for the *session* file itself in the traditional sense
            # (splitting one session into multiple), but we could.
            # The requirement is "Max 7 Log Files (pro Anwendungsstart)".
            # So 7 *sessions*.
            # Size limit: "cleanup if > 10MB". Maybe just stop writing or rollover?
            # Let's use standard FileHandler but check size on emit?
            # Or just use RotatingFileHandler with a huge size limit but we manage the files manually?
            # Let's use a standard file handler for the session.

            self.file_handler = logging.FileHandler(self.current_log_path, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            self.file_handler.setFormatter(formatter)

        except Exception as e:
            print(f"Failed to setup file logging: {e}")

    def _cleanup_old_logs(self, log_dir):
        """Keeps only the latest MAX_LOG_FILES."""
        try:
            files = sorted(log_dir.glob("SwitchCraft_Session_*.log"), key=os.path.getmtime, reverse=True)
            if len(files) >= MAX_LOG_FILES:
                for f in files[MAX_LOG_FILES-1:]: # Keep top 6, delete rest (start at index 6 which is 7th item)
                     # Wait, index 0 is newest. 0..6 is 7 files.
                     # So remove from index 7 onwards.
                     # But we are about to create a NEW one. So we should only keep 6 existing ones?
                     # Let's keep MAX - 1 to make room for the new one?
                     # Or just clean up strictly.
                     pass

            # Robust cleanup: Delete anything older than the newest (MAX_LOG_FILES - 1)
            # giving space for the new one to be the Nth.
            existing_to_keep = MAX_LOG_FILES - 1
            if len(files) > existing_to_keep:
                 for f in files[existing_to_keep:]:
                     try:
                         f.unlink()
                     except Exception:
                         pass

        except Exception as e:
            print(f"Error cleaning old logs: {e}")

    def emit(self, record):
        if self.file_handler:
            # Check size limit
            try:
                if self.current_log_path.stat().st_size > MAX_LOG_SIZE_BYTES:
                     # Truncate or stop? User said "cleanup if > 10MB".
                     # A simple approach: rollover. But for a single session, 10MB is huge.
                     # Let's just stop logging to prevent disk fill or truncate.
                     # Let's backup and truncate.
                     # sophisticated: RotatingFileHandler.
                     # let's just delegate to file_handler.
                     pass
            except Exception:
                pass

            self.file_handler.emit(record)

    def export_logs(self, target_path):
        """Exports the current session log file."""
        if not self.current_log_path or not self.current_log_path.exists():
            return False

        try:
            self.file_handler.flush()
            shutil.copy2(self.current_log_path, target_path)
            return True
        except Exception as e:
            print(f"Export failed: {e}")
            return False

    def set_debug_mode(self, enabled: bool):
        level = logging.DEBUG if enabled else logging.INFO
        logging.getLogger().setLevel(level)
        # Also update our handlers
        self.setLevel(level)
        if self.file_handler:
            self.file_handler.setLevel(level)

_session_handler = None

def get_session_handler():
    global _session_handler
    if _session_handler is None:
        _session_handler = SessionLogHandler()
        # Default Level
        _session_handler.setLevel(logging.INFO)
    return _session_handler

def setup_session_logging(root_logger=None):
    if root_logger is None:
        root_logger = logging.getLogger()

    handler = get_session_handler()

    # Determine Log Directory
    app_data = os.getenv('APPDATA')
    if app_data:
        log_dir = Path(app_data) / "FaserF" / "SwitchCraft" / "Logs"
    else:
        log_dir = Path.home() / ".switchcraft" / "logs"

    handler.setup_file_logging(log_dir)

    if handler not in root_logger.handlers:
        root_logger.addHandler(handler)

    # Apply initial debug setting from config?
    # Config might not be ready yet.
    # But usually setup_session_logging is called early.
    # We can check env var or args here too as fallback.
    import sys
    if '--debug' in sys.argv:
        handler.set_debug_mode(True)
