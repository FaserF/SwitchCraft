from dataclasses import dataclass, field
from typing import Dict, Optional, List

@dataclass
class InstallerInfo:
    file_path: str
    installer_type: str = "Unknown"
    product_name: Optional[str] = None
    product_version: Optional[str] = None
    manufacturer: Optional[str] = None
    install_switches: List[str] = field(default_factory=list)
    uninstall_switches: List[str] = field(default_factory=list)
    properties: Dict[str, str] = field(default_factory=dict)
    website: Optional[str] = None
    confidence: float = 0.0

    # MacOS specific
    bundle_id: Optional[str] = None
    min_os_version: Optional[str] = None
    package_ids: List[str] = field(default_factory=list)

    def __str__(self):
        return (
            f"Installer: {self.product_name} {self.product_version}\n"
            f"Type: {self.installer_type}\n"
            f"Silent Install: {' '.join(self.install_switches)}\n"
            f"Silent Uninstall: {' '.join(self.uninstall_switches)}"
        )
