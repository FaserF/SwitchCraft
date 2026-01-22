import logging
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Module-level logger
logger = logging.getLogger(__name__)

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

            # Close existing handler if it exists
            if self.file_handler:
                try:
                    self.file_handler.close()
                except Exception:
                    pass

            # Create FileHandler
            self.file_handler = logging.FileHandler(self.current_log_path, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            self.file_handler.setFormatter(formatter)
            # Set the file handler level to match the session handler level (default INFO)
            self.file_handler.setLevel(self.level if self.level else logging.DEBUG)

            # Write initial log entry to ensure file is created with content
            self.file_handler.stream.write(f"# SwitchCraft Log Session Started: {datetime.now().isoformat()}\n")
            self.file_handler.stream.flush()

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
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        # Also update our handlers
        self.setLevel(level)
        if self.file_handler:
            self.file_handler.setLevel(level)
        # Update all existing handlers to ensure they capture all levels
        for handler in root_logger.handlers:
            if hasattr(handler, 'setLevel'):
                handler.setLevel(level)
        if enabled:
            root_logger.info("Debug mode enabled - all log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) will be captured")
        else:
            root_logger.info("Debug mode disabled - only INFO and above will be captured")

    def get_github_issue_link(self):
        """
        Builds a prefilled GitHub issue URL for reporting a bug.

        The generated URL opens the repository's "new issue" page with a prefilled title, body (including OS, Python, and SwitchCraft version), and a "bug" label. If an error occurs while assembling the URL, the repository's new-issue page URL is returned unchanged.

        Returns:
            str: The URL to create a new GitHub issue with a prepopulated title, body, and labels, or the base new-issue URL on failure.
        """
        import platform
        from switchcraft import __version__

        base_url = "https://github.com/FaserF/SwitchCraft/issues/new"
        template = "bug_report.yml"

        try:
            os_name = platform.system()
            os_ver = platform.release()
            # Map OS to dropdown options if possible, otherwise use 'Other' or let user correct it
            # Template options: Windows 11, Windows 10, Windows Server, macOS, Linux, Other
            os_map = "Other"
            if os_name == "Windows":
                if "10" in os_ver:
                    os_map = "Windows 10"
                elif "11" in os_ver:
                    os_map = "Windows 11"
                elif "Server" in os_ver:
                    os_map = "Windows Server"
            elif os_name == "Darwin":
                os_map = "macOS"
            elif os_name == "Linux":
                os_map = "Linux"

            import urllib.parse

            # For Issue Forms, we pass params matching the 'id' of fields
            params = {
                "template": template,
                "labels": "bug",
                "title": f"[Bug]: Error in v{__version__}",
                "version": f"v{__version__}",
                "os": os_map,
                "description": "<!-- Please describe the bug here -->",
                "steps": "1. \n2. \n3. ",
                "expected": "..."
                # 'logs' is the ID for the log section
                # We can't easily paste full log file content into URL (URL length limits)
                # But we can put a placeholder or short info
            }

            # If we want to encourage attaching logs, we can mention it in the description or logs field
            params["logs"] = f"Python: {platform.python_version()}\n(Please attach the log file generated by the application if possible)"

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

    # Ensure root logger captures INFO by default so our handlers receive it
    if root_logger.level == logging.NOTSET or root_logger.level > logging.INFO:
        root_logger.setLevel(logging.INFO)

    if '--debug' in sys.argv:
        handler.set_debug_mode(True)