import os
import re
import datetime
import argparse
import subprocess

def get_current_date_version():
    """Returns the current date in Year.Month format (e.g., 2025.12)."""
    now = datetime.datetime.now()
    return f"{now.year}.{now.month}"

def get_existing_tags():
    """Fetches all tags from the repository."""
    try:
        # Fetch tags from remote to ensure we have the latest
        subprocess.run(["git", "fetch", "--tags"], check=True, capture_output=True)
        result = subprocess.run(["git", "tag"], capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError:
        return []

def calculate_next_version(base_version, tags):
    """
    Calculates the next version based on the base_version (Year.Month) and existing tags.
    Format: Year.Month.Version
    """
    max_patch = -1
    pattern = re.compile(rf"^{re.escape(base_version)}\.(\d+)$")

    for tag in tags:
        # Handle tags with or without 'v' prefix
        clean_tag = tag.lstrip('v')
        match = pattern.match(clean_tag)
        if match:
            patch = int(match.group(1))
            if patch > max_patch:
                max_patch = patch

    # If no existing tag for this month, start with 0 or 1?
    # User requested Year.Month.Version. Let's start with 0 if it's the first release of the month,
    # or 1? Standard is usually 0 or 1. Let's stick to 0 as the first one, or 1?
    # Usually 2025.12.0 or 2025.12.1.
    # Let's align with the example "2025.12.2" -> suggests 0-based or 1-based.
    # I'll start with 0.

    next_patch = max_patch + 1
    return f"{base_version}.{next_patch}"

def main():
    parser = argparse.ArgumentParser(description="Generate the next version number.")
    parser.add_argument("--dry-run", action="store_true", help="Print version without side effects")
    args = parser.parse_args()

    base_ver = get_current_date_version()
    tags = get_existing_tags()
    next_version = calculate_next_version(base_ver, tags)

    print(next_version)

    if not args.dry_run:
        # We might want to set this as an output for GitHub Actions
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"version={next_version}\n")

if __name__ == "__main__":
    main()
