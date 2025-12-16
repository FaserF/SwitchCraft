from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path
from switchcraft.models import InstallerInfo

class BaseAnalyzer(ABC):
    @abstractmethod
    def can_analyze(self, file_path: Path) -> bool:
        """Determine if this analyzer can handle the given file."""
        pass

    @abstractmethod
    def analyze(self, file_path: Path) -> InstallerInfo:
        """Analyze the file and return installer information."""
        pass
