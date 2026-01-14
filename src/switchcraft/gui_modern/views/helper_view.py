import flet as ft
import threading
import logging

logger = logging.getLogger(__name__)


def ModernHelperView(page: ft.Page):
    """AI Helper View."""
    ai_service = None

    # Try to load AI Service (uses stub if addon missing)
    try:
        from switchcraft.services.ai_service import SwitchCraftAI
        ai_service = SwitchCraftAI()
    except Exception as e:
        logger.error(f"AI Service init failed: {e}")

    if not ai_service:
        from switchcraft.utils.i18n import i18n

        def go_to_addons(e):
            # Navigate to Addon Manager (tab index 9 - Settings)
            if hasattr(page, 'switchcraft_app') and hasattr(page.switchcraft_app, 'goto_tab'):
                page.switchcraft_app.goto_tab(9)
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Please navigate to Addons tab manually"), bgcolor="ORANGE")
                page.snack_bar.open = True
                page.update()

        return ft.Column([
            ft.Icon(ft.Icons.SMART_TOY_OUTLINED, size=60, color="grey"),
            ft.Text(i18n.get("ai_helper") or "AI Helper", size=28, weight=ft.FontWeight.BOLD),
            ft.Text(i18n.get("addon_missing_msg_ai") or "The AI Addon is not installed or failed to load.", color="orange", text_align=ft.TextAlign.CENTER),
            ft.Text(i18n.get("addon_install_hint") or "Install the addon to enable this feature.", size=12, color="grey", text_align=ft.TextAlign.CENTER),
            ft.Container(height=10),
            ft.ElevatedButton(
                i18n.get("btn_go_to_addons") or "Go to Addon Manager",
                icon=ft.Icons.EXTENSION,
                bgcolor="BLUE_700",
                color="WHITE",
                on_click=go_to_addons
            )
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)

    from switchcraft.utils.i18n import i18n
    chat_history = ft.ListView(expand=True, spacing=10, auto_scroll=True)
    input_field = ft.TextField(
        label=i18n.get("ai_ask_hint") or "Ask a question...",
        expand=True,
        border_radius=10,
        content_padding=15,
        border_color="BLUE_400",
        focused_border_color="BLUE_600",
        filled=True,
        bgcolor="GREY_900",
    )

    def add_message(sender, text, is_user=False, is_error=False):
        bg_color = "GREY_800" if is_user else "BLUE_900"
        text_color = "WHITE"
        align = ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START

        chat_history.controls.append(
            ft.Row([
                ft.Container(
                    content=ft.Column([
                        ft.Text(sender, weight=ft.FontWeight.BOLD, size=12, color=text_color),
                        ft.Text(text, selectable=True, color=text_color)
                    ]),
                    bgcolor=bg_color,
                    padding=15,
                    border_radius=ft.border_radius.only(
                        top_left=15, top_right=15,
                        bottom_left=15 if not is_user else 0,
                        bottom_right=15 if is_user else 0
                    ),
                    # constraints=ft.BoxConstraints(max_width=500), # Removed from init
                )
            ], alignment=align)
        )
        # Apply constraints manually if needed or wrap in a constrained container
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
            if page:
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
        ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.SMART_TOY, size=30, color="BLUE_400"),
                ft.Text(i18n.get("ai_helper") or "AI Helper", size=24, weight=ft.FontWeight.BOLD),
            ]),
            padding=10,
            bgcolor="SURFACE_VARIANT",
            border_radius=10,
        ),
        ft.Container(height=10),
        ft.Container(
            content=chat_history,
            expand=True,
            bgcolor="BLACK12",
            border=ft.border.all(1, "GREY_700"),
            border_radius=10,
            padding=15
        ),
        ft.Container(height=10),
        ft.Container(
            content=ft.Row([
                input_field,
                ft.IconButton(
                    ft.Icons.SEND,
                    on_click=send_message,
                    tooltip="Send",
                    icon_color="BLUE_400",
                    bgcolor="BLUE_900",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                )
            ], spacing=10),
            bgcolor="SURFACE_VARIANT",
            padding=10,
            border_radius=10,
            border=ft.border.all(1, "GREY_700"),
        )
    ], expand=True)
