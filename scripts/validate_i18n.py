import json
import os
import sys
from pathlib import Path

def validate_translations():
    lang_dir = Path("src/switchcraft/assets/lang")
    if not lang_dir.exists():
        print(f"Error: Language directory {lang_dir} not found.")
        return False

    en_path = lang_dir / "en.json"
    de_path = lang_dir / "de.json"

    if not en_path.exists() or not de_path.exists():
        print("Error: Missing en.json or de.json.")
        return False

    with open(en_path, "r", encoding="utf-8") as f:
        en_data = json.load(f)
    with open(de_path, "r", encoding="utf-8") as f:
        de_data = json.load(f)

    en_keys = set(en_data.keys())
    de_keys = set(de_data.keys())

    missing_in_de = en_keys - de_keys
    missing_in_en = de_keys - en_keys

    success = True

    if missing_in_de:
        print(f"FAILED: Keys present in en.json but missing in de.json ({len(missing_in_de)}):")
        for key in sorted(missing_in_de):
            print(f"  - {key}")
        success = False

    if missing_in_en:
        print(f"FAILED: Keys present in de.json but missing in en.json ({len(missing_in_en)}):")
        for key in sorted(missing_in_en):
            print(f"  - {key}")
        success = False

    if success:
        print(f"SUCCESS: All {len(en_keys)} translation keys matched between en.json and de.json.")

    return success

if __name__ == "__main__":
    if not validate_translations():
        sys.exit(1)
    sys.exit(0)
