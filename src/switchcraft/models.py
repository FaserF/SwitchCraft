from dataclasses import dataclass, field
from typing import Any


@dataclass
class InstallerInfo:
    file_path: str
    installer_type: str = "Unknown"
    product_name: str | None = None
    product_version: str | None = None
    manufacturer: str | None = None
    product_code: str | None = None  # MSI GUID
    install_path: str | None = None  # Inferred Install Path
    install_switches: list[str] = field(default_factory=list)
    uninstall_switches: list[str] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)
    website: str | None = None
    confidence: float = 0.0

    # MacOS specific
    bundle_id: str | None = None
    min_os_version: str | None = None
    package_ids: list[str] = field(default_factory=list)

    # Validation
    is_corrupted: bool = False
    corruption_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
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
