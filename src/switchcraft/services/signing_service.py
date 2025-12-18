import subprocess
import logging
from pathlib import Path
from switchcraft.utils.config import SwitchCraftConfig

logger = logging.getLogger(__name__)

class SigningService:
    @staticmethod
    def sign_script(script_path: str) -> bool:
        """
        Signs a PowerShell script using the configured certificate.
        Returns True if successful, False otherwise.
        """
        # User Setting Check
        if not SwitchCraftConfig.get_value("SignScripts", False):
            logger.info("Signing is disabled in settings.")
            return True

        cert_path = SwitchCraftConfig.get_value("CertPath")
        script_path_obj = Path(script_path).resolve()

        if not script_path_obj.exists():
            logger.error(f"Script to sign not found: {script_path}")
            return False

        logger.info(f"Attempting to sign: {script_path}")

        ps_command = ""

        if cert_path and Path(cert_path).exists():
            # PFX Path Logic - Note: Set-AuthenticodeSignature with PFX usually requires password or import.
            # However, if the user points to a PFX, we can try to use it.
            # Since we can't easily prompt for password in headless/automation securely here without UI,
            # we check if it is imported or if we can use it.
            # Best Practice: Import to store, point to store. But user wants "Path".
            # For "File based" signing, we assume passwordless or already handled?
            # Actually, standard practice is Cert Store.
            # If "CertPath" is a file, we might warn.
            # But let's assume the user might have provided a .pfx that needs password?
            # To avoid password prompt issues, we will fallback to "Auto Detect" if path logic fails,
            # or try to import it to a temp store? Too complex.
            # Simpler: If path is provided, try `Get-PfxCertificate` (prompts if needed? No, fails if protected).

            logger.warning("Using direct PFX path might require manual password entry which is not supported in this automation yet. Prefer Certificate Store.")
            # We construct a command that attempts to load it.
            ps_command = (
                f'$pfx = "{cert_path}"; '
                f'$cert = Get-PfxCertificate -FilePath $pfx; '
                f'if ($cert) {{ Set-AuthenticodeSignature -FilePath "{script_path_obj}" -Certificate $cert }} '
                f'else {{ Write-Error "Could not load certificate from file." }}'
            )
        else:
            # Auto-Detect from Store (CurrentUser mainly, then LocalMachine)
            ps_command = (
                f'$cert = Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert | Select-Object -First 1; '
                f'if ($cert) {{ Write-Output "Found cert in CurrentUser\\My: $($cert.Subject)" }} '
                f'else {{ '
                f'   Write-Output "No cert in CurrentUser, checking LocalMachine..."; '
                f'   $cert = Get-ChildItem Cert:\\LocalMachine\\My -CodeSigningCert | Select-Object -First 1; '
                f'   if ($cert) {{ Write-Output "Found cert in LocalMachine\\My: $($cert.Subject)" }} '
                f'}} '
                f'if ($cert) {{ '
                f'   $sig = Set-AuthenticodeSignature -FilePath "{script_path_obj}" -Certificate $cert; '
                f'   if ($sig.Status -eq "Valid") {{ Write-Output "Signed Successfully" }} else {{ Write-Error "Signing Failed: $($sig.StatusMessage)" }} '
                f'}} '
                f'else {{ Write-Error "No CodeSigning certificate found in User or Machine store." }}'
            )

        try:
            # Run PowerShell
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
                capture_output=True, text=True
            )

            if completed.returncode == 0 and "Signed Successfully" in completed.stdout:
                logger.info(f"Successfully signed {script_path_obj.name}")
                return True
            else:
                if completed.stderr:
                    logger.error(f"Signing Error: {completed.stderr.strip()}")
                logger.warning(f"Signing Output: {completed.stdout.strip()}")
                return False

        except subprocess.CalledProcessError as e:
            logger.error(f"Signing failed exception: {e}")
            return False
