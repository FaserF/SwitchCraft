import os
import requests
import re
import sys

def main():
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("REPO")

    if not token or not repo:
        print("Error: GITHUB_TOKEN or REPO environment variables not set.")
        sys.exit(1)

    print(f"Cleaning up releases for {repo}...")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    # Fetch releases (per page loop if needed, but 100 is likely enough for recent history)
    # Ordered by created_at desc by default
    url = f"https://api.github.com/repos/{repo}/releases?per_page=100"

    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        releases = resp.json()
    except Exception as e:
        print(f"Failed to fetch releases: {e}")
        sys.exit(1)

    stable_releases = []
    beta_releases = []
    nightly_releases = []

    # Categorize
    for r in releases:
        if r.get("draft"):
            continue # Skip drafts

        tag_name = r.get("tag_name", "")
        version = tag_name.lstrip("v")
        is_prerelease = r.get("prerelease", False)

        # Logic matches generate_release_version.py and release.yml inputs
        # Stable: Not prerelease
        # Nightly: Prerelease AND contains .dev or + (typically .dev0)
        # Beta: Prerelease AND matches beta pattern (b, rc, alpha) but NOT dev

        if not is_prerelease:
            stable_releases.append(r)
        elif "dev" in version or "+" in version:
             nightly_releases.append(r)
        else:
             beta_releases.append(r)

    print(f"Found: {len(stable_releases)} Stable, {len(beta_releases)} Beta, {len(nightly_releases)} Nightly.")

    # Retention Policy
    # Stable: Keep All
    # Beta: Keep 2
    # Nightly: Keep 2

    to_delete = []

    # Process Betas
    if len(beta_releases) > 2:
        # Sorted by default from API (newest first). Keep 0 and 1. Delete 2 onwards.
        to_delete.extend(beta_releases[2:])

    # Process Nightlies
    if len(nightly_releases) > 2:
        to_delete.extend(nightly_releases[2:])

    if not to_delete:
        print("No releases to clean up.")
        return

    print(f"Deleting {len(to_delete)} old releases...")

    for r in to_delete:
        rid = r["id"]
        tag = r["tag_name"]
        print(f"Deleting release {tag} (ID: {rid})...")

        # Delete Release
        try:
            del_url = f"https://api.github.com/repos/{repo}/releases/{rid}"
            requests.delete(del_url, headers=headers).raise_for_status()
            print(f"  - Release deleted.")
        except Exception as e:
            print(f"  - Failed to delete release: {e}")
            continue

        # Delete Tag
        try:
            ref_url = f"https://api.github.com/repos/{repo}/git/refs/tags/{tag}"
            requests.delete(ref_url, headers=headers).raise_for_status()
            print(f"  - Tag {tag} deleted.")
        except Exception as e:
            print(f"  - Failed to delete tag: {e}")

    print("Cleanup complete.")

if __name__ == "__main__":
    main()
