import flet as ft
from switchcraft.utils.i18n import i18n

DESCRIPTION_MAP = {
    "Home": "desc_home",
    "Startseite": "desc_home",
    "Dashboard": "desc_dashboard",
    "Apps & Devices": "desc_winget", # Maps to 'Apps (Winget)' or similar
    "Apps (Winget)": "desc_winget",
    "Winget Store": "desc_winget",
    "Analyzer": "desc_analyzer",
    "Analyse": "desc_analyzer",
    "AI Helper": "desc_ai",
    "KI Helfer": "desc_ai",
    "Intune Utility": "desc_intune",
    "Intune": "desc_intune",
    "Intune Store": "desc_intune_store",
    "Scripts": "desc_scripts",
    "Skripte": "desc_scripts",
    "macOS Utility": "desc_macos",
    "History": "desc_history",
    "Verlauf": "desc_history",
    "Settings": "desc_settings",
    "Einstellungen": "desc_settings",
    "Update Settings": "desc_update_settings",
    "Update Einstellungen": "desc_update_settings",
    "Deployment Automation": "desc_automation",
    "Verteilungs-Automatisierung": "desc_automation",
    "Generate (Wizard)": "desc_wizard",
    "Generieren (Wizard)": "desc_wizard",
    "Detection Tester": "desc_tester",
    "Stack Manager": "desc_stacks",
    "Library": "desc_library",
    "Group Manager": "desc_groups",
    "Gruppen-Manager": "desc_groups",
    "Winget Creator": "desc_wingetcreate",
    "Help & Resources": "desc_help",
    "Hilfe & Ressourcen": "desc_help"
}

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

        # Determine description
        key = DESCRIPTION_MAP.get(label, None)
        if key:
            desc_text = i18n.get(key)
            # If the key exists but returns None or empty, fall back to click_to_open
            if not desc_text:
                desc_text = i18n.get("click_to_open") or "Click to open"
        else:
            # No mapping found for this label, use fallback
            desc_text = i18n.get("click_to_open") or "Click to open"

        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Icon(icon, size=40, color="PRIMARY"),
                    alignment=ft.alignment.center,
                    height=50,
                ),
                ft.Text(label, size=16, weight=ft.FontWeight.BOLD, color="ON_SURFACE", text_align=ft.TextAlign.CENTER),
                ft.Text(
                    desc_text,
                    size=13,
                    color="OUTLINE",
                    text_align=ft.TextAlign.CENTER,
                    no_wrap=False,
                    max_lines=3,
                    overflow=ft.TextOverflow.ELLIPSIS
                )
            ], alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            width=220,  # Slightly wider for text
            height=200, # Fixed height
            bgcolor="SURFACE_VARIANT",
            border_radius=15,
            padding=ft.Padding(20, 20, 20, 20),
            ink=True,
            on_click=lambda e: self.on_navigate(idx),
            border=ft.Border.all(1, "OUTLINE_VARIANT"),
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_hover=lambda e: setattr(e.control, "scale", 1.05 if e.data == "true" else 1.0) or e.control.update()
        )
