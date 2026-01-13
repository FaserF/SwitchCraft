import flet as ft
from switchcraft.utils.i18n import i18n

class ModernHomeView(ft.Container):
    """Enhanced Modern Home View with Quick Actions."""

    def __init__(self, page: ft.Page, on_navigate=None):
        super().__init__()
        self.app_page = page
        self.on_navigate = on_navigate
        self.expand = True
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.scroll = ft.ScrollMode.AUTO
        self.content = self._build_content()

    def _create_card(self, title, subtitle, icon, target_idx):
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, size=40, color=ft.Colors.BLUE_200),
                ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Text(subtitle, size=12, color=ft.Colors.WHITE70, text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton("Open",
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.WHITE12,
                    on_click=lambda _: on_navigate(target_idx) if on_navigate else None
                )
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=220,
            height=250,
            padding=20,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            border_radius=15,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
            blur=ft.Blur(10, ft.BlurTileMode.MIRROR),
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
                offset=ft.Offset(0, 5),
            ),
            animate_scale=ft.Animation(300, ft.AnimationCurve.EASE_OUT_BACK),
            on_hover=lambda e: setattr(e.control, "scale", 1.05 if e.data == "true" else 1.0) or e.control.update(),
        )

    def _build_content(self):
        create_card = self._create_card

        return ft.Column([
            ft.Container(
            content=ft.Column([
                ft.Text(i18n.get("welcome_title") or "SwitchCraft Modern", size=48, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER),
                ft.Text(i18n.get("welcome_subtitle") or "Your All-in-One Utility for App Deployment & Analysis",
                        size=18, italic=True, color=ft.Colors.BLUE_200, text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.Alignment(0, 0)
        ),

        ft.Row([
            create_card(i18n.get("home_card_analyzer_title") or "Analyzer", i18n.get("home_card_analyzer_desc") or "Deep Scan Installers", ft.Icons.SEARCH, 1),
            create_card(i18n.get("home_card_ai_title") or "AI Helper", i18n.get("home_card_ai_desc") or "AI Powered Support", ft.Icons.SMART_TOY, 2),
            create_card(i18n.get("home_card_winget_title") or "Winget", i18n.get("home_card_winget_desc") or "Browse App Store", ft.Icons.SHOP_TWO, 3),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=30),

        ft.Container(height=40),

        ft.Row([
            create_card(
                i18n.get("home_card_intune_title") or "Intune",
                i18n.get("home_card_intune_desc") or "Prep for Deployment",
                ft.Icons.CLOUD_UPLOAD, 4
            ),
            create_card("Dashboard", "Your Statistics", ft.Icons.DASHBOARD, 11),
            create_card("Stacks", "Batch Deployments", ft.Icons.LAYERS, 10),
            create_card("Live Check", "Test Detection Rules", ft.Icons.RULE, 9),
            create_card("Wizard", "End-to-End Packaging", ft.Icons.AUTO_FIX_HIGH, 8),  # Idx 8 for Wizard
            create_card(
                i18n.get("home_card_settings_title") or "Settings",
                i18n.get("home_card_settings_desc") or "Configure App",
                ft.Icons.SETTINGS, 7
            ),  # Fixed Settings Index
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=30),

    ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO)
