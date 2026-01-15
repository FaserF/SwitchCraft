import subprocess
import sys
import os

# Ensure the script's directory is in sys.path for git_utils import
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from git_utils import get_last_tag

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
    except subprocess.CalledProcessError:
        return True # Default to true if git diff fails

def main():
    last_tag = get_last_tag()
    relevance = "true" if has_relevant_changes(last_tag) else "false"

    print(f"relevance={relevance}")

    # Also write to GITHUB_OUTPUT if present
    output_file = os.getenv("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"relevance={relevance}\n")

    sys.exit(0)

if __name__ == "__main__":
    main()
