import customtkinter as ctk
from datetime import datetime
from pathlib import Path

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

        # Loading Frame (Progress + Status) - Packed but empty/hidden initially
        self.loading_frame = ctk.CTkFrame(self, fg_color="transparent", height=0)
        self.loading_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.progress_bar = ctk.CTkProgressBar(self.loading_frame, height=10)
        self.status_label = ctk.CTkLabel(self.loading_frame, text="Loading...", text_color="gray", font=ctk.CTkFont(size=12))

        # List
        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=5)

        self.load_history()

    def load_history(self):
        # 1. Clear existing
        for w in self.scroll.winfo_children():
            w.destroy()

        # 2. Show loading UI
        self.loading_frame.pack(fill="x", padx=10, pady=(0, 5))
        self.status_label.pack(fill="x", pady=(0, 5))
        self.progress_bar.pack(fill="x", pady=(0, 5))
        self.progress_bar.set(0)
        self.status_label.configure(text="Loading history...")

        # 3. Start Loading Async
        self.after(50, self._start_loading_process)

    def _start_loading_process(self):
        try:
            items = self.history_service.get_history()
        except Exception as e:
            self._hide_progress()
            ctk.CTkLabel(self.scroll, text=f"Error loading history: {e}", text_color="red").pack(pady=20)
            return

        if not items:
            self._hide_progress()
            ctk.CTkLabel(self.scroll, text="No history yet.", text_color="gray").pack(pady=20)
            return

        self._load_batch_recursive(items, 0, len(items))

    def _load_batch_recursive(self, items, index, total):
        batch_size = 20
        end_index = min(index + batch_size, total)

        for i in range(index, end_index):
            self._create_row(items[i])

        # Update progress
        progress = end_index / total
        self.progress_bar.set(progress)
        self.status_label.configure(text=f"Loading {end_index} / {total} ...")

        if end_index < total:
            # Schedule next batch (10ms delay to keep UI responsive)
            self.after(10, lambda: self._load_batch_recursive(items, end_index, total))
        else:
            # Done
            self.after(200, self._hide_progress)

    def _hide_progress(self):
        self.progress_bar.pack_forget()
        self.status_label.pack_forget()

    def _create_row(self, item):
        frame = ctk.CTkFrame(self.scroll)
        frame.pack(fill="x", pady=2)

        # Parse timestamp
        ts_str = item.get('timestamp', '')
        try:
            dt = datetime.fromisoformat(ts_str)
            date_display = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
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
