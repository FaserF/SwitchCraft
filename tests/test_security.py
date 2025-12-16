import unittest
from unittest.mock import MagicMock, patch
from switchcraft.utils.security import SecurityChecker

class TestSecurityChecker(unittest.TestCase):

    @patch('importlib.metadata.distributions')
    def test_get_installed_packages(self, mock_dists):
        # Mock a distribution
        mock_dist = MagicMock()
        mock_dist.metadata = {"Name": "test-package"}
        mock_dist.version = "1.0.0"
        mock_dists.return_value = [mock_dist]

        pkgs = SecurityChecker.get_installed_packages()
        self.assertEqual(len(pkgs), 1)
        self.assertEqual(pkgs[0]["package"]["name"], "test-package")
        self.assertEqual(pkgs[0]["version"], "1.0.0")

    @patch('requests.post')
    @patch('switchcraft.utils.config.SwitchCraftConfig.set_user_preference')
    @patch('switchcraft.utils.config.SwitchCraftConfig.get_value')
    @patch('switchcraft.utils.security.SecurityChecker.get_installed_packages')
    def test_check_vulnerabilities_found(self, mock_get_pkgs, mock_get_val, mock_set_val, mock_post):
        # Bypass rate limit
        mock_get_val.return_value = 0
        # Mock installed packages
        mock_get_pkgs.return_value = [{"package": {"name": "vuln-pkg", "ecosystem": "PyPI"}, "version": "1.0.0"}]

        # Mock OSV API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "vulns": [
                        {
                            "id": "GHSA-1234",
                            "aliases": ["CVE-2023-1234"],
                            "summary": "Bad vulnerability",
                            "details": "Details here"
                        }
                    ]
                }
            ]
        }
        mock_post.return_value = mock_response

        issues = SecurityChecker.check_vulnerabilities()

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["package"], "vuln-pkg")
        self.assertEqual(issues[0]["id"], "CVE-2023-1234") # Should prefer alias
        self.assertEqual(issues[0]["details_url"], "https://osv.dev/vulnerability/GHSA-1234")

    @patch('requests.post')
    @patch('switchcraft.utils.config.SwitchCraftConfig.set_user_preference')
    @patch('switchcraft.utils.config.SwitchCraftConfig.get_value')
    @patch('switchcraft.utils.security.SecurityChecker.get_installed_packages')
    def test_check_vulnerabilities_none(self, mock_get_pkgs, mock_get_val, mock_set_val, mock_post):
        # Bypass rate limit
        mock_get_val.return_value = 0
        mock_get_pkgs.return_value = [{"package": {"name": "safe-pkg", "ecosystem": "PyPI"}, "version": "1.0.0"}]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{}]} # No vulns
        mock_post.return_value = mock_response

        issues = SecurityChecker.check_vulnerabilities()
        self.assertEqual(len(issues), 0)

if __name__ == '__main__':
    unittest.main()
