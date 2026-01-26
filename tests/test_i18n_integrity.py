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
        self.src_dir = base_dir / "src" # Broaden to all src, including addons

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
            if key not in self.de:
                continue

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
        # Pattern to find i18n.get("key")
        get_pattern = re.compile(r'i18n\.get\s*\(\s*[\'"]([^\'"]+)[\'"]')
        # Heuristic pattern to find potential keys in string literals: "prefix_something"
        # We look for common prefixes like desc_, nav_, cat_, etc.
        heuristic_pattern = re.compile(r'[\'"]([a-z0-9]+_[a-z0-9_.-]+)[\'"]')

        found_keys = set()

        # Build a set of known prefixes from existing keys to refine heuristic
        known_prefixes = set()
        for k in self.en.keys():
            if "_" in k:
                known_prefixes.add(k.split("_")[0] + "_")

        for root, _, files in os.walk(self.src_dir):
            for file in files:
                if file.endswith(".py"):
                    path = Path(root) / file
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                            # 1. Catch explicit i18n.get calls
                            for m in get_pattern.findall(content):
                                found_keys.add(m)

                            # 2. Heuristic: catch things that look like keys in any string literal
                            for m in heuristic_pattern.findall(content):
                                # Only add if it starts with a known prefix
                                match_prefix = m.split("_")[0] + "_"
                                if match_prefix in known_prefixes:
                                    found_keys.add(m)
                    except Exception as e:
                        print(f"Could not read {path}: {e}")

        # Check validity
        missing = []
        # Keys to ignore (false positives that look like translation keys but are internal variables or attributes)
        SKIP_KEYS = {
            'temp_dir', 'uninstall_cmd_field', 'show_snack_bar', 'login_btn', 'cert_copy_btn',
            'notif_btn', 'loading_frame', 'install_cmd_field', 'winget_load_error', 'uninstall_switches',
            'app_page', 'cert_path_entry', 'config_context', 'start_analysis', 'intune_view',
            'manifest_url', 'status_txt', 'install_path', 'product_code', 'ai_provider', 'run_task',
            'ask_manual_zip', 'update_check_result', 'detected_type', 'package_ids',
            'generate_install_script', 'analyzer_view', 'current_metadata', 'lang_menu',
            'product_version', 'brute_force_output', 'search_by_name', 'sync_section_container',
            'all_attempts', 'product_name', 'winget_url', 'file_path', 'history_view', 'bundle_id',
            'winget_switch', 'packaging_wizard_view', 'setup_file', 'first_dynamic_index',
            'install_switches', 'ask_browser', 'history_service', 'silent_args', 'all_temp_dirs',
            'install_silent', 'winget_create', 'intune_store', 'version_field',
            # CLI option names and internal config/state keys (not i18n keys)
            'intunewin_file', 'msi_info', 'group_type', 'script_file', 'value_name', 'group_id',
            'rule_type', 'output_json', 'target_version', 'search_query',
            'error_description', 'import_settings', 'created_at', 'export_settings', 'export_logs',
            'admin_password', 'config_path', 'admin_password_hash', 'first_run', 'demo_mode',
            'current_password', 'new_password', 'confirm_password', 'update_exe'
        }

        for k in found_keys:
            if k not in self.en and k not in SKIP_KEYS:
                # Filter out obvious false positives (not following identifier pattern)
                if re.match(r'^[a-z0-9_.-]+$', k):
                     # Additional check: avoid things that are likely filenames or paths
                     if not (k.endswith(".exe") or k.endswith(".msi") or k.endswith(".intunewin") or "/" in k or "\\" in k):
                        missing.append(k)

        # We know some keys might be constructed dynamically, so we filter out known false positives checks if needed
        # But user asked to "Detect missing translations".
        # Let's Assert.

        # Filter out dynamic keys if possible (if they look like variable names inside string?)
        # The regex captures LITERALS only.
        # e.g. i18n.get("foo") -> foo
        # i18n.get(variable) -> Regex won't match (no quotes).

        self.assertFalse(missing, f"Found i18n keys in code missing from JSON: {missing}")

    def test_german_du_form(self):
        """
        Check that German translations use the informal Du-form rather than the formal Sie-form.

        Scans each value in the loaded German translations for capitalized Sie-form tokens and common formal phrases (e.g., "Sie", "Ihnen", "können Sie"). Records any occurrences (except the ambiguous "Ihr") with their translation key and fails the test if any violations are found.
        """
        # Patterns that indicate Sie-Form (formal German)
        # Note: We check for capitalized forms only, as lowercase "sie" means "they" (3rd person plural)
        # We use word boundaries and case-sensitive matching to avoid false positives
        sie_patterns = [
            r'\bSie\b',  # "Sie" (you formal) - capitalized only
            r'\bIhnen\b',  # "Ihnen" (to you formal) - capitalized
            r'\bIhre\b',  # "Ihre" (your formal, plural/feminine) - capitalized
            r'\bIhren\b',  # "Ihren" (your formal, accusative) - capitalized
            r'\bIhrem\b',  # "Ihrem" (your formal, dative) - capitalized
            r'\bIhres\b',  # "Ihres" (your formal, genitive) - capitalized
            r'\bkönnen Sie\b',  # "can you" formal
            r'\bmüssen Sie\b',  # "must you" formal
            r'\bsollten Sie\b',  # "should you" formal
        ]

        violations = []
        for key, value in self.de.items():
            text = str(value)
            for pattern in sie_patterns:
                # Use case-sensitive search (no IGNORECASE flag) to only catch capitalized forms
                matches = re.finditer(pattern, text)
                for match in matches:
                    matched_text = match.group()
                    # Skip "Ihr" as it can be ambiguous (could be "their" in some contexts)
                    # But flag all other capitalized forms
                    if matched_text != "Ihr":  # "Ihr" is too ambiguous
                        violations.append(f"{key}: Contains Sie-Form: '{matched_text}'")

        self.assertFalse(violations, "Found Sie-Form (formal) in German texts. Use Du-Form instead:\n" + "\n".join(violations))

if __name__ == '__main__':
    unittest.main()