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
        if "who are you" in q: return "I am SwitchCraft AI"
        if "wer bist du" in q: return "Ich bin SwitchCraft AI"
        if "silent" in q or "switches" in q:
            sw = self.ctx.get("install_silent", "/S")
            if "what" in q:
                return f"detected these silent switches: {sw}"
            return f"folgende Switches gefunden: {sw}"
        return f"Simulated Response: You asked '{query}'. (This is a local placeholder AI)"
"""
    create_addon("AI Assistant", "ai", {"service.py": ai_service_code})

    # Advanced Addon
    create_addon("Advanced Features", "advanced", {"start.txt": "Advanced features enabled"})

    # Winget Addon
    # Bundle the local source file from utils/winget.py into the addon zip
    winget_source = Path("src/switchcraft/utils/winget.py")
    if winget_source.exists():
        content = winget_source.read_text(encoding="utf-8")
        create_addon("Winget Integration", "winget", {
            "utils/winget.py": content,
            "utils/__init__.py": "" # Make utils a package
        })
    else:
        print("Warning: Winget source not found at src/switchcraft/utils/winget.py")

    print("Done.")

if __name__ == "__main__":
    main()
