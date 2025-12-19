import flet as ft
from switchcraft.utils.i18n import i18n
from switchcraft import __version__

class ModernApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.clean() # Remove splash
        self.setup_page()
        self.build_ui()

    def setup_page(self):
        self.page.title = f"SwitchCraft v{__version__}"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0
        self.page.window_min_width = 800
        self.page.window_min_height = 600
        # self.page.window_title_bar_hidden = True # Custom title bar in future?
        # self.page.window_frameless = False

    def build_ui(self):
        # Sidebar
        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME,
                    label="Home"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ANALYTICS_OUTLINED,
                    selected_icon=ft.Icons.ANALYTICS,
                    label="Analyzer"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SHOP_TWO_OUTLINED,
                    selected_icon=ft.Icons.SHOP_TWO,
                    label="Winget"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.CLOUD_UPLOAD_OUTLINED,
                    selected_icon=ft.Icons.CLOUD_UPLOAD,
                    label="Intune"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="Settings"
                ),
            ],
            on_change=self.nav_change,
        )


        # Content Area
        self.content_area = ft.Column(expand=True, controls=[
            ft.Text("Welcome to Modern SwitchCraft", size=30, weight=ft.FontWeight.BOLD),
            ft.Text("Select a tool from the sidebar to get started."),
        ])

        # Layout
        self.body = ft.Row(
            controls=[
                self.rail,
                ft.VerticalDivider(width=1),
                self.content_area,
            ],
            expand=True,
        )

        self.page.add(self.body)

    def nav_change(self, e):
        idx = e.control.selected_index
        self.content_area.controls.clear()

        if idx == 0:
            self.content_area.controls.append(ft.Text("Home", size=30))
        elif idx == 1:
            self.content_area.controls.append(ft.Text("Analyzer (Coming Soon)", size=30))
        elif idx == 2:
            self.content_area.controls.append(ft.Text("Winget (Coming Soon)", size=30))
        elif idx == 3:
            self.content_area.controls.append(ft.Text("Intune (Coming Soon)", size=30))
        elif idx == 4:
             self.content_area.controls.append(ft.Text("Settings (Coming Soon)", size=30))

        self.page.update()

# Adapter for flet.app target
def main(page: ft.Page):
    # Initial Splash
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    splash_text = ft.Text("SwitchCraft", size=40, weight=ft.FontWeight.BOLD)
    splash_progress = ft.ProgressBar(width=400, color="blue")

    splash_container = ft.Column(
        [
            splash_text,
            ft.Text("Starting modern experience...", size=16, color="gray"),
            ft.Container(height=20),
            splash_progress
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    page.add(splash_container)
    page.update()

    # Artificial delay to ensure splash is visible for at least 800ms
    # since initialization might be near-instant on fast machines
    import time
    time.sleep(0.8)

    # Initialize the app
    # ModernApp.__init__ calls page.clean()
    app = ModernApp(page)

# Allow direct run
if __name__ == "__main__":
    ft.app(target=main)
