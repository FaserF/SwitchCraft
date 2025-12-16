import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES
import threading
from pathlib import Path
from PIL import Image
import webbrowser
import logging

from switchcraft.analyzers.msi import MsiAnalyzer
from switchcraft.analyzers.exe import ExeAnalyzer
from switchcraft.utils.winget import WingetHelper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self) # Initialize DnD

        self.title("SwitchCraft 🧙‍♂️")
        self.geometry("800x600")

        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header
        self.header_frame = ctk.CTkFrame(self, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew")

        self.title_label = ctk.CTkLabel(self.header_frame, text="SwitchCraft", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=10)

        # Description / Drop Zone
        self.drop_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.drop_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=20)

        self.drop_label = ctk.CTkButton(self.drop_frame, text="Drag & Drop Installer Here\n(EXE / MSI)",
                                        height=100, corner_radius=10,
                                        fg_color=("#3B8ED0", "#1F6AA5"),
                                        hover_color=("#36719F", "#144870"),
                                        font=ctk.CTkFont(size=18),
                                        command=self.open_file_dialog)
        self.drop_label.pack(fill="x", expand=True)

        # Bind Drag and Drop
        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind('<<Drop>>', self.drop)

        # Result Area
        self.result_frame = ctk.CTkScrollableFrame(self, label_text="Analysis Results")
        self.result_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.result_frame.grid_columnconfigure(1, weight=1)

        # Status Bar
        self.status_bar = ctk.CTkLabel(self, text="Ready", anchor="w")
        self.status_bar.grid(row=3, column=0, sticky="ew", padx=20, pady=5)

    def open_file_dialog(self):
        file_path = ctk.filedialog.askopenfilename(filetypes=[("Installers", "*.exe;*.msi")])
        if file_path:
            self.start_analysis(file_path)

    def drop(self, event):
        file_path = event.data
        if file_path.startswith('{') and file_path.endswith('}'):
             file_path = file_path[1:-1] # Clean up DnD path artifacts
        self.start_analysis(file_path)

    def start_analysis(self, file_path):
        self.status_bar.configure(text=f"Analyzing {Path(file_path).name}...")
        self.clear_results()

        # Run in thread
        thread = threading.Thread(target=self.analyze, args=(file_path,))
        thread.start()

    def clear_results(self):
        for widget in self.result_frame.winfo_children():
            widget.destroy()

    def analyze(self, file_path_str):
        path = Path(file_path_str)
        if not path.exists():
             self.show_error("File not found.")
             return

        analyzers = [MsiAnalyzer(), ExeAnalyzer()]
        info = None
        for analyzer in analyzers:
            if analyzer.can_analyze(path):
                try:
                    info = analyzer.analyze(path)
                    break
                except Exception as e:
                    logger.error(f"Analysis failed: {e}")

        if info:
             # Find Winget match
             winget = WingetHelper()
             winget_url = winget.search_by_name(info.product_name) if info.product_name else None
             self.after(0, lambda: self.show_results(info, winget_url))
        else:
             self.after(0, lambda: self.show_error("Could not identify installer type."))

    def show_error(self, message):
         self.status_bar.configure(text="Error")
         label = ctk.CTkLabel(self.result_frame, text=message, text_color="red")
         label.pack(pady=20)

    def show_results(self, info, winget_url):
        self.status_bar.configure(text="Analysis Complete")

        self.add_result_row("File", info.file_path)
        self.add_result_row("Type", info.installer_type)
        self.add_result_row("Product Name", info.product_name or "Unknown")
        self.add_result_row("Version", info.product_version or "Unknown")
        self.add_result_row("Manufacturer", info.manufacturer or "Unknown")

        self.add_separator()

        if info.install_switches:
            cmd = " ".join(info.install_switches)
            self.add_copy_row("Silent Install", cmd, "green")
        else:
             self.add_result_row("Silent Install", "No automatic switches found.", color="yellow")
             if info.file_path.endswith('.exe'):
                  self.add_copy_row("Brute Force Help", f'"{info.file_path}" /?', "orange")

        if info.uninstall_switches:
            cmd = " ".join(info.uninstall_switches)
            self.add_copy_row("Silent Uninstall", cmd, "red")

        if winget_url:
            self.add_separator()
            link_btn = ctk.CTkButton(self.result_frame, text="View on Winget GitHub",
                                     fg_color="transparent", border_width=1,
                                     command=lambda: webbrowser.open(winget_url))
            link_btn.pack(pady=10, fill="x")

    def add_result_row(self, label_text, value_text, color=None):
        frame = ctk.CTkFrame(self.result_frame, fg_color="transparent")
        frame.pack(fill="x", pady=2)

        lbl = ctk.CTkLabel(frame, text=f"{label_text}:", width=120, anchor="w", font=ctk.CTkFont(weight="bold"))
        lbl.pack(side="left")

        val_lbl = ctk.CTkLabel(frame, text=value_text, anchor="w", wraplength=400, text_color=color if color else ("black", "white"))
        val_lbl.pack(side="left", fill="x", expand=True)

    def add_copy_row(self, label_text, value_text, color_theme="blue"):
        frame = ctk.CTkFrame(self.result_frame, fg_color="transparent")
        frame.pack(fill="x", pady=5)

        lbl = ctk.CTkLabel(frame, text=f"{label_text}:", width=120, anchor="w", font=ctk.CTkFont(weight="bold"))
        lbl.pack(side="left", anchor="n")

        # Textbox for easy selection
        txt = ctk.CTkTextbox(frame, height=50, fg_color=("gray90", "gray20"))
        txt.insert("0.0", value_text)
        txt.configure(state="disabled")
        txt.pack(side="left", fill="x", expand=True, padx=5)

        copy_btn = ctk.CTkButton(frame, text="Copy", width=60,
                                 fg_color="transparent", border_width=1,
                                 command=lambda: self.clipboard_clear() or self.clipboard_append(value_text) or self.update())
        copy_btn.pack(side="right")

    def add_separator(self):
        line = ctk.CTkFrame(self.result_frame, height=2, fg_color="gray50")
        line.pack(fill="x", pady=10)

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
