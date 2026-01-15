import subprocess
import sys

def get_last_tag():
    try:
        result = subprocess.run(
            ["git", "tag", "--sort=-creatordate"],
            capture_output=True, text=True, check=True
        )
        tags = result.stdout.strip().split('\n')
        return tags[0] if tags and tags[0] else None
    except:
        return None

def has_relevant_changes(since_tag):
    if not since_tag:
        return True

    range_spec = f"{since_tag}..HEAD"
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", range_spec],
            capture_output=True, text=True, check=True
        )
        changed_files = result.stdout.strip().split('\n')

        ignored_prefixes = [".github/", "docs/", "tests/", "README.md", ".gitignore", "LICENSE", "TODO.md"]

        for f in changed_files:
            if not f: continue
            is_ignored = False
            for prefix in ignored_prefixes:
                if f.startswith(prefix) or f == prefix:
                    is_ignored = True
                    break
            if not is_ignored:
                print(f"Relevant change detected in: {f}")
                return True
        return False
    except:
        return True # Default to true if something fails

def main():
    last_tag = get_last_tag()
    if has_relevant_changes(last_tag):
        print("relevance=true")
        sys.exit(0)
    else:
        print("relevance=false")
        sys.exit(0)

if __name__ == "__main__":
    main()
