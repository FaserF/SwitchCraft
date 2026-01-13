import os
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

# AI Addon
ai_service_code = """
class SwitchCraftAI:
    def __init__(self):
        pass
    def update_context(self, data):
        pass
    def ask(self, query):
        return f"Simulated Response: You asked '{query}'. (This is a local placeholder AI)"
"""
create_addon("AI Assistant", "ai", {"service.py": ai_service_code})

# Advanced Addon
create_addon("Advanced Features", "advanced", {"start.txt": "Advanced features enabled"})

print("Done.")
