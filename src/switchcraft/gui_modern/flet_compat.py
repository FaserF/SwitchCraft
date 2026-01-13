# Flet compatibility module for Colors enum
# Flet 0.80+ uses ft.colors (lowercase) while older versions use ft.Colors (uppercase)
# This module provides a unified interface

import flet as ft

# Try to use the correct colors attribute based on Flet version
if hasattr(ft, 'colors') and hasattr(ft.colors, 'RED'):
    # Flet 0.80+ (lowercase colors)
    colors = ft.colors
elif hasattr(ft, 'Colors') and hasattr(ft.Colors, 'RED'):
    # Older Flet (uppercase Colors)
    colors = ft.Colors
else:
    # Fallback - create a simple namespace with common colors as strings
    class FallbackColors:
        RED = "red"
        GREEN = "green"
        BLUE = "blue"
        ORANGE = "orange"
        GREY = "grey"
        WHITE = "white"
        BLACK = "black"
        SURFACE_VARIANT = None
        GREY_500 = "grey"
        GREY_600 = "grey"
        GREY_700 = "grey"
        GREY_900 = "grey"
        BLUE_400 = "blue"
        BLUE_700 = "blue"
        GREEN_700 = "green"
        RED_700 = "red"
        RED_900 = "red"
        PURPLE_400 = "purple"
        BLACK26 = "black"
        BLUE_50 = "blue"
        BLUE_900 = "blue"
    colors = FallbackColors()
