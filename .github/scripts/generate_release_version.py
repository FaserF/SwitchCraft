import os
import re
import datetime
import argparse
import subprocess
import sys

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

    # Add suffix based on release type (PEP 440 compliant)
    if release_type == "prerelease":
        return f"{base_ver}b1"  # beta1 is PEP 440 compliant
    elif release_type == "development":
        try:
            sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
            # PEP 440: Use .dev0 for development, +sha for build metadata
            return f"{base_ver}.dev0+{sha}"
        except Exception:
            return f"{base_ver}.dev0"
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

    # Fallback version if version generation fails
    FALLBACK_VERSION = "2026.1.4"

    try:
        base_ver = get_current_date_version()
        tags = get_existing_tags()
        next_version = calculate_next_version(base_ver, tags, args.release_type)

        # Validate version format (PEP 440 compliant)
        # Pattern matches MAJOR.MINOR.PATCH with optional pre-release (.dev0, .a1, .b1, .rc1) and build (+build) suffixes
        # Examples: 2026.1.2, 2026.1.2.dev0+9d07a00, 2026.1.2b1, 2026.1.2+9d07a00
        if not next_version or not re.match(r'^[0-9]+\.[0-9]+\.[0-9]+(\.[a-z]+[0-9]+|[a-z]+[0-9]+)?(\+[a-zA-Z0-9.-]+)?$', next_version):
            print(f"Warning: Generated version '{next_version}' is invalid, using fallback: {FALLBACK_VERSION}", file=sys.stderr)
            next_version = FALLBACK_VERSION
    except Exception as e:
        print(f"Error generating version: {e}, using fallback: {FALLBACK_VERSION}", file=sys.stderr)
        next_version = FALLBACK_VERSION

    print(next_version)

    if not args.dry_run:
        # Set outputs for GitHub Actions
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"version={next_version}\n")
                f.write(f"is_prerelease={args.release_type != 'stable'}\n")

if __name__ == "__main__":
    main()
