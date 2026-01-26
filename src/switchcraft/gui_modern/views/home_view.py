import flet as ft
import datetime
import random
from switchcraft.gui_modern.nav_constants import NavIndex
from switchcraft.utils.i18n import i18n
from switchcraft.services.intune_service import IntuneService
import threading

from switchcraft import IS_WEB, IS_DEMO

from switchcraft.gui_modern.utils.view_utils import ViewMixin

class ModernHomeView(ft.Container, ViewMixin):
    """Enhanced Modern Dashboard with Quick Actions and Recents."""

    def __init__(self, page: ft.Page, on_navigate=None):
        super().__init__()
        self.app_page = page
        self.on_navigate = on_navigate
        self.expand = True
        self.padding = 30
        self.news_container = ft.Column(spacing=10)
        self.content = self._build_content()

        # Start background news loading
        if not IS_WEB:
            threading.Thread(target=self._load_news, daemon=True).start()

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
        # Dynamic Greetings based on time of day with variations
        hour = datetime.datetime.now().hour

        # Determine time period and get all variations
        if hour < 5:
            # Very early morning (0-4)
            greeting_keys = [
                "greeting_early_morning_1", "greeting_early_morning_2",
                "greeting_early_morning_3", "greeting_early_morning_4"
            ]
            default_greetings = ["Good Night", "Still up?", "Late night?", "Working late?"]
        elif hour < 8:
            # Early morning (5-7)
            greeting_keys = [
                "greeting_early_1", "greeting_early_2",
                "greeting_early_3", "greeting_early_4", "greeting_early_5"
            ]
            default_greetings = ["Good morning, {name}", "Rise and shine, {name}!", "Early bird, {name}!", "Morning, {name}!", "Good start, {name}!"]
        elif hour < 12:
            # Morning (8-11)
            greeting_keys = [
                "greeting_morning_1", "greeting_morning_2",
                "greeting_morning_3", "greeting_morning_4", "greeting_morning_5", "greeting_morning_6"
            ]
            default_greetings = ["Good morning, {name}", "Morning, {name}!", "Have a great morning, {name}!", "Good day ahead, {name}!", "Hello {name}!", "Top of the morning, {name}!"]
        elif hour < 13:
            # Noon (12)
            greeting_keys = [
                "greeting_noon_1", "greeting_noon_2",
                "greeting_noon_3", "greeting_noon_4"
            ]
            default_greetings = ["Good noon, {name}", "Lunch time, {name}!", "Midday, {name}!", "Halfway there, {name}!"]
        elif hour < 15:
            # Early afternoon (13-14)
            greeting_keys = [
                "greeting_early_afternoon_1", "greeting_early_afternoon_2",
                "greeting_early_afternoon_3", "greeting_early_afternoon_4"
            ]
            default_greetings = ["Good afternoon, {name}", "Afternoon, {name}!", "Good day, {name}!", "Hello there, {name}!"]
        elif hour < 18:
            # Afternoon (15-17)
            greeting_keys = [
                "greeting_afternoon_1", "greeting_afternoon_2",
                "greeting_afternoon_3", "greeting_afternoon_4", "greeting_afternoon_5"
            ]
            default_greetings = ["Good afternoon, {name}", "Afternoon, {name}!", "Hope you're having a good day, {name}!", "Hello {name}!", "Afternoon vibes, {name}!"]
        elif hour < 21:
            # Evening (18-20)
            greeting_keys = [
                "greeting_evening_1", "greeting_evening_2",
                "greeting_evening_3", "greeting_evening_4", "greeting_evening_5"
            ]
            default_greetings = ["Good evening, {name}", "Evening, {name}!", "Good evening, {name}!", "Hello {name}!", "Evening time, {name}!"]
        else:
            # Late evening / Night (21-23)
            greeting_keys = [
                "greeting_night_1", "greeting_night_2",
                "greeting_night_3", "greeting_night_4"
            ]
            default_greetings = ["Good Night", "Evening!", "Late evening!", "Night!"]

        # Randomly select a variation
        # greeting_keys and default_greetings are always the same length (defined together above)
        selected_index = random.randint(0, len(greeting_keys) - 1)
        greeting_key = greeting_keys[selected_index]
        default_greeting = default_greetings[selected_index]

        # Use the placeholder logic if possible
        # We need to get the username first to pass it to i18n.get

        import os
        username = None

        # 1. Try to get username from web session (Server Auth)
        try:
            if hasattr(self.app_page, 'switchcraft_session') and self.app_page.switchcraft_session:
                session_user = self.app_page.switchcraft_session.get('username')
                if session_user:
                    username = session_user
        except Exception:
            pass

        # 2. Try to get display name from Windows (full name instead of login name)
        if not username:
            try:
                # Web Auth Check (Flet Auth)
                if self.app_page.auth and self.app_page.auth.user:
                     u = self.app_page.auth.user
                     val = None
                     # Could be dict or object depending on provider
                     if hasattr(u, "name"): val = u.name
                     elif hasattr(u, "get"): val = u.get("name")

                     if isinstance(val, str) and val:
                         username = val
            except Exception:
                 pass

        if not username:
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

        # 3. Fallback to environment variable or default
        if not username:
            username = os.getenv("USERNAME") or os.getenv("USER") or i18n.get("default_user") or "User"

        # If the environment/fallback returns "web_user" (usually in Pyodide), translate it
        if username == "web_user":
            username = i18n.get("demo_web_user" if IS_DEMO else "web_user")

        # Now get the greeting with the name
        greeting = i18n.get(greeting_key, name=username)
        # Handle fallback if the translation doesn't have the {name} placeholder yet or fails
        if greeting == greeting_key or greeting == default_greeting:
            if "{name}" in default_greeting:
                greeting = default_greeting.format(name=username)
            else:
                greeting = f"{default_greeting}, {username}"
        elif "{name}" not in greeting and username not in greeting:
            # If the translated string doesn't contain the name and it's not the key itself,
            # we should append the name to avoid "Hallo, User" issues if the key was just updated.
            # But we want to avoid double name if the key ALREADY had it.
            greeting = f"{greeting}, {username}"

        # Admin Privilege Check
        is_admin = False
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            pass

        privilege_text = i18n.get("running_as_admin" if is_admin else "running_as_user") or \
                        (f"Status: {'Administrator ✅' if is_admin else 'Standard User 👤'}")

        # Dynamic subtitle based on status
        subtitle = i18n.get("home_subtitle") or "Here is what's happening with your deployments."

        return ft.Column([
            # Header
            # Header
            ft.Row([
                ft.Column([
                    ft.Text(f"{greeting}", size=32, weight=ft.FontWeight.BOLD, color="PRIMARY"),
                    ft.Text(privilege_text, size=14, color="SECONDARY", weight=ft.FontWeight.W_500),
                    ft.Text(subtitle, size=14, color="SECONDARY"),
                ], expand=True, spacing=5),
                ft.Button(
                    content=ft.Row([
                        ft.Icon(ft.Icons.HELP_OUTLINE, color="WHITE"),
                        ft.Text(i18n.get("btn_help") or "Help & Docs", color="WHITE"),
                    ], spacing=10, tight=True),
                    on_click=lambda _: self._launch_url("https://faserf.github.io/SwitchCraft/"),
                    style=ft.ButtonStyle(
                        bgcolor="PRIMARY",
                        padding=15,
                        shape=ft.RoundedRectangleBorder(radius=10),
                    )
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START),

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
            self._build_recent_activity_section(),

            ft.Divider(height=20, color="TRANSPARENT"),

            # Intune News Section
            ft.Text(i18n.get("intune_news") or "Intune News", size=20, weight=ft.FontWeight.BOLD),
            self.news_container

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
                    color="ON_SURFACE_VARIANT"
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
                leading=ft.Icon(icon, color="ON_SURFACE_VARIANT"),
                title=ft.Text(entry.get("title", "Unknown")),
                subtitle=ft.Text(entry.get("timestamp", "")),
                dense=True
            ))

        items.append(
            ft.TextButton(
                content=ft.Text(i18n.get("view_full_history") or "View full history"),
                on_click=lambda e: self.on_navigate(NavIndex.HISTORY) if self.on_navigate else None
            )
        )

        return ft.Container(
            content=ft.Column(items, spacing=0),
            bgcolor="SURFACE_VARIANT",
            border_radius=10,
            padding=10
        )

    def _load_news(self):
        """Fetch and display Intune news in background."""
        # Initial loading state
        self.news_container.controls = [
            ft.Container(
                content=ft.Row([
                    ft.ProgressRing(width=20, height=20, stroke_width=2),
                    ft.Text(i18n.get("loading_news") or "Loading latest Intune news...", italic=True)
                ], spacing=10),
                padding=20,
                bgcolor="WHITE,0.05",
                border_radius=10
            )
        ]
        try:
            self.update()
        except Exception:
            pass

        try:
            service = IntuneService()
            news = service.get_intune_news()

            controls = []
            if not news:
                controls.append(ft.Text(i18n.get("no_news_available") or "No news available at the moment.", italic=True))
            else:
                for item in news[:5]: # Show top 5
                    controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(item["title"], weight=ft.FontWeight.BOLD, size=14, color="PRIMARY_LIGHT"),
                                    ft.Container(
                                        content=ft.Text(item["category"], size=10, color="WHITE"),
                                        bgcolor="PRIMARY",
                                        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                        border_radius=5
                                    )
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Text(item["description"], size=12, color="WHITE70", max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Row([
                                    ft.Text(item["week"], size=10, color="SECONDARY"),
                                    ft.TextButton(
                                        content=ft.Text(i18n.get("read_more") or "Read more", size=10),
                                        on_click=lambda _, url=item["link"]: self._launch_url(url)
                                    )
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                            ], spacing=5),
                            padding=15,
                            bgcolor="WHITE,0.05",
                            border_radius=10,
                            border=ft.Border.all(1, "WHITE,0.1")
                        )
                    )

            self.news_container.controls = controls
        except Exception as e:
            error_msg = str(e) or "Unknown error"
            self.news_container.controls = [
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color="ERROR"),
                        ft.Text(f"{i18n.get('news_error') or 'Could not load news'}: {error_msg}", color="ERROR", size=12)
                    ], spacing=10),
                    padding=20,
                    bgcolor="ERROR,0.1",
                    border_radius=10,
                    border=ft.Border.all(1, "ERROR,0.2")
                )
            ]

        try:
            self.update()
        except Exception:
            pass
