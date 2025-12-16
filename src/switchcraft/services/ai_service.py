import re

class SwitchCraftAI:
    """
    A rule-based 'Mini KI' expert system for packaging advice.
    Does not use external LLMs, runs locally.
    """

    def __init__(self):
        self.context = {} # Stores current analysis data

    def update_context(self, data: dict):
        """Updates the context with the latest analysis results."""
        self.context = data

    def ask(self, query: str) -> str:
        """
        Determines the answer based on query patterns and current context.
        """
        q = query.lower()

        # 1. Context-Aware Questions
        if "switch" in q or "silent" in q or "install" in q:
            if "how" in q or "what" in q:
                if self.context:
                    install_type = self.context.get("type", "Unknown")
                    switches = self.context.get("install_silent", "Unknown")

                    if install_type == "msi":
                        return (f"This is an MSI file. You should use standard MSI switches.\n"
                                f"Suggested command: msiexec /i \"{self.context.get('filename','')}\" /qn /norestart")
                    elif switches and switches != "Unknown":
                        return (f"For this {install_type} installer, I detected these silent switches:\n"
                                f"**{switches}**\n\n"
                                f"Try running: {self.context.get('filename','file.exe')} {switches}")
                    else:
                        return ("I analyzed the file but couldn't find confirmed silent switches. "
                                "It might not support silent installation, or requires a custom response file (iss/answer file).")
                else:
                    return "I haven't analyzed a file yet. Please drag and drop an installer first, then I can tell you the switches."

        # 2. General Knowledge Base
        rules = {
            r"msi": "MSI (Microsoft Installer) files are standard database-based installers. They almost always support '/qn' for silent install and '/x' for uninstall.",
            r"inno": "Inno Setup installers usually support '/VERYSILENT' and '/SUPPRESSMSGBOXES'.",
            r"nsis": "NSIS installers usually use '/S' (case sensitive!) for silent installation.",
            r"installshield": "InstallShield often uses '/s' and sometimes requires a response file created with '/r'.",
            r"intune": "For Intune, always ensure your script handles return codes correctly and suppresses all UI. Return 0 for success, 3010 for soft reboot.",
            r"error 1603": "Error 1603 is a generic MSI error 'Fatal error during installation'. It often means permission issues, or a prerequisite is missing.",
            r"error 1618": "Error 1618 means 'Another installation is already in progress'. Check if msiexec is already running.",
            r"powershell": "SwitchCraft can generate a PowerShell script for you! Check the 'Analyzer' tab results.",
        }

        for pattern, response in rules.items():
            if re.search(pattern, q):
                return response

        # 3. Default Fallback
        return ("I'm a specialized packaging assistant. I can help with:\n"
                "- Finding silent switches (Drag & Drop a file)\n"
                "- Explaining installer types (MSI, Inno, NSIS)\n"
                "- Intune error codes (1603, 1618)\n\n"
                "Updates: I'm running locally 🔒")
