import logging
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

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
            self.file_handler = logging.FileHandler(self.current_log_path, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            self.file_handler.setFormatter(formatter)

        except Exception as e:
            print(f"Failed to setup file logging: {e}")

    def _cleanup_old_logs(self, log_dir):
        """Keeps only the latest MAX_LOG_FILES."""
        try:
            # Keep only the newest MAX_LOG_FILES
            files = sorted(log_dir.glob("SwitchCraft_Session_*.log"), key=os.path.getmtime, reverse=True)
            existing_to_keep = MAX_LOG_FILES - 1
            if len(files) > existing_to_keep:
                 for f in files[existing_to_keep:]:
                     try:
                         f.unlink()
                     except Exception:
                         pass

        except Exception as e:
            # We use print here because logging might be broken or recursive
            print(f"Error cleaning old logs: {e}")

    def emit(self, record):
        if self.file_handler:
            # Check size limit
            try:
                if self.current_log_path.stat().st_size > MAX_LOG_SIZE_BYTES:
                     # Rotate: Rename to .bak (overwrite) and restart
                     self.file_handler.close()
                     self.file_handler = None

                     bak = self.current_log_path.with_suffix(".log.bak")
                     if bak.exists():
                        bak.unlink()
                     self.current_log_path.rename(bak)

                     # Re-init
                     self.file_handler = logging.FileHandler(self.current_log_path, encoding='utf-8')
                     formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                     self.file_handler.setFormatter(formatter)
                     self.file_handler.setLevel(self.level)
            except Exception:
                pass

            self.file_handler.emit(record)

    def export_logs(self, target_path):
        """Exports the current session log file."""
        if not self.current_log_path or not self.current_log_path.exists():
            return False

        try:
            if self.file_handler:
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

    def get_github_issue_link(self):
        """Generates a GitHub issue link (template)."""
        import platform
        from switchcraft import __version__

        base_url = "https://github.com/Starttoaster/SwitchCraft/issues/new"
        try:
            os_info = f"{platform.system()} {platform.release()} ({platform.version()})"
            py_ver = platform.python_version()
            body = f"""
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior.

**Environment**
- OS: {os_info}
- Python: {py_ver}
- SwitchCraft Version: {__version__}

**Additional context**
Add any other context about the problem here.
"""
            import urllib.parse
            params = {
                "title": f"[Bug]: Error in v{__version__}",
                "body": body,
                "labels": "bug"
            }
            query = urllib.parse.urlencode(params)
            return f"{base_url}?{query}"
        except Exception:
            return base_url

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

    if '--debug' in sys.argv:
        handler.set_debug_mode(True)
