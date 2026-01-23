import json
import os
import sys
from pathlib import Path

def bake_translations():
    print("Baking translations...")
    lang_dir = Path("src/switchcraft/assets/lang")
    translations = {}
    for lang in ["en", "de"]:
        path = lang_dir / f"{lang}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                translations[lang] = json.load(f)
        else:
            print(f"Warning: Translation file missing: {path}")

    out_path = Path("src/switchcraft/utils/wasm_translations.py")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"TRANSLATIONS = {repr(translations)}\n")
    print(f"Translations baked to {out_path}")

def patch_index_html(dist_dir):
    print(f"Patching index.html in {dist_dir}...")
    path = Path(dist_dir) / "index.html"
    if not path.exists():
        print(f"Error: {path} not found")
        return

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace "Working..." with a better message
    content = content.replace(
        '<p>Working...</p>',
        '<p style="color: #95a5a6; font-family: \'Segoe UI\', sans-serif; font-size: 14px;">Initializing SwitchCraft...</p>'
    )

    # Modernize the loader colors
    content = content.replace('border: 16px solid #f3f3f3;', 'border: 8px solid #34495e;')
    content = content.replace('border-top: 16px solid #3498db;', 'border-top: 8px solid #3498db;')

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("index.html patched successfuly")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--bake":
        bake_translations()
    elif len(sys.argv) > 2 and sys.argv[1] == "--patch":
        patch_index_html(sys.argv[2])
    else:
        print("Usage: python prepare_web_dist.py [--bake | --patch <dist_dir>]")
