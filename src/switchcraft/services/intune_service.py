import stat
import logging
import os
import subprocess
import requests
import base64
from pathlib import Path
import zipfile
from typing import Optional, Callable
from switchcraft.utils.i18n import i18n
from defusedxml import ElementTree as DefusedET
import jwt

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

            response = requests.get(self.TOOL_URL, stream=True, timeout=30)
            response.raise_for_status()

            with open(self.tool_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Grant execution permissions (for CI/Linux runners)
            st = os.stat(self.tool_path)
            os.chmod(self.tool_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

            logger.info("IntuneWinAppUtil downloaded successfully.")
            return True
        except Exception:
            logger.exception("Failed to download IntuneWinAppUtil")
            return False

    def create_intunewin(self, source_folder: str, setup_file: str, output_folder: str, catalog_folder: str = None, quiet: bool = True, progress_callback: Optional[Callable[[str], None]] = None) -> str:
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
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='cp1252', # Windows tool output encoding
                startupinfo=startupinfo,
                bufsize=1,
                universal_newlines=True
            )

            full_output = []

            # Stream output
            for line in process.stdout:
                line_str = line
                full_output.append(line_str)
                # If a callback is provided (e.g. for UI)
                if progress_callback:
                    progress_callback(line_str)

            process.wait()

            output_str = "".join(full_output)

            if process.returncode == 0:
                logger.info("IntuneWin package created successfully.")
                return output_str
            else:
                logger.error(f"IntuneWin creation failed: {output_str}")
                raise RuntimeError(f"Tool exited with code {process.returncode}: {output_str}")

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
            resp = requests.post(url, data=data, timeout=30)
            resp.raise_for_status()
            token = resp.json().get("access_token")
            logger.info("Successfully authenticated with Graph API.")
            return token
        except Exception:
            logger.exception("Authentication failed")
            raise RuntimeError("Authentication failed")

    def verify_graph_permissions(self, token):
        """Verifies Graph API permissions from JWT token."""
        try:
            # Simple JWT decoding using PyJWT without signature verification (done by Graph)
            payload = jwt.decode(token, options={"verify_signature": False})

            roles = payload.get("roles", [])

            mandatory = ["DeviceManagementApps.ReadWrite.All"]
            missing = [r for r in mandatory if r not in roles]

            if missing:
                return False, f"Missing Mandatory Role: {', '.join(missing)}"

            # Check optional (accept higher/alternative if logic allows, here we check Group Read)
            # Accept Group.Read.All OR Group.ReadWrite.All
            has_group_read = any(r in roles for r in ["Group.Read.All", "Group.ReadWrite.All"])

            if not has_group_read:
                return True, "ok_with_warning: Missing 'Group.Read.All'. App assignment verification will fail, but upload will work."

            return True, "OK"
        except Exception as e:
            return False, f"Token decode failed: {e}"

    def upload_win32_app(self, token, intunewin_path, app_info, progress_callback=None):
        """
        Uploads a .intunewin package to Intune.
        app_info: dict with keys: displayName, description, publisher, installCommandLine, uninstallCommandLine
        """
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
                    tree = DefusedET.parse(f)
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

        create_resp = requests.post(f"{base_url}/mobileApps", headers=headers, json=app_payload, timeout=60)
        create_resp.raise_for_status()
        app_id = create_resp.json().get("id")
        logger.info(f"App created with ID: {app_id}")

        if progress_callback:
            progress_callback(0.2, i18n.get("intune_status_created"))

        try:
            cv_resp = requests.post(f"{base_url}/mobileApps/{app_id}/contentVersions", headers=headers, json={}, timeout=60)
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

            file_resp = requests.post(f"{base_url}/mobileApps/{app_id}/contentVersions/{cv_id}/files", headers=headers, json=file_payload, timeout=60)
            file_resp.raise_for_status()
            file_data = file_resp.json()
            file_id = file_data.get("id")
            upload_url = file_data.get("uploadUrl")

            if progress_callback:
                progress_callback(0.4, i18n.get("intune_status_ready_upload"))

            # 5. Upload Blob
            logger.info(f"Uploading {file_size} bytes to {upload_url[:50]}...")

            # Use streaming upload for large files
            with open(intunewin_path, 'rb') as f:
                # Azure Blob requires specific headers for block blob? Usually x-ms-blob-type
                # Graph API uploadUrl usually contains SAS token.
                blob_headers = {"x-ms-blob-type": "BlockBlob"}

                # Ideally split into blocks (Intune requirement usually), but for single PUT:
                put_resp = requests.put(upload_url, headers=blob_headers, data=f, timeout=300) # Large file upload
                put_resp.raise_for_status()

            logger.info("Upload complete.")
            if progress_callback:
                progress_callback(0.8, i18n.get("intune_status_committing"))

            # 6. Commit File
            logger.info("Committing file...")
            commit_file_payload = {
                "fileEncryptionInfo": encryption_info
            }
            requests.post(f"{base_url}/mobileApps/{app_id}/contentVersions/{cv_id}/files/{file_id}/commit", headers=headers, json=commit_file_payload, timeout=60).raise_for_status()

            # 7. Commit Content Version
            logger.info("Committing content version...")
            # Wait for file to be processed? Typically Graph is async but commit expects file to be uploaded.

            # We might need to check file status first?
            # Assuming immediate consistency for this example.

            requests.post(f"{base_url}/mobileApps/{app_id}/contentVersions/{cv_id}/commit", headers=headers, json={}, timeout=60).raise_for_status()

            logger.info("App successfully published to Intune.")
            if progress_callback:
                progress_callback(1.0, i18n.get("intune_status_published"))

            return app_id

        except Exception as e:
            logger.error(f"Upload process failed: {e}")
            # Try to cleanup?
            raise e

    def assign_to_group(self, token, app_id, group_id, intent="required"):
        """
        Assigns the app to a specific Azure AD Group.
        intent: required, available, uninstall
        """
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        base_url = "https://graph.microsoft.com/beta/deviceAppManagement"

        url = f"{base_url}/mobileApps/{app_id}/assignments"

        payload = {
            "target": {
                "@odata.type": "#microsoft.graph.groupAssignmentTarget",
                "groupId": group_id
            },
            "intent": intent,
            "settings": None
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            logger.info(f"Assigned App {app_id} to Group {group_id} ({intent})")
            return True
        except Exception as e:
            logger.error(f"Failed to assign group: {e}")
            raise e

    def list_apps(self, token, filter_query=None):
        """
        List apps from Intune.
        Returns a list of dicts.
        """
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        base_url = "https://graph.microsoft.com/beta/deviceAppManagement/mobileApps"

        url = base_url
        params = {}
        if filter_query:
            params["$filter"] = filter_query
        else:
            # Default to showing Win32 apps if possible
            # params["$filter"] = "isof('microsoft.graph.win32LobApp')"
            pass

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("value", [])
        except Exception as e:
            logger.error(f"Failed to list apps: {e}")
            raise e

    def search_apps(self, token, query):
        """
        Search apps by name.
        """
        escaped_query = query.replace("'", "''")
        filter_str = f"contains(displayName, '{escaped_query}')"
        return self.list_apps(token, filter_query=filter_str)

    def get_app_details(self, token, app_id):
        """
        Fetch details for a specific app.
        """
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        base_url = f"https://graph.microsoft.com/beta/deviceAppManagement/mobileApps/{app_id}"

        try:
            resp = requests.get(base_url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to get app details: {e}")
            raise e

    def list_app_assignments(self, token, app_id):
        """
        Fetch assignments for a specific app.
        """
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        base_url = f"https://graph.microsoft.com/beta/deviceAppManagement/mobileApps/{app_id}/assignments"

        try:
            resp = requests.get(base_url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json().get("value", [])
        except Exception as e:
            logger.error(f"Failed to fetch app assignments for {app_id}: {e}")
            return []

    def upload_powershell_script(self, token, name, description, script_content, run_as_account="system"):
        """
        Uploads a PowerShell script to Intune (Device Management Script).
        run_as_account: 'system' or 'user'
        """
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        base_url = "https://graph.microsoft.com/beta/deviceManagement/deviceManagementScripts"

        # Script content must be base64 encoded
        if isinstance(script_content, bytes):
            encoded_script = base64.b64encode(script_content).decode('utf-8')
        else:
            encoded_script = base64.b64encode(script_content.encode('utf-8')).decode('utf-8')

        payload = {
            "@odata.type": "#microsoft.graph.deviceManagementScript",
            "displayName": name,
            "description": description,
            "scriptContent": encoded_script,
            "runAsAccount": run_as_account,
            "enforceSignatureCheck": False,
            "runAs32Bit": False
        }

        try:
            resp = requests.post(base_url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            logger.info(f"Uploaded PowerShell Script: {name}")
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to upload PS script: {e}")
            raise

    def upload_remediation_script(self, token, name, description, detection_content, remediation_content, run_as_account="system"):
        """
        Uploads a Remediation Script (Proactive Remediation) to Intune.
        Requires valid detection and remediation scripts.
        """
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        base_url = "https://graph.microsoft.com/beta/deviceManagement/deviceHealthScripts"

        if isinstance(detection_content, bytes):
             enc_detection = base64.b64encode(detection_content).decode('utf-8')
        else:
             enc_detection = base64.b64encode(detection_content.encode('utf-8')).decode('utf-8')

        if isinstance(remediation_content, bytes):
             enc_remediation = base64.b64encode(remediation_content).decode('utf-8')
        else:
             enc_remediation = base64.b64encode(remediation_content.encode('utf-8')).decode('utf-8')

        payload = {
            "@odata.type": "#microsoft.graph.deviceHealthScript",
            "displayName": name,
            "description": description,
            "detectionScriptContent": enc_detection,
            "remediationScriptContent": enc_remediation,
            "runAsAccount": run_as_account,
            "enforceSignatureCheck": False,
            "runAs32Bit": False,
            "isGlobalScript": False
        }

        try:
            resp = requests.post(base_url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            logger.info(f"Uploaded Remediation Script: {name}")
            return resp.json()
        except Exception as e:
            # Check for license errors common with Remediations
            logger.error(f"Failed to upload Remediation: {e}")
            raise

    def upload_macos_shell_script(self, token, name, description, script_content, run_as_account="system"):
        """
        Uploads a Shell Script for macOS (deviceManagementScript).
        """
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        # Note: Endpoint for macOS scripts is slightly different or shared.
        # Actually it's deviceShellScripts for macOS in some API versions, or shared deviceManagementScripts with distinct styling.
        # Graph beta: /deviceManagement/deviceShellScripts
        base_url = "https://graph.microsoft.com/beta/deviceManagement/deviceShellScripts"

        encoded_script = base64.b64encode(script_content.encode('utf-8')).decode('utf-8')

        payload = {
            "@odata.type": "#microsoft.graph.deviceShellScript",
            "displayName": name,
            "description": description,
            "scriptContent": encoded_script,
            "runAsAccount": run_as_account, # 'system' or 'user'
            "retryCount": 3,
            "blockExecutionNotifications": True,
            "executionFrequency": "PT15M", # Example P15M = 15 min? Or standard ISO duration.
            # actually usually simple execution is once.
        }

        try:
            resp = requests.post(base_url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            logger.info(f"Uploaded MacOS Shell Script: {name}")
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to upload MacOS Shell Script: {e}")
            raise e

    def upload_mobile_lob_app(self, token, msi_path, app_info=None, progress_callback=None):
        """
        Uploads a Line-of-Business (LOB) MSI directly to Intune.
        Does NOT wrap as .intunewin.
        """
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        base_url = "https://graph.microsoft.com/beta/deviceAppManagement"

        msi_path = Path(msi_path)
        if not msi_path.exists():
            raise FileNotFoundError(f"MSI not found: {msi_path}")

        file_size = msi_path.stat().st_size
        file_name = msi_path.name

        try:
            # 1. Create MobileApp Entity
            # For MSI LOB, use 'microsoft.graph.windowsMobileMSI'
            if progress_callback:
                progress_callback(0.1, "Creating App Entry...")

            # Basic defaults if not provided
            # Basic defaults if not provided
            app_info = app_info or {}
            default_info = {
                "@odata.type": "#microsoft.graph.windowsMobileMSI",
                "displayName": app_info.get("displayName", file_name),
                "description": app_info.get("description", "Uploaded by SwitchCraft"),
                "publisher": app_info.get("publisher", "Unknown"),
                "owner": "",
                "developer": "",
                "notes": "",
                "fileName": file_name,
                "size": file_size,
                "productCode": app_info.get("productCode"), # Critical for MSI
                "productVersion": app_info.get("productVersion"), # Critical for MSI
                "identityVersion": app_info.get("productVersion"),
                "ignoreVersionDetection": False,
                "commandLine": app_info.get("installCommandLine", "/q"),
            }

            # Merge provided info
            allowed_keys = ["displayName", "description", "publisher", "productCode", "productVersion", "installCommandLine"]
            for k, v in app_info.items():
                if k in allowed_keys:
                    default_info[k] = v

            # Create App
            create_resp = requests.post(f"{base_url}/mobileApps", headers=headers, json=default_info, timeout=30)
            create_resp.raise_for_status()
            app_data = create_resp.json()
            app_id = app_data['id']
            logger.info(f"Created LOB App: {app_id}")

            # 2. Create Content Version
            if progress_callback:
                progress_callback(0.2, "Creating Content Version...")
            cv_payload = {
                "@odata.type": "#microsoft.graph.mobileAppContent",
            }
            cv_resp = requests.post(f"{base_url}/mobileApps/{app_id}/contentVersions", headers=headers, json=cv_payload, timeout=30)
            cv_resp.raise_for_status()
            cv_data = cv_resp.json()
            cv_id = cv_data['id']

            # 3. Create Content File Entry
            # For LOB, we don't need encryption info usually, but depends on endpoint.
            # windowsMobileMSI uses simple file upload usually?
            # Actually, standard flow: create file -> get upload URL -> upload -> commit.
            file_payload = {
                "@odata.type": "#microsoft.graph.mobileAppContentFile",
                "name": file_name,
                "size": file_size,
                "sizeEncrypted": file_size, # Not encrypted by us
                "manifest": None,
                "isDependency": False
            }

            file_resp = requests.post(f"{base_url}/mobileApps/{app_id}/contentVersions/{cv_id}/files", headers=headers, json=file_payload, timeout=30)
            file_resp.raise_for_status()
            file_data = file_resp.json()
            file_id = file_data['id']
            upload_url = file_data['uploadUrl']

            # 4. Upload File
            if progress_callback:
                progress_callback(0.4, "Uploading MSI...")

            with open(msi_path, 'rb') as f:
                 blob_headers = {"x-ms-blob-type": "BlockBlob"}
                 put_resp = requests.put(upload_url, headers=blob_headers, data=f, timeout=300)
                 put_resp.raise_for_status()

            # 5. Commit File
            if progress_callback:
                progress_callback(0.8, "Committing File...")

            commit_file = {}
            # Omit fileEncryptionInfo entirely for unencrypted content
            # (or some endpoints might require it to be absent, not null)

            requests.post(f"{base_url}/mobileApps/{app_id}/contentVersions/{cv_id}/files/{file_id}/commit", headers=headers, json=commit_file, timeout=60).raise_for_status()

            # 6. Commit Content Version
            if progress_callback:
                progress_callback(0.9, "Finalizing App...")
            requests.post(f"{base_url}/mobileApps/{app_id}/contentVersions/{cv_id}/commit", headers=headers, json={}, timeout=60).raise_for_status()

            if progress_callback:
                progress_callback(1.0, "Success!")
            return app_id

        except Exception as e:
            logger.error(f"LOB Upload failed: {e}")
            raise

    def add_supersedence(self, token, child_app_id, parent_app_id, uninstall_prev=True):
        """
        Sets child_app to supersede parent_app.
        """
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        base_url = "https://graph.microsoft.com/beta/deviceAppManagement/mobileAppRelationships"

        # Correct Payload for Supersedence
        payload = {
            "@odata.type": "#microsoft.graph.mobileAppSupersedence",
            "targetId": parent_app_id,
            "sourceId": child_app_id,
            "targetType": "parent",
            "supersedenceType": "replace" if uninstall_prev else "update"
        }

        try:
            resp = requests.post(base_url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            logger.info(f"Supersedence added: {child_app_id} -> {parent_app_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add supersedence: {e}")
            raise




    def list_groups(self, token, filter_query=None):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url = "https://graph.microsoft.com/v1.0/groups"
        params = {}
        if filter_query:
            params["$filter"] = filter_query

        try:
            all_groups = []
            while url:
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                all_groups.extend(data.get('value', []))

                # Check for pagination
                url = data.get('@odata.nextLink')
                params = None # Query params are part of nextLink

            return all_groups
        except Exception as e:
            logger.error(f"Failed to list groups: {e}")
            raise

    def create_group(self, token, name, description, group_types=None):
        """
        Creates a new group.
        group_types: ["Unified"] for M365, [] or None for Security.
        """
        if group_types is None:
            group_types = []

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url = "https://graph.microsoft.com/v1.0/groups"

        # M365 groups require mailEnabled=True, securityEnabled=False
        is_m365 = "Unified" in group_types

        payload = {
            "displayName": name,
            "description": description,
            "mailEnabled": is_m365,
            "securityEnabled": not is_m365,
            "mailNickname": name.replace(" ", "").lower(),
            "groupTypes": group_types
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            logger.info(f"Created group: {name}")
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to create group: {e}")
            raise

    def delete_group(self, token, group_id):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url = f"https://graph.microsoft.com/v1.0/groups/{group_id}"

        try:
            resp = requests.delete(url, headers=headers, timeout=30)
            resp.raise_for_status()
            logger.info(f"Deleted group: {group_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete group: {e}")
            raise e

    def list_group_members(self, token, group_id):
        """List members of a group."""
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/members"

        try:
            members = []
            while url:
                resp = requests.get(url, headers=headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                members.extend(data.get('value', []))
                url = data.get('@odata.nextLink')
            return members
        except Exception as e:
            logger.error(f"Failed to list group members: {e}")
            raise

    def add_group_member(self, token, group_id, user_id):
        """Add a member to a group."""
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/members/$ref"

        payload = {
            "@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{user_id}"
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            logger.info(f"Added member {user_id} to group {group_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add group member: {e}")
            raise

    def remove_group_member(self, token, group_id, user_id):
        """Remove a member from a group."""
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/members/{user_id}/$ref"

        try:
            resp = requests.delete(url, headers=headers, timeout=30)
            resp.raise_for_status()
            logger.info(f"Removed member {user_id} from group {group_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove group member: {e}")
            raise

    def search_users(self, token, query):
        """Search for users by displayName or userPrincipalName."""
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        # Select specific fields to optimize
        url = "https://graph.microsoft.com/v1.0/users"

        # OData filter for 'startswith' is common, or 'search' if consistency enabled.
        # Simple startswith on displayName or userPrincipalName.
        # Graph supports $search="displayName:foo" with ConsistencyLevel header.

        headers["ConsistencyLevel"] = "eventual"
        escaped = query.replace("'", "''")
        params = {
            "$search": f"\"displayName:{escaped}\" OR \"userPrincipalName:{escaped}\" OR \"mail:{escaped}\"",
            "$select": "id,displayName,userPrincipalName,mail,jobTitle"
        }

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get('value', [])
        except Exception as e:
            logger.error(f"Failed to search users: {e}")
            raise
