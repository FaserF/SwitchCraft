import sys
import ctypes
import logging
import os

logger = logging.getLogger(__name__)


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors based on log level."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[90m',      # Gray
        'INFO': '\033[36m',       # Cyan
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[41m',   # Red background
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


class DebugConsole:
    _is_enabled = False
    _stdout = None
    _stderr = None
    _console_handler = None

    @classmethod
    def toggle(cls, enable: bool):
        if sys.platform != 'win32':
            return

        if enable == cls._is_enabled:
            return

        kernel32 = ctypes.windll.kernel32
        if enable:
            if kernel32.AllocConsole():
                cls._stdout = sys.stdout
                cls._stderr = sys.stderr

                # Enable ANSI escape code processing on Windows
                handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
                mode = ctypes.c_ulong()
                kernel32.GetConsoleMode(handle, ctypes.byref(mode))
                # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)

                sys.stdout = open("CONOUT$", "w", buffering=1, encoding="utf-8")
                sys.stderr = open("CONOUT$", "w", buffering=1, encoding="utf-8")
                cls._is_enabled = True

                # Add colored handler to root logger
                cls._console_handler = logging.StreamHandler(sys.stdout)
                cls._console_handler.setFormatter(ColoredFormatter(
                    '%(levelname)s:%(name)s:%(message)s'
                ))
                logging.getLogger().addHandler(cls._console_handler)

                print("\033[32mSwitchCraft Debug Console [Enabled]\033[0m")
                print("\033[90mDEBUG\033[0m | \033[36mINFO\033[0m | \033[33mWARNING\033[0m | \033[31mERROR\033[0m")
        else:
            try:
                # Remove console handler
                if cls._console_handler:
                    logging.getLogger().removeHandler(cls._console_handler)
                    cls._console_handler = None

                if sys.stdout and not sys.stdout.closed:
                    sys.stdout.close()
                if sys.stderr and not sys.stderr.closed:
                    sys.stderr.close()

                # Restore original streams
                if cls._stdout:
                    sys.stdout = cls._stdout
                if cls._stderr:
                    sys.stderr = cls._stderr
            except Exception:
                logger.exception("Error closing console")

            kernel32.FreeConsole()
            cls._is_enabled = False
