import argparse
import subprocess
import os
import re
import sys

# Constants
CATEGORY_EMOJIS = {
    "Features": "✨",
    "Bug Fixes": "🐛",
    "Styling": "🎨",
    "Documentation": "📝",
    "Maintenance": "🔨",
    "Other": "🔧"
}

EXCLUDE_PATTERNS = [
    r"auto-fix ruff linting issues",
    r"auto-fix linting issues",
    r"CI fixes",
    r"more CI fixes",
    r"bump version to .*? \[skip ci\]",
]

# Ensure the script's directory is in sys.path for git_utils import
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from git_utils import get_last_tag, get_last_stable_tag


def get_commits(since_tag=None):
    """Returns list of commit messages since the given tag (or all if None)."""
    range_spec = f"{since_tag}..HEAD" if since_tag else "HEAD"
    try:
        result = subprocess.run(
            ["git", "log", range_spec, "--pretty=format:%s"],
            capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore'
        )
        return [line for line in result.stdout.strip().split('\n') if line]
    except subprocess.CalledProcessError:
        return []

def parse_commits(commits):
    """
    Parses commits and categorizes them.
    Returns:
        tuple: (pr_count, categorized_commits)
    """
    pr_pattern = re.compile(r"Merge pull request #\d+|.*\(\#\d+\)$")

    categories = {
        "Features": [],
        "Bug Fixes": [],
        "Styling": [],
        "Documentation": [],
        "Maintenance": [],
        "Other": []
    }

    pr_count = 0

    for commit in commits:
        # Check exclusions
        should_exclude = False
        for pattern in EXCLUDE_PATTERNS:
            if re.search(pattern, commit, re.IGNORECASE):
                should_exclude = True
                break
        if should_exclude:
            continue

        if pr_pattern.search(commit):
            pr_count += 1

        # Conventional categorization
        lower_commit = commit.lower()
        if lower_commit.startswith("feat"):
            categories["Features"].append(commit)
        elif lower_commit.startswith("fix"):
            categories["Bug Fixes"].append(commit)
        elif lower_commit.startswith("style"):
            categories["Styling"].append(commit)
        elif lower_commit.startswith("docs"):
            categories["Documentation"].append(commit)
        elif lower_commit.startswith(("chore", "refactor", "test", "ci", "build")):
            categories["Maintenance"].append(commit)
        else:
            # Filter out merge commits from "Other" list if we want clean output
            if not lower_commit.startswith("merge"):
                categories["Other"].append(commit)

    return pr_count, categories

def generate_markdown(categories):
    """Generates markdown string from categories."""
    md = []

    # Order: Feat, Fix, Style, Docs, Maint, Other
    main_categories = ["Features", "Bug Fixes"]
    collapsible_categories = ["Styling", "Documentation", "Maintenance", "Other"]

    # 1. Main Categories (Always visible)
    for cat in main_categories:
        items = categories.get(cat, [])
        if items:
            emoji = CATEGORY_EMOJIS.get(cat, "")
            md.append(f"### {emoji} {cat}")
            for item in items:
                # Clean up prefixes for display
                clean_item = re.sub(r'^(feat|fix|docs|chore|refactor|style|test|ci|build)(\(.*\))?:', '', item, flags=re.IGNORECASE).strip()
                md.append(f"- {clean_item}")
            md.append("")

    # 2. Collapsible Details (Less critical)
    has_details = any(categories.get(cat) for cat in collapsible_categories)
    if has_details:
        md.append("<details>")
        md.append("<summary><b>🛠️ Maintenance & Details</b> (Click to expand)</summary>")
        md.append("")

        for cat in collapsible_categories:
            items = categories.get(cat, [])
            if items:
                emoji = CATEGORY_EMOJIS.get(cat, "")
                md.append(f"#### {emoji} {cat}")
                for item in items:
                     # Clean up prefixes for display
                    clean_item = re.sub(r'^(feat|fix|docs|chore|refactor|style|test|ci|build)(\(.*\))?:', '', item, flags=re.IGNORECASE).strip()
                    md.append(f"- {clean_item}")
                md.append("")

        md.append("</details>")
        md.append("")

    return "\n".join(md)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="Output file for changelog")
    parser.add_argument("--type", choices=['stable', 'prerelease', 'development'], default='stable', help="Release type")
    args = parser.parse_args()

    if args.type == 'stable':
        print("Detailed Mode: Stable Release (comparing against last stable tag)")
        last_tag = get_last_stable_tag()
    else:
        print(f"Detailed Mode: {args.type} (comparing against last tag)")
        last_tag = get_last_tag()

    print(f"Last tag detected: {last_tag}")

    commits = get_commits(last_tag)
    print(f"Found {len(commits)} commits")

    pr_count, categories = parse_commits(commits)
    print(f"Detected {pr_count} Pull Requests")

    # Always generate categorized output if we have commits
    print("Generating categorized changelog...")
    changelog_md = generate_markdown(categories)
    if not changelog_md:
        changelog_md = "No significant changes detected."

    if args.output:
        with open(args.output, "w", encoding='utf-8') as f:
            f.write(changelog_md)
    else:
        print("\n--- Generated Changelog ---")
        print(changelog_md)

if __name__ == "__main__":
    main()
