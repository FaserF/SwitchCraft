import sys
import ctypes
import logging

logger = logging.getLogger(__name__)

class DebugConsole:
    _is_enabled = False
    _stdout = None
    _stderr = None

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
                sys.stdout = open("CONOUT$", "w", buffering=1)
                sys.stderr = open("CONOUT$", "w", buffering=1)
                cls._is_enabled = True
                print("SwitchCraft Debug Console [Enabled]")
        else:
            try:
                if sys.stdout and not sys.stdout.closed:
                    sys.stdout.close()
                if sys.stderr and not sys.stderr.closed:
                    sys.stderr.close()

                # Restore original streams
                if cls._stdout:
                    sys.stdout = cls._stdout
                if cls._stderr:
                    sys.stderr = cls._stderr
            except Exception as e:
                logger.error(f"Error closing console: {e}")

            kernel32.FreeConsole()
            cls._is_enabled = False
