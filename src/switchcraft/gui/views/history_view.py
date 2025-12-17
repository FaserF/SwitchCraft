import customtkinter as ctk
from datetime import datetime
from pathlib import Path
from switchcraft.utils.i18n import i18n

class HistoryView(ctk.CTkFrame):
    def __init__(self, parent, history_service, app):
        super().__init__(parent)
        self.history_service = history_service
        self.app = app

        # Header
        header = ctk.CTkFrame(self, height=40)
        header.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(header, text="History", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=10)
        ctk.CTkButton(header, text="Refresh", width=80, command=self.load_history).pack(side="right", padx=5)
        # Clear button
        ctk.CTkButton(header, text="Clear", width=80, fg_color="red", command=self.clear_history).pack(side="right", padx=5)

        # List
        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=5)

        self.load_history()

    def load_history(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        items = self.history_service.get_history()

        if not items:
            ctk.CTkLabel(self.scroll, text="No history yet.", text_color="gray").pack(pady=20)
            return

        for item in items:
            self._create_row(item)

    def _create_row(self, item):
        frame = ctk.CTkFrame(self.scroll)
        frame.pack(fill="x", pady=2)

        # Parse timestamp
        ts_str = item.get('timestamp', '')
        try:
            dt = datetime.fromisoformat(ts_str)
            date_display = dt.strftime("%Y-%m-%d %H:%M")
        except:
            date_display = ts_str

        # Info
        info_frame = ctk.CTkFrame(frame, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=5)

        filename = item.get('filename', 'Unknown')
        product = item.get('product', 'Unknown')

        ctk.CTkLabel(info_frame, text=filename, font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        ctk.CTkLabel(info_frame, text=f"{date_display} | {product}", text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w")

        # Actions
        btn_view = ctk.CTkButton(frame, text="Load", width=60, command=lambda f=item.get('filepath'): self._load_analysis(f))
        btn_view.pack(side="right", padx=10, pady=5)

    def _load_analysis(self, filepath):
        if filepath and Path(filepath).exists():
            self.app.start_analysis_tab(filepath)
        else:
            # File might be gone
            from tkinter import messagebox
            messagebox.showerror("Error", "File no longer exists.")

    def clear_history(self):
        self.history_service.clear()
        self.load_history()
