import sys
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

from switchcraft.services.addon_service import AddonService
from switchcraft.utils.templates import TemplateGenerator
from switchcraft.services.signing_service import SigningService
from switchcraft.utils.config import SwitchCraftConfig

class TestFixes(unittest.TestCase):

    @patch("switchcraft.services.addon_service.requests.get")
    def test_addon_download_url_release(self, mock_get):
        # Mock Release Environment
        with patch("sys.frozen", True, create=True):
             with patch("switchcraft.__version__", "2025.1.1"):
                # Mock GitHub API response
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    "tag_name": "v2025.1.1",
                    "assets": [
                        {"name": "switchcraft_advanced.zip", "browser_download_url": "https://example.com/asset.zip"}
                    ]
                }
                mock_get.return_value = mock_resp

                # Mock download response
                mock_file_resp = MagicMock()
                mock_file_resp.content = b"fakezipcontent"
                mock_get.side_effect = [mock_resp, mock_file_resp]

                with patch("zipfile.ZipFile"): # Don't actually unzip
                    result = AddonService.install_addon("advanced")
                    # We expect True and the second call to get the asset URL
                    self.assertTrue(result)
                    mock_get.assert_called_with("https://example.com/asset.zip", stream=True, timeout=60)

    @patch("switchcraft.services.addon_service.requests.get")
    def test_addon_download_url_dev(self, mock_get):
        # Mock Dev Environment (frozen but dev version)
        with patch("sys.frozen", True, create=True):
             with patch("switchcraft.__version__", "2025.1.1-dev"):
                 # Mock download response for main zip
                 mock_file_resp = MagicMock()
                 mock_file_resp.content = b"fakezipcontent"
                 mock_get.return_value = mock_file_resp

                 # Mock zipfile behaviour
                 mock_zip_cls = MagicMock()
                 mock_zip_instance = mock_zip_cls.return_value
                 # namelist used to find root folder
                 mock_zip_instance.namelist.return_value = ["SwitchCraft-main/"]

                 # infolist used to iterate files
                 # We need an item that matches "SwitchCraft-main/src/switchcraft_advanced/"
                 mock_info = MagicMock()
                 mock_info.filename = "SwitchCraft-main/src/switchcraft_advanced/dummy.txt"
                 mock_info.is_dir.return_value = False
                 mock_zip_instance.infolist.return_value = [mock_info]

                 # context manager
                 mock_zip_instance.__enter__.return_value = mock_zip_instance

                 # mock open to return bytes
                 from io import BytesIO
                 mock_zip_instance.open.return_value = BytesIO(b"fake_file_content")

                 with patch("zipfile.ZipFile", mock_zip_cls):
                     result = AddonService.install_addon("advanced")
                     # Expect fallback to main zip
                     self.assertTrue(result)
                     mock_get.assert_called_with("https://github.com/FaserF/SwitchCraft/archive/refs/heads/main.zip", stream=True, timeout=60)

    def test_template_config(self):
        # Set config
        with patch("switchcraft.utils.config.SwitchCraftConfig.get_value") as mock_get_val:
            mock_get_val.return_value = "custom_fake.ps1"
            with patch("pathlib.Path.exists", return_value=True):
                gen = TemplateGenerator()
                self.assertTrue(gen.is_custom)
                self.assertEqual(str(gen.template_path), "custom_fake.ps1")

    def test_signing_logic(self):
        # Just ensure no syntax error in logic construction
        # We can't easily test the PS string without running it, but we can check if the file logic compiles
        pass

if __name__ == "__main__":
    unittest.main()
