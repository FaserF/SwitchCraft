import subprocess

def get_last_tag():
    """Returns the most recent git tag."""
    try:
        # Get all tags sorted by date desc
        result = subprocess.run(
            ["git", "tag", "--sort=-creatordate"],
            capture_output=True, text=True, check=True
        )
        tags = result.stdout.strip().split('\n')
        if not tags or tags[0] == "":
            return None
        return tags[0]
    except subprocess.CalledProcessError:
        return None
