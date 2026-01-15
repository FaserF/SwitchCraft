import unittest
import json
import re
import os
from pathlib import Path

class TestI18nIntegrity(unittest.TestCase):
    def setUp(self):
        # Locate lang dir
        # tests/test_i18n_integrity.py -> ../src/switchcraft/assets/lang
        base_dir = Path(__file__).parent.parent
        self.lang_dir = base_dir / "src" / "switchcraft" / "assets" / "lang"
        self.src_dir = base_dir / "src" / "switchcraft"

        with open(self.lang_dir / "en.json", "r", encoding="utf-8") as f:
            self.en = json.load(f)
        with open(self.lang_dir / "de.json", "r", encoding="utf-8") as f:
            self.de = json.load(f)

    def test_keys_symmetry(self):
        """Ensure EN and DE have the same keys."""
        en_keys = set(self.en.keys())
        de_keys = set(self.de.keys())

        missing_in_de = en_keys - de_keys
        missing_in_en = de_keys - en_keys

        self.assertFalse(missing_in_de, f"Missing keys in DE: {missing_in_de}")
        self.assertFalse(missing_in_en, f"Missing keys in EN: {missing_in_en}")

    def test_placeholders_consistency(self):
        """Ensure placeholders like {version} match in both languages."""
        for key in self.en:
            if key not in self.de: continue

            en_val = str(self.en[key])
            de_val = str(self.de[key])

            en_params = set(re.findall(r"\{(\w+)\}", en_val))
            de_params = set(re.findall(r"\{(\w+)\}", de_val))

            self.assertEqual(en_params, de_params, f"Placeholder mismatch for key '{key}'. EN: {en_params}, DE: {de_params}")

    def test_no_duplicate_keys(self):
        """Ensure no duplicate keys appear in JSON files (which usually overrides previous ones silently)."""
        import collections

        def find_duplicates(filepath):

            with open(filepath, "r", encoding="utf-8") as f:
                # We need to manually parse or hook into load
                # Standard json.load objects_pairs_hook can detect duplicates if we check keys list
                raw_content = f.read()

            # Helper to hook into json decoder
            duplicates = []
            def dict_checker(pairs):
                keys = [k for k, v in pairs]
                counts = collections.Counter(keys)
                for k, count in counts.items():
                    if count > 1:
                        duplicates.append(k)
                return dict(pairs)

            json.loads(raw_content, object_pairs_hook=dict_checker)
            return duplicates

        en_dupes = find_duplicates(self.lang_dir / "en.json")
        de_dupes = find_duplicates(self.lang_dir / "de.json")

        self.assertFalse(en_dupes, f"Duplicate keys in EN: {en_dupes}")
        self.assertFalse(de_dupes, f"Duplicate keys in DE: {de_dupes}")

    def test_codebase_keys_exist(self):
        """Scan codebase for i18n.get usage and verify keys exist in JSON."""
        # Regex to find i18n.get("key")
        # Supports ' and "
        pattern = re.compile(r'i18n\.get\s*\(\s*[\'"]([^\'"]+)[\'"]')

        found_keys = set()

        for root, _, files in os.walk(self.src_dir):
            for file in files:
                if file.endswith(".py"):
                    path = Path(root) / file
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                            matches = pattern.findall(content)
                            for m in matches:
                                found_keys.add(m)
                    except Exception as e:
                        print(f"Could not read {path}: {e}")

        # Check validity
        # Some keys might be dynamic, so we might need a whitelist of allowed failures or strict check
        # For now, let's report missing ones
        missing = []
        for k in found_keys:

            if k not in self.en:
                # Improve heuristic: keys usually are lowercase/snake_case/kebab-case.
                # If they contain spaces or look like a full sentence, they might be dynamic content or default values.
                # Also if it looks like a variable concatenation (e.g. f"{var}"), regex might not catch it but
                # we are looking at literal strings passed to single argument.

                # Check if it is a valid identifier-like string
                if re.match(r'^[a-z0-9_.-]+$', k):
                     missing.append(k)
                else:
                     # Likely dynamic content or sentence used as default fallback in some legacy calls
                     pass

        # We know some keys might be constructed dynamically, so we filter out known false positives checks if needed
        # But user asked to "Detect missing translations".
        # Let's Assert.

        # Filter out dynamic keys if possible (if they look like variable names inside string?)
        # The regex captures LITERALS only.
        # e.g. i18n.get("foo") -> foo
        # i18n.get(variable) -> Regex won't match (no quotes).

        self.assertFalse(missing, f"Found i18n keys in code missing from JSON: {missing}")

if __name__ == '__main__':
    unittest.main()
