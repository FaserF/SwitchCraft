"""
Custom URL Protocol Handler Registration for SwitchCraft.

Registers the `switchcraft://` protocol to allow deep linking into the app.
This is used by Windows toast notifications action buttons.

Usage:
    switchcraft://notifications  - Opens the notification drawer
    switchcraft://settings       - Opens settings
    switchcraft://updates        - Opens update settings

The protocol is registered in HKEY_CURRENT_USER\Software\Classes\switchcraft
"""

import logging
import sys
import os

logger = logging.getLogger(__name__)


def register_protocol_handler():
    """
    Register the switchcraft:// protocol handler in Windows Registry.
    This allows clicking links like switchcraft://notifications to open the app.
    """
    if sys.platform != "win32":
        logger.debug("Protocol handler registration skipped (non-Windows)")
        return False

    try:
        import winreg

        # Get the path to the current executable
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            exe_path = sys.executable
        else:
            # Running as script - use pythonw to avoid console
            python_exe = sys.executable.replace("python.exe", "pythonw.exe")
            if not os.path.exists(python_exe):
                python_exe = sys.executable

            # Point to modern_main.py
            script_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "modern_main.py"
            )
            exe_path = f'"{python_exe}" "{script_path}"'

        protocol_name = "switchcraft"
        protocol_description = "URL:SwitchCraft Protocol"

        # Create the protocol key under HKEY_CURRENT_USER (no admin needed)
        key_path = f"Software\\Classes\\{protocol_name}"

        # Main protocol key
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, protocol_description)
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")

        # shell\open\command subkey
        command_path = f"{key_path}\\shell\\open\\command"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, command_path) as key:
            # The %1 is replaced with the full URL when invoked
            command = f'{exe_path} --protocol "%1"'
            winreg.SetValue(key, "", winreg.REG_SZ, command)

        # Optional: Set default icon
        icon_path = f"{key_path}\\DefaultIcon"
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, icon_path) as key:
                if getattr(sys, 'frozen', False):
                    icon_file = sys.executable
                else:
                    icon_file = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "assets", "switchcraft_logo.ico"
                    )
                if os.path.exists(icon_file):
                    winreg.SetValue(key, "", winreg.REG_SZ, icon_file)
        except Exception:
            pass  # Icon is optional

        logger.info(f"Registered protocol handler: {protocol_name}://")
        return True

    except ImportError:
        logger.warning("winreg module not available (non-Windows?)")
        return False
    except PermissionError as e:
        logger.error(f"Permission denied registering protocol handler: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to register protocol handler: {e}")
        return False


def unregister_protocol_handler():
    """Remove the switchcraft:// protocol handler from Windows Registry."""
    if sys.platform != "win32":
        return False

    try:
        import winreg

        protocol_name = "switchcraft"
        key_path = f"Software\\Classes\\{protocol_name}"

        # Delete the entire key tree
        def delete_key_recursive(root, path):
            try:
                with winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS) as key:
                    # Delete all subkeys first
                    while True:
                        try:
                            subkey = winreg.EnumKey(key, 0)
                            delete_key_recursive(root, f"{path}\\{subkey}")
                        except OSError:
                            break
                winreg.DeleteKey(root, path)
            except FileNotFoundError:
                pass

        delete_key_recursive(winreg.HKEY_CURRENT_USER, key_path)
        logger.info(f"Unregistered protocol handler: {protocol_name}://")
        return True

    except Exception as e:
        logger.error(f"Failed to unregister protocol handler: {e}")
        return False


def parse_protocol_url(url: str) -> dict:
    """
    Parse a switchcraft:// URL into action and parameters.

    Examples:
        switchcraft://notifications -> {"action": "notifications"}
        switchcraft://settings/updates -> {"action": "settings", "sub": "updates"}
    """
    if not url or not url.startswith("switchcraft://"):
        return {"action": "home"}

    # Remove the protocol prefix
    path = url.replace("switchcraft://", "").strip("/")

    if not path:
        return {"action": "home"}

    parts = path.split("/")
    result = {"action": parts[0]}

    if len(parts) > 1:
        result["sub"] = parts[1]

    return result


def is_protocol_registered() -> bool:
    """Check if the switchcraft:// protocol is registered."""
    if sys.platform != "win32":
        return False

    try:
        import winreg
        key_path = "Software\\Classes\\switchcraft"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path):
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False
