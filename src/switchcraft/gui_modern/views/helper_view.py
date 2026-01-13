import flet as ft
import threading
import logging
from switchcraft.services.addon_service import AddonService

logger = logging.getLogger(__name__)


def ModernHelperView(page: ft.Page):
    """AI Helper View."""
    ai_service = None

    # Try to load AI Addon
    try:
        ai_mod = AddonService.import_addon_module("ai", "service")
        if ai_mod:
            ai_service = ai_mod.SwitchCraftAI()
    except Exception as e:
        logger.info(f"AI Addon not loaded: {e}")

    if not ai_service:
        from switchcraft.utils.i18n import i18n
        return ft.Column([
            ft.Icon(ft.Icons.SMART_TOY_OUTLINED, size=60, color="grey"),
            ft.Text(i18n.get("ai_helper") or "AI Helper", size=28, weight=ft.FontWeight.BOLD),
            ft.Text(i18n.get("addon_missing_msg_ai") or "The AI Addon is not installed or failed to load.", color="orange"),
            ft.Text(i18n.get("addon_install_hint") or "Install the addon to enable this feature.", size=12, color="grey"),
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    from switchcraft.utils.i18n import i18n
    chat_history = ft.ListView(expand=True, spacing=10, auto_scroll=True)
    input_field = ft.TextField(
        label=i18n.get("ai_ask_hint") or "Ask a question...",
        expand=True,
        border_radius=10,
        content_padding=15
    )

    def add_message(sender, text, is_user=False, is_error=False):
        bg_color = "BLUE_900" if is_user else ("RED_900" if is_error else "GREEN_900")

        chat_history.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Text(sender, weight=ft.FontWeight.BOLD, size=12),
                    ft.Text(text, selectable=True)
                ]),
                bgcolor=bg_color,
                padding=10,
                border_radius=8,
                margin=ft.margin.only(left=50 if is_user else 0, right=0 if is_user else 50)
            )
        )
        page.update()

    def send_message(e):
        user_msg = input_field.value
        if not user_msg:
            return

        input_field.value = ""
        add_message("You", user_msg, is_user=True)

        # Show typing indicator
        typing_indicator = ft.Text("AI is typing...", italic=True, color="grey")
        chat_history.controls.append(typing_indicator)
        page.update()
        input_field.focus()

        def _get_response():
            try:
                response = ai_service.ask(user_msg)
                if typing_indicator in chat_history.controls:
                    chat_history.controls.remove(typing_indicator)
                add_message("AI", response, is_user=False)
            except Exception as ex:
                if typing_indicator in chat_history.controls:
                    chat_history.controls.remove(typing_indicator)
                add_message("AI Error", str(ex), is_user=False, is_error=True)
            page.update()

        threading.Thread(target=_get_response, daemon=True).start()

    input_field.on_submit = send_message

    # Initial Welcome Message
    if len(chat_history.controls) == 0:
        from switchcraft.utils.i18n import i18n
        add_message(
            i18n.get("ai_welcome_title") or "AI Assistant",
            i18n.get("ai_welcome_msg") or "Hello! How can I help you today?",
            is_user=False
        )

    return ft.Column([
        ft.Row([
            ft.Icon(ft.Icons.SMART_TOY, size=30, color="BLUE"),
            ft.Text(i18n.get("ai_helper") or "AI Helper", size=24, weight=ft.FontWeight.BOLD),
        ]),
        ft.Divider(),
        ft.Container(
            content=chat_history,
            expand=True,
            bgcolor="SURFACE_CONTAINER_HIGHEST" if hasattr(getattr(ft, "colors", None), "SURFACE_CONTAINER_HIGHEST") else "GREY_900",
            border_radius=10,
            padding=10
        ),
        ft.Row([
            input_field,
            ft.IconButton(ft.Icons.SEND, on_click=send_message, tooltip="Send")
        ])
    ], expand=True)
