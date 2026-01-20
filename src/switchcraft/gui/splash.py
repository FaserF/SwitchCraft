import tkinter as tk
from tkinter import ttk
import os
import sys
import logging
import tempfile

# Setup debug logging for splash process
log_file = os.path.join(tempfile.gettempdir(), "switchcraft_splash_debug.log")
logger = logging.getLogger("switchcraft.splash")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(log_file)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.info(f"Splash process started. PID: {os.getpid()}")
logger.info(f"Python: {sys.executable}")

class LegacySplash:
    """
    Splash screen that uses a Toplevel window.
    This avoids the 'pyimage' error caused by creating multiple Tk() roots.
    The main_root should be passed in (created once in main.py).
    """
    def __init__(self, main_root=None):
        logger.info("Initializing LegacySplash...")
        # If no root passed, create one (standalone run)
        if main_root is None:
            logger.info("Creating new Tk root")
            self.root = tk.Tk()
            self._owns_root = True
        else:
            logger.info("Using existing Tk root")
            self.root = tk.Toplevel(main_root)
            self._owns_root = False

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        # Fallback font handling
        self.header_font = ("Segoe UI", 32, "bold")
        self.sub_font = ("Segoe UI", 12)
        self.status_font = ("Segoe UI", 9)

        # Basic fallback check (Tkinter doesn't robustly support family lists in tuples)
        # Assuming Windows mostly due to Segoe UI, but on Linux usually ignored or defaulted.
        # We keep it simple as requested but acknowledge fallback.

        # UI Setup
        self.root.configure(bg="#2c3e50")

        width = 450
        height = 250

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

        self.root.geometry(f"{width}x{height}+{x}+{y}")

        # Content
        main_frame = tk.Frame(self.root, bg="#2c3e50", highlightthickness=1, highlightbackground="#34495e")
        main_frame.pack(fill="both", expand=True)

        tk.Label(
            main_frame,
            text="SwitchCraft",
            font=self.header_font,
            bg="#2c3e50",
            fg="#ecf0f1"
        ).pack(pady=(40, 10))

        tk.Label(
            main_frame,
            text="Packaging Assistant for IT Professionals",
            font=self.status_font, # Use smaller font for longer text
            bg="#2c3e50",
            fg="#bdc3c7"
        ).pack()

        self.status_label = tk.Label(
            main_frame,
            text="Loading components...",
            font=self.status_font,
            bg="#2c3e50",
            fg="#95a5a6"
        )
        self.status_label.pack(side="bottom", pady=20)

        self.progress = ttk.Progressbar(main_frame, mode="indeterminate", length=300)
        self.progress.pack(pady=10)
        self.progress.start(10)

        # Safety Timeout: Close after 60 seconds automatically if app hangs
        self.root.after(60000, self._auto_close_timeout)

        self.root.update()

    def update_status(self, text):
        self.status_label.configure(text=text)
        self.root.update()

    def _auto_close_timeout(self):
        logger.warning("Splash screen timed out (safety timer). Force closing.")
        self.close()

    def close(self):
        if hasattr(self, 'progress'):
            try:
                self.progress.stop()
            except Exception:
                pass
        self.root.destroy()


def main():
    try:
        splash = LegacySplash()
        # Ensure it handles external termination signals if possible, or just runs until close()
        # When run as subprocess, it will be killed by parent.
        # But we want to ensure it pumps messages.
        splash.root.mainloop()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
