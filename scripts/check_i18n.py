import json
import os
import re
import sys
from pathlib import Path

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def flatten_dict(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def check_structure(en_path, de_path):
    print("Checking JSON structure...")
    en_data = flatten_dict(load_json(en_path))
    de_data = flatten_dict(load_json(de_path))

    en_keys = set(en_data.keys())
    de_keys = set(de_data.keys())

    missing_in_de = en_keys - de_keys
    missing_in_en = de_keys - en_keys

    errors = 0
    if missing_in_de:
        print(f"ERROR: Missing keys in DE: {missing_in_de}")
        errors += len(missing_in_de)

    if missing_in_en:
        print(f"WARNING: Extra keys in DE (missing in EN): {missing_in_en}")
        # Not a strict error, but good to know

    if errors == 0:
        print("Structure check passed.")
    return errors

def scan_for_hardcoded_strings(src_dir):
    print(f"Scanning for potentially hardcoded strings in {src_dir}...")
    # Heuristic: Find strings that look like sentences or UI labels
    # - Starts with capital letter
    # - Contains spaces
    # - Not inside log calls (logger.debug, etc - simplified check)
    # - Not inside imports

    string_pattern = re.compile(r'(?<!_)["\']([A-Z][a-zA-Z0-9\s\.\:\!\?]{5,})["\']')

    # Ignore list
    ignore_files = ["check_i18n.py", "test_", "conftest.py"]
    ignore_strings = ["SwitchCraft", "Windows", "Linux", "MacOS", "Program Files", "GitHub", "utf-8", "true", "false"]

    errors = 0
    for root, _, files in os.walk(src_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            if any(ign in file for ign in ignore_files):
                continue

            path = Path(root) / file
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()

                lines = content.splitlines()
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line.startswith("#"):
                        continue
                    if "logger." in line or "print(" in line:
                        continue # Assume logs/debug prints are fine

                    matches = string_pattern.findall(line)
                    for match in matches:
                        if any(ign in match for ign in ignore_strings):
                            continue

                        # Heuristic: If it has spaces and is not just a path
                        if " " in match and "/" not in match and "\\" not in match:
                             print(f"POTENTIAL HARDCODED STRING in {file}:{i+1}: \"{match}\"")
                             # We won't fail the build for this yet, as it produces false positives (SQL, paths with spaces etc)
                             # errors += 1
            except Exception as e:
                print(f"Could not read {path}: {e}")

    return errors

def main():
    base_dir = Path(__file__).parent.parent
    src_dir = base_dir / "src"
    assets_dir = src_dir / "switchcraft" / "assets" / "lang"

    en_file = assets_dir / "en.json"
    de_file = assets_dir / "de.json"

    if not en_file.exists() or not de_file.exists():
        print(f"Language files not found at {assets_dir}")
        sys.exit(1)

    errors = check_structure(en_file, de_file)

    # Optional: Enable hardcoded string check failure if needed
    # errors += scan_for_hardcoded_strings(src_dir)
    scan_for_hardcoded_strings(src_dir)

    if errors > 0:
        print(f"FAILED: Found {errors} i18n issues.")
        sys.exit(1)

    print("SUCCESS: i18n checks passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
