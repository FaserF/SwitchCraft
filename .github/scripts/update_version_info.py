import sys
import re
import argparse

def update_version_info(version_str, build_number=None, file_path='file_version_info.txt'):
    """
    Updates the file_version_info.txt with the given version.
    Handles versions with suffixes like '2025.12.0-beta' or '2026.1.5.dev0+hash'.
    """
    print(f"Processing version: {version_str} (Build Number: {build_number})")

    # 1. Extract the BASE numeric part (Major.Minor.Patch)
    # We want only the MAJOR.MINOR.PATCH part for the fixed file info tuples.
    match = re.search(r'([0-9]+\.[0-9]+\.[0-9]+)', version_str)
    if not match:
        print(f"Error: Could not find a valid numeric version in '{version_str}'")
        sys.exit(1)

    base_version = match.group(1)
    parts = base_version.split('.')

    # Ensure we have at least 3 parts
    while len(parts) < 3:
        parts.append('0')

    # 2. Add/Override the 4th component (Build/Revision)
    if build_number is not None:
        parts.append(str(build_number))
    else:
        # Default to 0 if not provided
        parts.append('0')

    # Limit to 4 components for Windows VersionInfo
    numeric_parts = parts[:4]

    # 3. Generate the formats needed for file_version_info.txt

    # tuple format: (2025, 12, 0, 0)
    tuple_str = f"({', '.join(numeric_parts)})"

    # string format: '2025.12.0.0' for FileVersion (must be numeric only)
    full_version_str = '.'.join(numeric_parts)

    # display_version_str is for ProductVersion (can include suffixes)
    display_version_str = version_str

    # 4. Read and Update the File
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        sys.exit(1)

    # Update filevers and prodvers tuples (must be numeric)
    # Use smart regex to match variation in whitespace
    content = re.sub(r'filevers\s*=\s*\([^)]+\)', f'filevers={tuple_str}', content)
    content = re.sub(r'prodvers\s*=\s*\([^)]+\)', f'prodvers={tuple_str}', content)

    # Update StringStructs (FileVersion and ProductVersion)
    # FileVersion should be numeric only for Windows stability
    content = re.sub(r"StringStruct\(u?'FileVersion', u?'[^']+'\)", f"StringStruct(u'FileVersion', u'{full_version_str}')", content)
    # ProductVersion can include suffix for display
    content = re.sub(r"StringStruct\(u?'ProductVersion', u?'[^']+'\)", f"StringStruct(u'ProductVersion', u'{display_version_str}')", content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Successfully updated {file_path}:")
    print(f"  - FileVersion (Numeric): {full_version_str}")
    print(f"  - ProductVersion (Display): {display_version_str}")
    print(f"  - Tuple (FFI): {tuple_str}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update version information in file_version_info.txt")
    parser.add_argument("version", help="Full version string (e.g., 2026.1.5.dev0+hash)")
    parser.add_argument("--build", type=int, help="Optional build number (4th component override)", default=None)
    parser.add_argument("--file", help="Path to version info file", default="file_version_info.txt")

    args = parser.parse_args()

    update_version_info(args.version, build_number=args.build, file_path=args.file)
