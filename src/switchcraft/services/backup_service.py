import json
import logging
from switchcraft.utils.config import SwitchCraftConfig

logger = logging.getLogger(__name__)

class BackupService:
    """
    Handles local file backup (Import/Export) of SwitchCraft settings.
    Allows users to save their configuration to a JSON file and restore it.
    """

    @staticmethod
    def export_settings_to_file(file_path: str) -> bool:
        """
        Exports the current user preferences to a specified JSON file.
        """
        try:
            prefs = SwitchCraftConfig.export_preferences()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, indent=4)
            logger.info(f"Settings exported successfully to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export settings to file '{file_path}': {e}")
            return False

    @staticmethod
    def import_settings_from_file(file_path: str) -> bool:
        """
        Imports user preferences from a specified JSON file.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, dict):
                logger.error(f"Invalid settings file format in '{file_path}'. Expected a dictionary.")
                return False

            SwitchCraftConfig.import_preferences(data)
            logger.info(f"Settings imported successfully from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to import settings from file '{file_path}': {e}")
            return False
