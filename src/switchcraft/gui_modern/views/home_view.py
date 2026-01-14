import flet as ft
import datetime
from switchcraft.gui_modern.nav_constants import NavIndex
from switchcraft.utils.i18n import i18n

class ModernHomeView(ft.Container):
    """Enhanced Modern Dashboard with Quick Actions and Recents."""

    def __init__(self, page: ft.Page, on_navigate=None):
        super().__init__()
        self.app_page = page
        self.on_navigate = on_navigate
        self.expand = True
        self.padding = 30
        self.content = self._build_content()

    def _create_action_card(self, title, subtitle, icon, target_idx, color="BLUE"):
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, size=32, color=f"{color}_200"),
                ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color="WHITE"),
                ft.Text(subtitle, size=11, color="WHITE70", text_align=ft.TextAlign.START),
            ], alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.START),
            width=180,
            height=120,
            padding=15,
            bgcolor="WHITE,0.1",
            border_radius=10,
            border=ft.Border.all(1, "WHITE,0.1"),
            ink=True,
            on_click=lambda _: self.on_navigate(target_idx) if self.on_navigate else None,
            on_hover=lambda e: setattr(e.control, "bgcolor", "WHITE,0.15" if e.data == "true" else "WHITE,0.1") or e.control.update(),
        )

    def _build_content(self):
        # Dynamic Greetings based on time of day
        hour = datetime.datetime.now().hour
        if hour < 12:
            greeting_key = "greeting_morning"
            default_greeting = "Good Morning"
        elif hour < 18:
            greeting_key = "greeting_afternoon"
            default_greeting = "Good Afternoon"
        else:
            greeting_key = "greeting_evening"
            default_greeting = "Good Evening"

        greeting = i18n.get(greeting_key) or default_greeting

        # Try to get display name from Windows (full name instead of login name)
        import os
        username = None
        try:
            import ctypes
            GetUserNameExW = ctypes.windll.secur32.GetUserNameExW
            NameDisplay = 3  # EXTENDED_NAME_FORMAT NameDisplay
            size = ctypes.pointer(ctypes.c_ulong(0))
            GetUserNameExW(NameDisplay, None, size)
            nameBuffer = ctypes.create_unicode_buffer(size.contents.value)
            GetUserNameExW(NameDisplay, nameBuffer, size)
            if nameBuffer.value:
                username = nameBuffer.value
        except Exception:
            pass

        # Fallback to environment variable or default
        if not username:
            username = os.getenv("USERNAME") or os.getenv("USER") or i18n.get("default_user") or "User"

        # Dynamic subtitle based on status
        subtitle = i18n.get("home_subtitle") or "Here is what's happening with your deployments."

        return ft.Column([
            # Header
            ft.Text(f"{greeting}, {username}", size=32, weight=ft.FontWeight.BOLD, color="PRIMARY"),
            ft.Text(subtitle, size=14, color="SECONDARY"),

            ft.Divider(height=30, color="TRANSPARENT"),

            # Quick Actions Section
            ft.Text(i18n.get("quick_actions") or "Quick Actions", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([
                self._create_action_card(i18n.get("home_card_analyzer_title") or "Analyzer", i18n.get("home_card_analyzer_desc") or "Deep Scan Installers", ft.Icons.SEARCH, NavIndex.ANALYZER, "CYAN"),
                self._create_action_card(i18n.get("home_card_wizard_title") or "Wizard", i18n.get("home_card_wizard_desc") or "Packaging Wizard", ft.Icons.AUTO_FIX_HIGH, NavIndex.PACKAGING_WIZARD, "PURPLE"),
                self._create_action_card(i18n.get("home_card_winget_title") or "Winget", i18n.get("home_card_winget_desc") or "Browse Store", ft.Icons.SHOP_TWO, NavIndex.WINGET, "BLUE"),
            ], wrap=True, spacing=15),

            ft.Divider(height=20, color="TRANSPARENT"),

            # Recent Activity Section (Real data from history service)
            ft.Text(i18n.get("recent_activity") or "Recent Activity", size=20, weight=ft.FontWeight.BOLD),
            self._build_recent_activity_section()

        ], scroll=ft.ScrollMode.AUTO, expand=True)

    def _build_recent_activity_section(self):
        """Build the recent activity section with real history data."""
        # Try to get real history data
        try:
            from switchcraft.services.history_service import HistoryService
            history = HistoryService().get_recent(limit=3)
        except Exception:
            history = []

        if not history:
            return ft.Container(
                content=ft.Text(
                    i18n.get("no_recent_activity") or "No recent activity.",
                    italic=True,
                    color="GREY"
                ),
                bgcolor="SURFACE_VARIANT",
                border_radius=10,
                padding=20
            )

        items = []
        for entry in history:
            icon = ft.Icons.HISTORY
            if "upload" in entry.get("action", "").lower():
                icon = ft.Icons.CLOUD_UPLOAD
            elif "analysis" in entry.get("action", "").lower():
                icon = ft.Icons.SEARCH

            items.append(ft.ListTile(
                leading=ft.Icon(icon, color="GREY"),
                title=ft.Text(entry.get("title", "Unknown")),
                subtitle=ft.Text(entry.get("timestamp", "")),
                dense=True
            ))

        items.append(
            ft.TextButton(
                i18n.get("view_full_history") or "View full history",
                on_click=lambda e: self.on_navigate(NavIndex.HISTORY) if self.on_navigate else None
            )
        )

        return ft.Container(
            content=ft.Column(items, spacing=0),
            bgcolor="SURFACE_VARIANT",
            border_radius=10,
            padding=10
        )
