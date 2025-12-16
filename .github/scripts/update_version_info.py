import sys
import re

def update_version_info(version_str, file_path='file_version_info.txt'):
    """
    Updates the file_version_info.txt with the given version.
    Handles versions with suffixes like '2025.12.0-beta' or '2025.12.0-dev'.
    """
    # Strip suffix for numeric tuple (e.g., "2025.12.0-beta" -> "2025.12.0")
    base_version = re.sub(r'-.*$', '', version_str)

    parts = base_version.split('.')
    while len(parts) < 4:
        parts.append('0')

    # Ensure all parts are numeric
    numeric_parts = []
    for p in parts[:4]:
        try:
            numeric_parts.append(str(int(p)))
        except ValueError:
            numeric_parts.append('0')

    # tuple format: (2025, 12, 0, 0)
    tuple_str = f"({', '.join(numeric_parts)})"
    # string format: '2025.12.0.0' for file version (numeric only)
    full_version_str = '.'.join(numeric_parts)
    # Display version includes suffix for ProductVersion string
    display_version_str = version_str if '-' in version_str else full_version_str

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update filevers and prodvers tuples (must be numeric)
    content = re.sub(r'filevers=\(\d+, \d+, \d+, \d+\)', f'filevers={tuple_str}', content)
    content = re.sub(r'prodvers=\(\d+, \d+, \d+, \d+\)', f'prodvers={tuple_str}', content)

    # Update StringStructs
    # FileVersion should be numeric only
    content = re.sub(r"StringStruct\(u'FileVersion', u'[^']+'\)", f"StringStruct(u'FileVersion', u'{full_version_str}')", content)
    # ProductVersion can include suffix for display
    content = re.sub(r"StringStruct\(u'ProductVersion', u'[^']+'\)", f"StringStruct(u'ProductVersion', u'{display_version_str}')", content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Updated {file_path} to version {display_version_str} (numeric: {full_version_str})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_version_info.py <version>")
        sys.exit(1)

    update_version_info(sys.argv[1])
