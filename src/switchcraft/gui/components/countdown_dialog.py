import customtkinter as ctk
import time
from switchcraft.utils.i18n import i18n
import threading

class CountdownDialog(ctk.CTkToplevel):
    """
    A dialog that shows a countdown and then executes a callback (e.g., restart).
    Can be cancelled by the user.
    """
    def __init__(self, parent, title, message, timeout_seconds=5, on_timeout=None, on_cancel=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x200")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.timeout_seconds = timeout_seconds
        self.on_timeout = on_timeout
        self.on_cancel = on_cancel
        self.running = True

        # Center on parent
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
            y = parent.winfo_y() + (parent.winfo_height() // 2) - 100
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        # UI
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))

        self.lbl_msg = ctk.CTkLabel(self, text=message, wraplength=350)
        self.lbl_msg.pack(pady=5)

        self.lbl_timer = ctk.CTkLabel(self, text=str(timeout_seconds), font=ctk.CTkFont(size=30, weight="bold"), text_color="#3B8ED0")
        self.lbl_timer.pack(pady=10)

        ctk.CTkButton(self, text=i18n.get("btn_cancel") or "Cancel", fg_color="gray", command=self.cancel).pack(pady=20)

        # Start Timer
        self._update_timer()

    def _update_timer(self):
        if not self.running:
            return

        self.lbl_timer.configure(text=f"{self.timeout_seconds}s")

        if self.timeout_seconds <= 0:
            self.running = False
            self.destroy()
            if self.on_timeout:
                self.on_timeout()
            return

        self.timeout_seconds -= 1
        self.after(1000, self._update_timer)

    def cancel(self):
        self.running = False
        self.destroy()
        if self.on_cancel:
            self.on_cancel()
