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

    custom_css = """
    <style>
        #loading {
            background-color: #1a1c1e !important;
            display: flex;
            justify-content: center;
            align-items: center;
            flex-direction: column;
        }
        .lds-ring div { border-color: #0066cc transparent transparent transparent !important; }

        /* Attempt to target common loading text classes if they exist */
        #loading p, .loading-text {
            color: #bdc3c7 !important;
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 16px;
            letter-spacing: 0.5px;
            margin-top: 20px;
        }
    </style>
    """

    # Insert CSS before </head>
    if "</head>" in content:
        content = content.replace("</head>", f"{custom_css}\n</head>")

    # Replace the text "Working..." if found
    if "Working..." in content:
        content = content.replace("Working...", "Initializing SwitchCraft...")
        print("Replaced 'Working...' text.")
    elif "Loading..." in content:
        content = content.replace("Loading...", "Initializing SwitchCraft...")
        print("Replaced 'Loading...' text.")
    else:
        # Fallback: Flutter Web often puts the loading logic in 'flutter_service_worker.js' or main.dart.js
        # But Flet's index.html template usually exposes it.
        # If not found, we might need to rely on the CSS overlay approach or look for JS string.
        print("Warning: Could not find 'Working...' or 'Loading...' text to replace.")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("index.html patched.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--bake":
        bake_translations()
    elif len(sys.argv) > 2 and sys.argv[1] == "--patch":
        patch_index_html(sys.argv[2])
    else:
        print("Usage: python prepare_web_dist.py [--bake | --patch <dist_dir>]")
