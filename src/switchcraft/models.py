from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any

@dataclass
class InstallerInfo:
    file_path: str
    installer_type: str = "Unknown"
    product_name: Optional[str] = None
    product_version: Optional[str] = None
    manufacturer: Optional[str] = None
    product_code: Optional[str] = None  # MSI GUID
    install_path: Optional[str] = None  # Inferred Install Path
    install_switches: List[str] = field(default_factory=list)
    uninstall_switches: List[str] = field(default_factory=list)
    properties: Dict[str, str] = field(default_factory=dict)
    website: Optional[str] = None
    confidence: float = 0.0

    # MacOS specific
    bundle_id: Optional[str] = None
    min_os_version: Optional[str] = None
    package_ids: List[str] = field(default_factory=list)

    # Validation
    is_corrupted: bool = False
    corruption_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "installer_type": self.installer_type,
            "product_name": self.product_name,
            "product_version": self.product_version,
            "manufacturer": self.manufacturer,
            "product_code": self.product_code,
            "install_path": self.install_path,
            "install_switches": self.install_switches,
            "uninstall_switches": self.uninstall_switches,
            "properties": self.properties,
            "is_corrupted": self.is_corrupted,
            "corruption_reason": self.corruption_reason,
            "bundle_id": self.bundle_id,
            "min_os_version": self.min_os_version,
            "package_ids": self.package_ids,
            "website": self.website,
            "confidence": self.confidence
        }

    def __str__(self):
        return (
            f"Installer: {self.product_name} {self.product_version}\n"
            f"Type: {self.installer_type}\n"
            f"Silent Install: {' '.join(self.install_switches)}\n"
            f"Silent Uninstall: {' '.join(self.uninstall_switches)}"
        )
