import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from switchcraft.analyzers.msi import MsiAnalyzer
from switchcraft.analyzers.exe import ExeAnalyzer
from switchcraft.models import InstallerInfo

class TestAnalyzers(unittest.TestCase):
    @patch('pathlib.Path.exists', return_value=True)
    @patch('olefile.isOleFile', return_value=False)
    def test_msi_analyzer_extension(self, mock_ole, mock_exists):
        analyzer = MsiAnalyzer()
        self.assertTrue(analyzer.can_analyze(Path("test.msi")))
        self.assertFalse(analyzer.can_analyze(Path("test.exe")))

    @patch('pathlib.Path.exists', return_value=True)
    def test_exe_analyzer_extension(self, mock_exists):
        analyzer = ExeAnalyzer()
        self.assertTrue(analyzer.can_analyze(Path("test.exe")))
        self.assertFalse(analyzer.can_analyze(Path("test.msi")))

    @patch('pefile.PE')
    def test_exe_nsis_detection(self, mock_pe):
        # Mock NSIS valid PE
        mock_pe_instance = MagicMock()
        mock_pe.return_value = mock_pe_instance

        # Mock section
        section = MagicMock()
        section.Name = b".ndata"
        mock_pe_instance.sections = [section]

        # We need a real file for the analyzer to open in _check_nsis fallback logic if needed,
        # but since we mock PE sections, it should return True before file I/O for the secondary check.
        # Wait, the code checks sections first.

        analyzer = ExeAnalyzer()
        # We need to mock file existence check too
        with patch('pathlib.Path.exists', return_value=True):
            info = analyzer.analyze(Path("dummy_nsis.exe"))
            self.assertEqual(info.installer_type, "NSIS")
            self.assertIn("/S", info.install_switches)

if __name__ == '__main__':
    unittest.main()
