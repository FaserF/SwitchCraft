"""
Web Demo Entry Point for Flet Publish.

This file exists in the project root to serve as the flet publish entry point.
It imports and runs the modern Flet GUI.
"""
import sys
import os

# Add src to path so switchcraft package is importable
src_path = os.path.join(os.path.dirname(__file__), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import and run the modern main
import flet as ft
from switchcraft.gui_modern.app import ModernApp
from switchcraft.utils.i18n import i18n


def main(page: ft.Page):
    """Main entry point for web demo."""
    page.title = "SwitchCraft"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 0
    page.spacing = 0
    
    # Set favicon for web mode
    if page.web:
        page.favicon = "/switchcraft_logo.png"
    
    # Show loading screen
    loading_container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(ft.Icons.INSTALL_DESKTOP, size=80, color="BLUE_400"),
                ft.Text(i18n.get("app_title") or "SwitchCraft", size=32, weight=ft.FontWeight.BOLD),
                ft.Container(height=20),
                ft.ProgressRing(width=50, height=50, stroke_width=4, color="BLUE_400"),
                ft.Container(height=10),
                ft.Text(i18n.get("loading_switchcraft") or "Loading SwitchCraft...", size=18, color="GREY_400"),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        ),
        expand=True,
        alignment=ft.Alignment(0, 0),
        bgcolor="SURFACE",
    )
    
    page.add(loading_container)
    page.update()
    
    try:
        # Create and run the app
        app = ModernApp(page)
    except Exception as e:
        # Show error on failure
        page.clean()
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ERROR, color="RED_400", size=64),
                    ft.Text("Failed to load SwitchCraft", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(str(e), size=14, color="RED_300", selectable=True),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
                expand=True,
                alignment=ft.Alignment(0, 0),
            )
        )
        page.update()


if __name__ == "__main__":
    ft.app(target=main, assets_dir="src/switchcraft/assets")
