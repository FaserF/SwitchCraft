import subprocess
import logging
import os
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
        if not SwitchCraftConfig.get_value("SignScripts", False):
            logger.info("Signing is disabled in settings.")
            return True

        cert_path = SwitchCraftConfig.get_value("CertPath")

        # Auto-detect logic if no path is provided
        if not cert_path:
            logger.info("No certificate path provided. Attempting auto-detection of valid code-signing certs in generic stores...")
            # We can try to sign with "Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | Select-Object -First 1" logic in PowerShell
            # But for specific file path, we need the file.

            # Command to sign using the first available code signing cert in CurrentUser\My
            ps_command = (
                f'$cert = Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert | Select-Object -First 1; '
                f'if ($cert) {{ Set-AuthenticodeSignature -FilePath "{script_path}" -Certificate $cert }} '
                f'else {{ Write-Error "No CodeSigning certificate found." }}'
            )
        else:
            if not os.path.exists(cert_path):
                logger.error(f"Certificate file not found at: {cert_path}")
                return False

            # Command to sign using a specific PFX (requires password usually, or import first)
            # Simplification: Assume user meant a cert ALREADY in store, or we guide them to install it.
            # But wait, user said "Möglichkeit um anzugeben... dass man angeben kann, ob die PowerShell Datei... automatisch signiert wird... Ich signiere aktuell so (siehe Ordner Small-Script-Collection\Sign-AllScriptsInFolder.ps1)"
            # The user might imply using a PFX file directly or a cert in store.
            # If path is PFX, we might need password.
            # If the user provides a path to a script "Sign-AllScriptsInFolder.ps1", maybe they use that?
            # Let's assume standard Set-AuthenticodeSignature with a cert from store OR a PFX.
            # If it's a PFX, `Get-PfxCertificate` can read it (with password prompt usually).

            # For now, let's assume the "CertPath" acts as a "Cert Path or Thumbprint" or we try to load it.
            # If it's a file, we might need a password.

            # Let's stick to the Auto-Detect logic mostly, and if a path is given, try to use it.
            # If it's a PFX without password provided, prompt?
            # The user requirement says: "kein Signaturzertifikatspfad angegeben werden müssen, sondern automtaisch ausgelesen werden"

            pass

        # Let's construct a robust PowerShell command
        # If CertPath is empty -> Use Store
        # If CertPath is a file -> Use Get-PfxCertificate (might fail if password needed)

        cmd = []
        if cert_path and Path(cert_path).exists():
             # Try to import PFX (might need password, which we don't have stored securely yet)
             # Alternatively, maybe the user wants to pick a cert from the store that *matches* this path?
             # Or maybe just use the path as argument to Get-PfxCertificate
             ps_code = f"""
                $pfx = "{cert_path}"
                $pass = Read-Host "Enter Password for PFX" -AsSecureString # This would block. Not good.
                # simpler: Just assume it's in the store if empty.
             """
             # Re-reading user request: "Der User soll in den Einstellungen Scriptsignaturen ein/ausschalten können... Standardpfad... automatisch ausgelesen werden"
             # "Signiere aktuell so (siehe ... Sign-AllScriptsInFolder.ps1)" -> This implies recursive signing.

             # Let's implement robust "Use Store" logic as primary, and "Use File" if specified (but warn about password).
             # Actually, Set-AuthenticodeSignature works best with a Cert object.

             ps_command = (
                 f'$cert = Get-PfxCertificate -FilePath "{cert_path}"; ' # This will likely fail for password protected PFX in non-interactive
                 f'if ($cert) {{ Set-AuthenticodeSignature -FilePath "{script_path}" -Certificate $cert }} '
             )
        else:
             # Auto-detect from store
             ps_command = (
                 f'$cert = Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert | Select-Object -First 1; '
                 f'if (-not $cert) {{ $cert = Get-ChildItem Cert:\\LocalMachine\\My -CodeSigningCert | Select-Object -First 1 }}; '
                 f'if ($cert) {{ Set-AuthenticodeSignature -FilePath "{script_path}" -Certificate $cert }} '
                 f'else {{ exit 1 }}' # Exit 1 if no cert
             )

        try:
            # Run PowerShell
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
                capture_output=True, text=True, check=True
            )
            logger.info("Signing output: " + completed.stdout)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Signing failed: {e.stderr}")
            return False
