import sys
import ctypes
import logging

logger = logging.getLogger(__name__)

class DebugConsole:
    @staticmethod
    def toggle(enable: bool):
        if sys.platform != 'win32':
            return

        kernel32 = ctypes.windll.kernel32
        if enable:
            kernel32.AllocConsole()
            sys.stdout = open("CONOUT$", "w")
            sys.stderr = open("CONOUT$", "w")
            print("SwitchCraft Debug Console [Enabled]")
        else:
            try:
                sys.stdout.close()
                sys.stderr.close()
                # Restore std streams to avoid errors (to default)
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
            except Exception as e:
                logger.error(f"Error closing console: {e}")
            kernel32.FreeConsole()
