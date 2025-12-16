import importlib.metadata
import requests
import logging
import json
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class SecurityChecker:
    """
    Checks installed Python packages against the OSV.dev vulnerability database.
    """
    OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"

    @staticmethod
    def get_installed_packages() -> List[Dict[str, str]]:
        """
        Returns a list of installed packages and their versions.
        Format compatible with OSV batch query.
        """
        packages = []
        try:
            dists = importlib.metadata.distributions()
            for dist in dists:
                packages.append({
                    "package": {"name": dist.metadata["Name"], "ecosystem": "PyPI"},
                    "version": dist.version
                })
        except Exception as e:
            logger.error(f"Failed to list installed packages: {e}")
        return packages

    @classmethod
    def check_vulnerabilities(cls) -> List[Dict]:
        """
        Queries OSV.dev for vulnerabilities in installed packages.
        Returns a list of finding dicts:
        {
            "package": str,
            "version": str,
            "id": str, # CVE or OSV ID
            "summary": str,
            "severity": str, # LOW, MEDIUM, HIGH, CRITICAL (inferred)
            "details_url": str
        }
        """
        packages = cls.get_installed_packages()
        if not packages:
            return []

        # Rate Limiting: Check once every 7 days
        from switchcraft.utils.config import SwitchCraftConfig
        import time

        last_check = SwitchCraftConfig.get_value("LastSecurityCheck", 0)
        try:
            # Handle possible string/int mismatch from manual registry edits
            last_check = float(last_check)
        except (ValueError, TypeError):
            last_check = 0

        current_time = time.time()
        # 7 days = 604800 seconds
        if current_time - last_check < 604800:
            logger.info("Skipping security check (rate limited)")
            return []

        SwitchCraftConfig.set_user_preference("LastSecurityCheck", int(current_time))

        # OSV Batch Query Format: {"queries": [...]}
        payload = {"queries": packages}

        findings = []

        try:
            response = requests.post(cls.OSV_BATCH_URL, json=payload, timeout=10)
            if response.status_code != 200:
                logger.error(f"OSV API failed with {response.status_code}: {response.text}")
                return []

            results = response.json().get("results", [])

            # Results correspond to queries by index
            for idx, result in enumerate(results):
                vulns = result.get("vulns", [])
                if vulns:
                    pkg_info = packages[idx]
                    pkg_name = pkg_info["package"]["name"]
                    pkg_ver = pkg_info["version"]

                    for vuln in vulns:
                        # Extract basic info
                        vuln_id = vuln.get("id")
                        summary = vuln.get("summary") or vuln.get("details", "")[:100] + "..."

                        # Use alias IDs if available (often friendlier, e.g. CVE-202X-XXXX)
                        if vuln.get("aliases"):
                             # Prefer CVEs
                             cves = [a for a in vuln["aliases"] if a.startswith("CVE")]
                             if cves:
                                 vuln_id = cves[0]

                        # Determine severity (simplified)
                        severity = "UNKNOWN"
                        if vuln.get("severity"): # CVSSv3 vector usually
                             # Very basic check, parsing vector is complex without library
                             # Just checking if any severity field exists
                             pass

                        # Check database specific severity often found in 'database_specific' or 'ecosystem_specific'
                        # For now, treat existence as warning.

                        findings.append({
                            "package": pkg_name,
                            "version": pkg_ver,
                            "id": vuln_id,
                            "summary": summary,
                            "details_url": f"https://osv.dev/vulnerability/{vuln.get('id')}"
                        })

        except Exception as e:
            logger.error(f"Vulnerability check failed: {e}")

        return findings
