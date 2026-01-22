import flet as ft
import threading
import logging

logger = logging.getLogger(__name__)


def ModernHelperView(page: ft.Page):
    """
    Builds the AI Helper UI view for the provided Flet page.

    Constructs and returns a Column containing the AI Helper interface: a header (title and subtitle), a chat history area, and an input row with send functionality. If the AI addon fails to initialize, returns a fallback view that prompts the user to install or navigate to the Addon Manager.

    Parameters:
        page (ft.Page): The Flet Page instance used for rendering, navigation, clipboard operations, and calling page.update().

    Returns:
        ft.Column: A Flet Column control representing the complete AI Helper UI (either the active chat interface or a fallback addon-install prompt).
    """
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
            """
            Navigate the application to the Addon Manager tab (tab index 9) or display a snackbar instructing the user to navigate there manually.

            Parameters:
                e: The UI event object from the trigger (click/submit). This parameter is accepted for handler compatibility and is not used.
            """
            if hasattr(page, 'switchcraft_app') and hasattr(page.switchcraft_app, 'goto_tab'):
                page.switchcraft_app.goto_tab(9)
            else:
                page.snack_bar = ft.SnackBar(ft.Text(i18n.get("please_navigate_manually") or "Please navigate to Addons tab manually"), bgcolor="ORANGE")
                page.snack_bar.open = True
                page.update()

        return ft.Column([
            ft.Icon(ft.Icons.SMART_TOY_OUTLINED, size=60, color="ON_SURFACE_VARIANT"),
            ft.Text(i18n.get("ai_helper") or "AI Helper", size=28, weight=ft.FontWeight.BOLD),
            ft.Text(i18n.get("addon_missing_msg_ai") or "The AI Addon is not installed or failed to load.", color="orange", text_align=ft.TextAlign.CENTER),
            ft.Text(i18n.get("addon_install_hint") or "Install the addon to enable this feature.", size=12, color="ON_SURFACE_VARIANT", text_align=ft.TextAlign.CENTER),
            ft.Container(height=10),
            ft.Button(
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
        """
        Add a chat message row to the UI and update the page.

        Renders the provided text as a message from `sender`, appends it to `chat_history`, and refreshes `page`. AI messages are rendered as Markdown (links open in the page), while user messages are rendered as plain selectable text. A copy button is included for each message; activating it attempts to copy the message text to the clipboard using multiple fallback methods and displays a transient success or failure snackbar.

        Parameters:
            sender (str): Label to display as the message sender (e.g., "AI" or a username).
            text (str): The message content to render.
            is_user (bool): If True, treat the message as sent by the user (affects alignment, styling, and rendering).
            is_error (bool): If True, render the message with error styling to indicate an error state.
        """
        if is_error:
            bg_color = "RED_900"
        else:
            bg_color = "GREY_800" if is_user else "BLUE_900"

        text_color = "WHITE"
        align = ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START

        # Message Content (Markdown for AI, Text for User)
        content = ft.Markdown(
            text,
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
            on_tap_link=lambda e: page.launch_url(e.data),
        ) if not is_user else ft.Text(text, selectable=True, color=text_color)

        # Copy button handler - capture text explicitly in closure
        # Store text in a variable that will be captured by the lambda
        message_text = text  # Explicit variable for closure

        def copy_handler(e):
            """
            Attempts to copy the captured `message_text` to the system clipboard and shows a localized success or failure snackbar.

            Tries `pyperclip` first; if unavailable or failing it falls back to the Windows `clip` command, then to `page.set_clipboard` if available. On success displays a green snackbar using the i18n key "copied_to_clipboard"; on failure displays a red snackbar using the i18n key "copy_failed".
            """
            success = False
            try:
                # Try pyperclip first (most reliable for desktop)
                import pyperclip
                pyperclip.copy(message_text)
                success = True
            except ImportError:
                # Fallback to Windows clip command
                try:
                    import subprocess
                    subprocess.run(['clip'], input=message_text.encode('utf-8'), check=True)
                    success = True
                except Exception:
                    pass
            except Exception as ex:
                logger.warning(f"pyperclip failed, trying Flet: {ex}")
                # Last resort: try Flet's clipboard
                try:
                    if hasattr(page, 'set_clipboard'):
                        page.set_clipboard(message_text)
                        success = True
                except Exception:
                    pass

            # Show feedback
            if success:
                from switchcraft.utils.i18n import i18n
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(i18n.get("copied_to_clipboard") or "Copied to clipboard!"),
                    duration=2000,
                    bgcolor="GREEN_700"
                )
            else:
                from switchcraft.utils.i18n import i18n
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(i18n.get("copy_failed") or "Failed to copy to clipboard!"),
                    duration=2000,
                    bgcolor="RED_700"
                )
            page.snack_bar.open = True
            page.update()

        chat_history.controls.append(
            ft.Row([
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(sender, weight=ft.FontWeight.BOLD, size=12, color=text_color),
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
                    width=min(page.width * 0.75, 700) if isinstance(page.width, (int, float)) else 600,
                    margin=ft.Margin(0, 5, 0, 5),
                )
            ], alignment=align)
        )
        page.update()

    def send_message(e):
        """
        Handle sending the current input as a user message, display a typing indicator, and asynchronously fetch and display the AI response.

        Clears the input field, appends the user's message to the chat, shows an "AI is typing..." indicator, and starts a background thread that calls the AI service to obtain a response. When the response arrives the typing indicator is removed and the AI's reply is appended; if an exception occurs, an error message from the AI is appended instead. The page is updated and the input field is refocused.

        Parameters:
            e: The click/submit event from the UI control that triggered sending (unused by the function).
        """
        user_msg = input_field.value
        if not user_msg:
            return

        input_field.value = ""
        add_message("You", user_msg, is_user=True)

        # Show typing indicator
        typing_indicator = ft.Text("AI is typing...", italic=True, color="ON_SURFACE_VARIANT")
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
            margin=ft.Margin(0, 0, 0, 0),
        ),
        ft.Container(height=15),
        ft.Container(
            content=chat_history,
            expand=True,
            bgcolor="SURFACE_CONTAINER_HIGHEST" if hasattr(getattr(ft, "colors", None), "SURFACE_CONTAINER_HIGHEST") else "BLACK12",
            border=ft.Border.all(1, "OUTLINE_VARIANT"),
            border_radius=12,
            padding=20
        ),
        ft.Container(height=15),
        ft.Container(
            content=ft.Row([
                input_field,
                ft.IconButton(
                    ft.Icons.SEND_ROUNDED,
                    on_click=send_message,
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
    ], expand=True, spacing=0)
