import logging
import flet as ft
import traceback
logger = logging.getLogger(__name__)

def _create_broken_view(name, exc):
    """Factory to create a placeholder view for failed imports."""
    tb = traceback.format_exc()
    class BrokenView(ft.Column):
        def __init__(self, page: ft.Page):
            super().__init__(expand=True)
            self.controls = [
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color="red", size=48),
                        ft.Text(f"Failed to load {name}", size=20, weight=ft.FontWeight.BOLD, color="red"),
                        ft.Container(
                            content=ft.Column([
                                ft.Text(str(exc), color="white", weight=ft.FontWeight.BOLD),
                                ft.Text(tb, font_family="Consolas", size=10, color="grey"),
                            ], scroll=ft.ScrollMode.AUTO),
                            bgcolor="black", padding=10, border_radius=5, expand=True
                        )
                    ]),
                    padding=20, alignment=ft.alignment.center, expand=True
                )
            ]
    return BrokenView

# Safe Imports
try:
    from .home_view import ModernHomeView
except Exception as e:
    logger.error(f"Failed to import ModernHomeView: {e}")
    ModernHomeView = _create_broken_view("ModernHomeView", e)

try:
    from .analyzer_view import ModernAnalyzerView
except Exception as e:
    logger.error(f"Failed to import ModernAnalyzerView: {e}")
    ModernAnalyzerView = _create_broken_view("ModernAnalyzerView", e)

try:
    from .packaging_wizard_view import PackagingWizardView
except Exception:
    # Try correct spelling if typo existed? No, user report says 'packaging_wizard_view'.
    try:
        from .packaging_wizard_view import PackagingWizardView
    except Exception as e2:
        logger.error(f"Failed to import PackagingWizardView: {e2}")
        PackagingWizardView = _create_broken_view("PackagingWizardView", e2)

try:
    from .winget_view import ModernWingetView
except Exception as e:
    logger.error(f"Failed to import ModernWingetView: {e}")
    ModernWingetView = _create_broken_view("ModernWingetView", e)

try:
    from .intune_view import ModernIntuneView
except Exception as e:
    logger.error(f"Failed to import ModernIntuneView: {e}")
    ModernIntuneView = _create_broken_view("ModernIntuneView", e)

try:
    from .intune_store_view import ModernIntuneStoreView
except Exception as e:
    logger.error(f"Failed to import ModernIntuneStoreView: {e}")
    ModernIntuneStoreView = _create_broken_view("ModernIntuneStoreView", e)

try:
    from .history_view import ModernHistoryView
except Exception as e:
    logger.error(f"Failed to import ModernHistoryView: {e}")
    ModernHistoryView = _create_broken_view("ModernHistoryView", e)

try:
    from .settings_view import ModernSettingsView
except Exception as e:
    logger.error(f"Failed to import ModernSettingsView: {e}")
    ModernSettingsView = _create_broken_view("ModernSettingsView", e)

try:
    from .helper_view import ModernHelperView
except Exception as e:
    logger.error(f"Failed to import ModernHelperView: {e}")
    ModernHelperView = _create_broken_view("ModernHelperView", e)

try:
    from .detection_tester_view import DetectionTesterView
except Exception as e:
    logger.error(f"Failed to import DetectionTesterView: {e}")
    DetectionTesterView = _create_broken_view("DetectionTesterView", e)

try:
    from .stack_manager_view import StackManagerView
except Exception as e:
    logger.error(f"Failed to import StackManagerView: {e}")
    StackManagerView = _create_broken_view("StackManagerView", e)

try:
    from .dashboard_view import DashboardView
except Exception as e:
    logger.error(f"Failed to import DashboardView: {e}")
    DashboardView = _create_broken_view("DashboardView", e)

try:
    from .library_view import LibraryView
except Exception as e:
    logger.error(f"Failed to import LibraryView: {e}")
    LibraryView = _create_broken_view("LibraryView", e)

try:
    from .script_upload_view import ScriptUploadView
except Exception as e:
    # Handle cases where this view might not exist in all branches yet
    logger.error(f"Failed to import ScriptUploadView: {e}")
    ScriptUploadView = _create_broken_view("ScriptUploadView", e)
try:
    from .macos_wizard_view import MacOSWizardView
except Exception as e:
    logger.error(f"Failed to import MacOSWizardView: {e}")
    MacOSWizardView = _create_broken_view("MacOSWizardView", e)

try:
    from .group_manager_view import GroupManagerView
except Exception as e:
    logger.error(f"Failed to import GroupManagerView: {e}")
    GroupManagerView = _create_broken_view("GroupManagerView", e)
