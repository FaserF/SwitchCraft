import flet as ft
import datetime

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
        # Greetings
        hour = datetime.datetime.now().hour
        greeting = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 18 else "Good Evening"

        return ft.Column([
            # Header
            ft.Text(f"{greeting}, User", size=32, weight=ft.FontWeight.BOLD, color="PRIMARY"),
            ft.Text("Here is what's happening with your deployments.", size=14, color="SECONDARY"),

            ft.Divider(height=30, color="TRANSPARENT"),

            # Quick Actions Section
            ft.Text("Quick Actions", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([
                self._create_action_card("Analyzer", "Deep Scan Installers", ft.Icons.SEARCH, 2, "CYAN"),
                self._create_action_card("Wizard", "Packaging Wizard", ft.Icons.AUTO_FIX_HIGH, 10, "PURPLE"),
                self._create_action_card("Winget", "Browse Store", ft.Icons.SHOP_TWO, 1, "BLUE"),
            ], wrap=True, spacing=15),

            ft.Divider(height=20, color="TRANSPARENT"),

            # Recent Activity Section (Mockup for now)
            ft.Text("Recent Activity", size=20, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Column([
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.HISTORY, color="GREY"),
                        title=ft.Text("Analysis: setup_v2.exe"),
                        subtitle=ft.Text("2 hours ago • No issues found"),
                        dense=True
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.CLOUD_UPLOAD, color="GREY"),
                        title=ft.Text("Intune Upload: Firefox 120"),
                        subtitle=ft.Text("Yesterday • Success"),
                        dense=True
                    ),
                    ft.Text("View full history", size=12, color="BLUE", italic=True)
                ], spacing=0),
                bgcolor="SURFACE_VARIANT",
                border_radius=10,
                padding=10
            )

        ], scroll=ft.ScrollMode.AUTO, expand=True)
