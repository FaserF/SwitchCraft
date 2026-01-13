import logging
from pathlib import Path
import olefile
from switchcraft.analyzers.base import BaseAnalyzer
from switchcraft.models import InstallerInfo

logger = logging.getLogger(__name__)

class MsiAnalyzer(BaseAnalyzer):
    def can_analyze(self, file_path: Path) -> bool:
        if not file_path.exists():
            return False
        # Check signature or extension
        if file_path.suffix.lower() == '.msi':
            return True
        if olefile.isOleFile(file_path):
            return True
        return False

    def analyze(self, file_path: Path) -> InstallerInfo:
        info = InstallerInfo(file_path=str(file_path), installer_type="MSI Database")
        info.install_switches = ["/qn", "/norestart"]
        info.uninstall_switches = ["/x", str(file_path), "/qn", "/norestart"] # Placeholder, usually needs ProductCode
        info.properties = {} # Initialize properties dictionary

        try:
            # Try using msilib on Windows for full property access
            import msilib
            db = msilib.OpenDatabase(str(file_path), msilib.MSIDBOPEN_READONLY)
            view = db.OpenView("SELECT Property, Value FROM Property")
            view.Execute(None)
            record = view.Fetch()
            while record:
                prop = record.GetString(1)
                val = record.GetString(2)
                info.properties[prop] = val
                record = view.Fetch()

            info.product_name = info.properties.get("ProductName")
            info.product_version = info.properties.get("ProductVersion")
            info.manufacturer = info.properties.get("Manufacturer")
            product_code = info.properties.get("ProductCode")
            info.product_code = product_code

            if product_code:
                 # Standard MSI uninstall string
                info.uninstall_switches = ["msiexec.exe", "/x", product_code, "/qn", "/norestart"]

            info.confidence = 1.0
            return info

        except ImportError:
            # Fallback for non-Windows or if msilib is missing
            pass
        except Exception as e:
            logger.warning(f"msilib parsing failed: {e}")

        try:
            with olefile.OleFileIO(file_path) as ole:
                # Basic OLE metadata fallback
                info.confidence = 0.8 # Less confident if we only have summary info

                meta = ole.get_metadata()
                if meta:
                    info.product_name = meta.title if meta.title else meta.subject
                    info.manufacturer = meta.author
                    # Note: OLE summary comments often contain the Installer UUIDs but not always reliably
                    if meta.comments:
                        info.properties["Comments"] = meta.comments

        except Exception as e:
            logger.error(f"Error parsing MSI {file_path}: {e}")
            info.confidence = 0.0

        return info
