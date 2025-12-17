import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from pathlib import Path

# Fix path to basic source
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from switchcraft.services.ai_service import SwitchCraftAI
from switchcraft.analyzers.universal import UniversalAnalyzer

class TestPhase2Features(unittest.TestCase):

    def setUp(self):
        self.ai = SwitchCraftAI()

    # --- AI Service Tests ---
    def test_ai_language_fallback(self):
        """Test that unknown queries return generic fallback."""
        response = self.ai.ask("Hola como estas")
        # Current implementation treats unknown lang as English fallback
        self.assertIn("packaging assistant", response)

    def test_ai_german_smalltalk(self):
        """Test German smalltalk response."""
        response = self.ai.ask("Hallo wer bist du")
        # Check against German translation key value
        self.assertIn("Ich bin SwitchCraft AI", response)

    def test_ai_english_smalltalk(self):
        """Test English smalltalk response."""
        response = self.ai.ask("Hello who are you")
        self.assertIn("I am SwitchCraft AI", response)

    def test_ai_context_answer_de(self):
        """Test context-aware answer in German."""
        self.ai.update_context({"type": "Inno Setup", "install_silent": "/VERYSILENT", "filename": "setup.exe"})
        response = self.ai.ask("Welche switches für silent install?")
        # Update assertion to match what i18n actually returns
        # "Für diesen Inno Setup Installer habe ich folgende Switches gefunden"
        self.assertIn("folgende Switches gefunden", response, f"DE Output mismatch. Got: {response}")
        self.assertIn("/VERYSILENT", response)

    def test_ai_context_answer_en(self):
        """Test context-aware answer in English."""
        self.ai.update_context({"type": "Inno Setup", "install_silent": "/VERYSILENT", "filename": "setup.exe"})
        response = self.ai.ask("What are the silent switches?")
        # Update assertion to match what i18n actually returns
        self.assertIn("detected these silent switches", response, f"EN Output mismatch. Got: {response}")
        self.assertIn("/VERYSILENT", response)

    # --- Brute Force Tests ---
    @patch("switchcraft.analyzers.universal.subprocess.run")
    def test_brute_force_try_all(self, mock_run):
        """Test that the new 'Try All' strategy is attempted."""
        uni = UniversalAnalyzer()

        # Mock successful output on first 'all params' try
        mock_run.return_value.stdout = "Usage: app.exe [options] ... /S = Silent Mode"
        mock_run.return_value.stderr = ""
        mock_run.return_value.returncode = 0

        # Determine strict logic isn't easily unit testable without mocking internal methods
        # But we can check if it returns a result if the first call succeeds

        # We need to mock _analyze_help_text to confirm it "found" something
        with patch.object(uni, "_analyze_help_text", return_value=("Generic", ["/S"])) as mock_analyze:
             result = uni.brute_force_help(Path("dummy.exe"))

             self.assertEqual(result["detected_type"], "Generic")
             self.assertEqual(result["suggested_switches"], ["/S"])
             # Should have stopped early, meaning all_attempts list is empty (no individual commands run)
             self.assertEqual(result["all_attempts"], [])

             # Additional check: Ensure output contains our mocked "usage" text
             self.assertIn("Usage: app.exe", result["output"])

    # --- Install Script Logic (Conceptual) ---
    # Since install.ps1 is PowerShell, we can't unit test it easily in Python.
    # The smoke test already checks if CLI entry point works.

if __name__ == '__main__':
    unittest.main()
