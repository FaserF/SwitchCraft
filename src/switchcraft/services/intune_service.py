import sys
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
from switchcraft.utils.shell_utils import ShellUtils
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
        from switchcraft.utils.config import SwitchCraftConfig

        # Check for custom path in config first
        custom_path = SwitchCraftConfig.get_value("IntuneToolPath")
        if custom_path and os.path.exists(custom_path):
            p = Path(custom_path)
            if p.is_file():
                self.tool_path = p
                self.tools_dir = p.parent
            else:
                self.tools_dir = p
                self.tool_path = self.tools_dir / self.TOOL_FILENAME
        else:
            if tools_dir:
                self.tools_dir = Path(tools_dir)
                self.tool_path = self.tools_dir / self.TOOL_FILENAME
            else:
                # Search priority:
                # 1. Standard AppData: %APPDATA%\FaserF\SwitchCraft\tools
                # 2. Legacy/User Home: ~/.switchcraft/tools

                paths_to_check = []

                if os.name == 'nt':
                    app_data = os.environ.get("APPDATA")
                    if app_data:
                        paths_to_check.append(Path(app_data) / "FaserF" / "SwitchCraft" / "tools")

                # Always check home dir as fallback
                paths_to_check.append(Path.home() / ".switchcraft" / "tools")

                found = False
                for p_dir in paths_to_check:
                    t_path = p_dir / self.TOOL_FILENAME
                    if t_path.exists():
                        self.tools_dir = p_dir
                        self.tool_path = t_path
                        found = True
                        break

                if not found:
                    # Default to first preferred path (AppData on Windows) for download
                    if paths_to_check:
                        self.tools_dir = paths_to_check[0]
                    else:
                        self.tools_dir = Path.home() / ".switchcraft" / "tools"
                    self.tool_path = self.tools_dir / self.TOOL_FILENAME

    def is_tool_available(self) -> bool:
        return self.tool_path.exists()

    def get_tool_version(self) -> str:
        """Returns the file version of the IntuneWinAppUtil.exe if available."""
        if not self.tool_path.exists():
            return None

        try:
            # PowerShell method to get file version (robust on Windows)
            # Use single quotes for the path to avoid issues with double quotes if the path has spaces
            # Ensure we use the full resolved path
            resolved_path = str(self.tool_path.resolve())
            cmd = f"(Get-Item '{resolved_path}').VersionInfo.FileVersion"
            result = ShellUtils.run_command(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd], silent=True)
            if result and result.returncode == 0:
                ver = result.stdout.strip()
                if ver:
                    return ver

            # Fallback or Non-Windows (unlikely for this tool)
            return "Unknown"
        except Exception as e:
            logger.warning(f"Failed to get tool version: {e}")
            return "Error"

    def download_tool(self) -> bool:
        """Downloads the IntuneWinAppUtil.exe from Microsoft."""
        try:
            # Always download to the calculated tools_dir (which might be custom or default)
            self.tools_dir.mkdir(parents=True, exist_ok=True)
            # target_path = self.tools_dir / self.TOOL_FILENAME

            # If the user configured a file path specifically, we should probably update THAT specific file
            # But self.tool_path is already set to it.

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

        # Check config for "Show Console" preference
        # If ShowIntuneConsole is True, we want silent=False
        from switchcraft.utils.config import SwitchCraftConfig
        show_console = SwitchCraftConfig.get_value("ShowIntuneConsole", False)
        silent_execution = not show_console

        logger.info(f"Running IntuneWinAppUtil: {cmd} (Show Console: {show_console})")

        startupinfo = None
        if silent_execution and sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        try:
            process = ShellUtils.Popen(
                cmd,
                silent=False, # We handle hiding via startupinfo manually to avoid "No Window" vs "Hidden Window" conflict
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='cp1252', # Windows tool output encoding
                startupinfo=startupinfo,
                bufsize=1,
                universal_newlines=True
            )
            if not process:
                raise RuntimeError("Failed to start process (likely WASM environment)")

            with process:

                full_output = []

                # Stream output
                for line in process.stdout:
                    line_str = line
                    full_output.append(line_str)
                    # If a callback is provided (e.g. for UI)
                    if progress_callback:
                        progress_callback(line_str)

                # No need to call process.wait() explicitly as 'with' handles it,
                # but we can do it if we want the return code check immediately after loop
                # The loop ends when stdout closes (process exit usually)

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
            # Default limits and select to improve performance
            params["$top"] = "100"
            params["$select"] = "id,displayName,publisher,appType,largeIcon,iconUrl,logoUrl"

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30, stream=False)
            resp.raise_for_status()
            data = resp.json()
            return data.get("value", [])
        except requests.exceptions.Timeout as e:
            logger.error("Request to Graph API timed out after 30 seconds")
            raise requests.exceptions.Timeout("Request timed out. The server took too long to respond.") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error in list_apps: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to list apps: {e}")
            raise e

    def search_apps(self, token, query):
        """
        Finds Intune apps whose displayName contains the provided query using case-insensitive matching.

        Attempts a server-side case-insensitive filter first (using tolower). If that is not supported or returns no results, falls back to a server-side contains filter and then applies client-side case-insensitive filtering. As a last resort, retrieves all apps and filters client-side. An empty or whitespace-only query returns an empty list.

        Parameters:
            token: Authentication token used for Graph API requests.
            query: Substring to search for in app display names.

        Returns:
            A list of app objects whose `displayName` contains `query`, matched case-insensitively.

        Raises:
            Exception: Re-raises the original error from the Graph requests if all search attempts fail.
        """
        if not query or not query.strip():
            return []

        # Escape single quotes for OData
        escaped_query = query.replace("'", "''")

        # Try case-insensitive search using tolower() - if that fails, fall back to regular contains
        # Some Graph API versions might not support tolower(), so we try both
        try:
            filter_str = f"contains(tolower(displayName), tolower('{escaped_query}'))"
            apps = self.list_apps(token, filter_query=filter_str)
            # If we got results, return them
            if apps:
                return apps
        except Exception as e:
            logger.debug(f"tolower() search failed, trying simple contains: {e}")

        # Fallback: simple contains (case-sensitive but more compatible)
        try:
            filter_str = f"contains(displayName, '{escaped_query}')"
            apps = self.list_apps(token, filter_query=filter_str)
            # Filter results client-side for case-insensitive match
            query_lower = query.lower()
            filtered_apps = [app for app in apps if query_lower in app.get('displayName', '').lower()]
            return filtered_apps
        except requests.exceptions.Timeout:
            # Re-raise timeout immediately - don't try fallbacks
            raise
        except requests.exceptions.RequestException:
            # Re-raise network errors immediately
            raise
        except Exception as e:
            logger.error(f"Search failed with both methods: {e}")
            # Last resort: get all apps and filter client-side
            try:
                all_apps = self.list_apps(token)
                query_lower = query.lower()
                return [app for app in all_apps if query_lower in app.get('displayName', '').lower()]
            except requests.exceptions.Timeout:
                raise
            except requests.exceptions.RequestException:
                raise
            except Exception as e2:
                logger.error(f"Fallback search also failed: {e2}")
                raise e  # Re-raise original error

    def get_app_details(self, token, app_id):
        """
        Retrieve details for a specific Intune mobile app.

        Parameters:
            token (str): OAuth2 access token with Graph API permissions.
            app_id (str): The mobileApp resource identifier.

        Returns:
            dict: JSON-decoded app resource as returned by Microsoft Graph.
        """
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        base_url = f"https://graph.microsoft.com/beta/deviceAppManagement/mobileApps/{app_id}"

        try:
            resp = requests.get(base_url, headers=headers, timeout=30, stream=False)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timed out while getting app details for {app_id}")
            raise requests.exceptions.Timeout("Request timed out. The server took too long to respond.") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error getting app details: {e}")
            raise requests.exceptions.RequestException(f"Network error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Failed to get app details: {e}")
            raise e

    def list_app_assignments(self, token, app_id):
        """
        Fetch assignments for a specific app.
        Raises an exception if the request fails.
        """
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        base_url = f"https://graph.microsoft.com/beta/deviceAppManagement/mobileApps/{app_id}/assignments"

        try:
            resp = requests.get(base_url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json().get("value", [])
        except Exception as e:
            logger.error(f"Failed to fetch app assignments for {app_id}: {e}")
            raise e

    def update_app(self, token, app_id, app_data):
        """
        Update an Intune mobile app using PATCH request.

        Parameters:
            token (str): OAuth2 access token with Graph API permissions.
            app_id (str): The mobileApp resource identifier.
            app_data (dict): Dictionary containing fields to update (e.g., displayName, description, etc.)

        Returns:
            dict: Updated app resource as returned by Microsoft Graph.
        """
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        base_url = f"https://graph.microsoft.com/beta/deviceAppManagement/mobileApps/{app_id}"

        try:
            resp = requests.patch(base_url, headers=headers, json=app_data, timeout=60)
            resp.raise_for_status()
            logger.info(f"Successfully updated app {app_id}")

            # Handle empty/no-content responses (204 No Content or empty body)
            if resp.status_code == 204 or not resp.content:
                # PATCH returned no content, fetch the updated resource
                logger.debug(f"PATCH returned empty response for app {app_id}, fetching updated resource")
                return self.get_app_details(token, app_id)

            # Try to parse JSON response
            try:
                return resp.json()
            except (ValueError, requests.exceptions.JSONDecodeError) as json_err:
                # JSON parsing failed, fall back to fetching the resource
                logger.warning(f"Failed to parse PATCH response JSON for app {app_id}: {json_err}, fetching updated resource")
                return self.get_app_details(token, app_id)
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timed out while updating app {app_id}")
            raise requests.exceptions.Timeout("Request timed out. The server took too long to respond.") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error updating app {app_id}: {e}")
            raise requests.exceptions.RequestException(f"Network error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Failed to update app {app_id}: {e}")
            raise e

    def update_app_assignments(self, token, app_id, assignments):
        """
        Update app assignments by replacing all existing assignments.

        Parameters:
            token (str): OAuth2 access token with Graph API permissions.
            app_id (str): The mobileApp resource identifier.
            assignments (list): List of assignment dictionaries, each with:
                - target: dict with groupId or "@odata.type": "#microsoft.graph.allDevicesAssignmentTarget" / "#microsoft.graph.allLicensedUsersAssignmentTarget"
                - intent: "required", "available", or "uninstall"
                - settings: dict (optional)

        Returns:
            bool: True if successful
        """
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        base_url = f"https://graph.microsoft.com/beta/deviceAppManagement/mobileApps/{app_id}/assignments"

        # First, delete all existing assignments
        try:
            existing = self.list_app_assignments(token, app_id)
            for assignment in existing:
                assignment_id = assignment.get("id")
                if assignment_id:
                    delete_url = f"{base_url}/{assignment_id}"
                    delete_resp = requests.delete(delete_url, headers=headers, timeout=30)
                    delete_resp.raise_for_status()
        except Exception as e:
            logger.warning(f"Failed to delete existing assignments: {e}")
            # Continue anyway - might be a permission issue

        # Then, create new assignments
        for assignment in assignments:
            try:
                resp = requests.post(base_url, headers=headers, json=assignment, timeout=60)
                resp.raise_for_status()
                logger.info(f"Created assignment for app {app_id}: {assignment.get('intent')}")
            except Exception as e:
                logger.error(f"Failed to create assignment: {e}")
                raise e

        return True

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