import subprocess
import re

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

def get_last_stable_tag():
    """Returns the most recent stable git tag (vX.Y.Z without suffix)."""
    try:
        # Get all tags sorted by date desc
        result = subprocess.run(
            ["git", "tag", "--sort=-creatordate"],
            capture_output=True, text=True, check=True
        )
        tags = result.stdout.strip().split('\n')
        # Regex for stable tag: v + digits + . + digits + . + digits + end of string
        stable_pattern = re.compile(r"^v\d+\.\d+\.\d+$")

        for tag in tags:
            if tag and stable_pattern.match(tag.strip()):
                return tag.strip()

        return None
    except subprocess.CalledProcessError:
        return None
