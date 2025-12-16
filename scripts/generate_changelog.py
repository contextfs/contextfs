#!/usr/bin/env python3
"""Generate categorized changelog from git history.

Usage:
    python scripts/generate_changelog.py [--from TAG] [--to TAG] [--format FORMAT]

Examples:
    python scripts/generate_changelog.py                    # From last tag to HEAD
    python scripts/generate_changelog.py --from v0.1.8      # From specific tag
    python scripts/generate_changelog.py --format markdown  # Output format
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class Commit:
    hash: str
    subject: str
    category: str
    scope: str | None
    breaking: bool


# Conventional commit patterns
COMMIT_PATTERN = re.compile(
    r"^(?P<type>\w+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?: (?P<subject>.+)$"
)

# Category mappings
CATEGORIES = {
    "feat": "New Features",
    "feature": "New Features",
    "add": "New Features",
    "fix": "Bug Fixes",
    "bugfix": "Bug Fixes",
    "docs": "Documentation",
    "doc": "Documentation",
    "style": "Styling",
    "refactor": "Refactoring",
    "perf": "Performance",
    "test": "Testing",
    "tests": "Testing",
    "chore": "Maintenance",
    "ci": "CI/CD",
    "build": "Build",
    "deps": "Dependencies",
}

# Display order for categories
CATEGORY_ORDER = [
    "New Features",
    "Bug Fixes",
    "Performance",
    "Refactoring",
    "Documentation",
    "Testing",
    "CI/CD",
    "Build",
    "Dependencies",
    "Maintenance",
    "Styling",
    "Other Changes",
]


def run_git(*args: str) -> str:
    """Run a git command and return output."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_previous_tag(current_ref: str = "HEAD") -> str | None:
    """Get the previous tag before the given ref."""
    try:
        return run_git("describe", "--tags", "--abbrev=0", f"{current_ref}^")
    except subprocess.CalledProcessError:
        return None


def get_commits(from_ref: str | None, to_ref: str = "HEAD") -> list[Commit]:
    """Get commits between two refs."""
    range_spec = f"{from_ref}..{to_ref}" if from_ref else to_ref

    try:
        log_output = run_git(
            "log",
            range_spec,
            "--pretty=format:%H|%s",
            "--no-merges",
        )
    except subprocess.CalledProcessError:
        return []

    if not log_output:
        return []

    commits = []
    for line in log_output.split("\n"):
        if not line.strip():
            continue
        parts = line.split("|", 1)
        if len(parts) != 2:
            continue
        hash_val, subject = parts
        commit = parse_commit(hash_val, subject)
        commits.append(commit)

    return commits


def parse_commit(hash_val: str, subject: str) -> Commit:
    """Parse a commit message into structured data."""
    match = COMMIT_PATTERN.match(subject)

    if match:
        commit_type = match.group("type").lower()
        scope = match.group("scope")
        breaking = match.group("breaking") == "!"
        clean_subject = match.group("subject")
        category = CATEGORIES.get(commit_type, "Other Changes")
    else:
        # Try to infer category from subject
        subject_lower = subject.lower()
        category = "Other Changes"
        clean_subject = subject
        scope = None
        breaking = False

        if subject_lower.startswith("add "):
            category = "New Features"
        elif subject_lower.startswith("fix "):
            category = "Bug Fixes"
        elif subject_lower.startswith("update ") or subject_lower.startswith("improve "):
            category = "Other Changes"
        elif subject_lower.startswith("bump "):
            category = "Maintenance"

    return Commit(
        hash=hash_val[:8],
        subject=clean_subject,
        category=category,
        scope=scope,
        breaking=breaking,
    )


def group_commits(commits: list[Commit]) -> dict[str, list[Commit]]:
    """Group commits by category."""
    groups: dict[str, list[Commit]] = {}
    for commit in commits:
        if commit.category not in groups:
            groups[commit.category] = []
        groups[commit.category].append(commit)
    return groups


def format_markdown(groups: dict[str, list[Commit]], include_hashes: bool = False) -> str:
    """Format grouped commits as markdown."""
    lines = []

    # Breaking changes first
    breaking = [c for commits in groups.values() for c in commits if c.breaking]
    if breaking:
        lines.append("### ⚠️ Breaking Changes")
        lines.append("")
        for commit in breaking:
            scope = f"**{commit.scope}**: " if commit.scope else ""
            hash_str = f" ({commit.hash})" if include_hashes else ""
            lines.append(f"- {scope}{commit.subject}{hash_str}")
        lines.append("")

    # Regular categories
    for category in CATEGORY_ORDER:
        if category not in groups:
            continue
        commits = [c for c in groups[category] if not c.breaking]
        if not commits:
            continue

        # Use emoji prefixes for key categories
        emoji = {
            "New Features": "✨",
            "Bug Fixes": "🐛",
            "Performance": "⚡",
            "Documentation": "📚",
        }.get(category, "")

        header = f"{emoji} {category}" if emoji else category
        lines.append(f"### {header}")
        lines.append("")
        for commit in commits:
            scope = f"**{commit.scope}**: " if commit.scope else ""
            hash_str = f" ({commit.hash})" if include_hashes else ""
            lines.append(f"- {scope}{commit.subject}{hash_str}")
        lines.append("")

    return "\n".join(lines).strip()


def format_plain(groups: dict[str, list[Commit]]) -> str:
    """Format grouped commits as plain text."""
    lines = []
    for category in CATEGORY_ORDER:
        if category not in groups:
            continue
        commits = groups[category]
        lines.append(f"{category}:")
        for commit in commits:
            scope = f"[{commit.scope}] " if commit.scope else ""
            lines.append(f"  - {scope}{commit.subject}")
        lines.append("")
    return "\n".join(lines).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate changelog from git history")
    parser.add_argument("--from", dest="from_ref", help="Starting ref (tag or commit)")
    parser.add_argument("--to", dest="to_ref", default="HEAD", help="Ending ref")
    parser.add_argument(
        "--format",
        choices=["markdown", "plain", "github"],
        default="markdown",
        help="Output format",
    )
    parser.add_argument("--hashes", action="store_true", help="Include commit hashes")
    args = parser.parse_args()

    # Determine from_ref
    from_ref = args.from_ref
    if not from_ref:
        from_ref = get_previous_tag(args.to_ref)

    # Get commits
    commits = get_commits(from_ref, args.to_ref)

    if not commits:
        print("No commits found in range.", file=sys.stderr)
        return 1

    # Group and format
    groups = group_commits(commits)

    if args.format == "plain":
        output = format_plain(groups)
    else:  # markdown or github
        output = format_markdown(groups, include_hashes=args.hashes)

    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
