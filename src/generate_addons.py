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
    ai_src_dir = Path("src/switchcraft_ai")
    ai_service = ai_src_dir / "service.py"
    ai_manifest = ai_src_dir / "manifest.json"

    if ai_service.exists() and ai_manifest.exists():
        files = {
            "service.py": ai_service.read_text(encoding="utf-8")
        }
        with open(ai_manifest, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        # We use a custom manifest in create_addon, but we can bypass it
        # Or just use the real values
        base_dir = Path("src/switchcraft/assets/addons")
        base_dir.mkdir(parents=True, exist_ok=True)
        zip_path = base_dir / "ai.zip"
        with zipfile.ZipFile(zip_path, 'w') as z:
            z.writestr("manifest.json", json.dumps(manifest, indent=2))
            z.writestr("service.py", files["service.py"])
        print(f"Created {zip_path} from real source")
    else:
        # Mock / Fallback AI Addon (Previous logic)
        ai_service_code = """
class SwitchCraftAI:
    def __init__(self):
        self.ctx = {}
    def update_context(self, data):
        self.ctx = data
    def ask(self, query):
        return "Ich bin der interner SwitchCraft AI Helper. (Mock)"
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
