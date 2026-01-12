import flet as ft
from switchcraft.utils.i18n import i18n

def ModernHomeView(page: ft.Page, on_navigate=None):
    """Enhanced Modern Home View with Quick Actions."""

    def create_card(title, subtitle, icon, target_idx):
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, size=40, color=ft.Colors.BLUE_400),
                ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
                ft.Text(subtitle, size=12, color=ft.Colors.GREY_400, text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton("Open", on_click=lambda _: on_navigate(target_idx) if on_navigate else None)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=220,
            height=250,
            padding=20,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST if hasattr(ft.Colors, "SURFACE_CONTAINER_HIGHEST") else ft.Colors.GREY_900,
            border_radius=15,
            border=ft.Border.all(1, ft.Colors.BLUE_700),
            animate_scale=ft.Animation(300, ft.AnimationCurve.DECELERATE),
            on_hover=lambda e: setattr(e.control, "scale", 1.05 if e.data == "true" else 1.0) or e.control.update(),
        )

    return ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text(i18n.get("welcome_title") or "SwitchCraft Modern", size=48, weight=ft.FontWeight.BOLD),
                ft.Text(i18n.get("welcome_subtitle") or "Your All-in-One Utility for App Deployment & Analysis", size=18, italic=True, color=ft.Colors.BLUE_200),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            margin=ft.margin.only(bottom=40, top=20)
        ),

        ft.Row([
            create_card(i18n.get("home_card_analyzer_title") or "Analyzer", i18n.get("home_card_analyzer_desc") or "Deep Scan Installers", ft.Icons.SEARCH, 1),
            create_card(i18n.get("home_card_ai_title") or "AI Helper", i18n.get("home_card_ai_desc") or "AI Powered Support", ft.Icons.SMART_TOY, 2),
            create_card(i18n.get("home_card_winget_title") or "Winget", i18n.get("home_card_winget_desc") or "Browse App Store", ft.Icons.SHOP_TWO, 3),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=30),

        ft.Container(height=40),

        ft.Row([
            create_card(i18n.get("home_card_intune_title") or "Intune", i18n.get("home_card_intune_desc") or "Prep for Deployment", ft.Icons.CLOUD_UPLOAD, 4),
            create_card(i18n.get("home_card_settings_title") or "Settings", i18n.get("home_card_settings_desc") or "Configure App", ft.Icons.SETTINGS, 6),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=30),

    ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO)
