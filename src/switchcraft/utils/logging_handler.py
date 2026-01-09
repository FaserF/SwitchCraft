import logging
import collections
from datetime import datetime

class SessionLogHandler(logging.Handler):
    """
    A custom logging handler that stores log records in memory for the current session.
    Allows exporting logs to a file.
    """
    def __init__(self, capacity=5000):
        super().__init__()
        self.log_records = collections.deque(maxlen=capacity)
        # Default format
        self.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_records.append(msg)
        except Exception:
            self.handleError(record)

    def export_logs(self, file_path):
        """Export captured logs to the specified file path."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"SwitchCraft Session Logs - Exported at {datetime.now()}\n")
                f.write("-" * 50 + "\n")
                for line in self.log_records:
                    f.write(line + "\n")
            return True
        except Exception as e:
            # Fallback print if export fails
            print(f"Failed to export logs: {e}")
            return False

    def get_github_issue_link(self):
        """Returns the URL to create a new issue on GitHub."""
        return "https://github.com/FaserF/SwitchCraft/issues/new"

# Singleton instance to be shared
_session_handler = None

def get_session_handler():
    global _session_handler
    if _session_handler is None:
        _session_handler = SessionLogHandler()
        _session_handler.setLevel(logging.WARNING) # Capture Warnings and Errors by default as requested
    return _session_handler

def setup_session_logging(root_logger=None):
    """Attaches the session handler to the root logger."""
    if root_logger is None:
        root_logger = logging.getLogger()

    handler = get_session_handler()
    if handler not in root_logger.handlers:
        root_logger.addHandler(handler)
