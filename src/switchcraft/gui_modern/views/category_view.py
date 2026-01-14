import flet as ft

class CategoryView(ft.Container):
    def __init__(self, page: ft.Page, category_name: str, items: list, on_navigate, app_destinations):
        super().__init__()
        self.app_page = page
        self.category_name = category_name
        self.items = items # List of indices
        self.on_navigate = on_navigate
        self.app_destinations = app_destinations
        self.expand = True
        self.padding = 30
        self.content = self._build_content()

    def _build_content(self):
        cards = []
        for idx in self.items:
            if idx < len(self.app_destinations):
                dest = self.app_destinations[idx]
                cards.append(self._create_card(dest, idx))

        return ft.Column([
            ft.Text(self.category_name, size=32, weight=ft.FontWeight.BOLD, color="PRIMARY"),
            ft.Divider(height=20, color="TRANSPARENT"),
            ft.Row(
                controls=cards,
                wrap=True,
                spacing=20,
                run_spacing=20,
                alignment=ft.MainAxisAlignment.START,
            )
        ], scroll=ft.ScrollMode.AUTO, expand=True)

    def _create_card(self, dest, idx):
        # dest is NavigationRailDestination
        icon = dest.icon
        label = dest.label

        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, size=40, color="PRIMARY"),
                ft.Text(label, size=16, weight=ft.FontWeight.BOLD, color="ON_SURFACE"),
                ft.Text("Click to open", size=12, color="OUTLINE")
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=200,
            height=200,
            bgcolor="SURFACE_VARIANT",
            border_radius=15,
            padding=20,
            ink=True,
            on_click=lambda e: self.on_navigate(idx),
            border=ft.border.all(1, "OUTLINE_VARIANT"),
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_hover=lambda e: setattr(e.control, "scale", 1.05 if e.data == "true" else 1.0) or e.control.update()
        )
