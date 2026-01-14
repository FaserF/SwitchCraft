"""
Navigation constants for SwitchCraft GUI.

This file is the SINGLE SOURCE OF TRUTH for all navigation view indices.
Import these constants instead of using magic numbers.

Usage:
    from switchcraft.gui_modern.nav_constants import NavIndex
    self.page.switchcraft_app.goto_tab(NavIndex.SETTINGS)
"""


class NavIndex:
    """Central registry of all navigation view indices."""

    # === MAIN VIEWS ===
    HOME = 0
    ADDON_MANAGER = 1

    # === SETTINGS SUB-VIEWS (via SettingsView tabs) ===
    SETTINGS_UPDATES = 2      # Settings tab index 1
    SETTINGS_GRAPH = 3        # Settings tab index 2
    SETTINGS_HELP = 4         # Settings tab index 3

    # === TOOLS & APPS ===
    WINGET = 5                # Apps (Winget Search)
    ANALYZER = 6              # Installer Analyzer
    HELPER = 7                # AI Helper / Generator
    INTUNE = 8                # Intune Packager
    INTUNE_STORE = 9          # Intune Store View
    SCRIPTS = 10              # Script Upload
    MACOS = 11                # macOS Wizard
    HISTORY = 12              # History View

    # === PRIMARY SETTINGS ===
    SETTINGS = 13             # General Settings (tab index 0)

    # === WIZARDS & ADVANCED ===
    PACKAGING_WIZARD = 14     # Packaging Wizard
    DETECTION_TESTER = 15     # Detection Tester
    STACK_MANAGER = 16        # Stack Manager

    # === DASHBOARD & LIBRARY ===
    DASHBOARD = 17            # Dashboard View
    LIBRARY = 18              # Library View
    GROUP_MANAGER = 19        # Group Manager


# Mapping from NavIndex to sidebar category for reference
NAV_CATEGORIES = {
    "Dashboard": [NavIndex.HOME, NavIndex.DASHBOARD],
    "Apps & Devices": [
        NavIndex.INTUNE, NavIndex.INTUNE_STORE, NavIndex.WINGET,
        NavIndex.LIBRARY, NavIndex.GROUP_MANAGER, NavIndex.STACK_MANAGER
    ],
    "Tools": [
        NavIndex.ANALYZER, NavIndex.HELPER, NavIndex.SCRIPTS,
        NavIndex.MACOS, NavIndex.PACKAGING_WIZARD, NavIndex.DETECTION_TESTER,
        NavIndex.ADDON_MANAGER
    ],
    "System": [
        NavIndex.SETTINGS, NavIndex.SETTINGS_UPDATES,
        NavIndex.SETTINGS_GRAPH, NavIndex.HISTORY, NavIndex.SETTINGS_HELP
    ]
}
