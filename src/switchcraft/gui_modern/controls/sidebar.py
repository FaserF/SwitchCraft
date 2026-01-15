import flet as ft
from switchcraft.gui_modern.nav_constants import NavIndex
from switchcraft.utils.i18n import i18n

class HoverSidebar(ft.Stack):
    def __init__(self, app, destinations, on_navigate):
        """
        Initialize the HoverSidebar component, configure navigation categories, and build the sidebar and content area controls.
        
        Parameters:
            app: Application instance used by the widget (UI context).
            destinations (list): List of destination definitions available for navigation.
            on_navigate (callable): Callback invoked with a destination index when navigation occurs.
        """
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
            (ft.Icons.DASHBOARD, i18n.get("cat_dashboard") or "Dashboard", [NavIndex.HOME, NavIndex.DASHBOARD]), # Home, Dashboard
            (ft.Icons.APPS, i18n.get("cat_apps_devices") or "Apps & Devices", [NavIndex.INTUNE, NavIndex.INTUNE_STORE, NavIndex.WINGET, NavIndex.LIBRARY, NavIndex.GROUP_MANAGER, NavIndex.STACK_MANAGER]), # Intune, Store, Winget, Library, Groups, Stacks
            (ft.Icons.BUILD, i18n.get("cat_tools") or "Tools", [NavIndex.ANALYZER, NavIndex.HELPER, NavIndex.SCRIPTS, NavIndex.MACOS, NavIndex.PACKAGING_WIZARD, NavIndex.DETECTION_TESTER, NavIndex.ADDON_MANAGER, NavIndex.WINGET_CREATE]), # Analyze, Generate, Scripts, MacOS, Wizard, Tester, AddonMgr, WingetCreate
            (ft.Icons.SETTINGS, i18n.get("cat_system") or "System", [NavIndex.SETTINGS, NavIndex.SETTINGS_UPDATES, NavIndex.SETTINGS_GRAPH, NavIndex.HISTORY, NavIndex.SETTINGS_HELP]), # Settings, Updates, Graph, History, Help
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
            padding=ft.Padding(0, 20, 0, 0), # Top only
            border=ft.Border(right=ft.BorderSide(1, "OUTLINE_VARIANT"))
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