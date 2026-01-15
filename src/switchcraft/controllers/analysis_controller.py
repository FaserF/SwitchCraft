from dataclasses import dataclass
from typing import Optional, Dict, Callable
from pathlib import Path
import time
import logging

from switchcraft.analyzers.msi import MsiAnalyzer
from switchcraft.analyzers.exe import ExeAnalyzer
from switchcraft.analyzers.macos import MacOSAnalyzer
from switchcraft.analyzers.universal import UniversalAnalyzer
from switchcraft.services.community_db_service import CommunityDBService
from switchcraft.models import InstallerInfo
from switchcraft.utils.config import SwitchCraftConfig

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    info: InstallerInfo
    winget_url: Optional[str] = None
    brute_force_data: Optional[str] = None
    nested_data: Optional[Dict] = None
    silent_disabled_info: Optional[Dict] = None
    community_match: bool = False
    error: Optional[str] = None


class AnalysisController:
    """
    Shared controller for handling the analysis workflow.
    Used by both Classic (Tkinter) and Modern (Flet) UIs.
    """

    def __init__(self, ai_service=None):
        self.ai_service = ai_service
        self.community_db = CommunityDBService()

    def analyze_file(
        self, file_path_str: str, progress_callback: Callable[[float, str, Optional[float]], None] = None
    ) -> AnalysisResult:
        """
        Runs the full analysis pipeline on the given file.

        Args:
            file_path_str: Path to the installer file.
            progress_callback: Optional callback (percent [0.0-1.0], message, eta_seconds).

        Returns:
            AnalysisResult object containing all findings.
        """
        path = Path(file_path_str)
        if not path.exists():
            return AnalysisResult(info=None, error="File not found")

        # Helper to report progress safely
        def report(pct: float, msg: str, eta: float = None):
            if progress_callback:
                progress_callback(pct, msg, eta)

        try:
            start_time = time.time()
            report(0.1, f"Analyzing {path.name}...")

            analyzers = [MsiAnalyzer(), ExeAnalyzer(), MacOSAnalyzer()]
            info = None
            total_analyzers = len(analyzers)

            # Phase 1: Standard Analyzers
            for idx, analyzer in enumerate(analyzers):
                report(0.1 + (0.3 * (idx / total_analyzers)), f"Running {analyzer.__class__.__name__}...")
                if analyzer.can_analyze(path):
                    try:
                        info = analyzer.analyze(path)
                        break
                    except Exception as e:
                        logger.error(f"Analysis failed for {analyzer.__class__.__name__}: {e}")

            # Phase 2: Universal / Brute Force
            brute_force_data = None
            nested_data = None
            silent_disabled = None
            uni = UniversalAnalyzer()
            wrapper = uni.check_wrapper(path)

            if not info or info.installer_type == "Unknown" or "Unknown" in (info.installer_type or "") or wrapper:
                logger.info("Starting Universal Analysis...")
                report(0.5, "Running Universal Analysis...")

                if not info or "Unknown" in (info.installer_type or ""):
                    report(0.6, "Attempting Brute Force Analysis...")
                    bf_results = uni.brute_force_help(path)

                    if bf_results.get("detected_type"):
                        if not info:
                            info = InstallerInfo(file_path=str(path), installer_type=bf_results["detected_type"])
                        else:
                            info.installer_type = bf_results["detected_type"]

                        info.install_switches = bf_results["suggested_switches"]
                        if "MSI" in bf_results["detected_type"]:
                            info.uninstall_switches = ["/x", "{ProductCode}"]

                    brute_force_data = bf_results.get("output", "")
                    silent_disabled = uni.detect_silent_disabled(path, brute_force_data)

                if wrapper:
                    if not info:
                        info = InstallerInfo(file_path=str(path), installer_type="Wrapper")
                    info.installer_type += f" ({wrapper})"

            if not info:
                info = InstallerInfo(file_path=str(path), installer_type="Unknown")

            # Phase 3: Nested Extraction
            if not info.install_switches and path.suffix.lower() == '.exe':
                report(0.5, "Extracting ecosystem for nested analysis... (This may take a while)", eta=15)

                # Callback adapter for nested extraction
                def nested_progress_handler(pct, message, _=None):
                    global_pct = 0.5 + (pct / 100 * 0.4)
                    elapsed = time.time() - start_time
                    eta = 0
                    if global_pct > 0.1:
                        total_est = elapsed / global_pct
                        eta = max(0, total_est - elapsed)
                    report(global_pct, message, eta)

                nested_data = uni.extract_and_analyze_nested(path, progress_callback=nested_progress_handler)
                report(0.9, "Deep Analysis Complete")

            community_match = False
            # Phase 3.5: Community DB Lookup (Enhancement)
            report(0.9, "Checking Community DB...")
            try:
                # Use cached service instance
                db_switches = self.community_db.get_switches_by_hash(path)
                if not db_switches:
                    # Fallback to name
                    db_switches = self.community_db.get_switches_by_name(path.name)

                if db_switches:
                    if not info.install_switches:
                        info.install_switches = db_switches
                        community_match = True
                    else:
                        # Log if we found alternatives but ignored them because analyzer succeeded
                        logger.info(f"Community DB found alternative switches: {db_switches}, but using analyzer result: {info.install_switches}")
            except Exception as e:
                logger.error(f"Community DB Lookup failed: {e}")

            # Phase 4: Winget Search
            report(0.9, "Searching Winget...")
            winget_url = None
            if SwitchCraftConfig.get_value("EnableWinget", True):
                try:
                    from switchcraft.services.addon_service import AddonService
                    addon_service = AddonService()
                    winget_mod = addon_service.import_addon_module("winget", "utils.winget")
                    if winget_mod and info.product_name:
                        winget = winget_mod.WingetHelper()
                        winget_url = winget.search_by_name(info.product_name)
                except Exception as e:
                    logger.error(f"Winget search failed: {e}")
            else:
                logger.info("Winget search disabled in settings.")

            # Phase 5: AI Context Update
            context_data = {
                "type": info.installer_type,
                "filename": path.name,
                "install_silent": " ".join(info.install_switches) if info.install_switches else "Unknown",
                "product": info.product_name or "Unknown",
                "manufacturer": info.manufacturer or "Unknown"
            }
            if self.ai_service:
                try:
                    self.ai_service.update_context(context_data)
                except Exception as e:
                    logger.error(f"AI Context update failed: {e}")

            report(1.0, "Analysis Complete")

            return AnalysisResult(
                info=info,
                winget_url=winget_url,
                brute_force_data=brute_force_data,
                nested_data=nested_data,
                silent_disabled_info=silent_disabled,
                community_match=community_match
            )

        except Exception as e:
            logger.exception("Controller Analysis Error")
            return AnalysisResult(info=None, error=str(e))
