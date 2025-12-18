import logging
from switchcraft.services.addon_service import AddonService

logger = logging.getLogger(__name__)

# Try to import the real analyzer from the addon
_real_module = AddonService.import_addon_module("advanced", "analyzers.universal")

if _real_module:
    UniversalAnalyzer = _real_module.UniversalAnalyzer
else:
    class UniversalAnalyzer:
        """
        Stub UniversalAnalyzer when the Addon is not installed.
        """
        def __init__(self):
            pass

        def check_wrapper(self, path):
            return None

        def brute_force_help(self, path):
            return {"detected_type": None, "suggested_switches": [], "output": "Advanced Feature (Addon) Required."}

        def detect_silent_disabled(self, path, output=""):
            return None

        def extract_and_analyze_nested(self, path, depth=1, max_depth=2, progress_callback=None):
            """Stub - returns None when addon not installed."""
            return None

        def cleanup_temp_dir(self, path):
            pass
