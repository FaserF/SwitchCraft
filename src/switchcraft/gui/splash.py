import tkinter as tk
from tkinter import ttk
import sys
import os
from pathlib import Path

class LegacySplash:
    """
    Splash screen that uses a Toplevel window.
    This avoids the 'pyimage' error caused by creating multiple Tk() roots.
    The main_root should be passed in (created once in main.py).
    """
    def __init__(self, main_root=None):
        # If no root passed, create one (standalone run)
        if main_root is None:
            self.root = tk.Tk()
            self._owns_root = True
        else:
            self.root = tk.Toplevel(main_root)
            self._owns_root = False

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

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
            font=("Segoe UI", 32, "bold"),
            bg="#2c3e50",
            fg="#ecf0f1"
        ).pack(pady=(40, 10))

        tk.Label(
            main_frame,
            text="Universal Installer Analyzer",
            font=("Segoe UI", 12),
            bg="#2c3e50",
            fg="#bdc3c7"
        ).pack()

        self.status_label = tk.Label(
            main_frame,
            text="Loading components...",
            font=("Segoe UI", 9),
            bg="#2c3e50",
            fg="#95a5a6"
        )
        self.status_label.pack(side="bottom", pady=20)

        progress = ttk.Progressbar(main_frame, mode="indeterminate", length=300)
        progress.pack(pady=10)
        progress.start(10)

        self.root.update()

    def update_status(self, text):
        self.status_label.configure(text=text)
        self.root.update()

    def close(self):
        self.root.destroy()
