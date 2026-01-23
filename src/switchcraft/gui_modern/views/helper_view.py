import flet as ft
import threading
import logging

logger = logging.getLogger(__name__)


from switchcraft.gui_modern.utils.view_utils import ViewMixin

class ModernHelperView(ft.Column, ViewMixin):
    """
    Builds the AI Helper UI view for the provided Flet page.
    """
    def __init__(self, page: ft.Page):
        super().__init__(expand=True, spacing=0)
        self.app_page = page
        self.ai_service = None
        self._init_ui()

    def _init_ui(self):
        # Try to load AI Service (uses stub if addon missing)
        try:
            from switchcraft.services.ai_service import SwitchCraftAI
            self.ai_service = SwitchCraftAI()
        except Exception as e:
            logger.error(f"AI Service init failed: {e}")

        if not self.ai_service:
            self.controls = self._build_missing_addon_view()
            return

        self.chat_history = ft.ListView(expand=True, spacing=10, auto_scroll=True)
        self.input_field = ft.TextField(
            label=i18n.get("ai_ask_hint") or "Ask a question...",
            expand=True,
            border_radius=10,
            content_padding=15,
            border_color="BLUE_400",
            focused_border_color="BLUE_600",
            filled=True,
            bgcolor="GREY_900",
            on_submit=self.send_message
        )

        # Initial Welcome Message
        self.add_message(
            i18n.get("ai_welcome_title") or "AI Assistant",
            i18n.get("ai_welcome_msg") or "Hello! How can I help you today?",
            is_user=False
        )

        self.controls = [
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.SMART_TOY, size=32, color="BLUE_400"),
                    ft.Column([
                        ft.Text(i18n.get("ai_helper") or "AI Helper", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(i18n.get("ai_helper_subtitle") or "Ask me about silent switches, Intune errors, PowerShell, and Winget packages",
                               size=12, color="GREY_400")
                    ], spacing=2, expand=True)
                ], spacing=12),
                padding=ft.Padding(20, 15, 20, 15),
                bgcolor="SURFACE_VARIANT",
                border_radius=12,
            ),
            ft.Container(height=15),
            ft.Container(
                content=self.chat_history,
                expand=True,
                bgcolor="SURFACE_CONTAINER_HIGHEST" if hasattr(getattr(ft, "colors", None), "SURFACE_CONTAINER_HIGHEST") else "BLACK12",
                border=ft.Border.all(1, "OUTLINE_VARIANT"),
                border_radius=12,
                padding=20
            ),
            ft.Container(height=15),
            ft.Container(
                content=ft.Row([
                    self.input_field,
                    ft.IconButton(
                        ft.Icons.SEND_ROUNDED,
                        on_click=self.send_message,
                        tooltip="Send message",
                        icon_color="WHITE",
                        bgcolor="BLUE_600",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        icon_size=24
                    )
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor="SURFACE_VARIANT",
                padding=ft.Padding(15, 12, 15, 12),
                border_radius=12,
                border=ft.Border.all(1, "OUTLINE_VARIANT"),
            )
        ]

    def _build_missing_addon_view(self):
        def go_to_addons(e):
            if hasattr(self.app_page, 'switchcraft_app') and hasattr(self.app_page.switchcraft_app, 'goto_tab'):
                self.app_page.switchcraft_app.goto_tab(9)
            else:
                self._show_snack(i18n.get("please_navigate_manually") or "Please navigate to Addons tab manually", "ORANGE")

        return [
            ft.Icon(ft.Icons.SMART_TOY_OUTLINED, size=60, color="ON_SURFACE_VARIANT"),
            ft.Text(i18n.get("ai_helper") or "AI Helper", size=28, weight=ft.FontWeight.BOLD),
            ft.Text(i18n.get("addon_missing_msg_ai") or "The AI Addon is not installed or failed to load.", color="orange", text_align=ft.TextAlign.CENTER),
            ft.Text(i18n.get("addon_install_hint") or "Install the addon to enable this feature.", size=12, color="ON_SURFACE_VARIANT", text_align=ft.TextAlign.CENTER),
            ft.Container(height=10),
            ft.FilledButton(
                content=ft.Row([ft.Icon(ft.Icons.EXTENSION), ft.Text(i18n.get("btn_go_to_addons") or "Go to Addon Manager")], alignment=ft.MainAxisAlignment.CENTER),
                bgcolor="BLUE_700",
                color="WHITE",
                on_click=go_to_addons
            )
        ]

    def add_message(self, sender, text, is_user=False, is_error=False):
        if is_error:
            bg_color = "RED_900"
        else:
            bg_color = "GREY_800" if is_user else "BLUE_900"

        align = ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START

        # Message Content (Markdown for AI, Text for User)
        content = ft.Markdown(
            text,
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
            on_tap_link=lambda e: self._launch_url(e.data),
        ) if not is_user else ft.Text(text, selectable=True, color="WHITE")

        # Copy button handler
        def copy_handler(e):
            try:
                import pyperclip
                pyperclip.copy(text)
                self._show_snack(i18n.get("copied_to_clipboard") or "Copied to clipboard!", "GREEN_700")
            except Exception:
                # Fallback to internal method
                if hasattr(self.app_page, 'set_clipboard'):
                    self.app_page.set_clipboard(text)
                    self._show_snack(i18n.get("copied_to_clipboard") or "Copied to clipboard!", "GREEN_700")
                else:
                    self._show_snack(i18n.get("copy_failed") or "Failed to copy to clipboard!", "RED_700")

        self.chat_history.controls.append(
            ft.Row([
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(sender, weight=ft.FontWeight.BOLD, size=12, color="WHITE"),
                            ft.IconButton(
                                ft.Icons.COPY,
                                icon_size=16,
                                icon_color="GREY_400",
                                tooltip="Copy message",
                                on_click=copy_handler
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=10),
                        content
                    ], tight=True, spacing=8),
                    bgcolor=bg_color,
                    padding=15,
                    border_radius=15,
                    width=min(self.app_page.width * 0.75, 700) if self.app_page and isinstance(self.app_page.width, (int, float)) else 600,
                    margin=ft.Margin(0, 5, 0, 5),
                )
            ], alignment=align)
        )
        self.update()

    def send_message(self, e):
        user_msg = self.input_field.value
        if not user_msg:
            return

        self.input_field.value = ""
        self.add_message("You", user_msg, is_user=True)

        # Show typing indicator
        typing_indicator = ft.Text("AI is typing...", italic=True, color="ON_SURFACE_VARIANT")
        self.chat_history.controls.append(typing_indicator)
        self.update()
        self.input_field.focus()

        def _get_response():
            try:
                response = self.ai_service.ask(user_msg)
                if typing_indicator in self.chat_history.controls:
                    self.chat_history.controls.remove(typing_indicator)
                self.add_message("AI", response, is_user=False)
            except Exception as ex:
                if typing_indicator in self.chat_history.controls:
                    self.chat_history.controls.remove(typing_indicator)
                self.add_message("AI Error", str(ex), is_user=False, is_error=True)
            self.update()

        threading.Thread(target=_get_response, daemon=True).start()
