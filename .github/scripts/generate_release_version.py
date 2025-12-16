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

def calculate_next_version(base_version, tags, release_type="stable"):
    """
    Calculates the next version based on the base_version (Year.Month) and existing tags.
    Format: Year.Month.Version[-suffix]

    Args:
        base_version: The Year.Month base (e.g., "2025.12")
        tags: List of existing git tags
        release_type: One of "stable", "prerelease", "development"

    Returns:
        Version string with appropriate suffix
    """
    max_patch = -1

    # Pattern matches versions with or without suffix
    pattern = re.compile(rf"^{re.escape(base_version)}\.(\d+)(?:-.*)?$")

    for tag in tags:
        # Handle tags with or without 'v' prefix
        clean_tag = tag.lstrip('v')
        match = pattern.match(clean_tag)
        if match:
            patch = int(match.group(1))
            if patch > max_patch:
                max_patch = patch

    next_patch = max_patch + 1
    base_ver = f"{base_version}.{next_patch}"

    # Add suffix based on release type
    if release_type == "prerelease":
        return f"{base_ver}-beta"
    elif release_type == "development":
        return f"{base_ver}-dev"
    else:  # stable
        return base_ver

def main():
    parser = argparse.ArgumentParser(description="Generate the next version number.")
    parser.add_argument("--dry-run", action="store_true", help="Print version without side effects")
    parser.add_argument("--type", dest="release_type",
                       choices=["stable", "prerelease", "development"],
                       default="stable",
                       help="Type of release (stable, prerelease, development)")
    args = parser.parse_args()

    base_ver = get_current_date_version()
    tags = get_existing_tags()
    next_version = calculate_next_version(base_ver, tags, args.release_type)

    print(next_version)

    if not args.dry_run:
        # Set outputs for GitHub Actions
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"version={next_version}\n")
                f.write(f"is_prerelease={args.release_type != 'stable'}\n")

if __name__ == "__main__":
    main()
