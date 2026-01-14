import flet as ft

class HoverSidebar(ft.Stack):
    def __init__(self, app, destinations, on_navigate):
        super().__init__()
        self.app = app
        self.all_destinations = destinations
        self.on_navigate = on_navigate
        self.expand = True

        # Determine current selection
        self.selected_index = 0
        self.selected_category_index = 0 # Track which category is active

        # Categories definition
        # (Icon, Label, [Destination Indices])
        self.categories = [
            (ft.Icons.SPACE_DASHBOARD_OUTLINED, "General", [0, 13, 8]),
            (ft.Icons.BUILD_OUTLINED, "Tools", [1, 2, 3, 11]),
            (ft.Icons.CATEGORY_OUTLINED, "Management", [4, 10, 12, 7, 15, 14, 6, 5]),
            (ft.Icons.SETTINGS_OUTLINED, "Settings", [9, 17, 18, 19]),
        ]

        self.sidebar_column = ft.Column(
             width=60,
             spacing=10,
             controls=[],
             horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        self.sidebar_container = ft.Container(
            width=70,
            bgcolor="SURFACE",
            content=self.sidebar_column,
            padding=ft.padding.only(top=20),
            border=ft.border.only(right=ft.BorderSide(1, "OUTLINE_VARIANT"))
        )

        self._build_sidebar_items()

        self.content_area = ft.Container(expand=True)

        self.controls = [
            ft.Row([
                self.sidebar_container,
                self.content_area
            ], expand=True, spacing=0)
        ]

    def set_content(self, content):
        self.content_area.content = content

    def set_selected_index(self, index):
        self.selected_index = index

        # Determine category based on index
        # We use a special offset (100+) for category views themselves
        if index >= 100:
            self.selected_category_index = index - 100
        else:
            # It's a tool index, find which category it belongs to
            for i, cat in enumerate(self.categories):
                if index in cat[2]:
                    self.selected_category_index = i
                    break

        self._update_sidebar_visuals()

    def _build_sidebar_items(self):
        self.sidebar_column.controls.clear()

        for i, (icon, label, dest_indices) in enumerate(self.categories):
            is_selected = (i == self.selected_category_index)

            # Button for category
            btn = ft.Container(
                content=ft.Column([
                    ft.Icon(icon, color="PRIMARY" if is_selected else "ON_SURFACE", size=24),
                    # Compact: No Text
                ], spacing=0, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=60,
                height=60,
                border_radius=5,
                bgcolor="SECONDARY_CONTAINER" if is_selected else None,
                ink=True,
                tooltip=label, # Add tooltip since text is hidden
                on_click=lambda e, idx=i: self._on_category_click(idx),
                padding=5,
                alignment=ft.Alignment(0, 0)
            )
            self.sidebar_column.controls.append(btn)

        # Add Version at bottom provided we use expand on a spacer
        self.sidebar_column.controls.insert(0, ft.Container(height=10)) # Top spacer

    def _update_sidebar_visuals(self):
        self._build_sidebar_items()
        try:
            if self.page:
                self.sidebar_column.update()
        except Exception:
            pass

    def _on_category_click(self, category_index):
        # Navigate to Category View (Offset 100)
        self.on_navigate(100 + category_index)
