import os
import requests
import sys

def main():
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("REPO") # e.g. FaserF/SwitchCraft
    package_name = "switchcraft"

    if not token or not repo:
        print("Error: GITHUB_TOKEN or REPO environment variables not set.")
        sys.exit(1)

    owner, repo_name = repo.split("/", 1)
    owner = owner.lower()

    # We need to determine if owner is an organization or a user
    # Check org first, if not found try user
    org_url = f"https://api.github.com/orgs/{owner}/packages/container/{package_name}/versions"
    user_url = f"https://api.github.com/users/{owner}/packages/container/{package_name}/versions"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    print(f"Fetching versions for container '{package_name}' owned by {owner}...")

    resp = requests.get(org_url, headers=headers)
    if resp.status_code == 404:
        print(f"Package not found in org {owner}, checking user packages...")
        resp = requests.get(user_url, headers=headers)

    try:
        resp.raise_for_status()
        versions = resp.json()
    except Exception as e:
        print(f"Failed to fetch package versions: {e}")
        # If the package doesn't exist yet, it's not a fatal error for cleanup
        if resp.status_code == 404:
            print("Package not found. Nothing to clean up.")
            sys.exit(0)
        sys.exit(1)

    stable_versions = []
    beta_versions = []
    nightly_versions = []

    # Categorize versions by their tags
    for v in versions:
        metadata = v.get("metadata", {})
        container = metadata.get("container", {})
        tags = container.get("tags", [])

        if not tags:
            # Untagged versions are candidates for deletion if they are old
            # For now, let's treat them as nightly or just ignore if they are the latest
            nightly_versions.append(v)
            continue

        # Check if 'latest' or 'prerelease' tags exist - these are pointers, usually keep
        is_latest = "latest" in tags
        is_prerelease_ptr = "prerelease" in tags

        # Use first specific version tag for categorization
        # Example: 2026.1.5.dev0-32a44e0
        version_tag = next((t for t in tags if t not in ["latest", "prerelease"]), tags[0])

        # Logic:
        # Stable: No 'dev' or '-' (sanitized '+')
        # Nightly: Contains 'dev' or '-'
        # Beta: Matches beta patterns (b1, rc1) but not dev

        if "dev" in version_tag or "-" in version_tag:
            nightly_versions.append(v)
        elif any(x in version_tag for x in ["b", "rc", "alpha"]):
            beta_versions.append(v)
        else:
            # Check if it looks like a version number
            if any(char.isdigit() for char in version_tag):
                stable_versions.append(v)
            else:
                nightly_versions.append(v)

    print(f"Found: {len(stable_versions)} Stable, {len(beta_versions)} Beta, {len(nightly_versions)} Nightly (including untagged).")

    # Retention Policy
    to_delete = []

    # Process Betas: Keep 2
    if len(beta_versions) > 2:
        to_delete.extend(beta_versions[2:])

    # Process Nightlies: Keep 2
    if len(nightly_versions) > 2:
        to_delete.extend(nightly_versions[2:])

    if not to_delete:
        print("No Docker versions to clean up.")
        return

    print(f"Deleting {len(to_delete)} old Docker versions...")

    # For orgs: DELETE /orgs/{org}/packages/{package_type}/{package_name}/versions/{package_version_id}
    # For users: DELETE /user/packages/{package_type}/{package_name}/versions/{package_version_id}
    # Note: /user/ is literal for the authenticated user, or we can use /users/{owner}/

    # Actually the API endpoint for deletion varies:
    # Org: https://api.github.com/orgs/{org}/packages/container/{package_name}/versions/{version_id}
    # User: https://api.github.com/users/{user}/packages/container/{package_name}/versions/{version_id}

    # We'll use the URL format that succeeded for listing
    base_del_url = org_url if "orgs" in resp.url else user_url

    for v in to_delete:
        vid = v["id"]
        tags = v.get("metadata", {}).get("container", {}).get("tags", [])
        tag_str = ", ".join(tags) if tags else "untagged"
        print(f"Deleting version {vid} (Tags: {tag_str})...")

        try:
            del_url = f"{base_del_url}/{vid}"
            requests.delete(del_url, headers=headers).raise_for_status()
            print(f"  - Version deleted.")
        except Exception as e:
            print(f"  - Failed to delete version: {e}")

    print("Docker cleanup complete.")

if __name__ == "__main__":
    main()
