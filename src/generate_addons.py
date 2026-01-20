import zipfile
import json
from pathlib import Path

def create_addon(name, addon_id, files):
    base_dir = Path("src/switchcraft/assets/addons")
    base_dir.mkdir(parents=True, exist_ok=True)

    zip_path = base_dir / f"{addon_id}.zip"

    with zipfile.ZipFile(zip_path, 'w') as z:
        # Manifest
        manifest = {
            "id": addon_id,
            "name": name,
            "version": "1.0.0",
            "author": "SwitchCraft Internal",
            "description": f"Bundled {name} for SwitchCraft"
        }
        z.writestr("manifest.json", json.dumps(manifest, indent=2))

        # Files
        for fname, content in files.items():
            z.writestr(fname, content)

    print(f"Created {zip_path}")

def main():
    # AI Addon
    ai_service_code = """
class SwitchCraftAI:
    def __init__(self):
        self.ctx = {}
    def update_context(self, data):
        self.ctx = data
    def ask(self, query):
        q = query.lower()
        if "hi" in q or "hallo" in q:
            return "Hallo! Ich bin der interner SwitchCraft AI Helper. Wie kann ich dir heute beim Paketieren helfen?"
        if "who are you" in q or "wer bist du" in q:
            return "Ich bin der integrierte SwitchCraft AI Assistent. Ich kann dir bei Silent-Switches, MSI-Properties und Intune-Deployments helfen."
        if "silent" in q or "switches" in q:
            sw = self.ctx.get("install_silent", "/S")
            return f"Für dieses Paket wurden folgende Silent-Switches erkannt: `{sw}`. Du kannst diese im Packaging Wizard noch anpassen."
        if "intune" in q:
            return "Um Apps nach Intune hochzuladen, stelle sicher, dass du die Graph API Credentials in den Einstellungen hinterlegt hast."
        return f"Ich habe deine Frage zu '{query}' verstanden, kann aber ohne aktive Verbindung zu Gemini oder OpenAI keine tiefergehende Analyse durchführen. Nutze den Packaging Wizard für automatische Erkennungen!"
"""
    create_addon("AI Assistant", "ai", {"service.py": ai_service_code})

    # Advanced Addon
    create_addon("Advanced Features", "advanced", {"start.txt": "Advanced features enabled"})

    # Winget Addon
    # Bundle the local source file from switchcraft_winget package into the addon zip
    winget_pkg_dir = Path("src/switchcraft_winget/utils")
    winget_source = winget_pkg_dir / "winget.py"
    static_data = winget_pkg_dir / "static_data.json"

    if winget_source.exists():
        files = {
            "utils/winget.py": winget_source.read_text(encoding="utf-8"),
            "utils/__init__.py": "" # Make utils a package
        }

        if static_data.exists():
            files["utils/static_data.json"] = static_data.read_text(encoding="utf-8")
        else:
            print(f"Warning: Static data not found at {static_data}")

        create_addon("Winget Integration", "winget", files)
    else:
        print(f"Warning: Winget source not found at {winget_source}")

    print("Done.")

if __name__ == "__main__":
    main()
