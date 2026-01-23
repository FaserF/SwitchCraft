import flet as ft
import logging
import subprocess
import os
from pathlib import Path
import sys

# Windows-specific imports (lazy loaded when needed)
winreg = None
win32api = None
if sys.platform == 'win32':
    try:
        import winreg
        import win32api
    except ImportError:
        pass  # Will show error when feature is used

logger = logging.getLogger(__name__)


class DetectionTesterView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page

        # State
        self.rule_type = ft.Dropdown(
            options=[
                ft.dropdown.Option("File", "File Path"),
                ft.dropdown.Option("Registry", "Registry Key"),
                ft.dropdown.Option("MSI", "MSI Product Code"),
                ft.dropdown.Option("Version", "File Version"),
                ft.dropdown.Option("Script", "PowerShell Script"),
            ],
            value="File",
            label="Detection Type",
        )
        self.rule_type.on_change = self._on_type_change

        # Input Fields
        self.path_field = ft.TextField(label="Path / Key / Code", expand=True)
        self.prop_field = ft.TextField(
            label="Value Name (Optional for Registry)", visible=False, expand=True
        )
        self.val_field = ft.TextField(
            label="Expected Value (Optional)", visible=False, expand=True
        )

        self.operator_dd = ft.Dropdown(
            label="Operator",
            options=[
                ft.dropdown.Option("=="),
                ft.dropdown.Option(">="),
            ],
            value=">=",
            visible=False,
            width=100
        )
        self.script_field = ft.TextField(
            label="PowerShell Script (Return 0 = Detected, Non-0 = Not Detected)",
            multiline=True,
            min_lines=5,
            visible=False,
            expand=True
        )

        self.check_btn = ft.FilledButton(
            content=ft.Row([ft.Icon(ft.Icons.PLAY_ARROW), ft.Text("Test Detection")], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor="GREEN",
            color="WHITE",
            on_click=self._run_check
        )

        self.result_area = ft.Container(
            padding=20,
            border_radius=10,
            bgcolor="BLACK",
            visible=False,
            width=500
        )

        if sys.platform != "win32":
            self.controls = [
                ft.Text("Live Detection Tester", size=28, weight=ft.FontWeight.BOLD),
                ft.Container(height=20),
                ft.Row([
                    ft.Icon(ft.Icons.WARNING, color="ORANGE", size=40),
                    ft.Text("This feature is only available on Windows.", size=16)
                ])
            ]
        else:
            self.controls = [
                ft.Text("Live Detection Tester", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("Verify your Intune detection rules locally before uploading.", size=16, color="ON_SURFACE_VARIANT"),
                ft.Container(height=20),
                ft.Row([self.rule_type, self.operator_dd, self.path_field]),
                self.script_field,
                ft.Row([self.prop_field, self.val_field]),
                ft.Container(height=10),
                self.check_btn,
                ft.Container(height=20),
                self.result_area
            ]

    def _on_type_change(self, e):
        t = self.rule_type.value
        if t == "Registry":
            self.path_field.label = "Registry Key (HKLM\\Software\\...)"
            self.prop_field.visible = True
            self.val_field.visible = True
            self.path_field.hint_text = "HKLM\\SOFTWARE\\Google\\Chrome\\BLBeacon"
        elif t == "File":
            self.path_field.label = "File or Folder Path"
            self.prop_field.visible = False
            self.val_field.visible = False
            self.path_field.hint_text = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        elif t == "MSI":
            self.path_field.label = "Product Code (GUID)"
            self.prop_field.visible = False
            self.val_field.visible = False
            self.path_field.hint_text = "{8A69D345-D564-463C-AFF1-A69D9E530F96}"
            self.operator_dd.visible = False
            self.script_field.visible = False
            self.path_field.visible = True
        elif t == "Version":
            self.path_field.label = "File Path"
            self.val_field.label = "Target Version"
            self.val_field.visible = True
            self.operator_dd.visible = True
            self.prop_field.visible = False
            self.script_field.visible = False
            self.path_field.visible = True
        elif t == "Script":
            self.path_field.visible = False
            self.prop_field.visible = False
            self.val_field.visible = False
            self.operator_dd.visible = False
            self.script_field.visible = True
        self.update()

    def _run_check(self, e):
        t = self.rule_type.value
        path = self.path_field.value

        if t != "Script" and not path:
            self._display_result(False, "Path/Key is required")
            return
        if t == "Script" and not self.script_field.value:
            self._display_result(False, "Script content is required")
            return

        detected = False
        msg = ""

        try:
            if t == "File":
                p = Path(path)
                if p.exists():
                    detected = True
                    msg = f"Found: {path}"
                else:
                    msg = f"Not Found: {path}"

            elif t == "Registry":
                detected, msg = self._check_registry(path, self.prop_field.value, self.val_field.value)

            elif t == "MSI":
                detected, msg = self._check_msi(path)

            elif t == "Version":
                detected, msg = self._check_file_version(path, self.operator_dd.value, self.val_field.value)

            elif t == "Script":
                detected, msg = self._check_script(self.script_field.value)

            self._display_result(detected, msg)

        except Exception as ex:
            self._display_result(False, f"Error: {ex}")

    def _check_registry(self, key_path, value_name, expected_value):
        # Parse HIVE
        key_path = key_path.upper()
        hive = winreg.HKEY_LOCAL_MACHINE
        sub_key = key_path

        if key_path.startswith("HKLM\\") or key_path.startswith("HKEY_LOCAL_MACHINE\\"):
            sub_key = key_path.replace("HKLM\\", "").replace("HKEY_LOCAL_MACHINE\\", "")
            hive = winreg.HKEY_LOCAL_MACHINE
        elif key_path.startswith("HKCU\\") or key_path.startswith("HKEY_CURRENT_USER\\"):
            sub_key = key_path.replace("HKCU\\", "").replace("HKEY_CURRENT_USER\\", "")
            hive = winreg.HKEY_CURRENT_USER

        try:
            with winreg.OpenKey(hive, sub_key, 0, winreg.KEY_READ) as key:
                if not value_name:
                    return True, "Key Exists"

                val, _ = winreg.QueryValueEx(key, value_name)
                if expected_value:
                    if str(val) == str(expected_value):
                        return True, f"Key & Value Match: {val}"
                    else:
                        return False, f"Value Mismatch. Found: {val}"
                return True, f"Value Found: {val}"
        except FileNotFoundError:
            return False, "Key or Value Not Found"
        except Exception as e:
            return False, str(e)

    def _check_msi(self, product_code):
        import ctypes
        # MsiQueryProductState
        INSTALLSTATE_DEFAULT = 5

        # Checking via MsiQueryProductStateW
        # But simpler logic: does it exist in Uninstall keys?
        # Actually proper way is MSI API.

        try:
            msi = ctypes.windll.msi
            state = msi.MsiQueryProductStateW(product_code)
            if state == INSTALLSTATE_DEFAULT:
                return True, "Product Check: INSTALLED"
            # 1: Advertised, 2: Absent ...
            if state != -1 and state != 2:  # 2 is absent
                return True, f"Product State: {state} (Likely Installed)"

            return False, "Product Not Found (State 2 or -1)"
        except Exception as e:
            return False, f"MSI Check Error: {e}"

    def _check_file_version(self, path, operator, target_version):
        if not Path(path).exists():
            return False, "File Not Found"

        try:
            # Get file version
            info = win32api.GetFileVersionInfo(path, "\\")
            ms = info['FileVersionMS']
            ls = info['FileVersionLS']
            # Version tuple
            v_major = win32api.HIWORD(ms)
            v_minor = win32api.LOWORD(ms)
            v_build = win32api.HIWORD(ls)
            v_revision = win32api.LOWORD(ls)
            current_ver_str = f"{v_major}.{v_minor}.{v_build}.{v_revision}"

            if not target_version:
                 return True, f"File Exists. Version: {current_ver_str}"

            # Simple comparison logic (needs proper version parsing)
            # Normalizing to list of ints for comparison with zero padding
            def parse_ver(v_str):
                return [int(x) for x in v_str.split('.')]

            curr_v_list = parse_ver(current_ver_str)
            target_v_list = parse_ver(target_version)

            # Pad lists to equal length
            max_len = max(len(curr_v_list), len(target_v_list))
            curr_v_list += [0] * (max_len - len(curr_v_list))
            target_v_list += [0] * (max_len - len(target_v_list))

            # operator
            match = False
            if operator == "==":
                match = curr_v_list == target_v_list
            elif operator == ">=":
                match = curr_v_list >= target_v_list

            if match:
                return True, f"Match: {current_ver_str} {operator} {target_version}"
            else:
                return False, f"Mismatch: {current_ver_str} not {operator} {target_version}"

        except Exception as e:
            return False, f"Version Check Error: {e}"

    def _check_script(self, script_content):
        # Run script in temp file
        import tempfile
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".ps1") as f:
                f.write(script_content)
                temp_path = f.name

            # Intune Detection Script logic:
            # "The script must return an exit code of 0 to indicate detection."
            # "It can also write to STDOUT."
            # Actually standard Intune discovery:
            # "Exit code 0 and STDOUT is not empty -> Detected"
            # "Exit code 0 and STDOUT empty -> Not Detected"
            # "Non-zero exit code -> Not Detected/Error"

            # Let's emulate that strict logic.

            cmd = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", temp_path]

            # Using startupinfo to hide window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            res = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)

            stdout = res.stdout.strip()
            stderr = res.stderr.strip()
            exit_code = res.returncode

            if exit_code == 0:
                if stdout:
                     return True, f"Detected (Exit 0 + Stdout): {stdout[:100]}..."
                else:
                     return False, "Not Detected (Exit 0 but Empty Stdout)"
            else:
                return False, f"Not Detected (Exit Code {exit_code}). Err: {stderr[:100]}"

        except Exception as e:
            return False, f"Script Execution Error: {e}"
        finally:
            # Ensure temp file is always cleaned up
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def _display_result(self, detected, message):
        self.result_area.visible = True
        icon = ft.Icons.CHECK_CIRCLE if detected else ft.Icons.CANCEL
        color = "GREEN" if detected else "RED"

        self.result_area.content = ft.Row([
            ft.Icon(icon, color=color, size=40),
            ft.Column([
                ft.Text("DETECTED" if detected else "NOT DETECTED", size=20, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(message, color="WHITE")
            ])
        ])
        self.result_area.bgcolor = "GREEN_900" if detected else "RED_900"
        self.update()
