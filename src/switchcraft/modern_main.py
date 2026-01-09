import sys
from pathlib import Path

# Ensure src is in path for addons
src_path = str(Path(__file__).parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import flet as ft
from switchcraft.gui_modern.app import ModernApp
from switchcraft.utils.logging_handler import setup_session_logging

# Setup session logging
setup_session_logging()

def main(page: ft.Page):
    """Entry point for the Modern Flet GUI."""
    ModernApp(page)

if __name__ == "__main__":
    ft.app(target=main)
