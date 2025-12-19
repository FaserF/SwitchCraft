import flet as ft
from switchcraft.gui_modern.app import ModernApp

def main(page: ft.Page):
    """Entry point for the Modern Flet GUI."""
    ModernApp(page)

if __name__ == "__main__":
    ft.app(target=main)
