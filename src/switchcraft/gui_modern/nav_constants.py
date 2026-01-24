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
    SETTINGS_UPDATES = 1      # Settings tab index 1
    SETTINGS_GRAPH = 2        # Settings tab index 2
    SETTINGS_HELP = 3         # Settings tab index 4 (Help & Resources)
    ADDON_MANAGER = 3         # Alias for SETTINGS_HELP

    # === TOOLS & APPS ===
    WINGET = 4                # Apps (Winget Search)
    ANALYZER = 5              # Installer Analyzer
    HELPER = 6                # AI Helper / Generator
    INTUNE = 7                # Intune Packager
    INTUNE_STORE = 8          # Intune Store View
    SCRIPTS = 9               # Script Upload
    MACOS = 10                # macOS Wizard
    HISTORY = 11              # History View

    # === PRIMARY SETTINGS ===
    SETTINGS = 12             # General Settings (tab index 0)

    # === WIZARDS & ADVANCED ===
    PACKAGING_WIZARD = 13     # Packaging Wizard
    DETECTION_TESTER = 14     # Detection Tester
    STACK_MANAGER = 15        # Stack Manager

    # === DASHBOARD & LIBRARY ===
    DASHBOARD = 16            # Dashboard View
    LIBRARY = 17              # Library View
    GROUP_MANAGER = 18        # Group Manager
    WINGET_CREATE = 19        # WingetCreate Manager
    EXCHANGE = 20             # Exchange Online View

    SETTINGS_POLICIES = 21    # Settings tab index 3 (Policies)
    SAP_WIZARD = 22           # SAP Management Wizard


# Mapping from NavIndex to sidebar category for reference
NAV_CATEGORIES = {
    "Dashboard": [NavIndex.HOME, NavIndex.DASHBOARD],
    "Apps & Devices": [
        NavIndex.INTUNE, NavIndex.INTUNE_STORE, NavIndex.WINGET,
        NavIndex.LIBRARY, NavIndex.GROUP_MANAGER, NavIndex.EXCHANGE, NavIndex.STACK_MANAGER
    ],
    "Tools": [
        NavIndex.ANALYZER, NavIndex.HELPER, NavIndex.SCRIPTS,
        NavIndex.MACOS, NavIndex.PACKAGING_WIZARD, NavIndex.DETECTION_TESTER,
        NavIndex.WINGET_CREATE, NavIndex.SAP_WIZARD
    ],
    "System": [
        NavIndex.SETTINGS, NavIndex.SETTINGS_UPDATES,
        NavIndex.SETTINGS_GRAPH, NavIndex.SETTINGS_POLICIES,
        NavIndex.HISTORY, NavIndex.SETTINGS_HELP
    ]
}
