import customtkinter as ctk
import logging
from switchcraft.utils.i18n import i18n
from switchcraft.utils.config import SwitchCraftConfig

logger = logging.getLogger(__name__)

class AIView(ctk.CTkFrame):
    def __init__(self, parent, ai_service):
        super().__init__(parent)
        self.ai_service = ai_service

        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_ui()

    def setup_ui(self):
        """Setup the AI Helper tab."""
        # Chat History Area
        self.chat_frame = ctk.CTkTextbox(self, state="disabled")
        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Welcome Message
        self.append_chat("System", i18n.get("ai_helper_welcome"))

        # Privacy Disclaimer (Green Text)
        disclaimer_frame = ctk.CTkFrame(self, fg_color="transparent")
        disclaimer_frame.grid(row=1, column=0, sticky="ew", padx=10)

        # Privacy Disclaimer
        provider = SwitchCraftConfig.get_value("AIProvider", "local")
        if provider == "local":
             text_key = "privacy_note_local"
             color = "green"
             provider_name = i18n.get("ai_local")
        else:
             text_key = "privacy_note_cloud"
             color = "red"
             provider_name = i18n.get("ai_openai") if provider == "openai" else i18n.get("ai_gemini")

        ctk.CTkLabel(
            disclaimer_frame,
            text=f"🔒 {i18n.get(text_key, provider=provider_name)}",
            text_color=color,
            font=ctk.CTkFont(size=11, weight="bold")
        ).pack(anchor="w")

        # Input Area
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        self.chat_entry = ctk.CTkEntry(input_frame, placeholder_text="Ask something...")
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.chat_entry.bind("<Return>", self.handle_chat)

        send_btn = ctk.CTkButton(input_frame, text="Send", width=80, command=self.handle_chat)
        send_btn.pack(side="right")

    def handle_chat(self, event=None):
        msg = self.chat_entry.get()
        if not msg:
            return
        self.append_chat("You", msg)
        self.chat_entry.delete(0, "end")

        # Query AI
        if self.ai_service:
            answer = self.ai_service.ask(msg)
            self.after(200, lambda: self.append_chat("SwitchCraft AI", answer))
        else:
            self.after(500, lambda: self.append_chat("System", "AI Service not initialized."))

    def append_chat(self, sender, message):
        self.chat_frame.configure(state="normal")
        self.chat_frame.insert("end", f"[{sender}]: {message}\n\n")
        self.chat_frame.configure(state="disabled")
        self.chat_frame.see("end")
