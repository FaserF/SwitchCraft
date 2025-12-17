
import logging
import os
import subprocess
import requests
from pathlib import Path
from switchcraft.utils.i18n import i18n

logger = logging.getLogger(__name__)

class IntuneService:
    """
    Service to handle Microsoft Win32 Content Prep Tool operations.
    """

    TOOL_URL = "https://github.com/microsoft/Microsoft-Win32-Content-Prep-Tool/raw/master/IntuneWinAppUtil.exe"
    TOOL_FILENAME = "IntuneWinAppUtil.exe"

    def __init__(self, tools_dir: str = None):
        if tools_dir:
            self.tools_dir = Path(tools_dir)
        else:
            # Default to a 'tools' directory in the user's home or app data
            self.tools_dir = Path.home() / ".switchcraft" / "tools"

        self.tool_path = self.tools_dir / self.TOOL_FILENAME

    def is_tool_available(self) -> bool:
        return self.tool_path.exists()

    def download_tool(self) -> bool:
        """Downloads the IntuneWinAppUtil.exe from Microsoft."""
        try:
            self.tools_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Downloading IntuneWinAppUtil from {self.TOOL_URL}...")

            response = requests.get(self.TOOL_URL, stream=True)
            response.raise_for_status()

            with open(self.tool_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info("IntuneWinAppUtil downloaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to download IntuneWinAppUtil: {e}")
            return False

    def create_intunewin(self, source_folder: str, setup_file: str, output_folder: str, catalog_folder: str = None, quiet: bool = True) -> str:
        """
        Runs the IntuneWinAppUtil to generate the .intunewin package.
        Returns the output text from the tool.
        """
        if not self.is_tool_available():
            if not self.download_tool():
                raise FileNotFoundError("IntuneWinAppUtil.exe not found and could not be downloaded.")

        # Ensure paths are absolute strings
        source_folder = str(Path(source_folder).resolve())

        # Check if setup_file looks like a full path, verify it is inside source_folder
        setup_path = Path(setup_file)
        if setup_path.is_absolute():
            # If absolute, verify it starts with source_folder
             try:
                 rel_path = setup_path.relative_to(source_folder)
                 setup_arg = str(rel_path)
             except ValueError:
                 # It's not inside? Intune tool might fail.
                 # But let's assume the user provided just the filename or correct relative path if possible.
                 setup_arg = setup_file
        else:
            setup_arg = setup_file

        output_folder = str(Path(output_folder).resolve())
        Path(output_folder).mkdir(parents=True, exist_ok=True)

        cmd = [
            str(self.tool_path),
            "-c", source_folder,
            "-s", setup_arg,
            "-o", output_folder
        ]

        if catalog_folder:
             cmd.extend(["-a", str(Path(catalog_folder).resolve())])

        if quiet:
            cmd.append("-q")

        logger.info(f"Running IntuneWinAppUtil: {cmd}")

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='cp1252', # Windows tool output encoding
                startupinfo=startupinfo
            )

            if process.returncode == 0:
                logger.info("IntuneWin package created successfully.")
                return process.stdout
            else:
                logger.error(f"IntuneWin creation failed: {process.stderr}")
                raise RuntimeError(f"Tool exited with code {process.returncode}: {process.stdout}")

        except Exception as e:
            logger.error(f"Error running IntuneWinAppUtil: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error running IntuneWinAppUtil: {e}")
            raise e

    # --- Graph API Integration ---

    def authenticate(self, tenant_id, client_id, client_secret):
        """Authenticates with MS Graph using Client Credentials."""
        url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": client_id,
            "scope": "https://graph.microsoft.com/.default",
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        }
        try:
            resp = requests.post(url, data=data)
            resp.raise_for_status()
            token = resp.json().get("access_token")
            logger.info("Successfully authenticated with Graph API.")
            return token
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise RuntimeError(f"Authentication failed: {e}")

    def upload_win32_app(self, token, intunewin_path, app_info, progress_callback=None):
        """
        Uploads a .intunewin package to Intune.
        app_info: dict with keys: displayName, description, publisher, installCommandLine, uninstallCommandLine
        """
        import zipfile
        import xml.etree.ElementTree as ET
        import base64

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        base_url = "https://graph.microsoft.com/beta/deviceAppManagement" # Use beta for win32LobApp usually

        intunewin_path = Path(intunewin_path)
        if not intunewin_path.exists():
            raise FileNotFoundError(f"File not found: {intunewin_path}")

        # 1. Parse .intunewin for Encryption Info
        logger.info("Parsing .intunewin metadata...")
        encryption_info = {}
        try:
            with zipfile.ZipFile(intunewin_path, 'r') as z:
                # Find detection.xml
                # Structure is usually IntuneWinPackage/Metadata/Detection.xml
                # But let's find it.
                names = z.namelist()
                det_xml = next((n for n in names if n.endswith("Detection.xml")), None)
                if not det_xml:
                    raise ValueError("Detection.xml not found in .intunewin package")

                with z.open(det_xml) as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    # Parse EncryptionInfo
                    # Expected structure via analysis of IntuneWinAppUtil output
                    enc_node = root.find("EncryptionInfo")
                    if enc_node is None:
                         # Fallback search
                         enc_node = root.find(".//EncryptionInfo")

                    if enc_node is not None:
                        encryption_info = {
                            "encryptionKey": enc_node.get("EncryptionKey"),
                            "macKey": enc_node.get("MacKey"),
                            "initializationVector": enc_node.get("InitializationVector"),
                            "fileDigest": enc_node.get("FileDigest"),
                            "fileDigestAlgorithm": enc_node.get("FileDigestAlgorithm"),
                            "profileIdentifier": enc_node.get("ProfileIdentifier")
                        }

                        # Fix byte/string issues if needed (usually they are B64 strings in XML)
                    else:
                        raise ValueError("EncryptionInfo not found in Detection.xml")

                # Get file size logic
                # The file inside the intunewin is also encrypted. Actually, the intunewin IS the package.
                # Intune expects 'Manifest' which is the detection.xml usually?
                # No, standard Graph API calls for create file expect 'fileEncryptionInfo'.

        except Exception as e:
             raise RuntimeError(f"Failed to parse .intunewin: {e}")

        # 2. Create MobileApp
        logger.info("Creating Win32 App entity...")
        app_payload = {
            "@odata.type": "#microsoft.graph.win32LobApp",
            "displayName": app_info.get("displayName", "New App"),
            "description": app_info.get("description", "Uploaded by SwitchCraft"),
            "publisher": app_info.get("publisher", "Unknown"),
            "installCommandLine": app_info.get("installCommandLine", "install.cmd"),
            "uninstallCommandLine": app_info.get("uninstallCommandLine", "uninstall.cmd"),
            "applicableArchitectures": "x64", # Defaulting to x64
            "runSystemAccount": True,
            # "fileName": intunewin_path.name # Required? Property is 'fileName' of the package?
            "fileName": intunewin_path.name
        }

        create_resp = requests.post(f"{base_url}/mobileApps", headers=headers, json=app_payload)
        create_resp.raise_for_status()
        app_id = create_resp.json().get("id")
        logger.info(f"App created with ID: {app_id}")

        if progress_callback: progress_callback(0.2, "App entity created.")

        try:
            # 3. Create Content Version
            logger.info("Creating Content Version...")
            cv_resp = requests.post(f"{base_url}/mobileApps/{app_id}/contentVersions", headers=headers, json={})
            cv_resp.raise_for_status()
            cv_id = cv_resp.json().get("id")

            # 4. Create File Entry
            logger.info("Creating File Entry...")
            file_size = intunewin_path.stat().st_size

            file_payload = {
                "@odata.type": "#microsoft.graph.mobileAppContentFile",
                "name": intunewin_path.name,
                "size": file_size,
                "sizeEncrypted": file_size, # Since intunewin is already encrypted
                "manifest": None, # Usually optional or auto-extracted?
                "isDependency": False
            }

            file_resp = requests.post(f"{base_url}/mobileApps/{app_id}/contentVersions/{cv_id}/files", headers=headers, json=file_payload)
            file_resp.raise_for_status()
            file_data = file_resp.json()
            file_id = file_data.get("id")
            upload_url = file_data.get("uploadUrl")

            if progress_callback: progress_callback(0.4, "Ready to upload.")

            # 5. Upload Blob
            logger.info(f"Uploading {file_size} bytes to {upload_url[:50]}...")

            # Use streaming upload for large files
            with open(intunewin_path, 'rb') as f:
                # Azure Blob requires specific headers for block blob? Usually x-ms-blob-type
                # Graph API uploadUrl usually contains SAS token.
                blob_headers = {"x-ms-blob-type": "BlockBlob"}

                # Ideally split into blocks (Intune requirement usually), but for single PUT:
                put_resp = requests.put(upload_url, headers=blob_headers, data=f)
                put_resp.raise_for_status()

            logger.info("Upload complete.")
            if progress_callback: progress_callback(0.8, "Upload complete. Committing...")

            # 6. Commit File
            logger.info("Committing file...")
            commit_file_payload = {
                "fileEncryptionInfo": encryption_info
            }
            requests.post(f"{base_url}/mobileApps/{app_id}/contentVersions/{cv_id}/files/{file_id}/commit", headers=headers, json=commit_file_payload).raise_for_status()

            # 7. Commit Content Version
            logger.info("Committing content version...")
            # Wait for file to be processed? Typically Graph is async but commit expects file to be uploaded.

            # We might need to check file status first?
            # Assuming immediate consistency for this example.

            requests.post(f"{base_url}/mobileApps/{app_id}/contentVersions/{cv_id}/commit", headers=headers, json={}).raise_for_status()

            logger.info("App successfully published to Intune.")
            if progress_callback: progress_callback(1.0, "Published successfully!")

            return app_id

        except Exception as e:
            logger.error(f"Upload process failed: {e}")
            # Try to cleanup?
            raise e
