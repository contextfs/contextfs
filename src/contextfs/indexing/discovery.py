"""
Repository discovery and detection for auto-indexing.

This module provides functionality for:
- Discovering git repositories in a directory tree
- Detecting programming languages, frameworks, and project types
- Analyzing repository metadata
"""

import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from contextfs.schemas import Memory, MemoryType


class RepoInfo(TypedDict):
    """Information about a discovered git repository."""

    path: Path
    name: str
    project: str | None
    suggested_tags: list[str]
    remote_url: str | None
    relative_path: str


@dataclass
class LanguageDetector:
    """Detects programming languages based on indicator files."""

    language: str
    indicators: list[str]

    def matches(self, repo_path: Path) -> bool:
        """Check if any indicator file exists in the repo."""
        for indicator in self.indicators:
            if "*" in indicator:
                if list(repo_path.glob(indicator)):
                    return True
            elif (repo_path / indicator).exists():
                return True
        return False


@dataclass
class FrameworkDetector:
    """Detects frameworks from package dependencies or config files."""

    framework: str
    config_files: list[str] = field(default_factory=list)
    npm_packages: list[str] = field(default_factory=list)
    pip_packages: list[str] = field(default_factory=list)

    def matches(self, repo_path: Path, npm_deps: set[str], pip_content: str) -> bool:
        """Check if framework is detected."""
        # Check config files
        for cf in self.config_files:
            if (repo_path / cf).exists():
                return True
        # Check npm packages
        for pkg in self.npm_packages:
            if pkg in npm_deps:
                return True
        # Check pip packages
        return any(pkg in pip_content for pkg in self.pip_packages)


@dataclass
class TypeIndicator:
    """Detects project type based on file/directory presence."""

    tag: str
    paths: list[str]

    def matches(self, repo_path: Path) -> bool:
        """Check if any path exists."""
        return any((repo_path / p).exists() for p in self.paths)


# Registry of language detectors
LANGUAGE_DETECTORS = [
    LanguageDetector("python", ["setup.py", "pyproject.toml", "requirements.txt", "Pipfile"]),
    LanguageDetector("javascript", ["package.json"]),
    LanguageDetector("typescript", ["tsconfig.json"]),
    LanguageDetector("rust", ["Cargo.toml"]),
    LanguageDetector("go", ["go.mod"]),
    LanguageDetector("java", ["pom.xml", "build.gradle"]),
    LanguageDetector("ruby", ["Gemfile"]),
    LanguageDetector("php", ["composer.json"]),
    LanguageDetector("swift", ["Package.swift"]),
    LanguageDetector("csharp", ["*.csproj", "*.sln"]),
]

# Registry of framework detectors
FRAMEWORK_DETECTORS = [
    FrameworkDetector("react", npm_packages=["react"]),
    FrameworkDetector(
        "vue", config_files=["vue.config.js", "nuxt.config.js"], npm_packages=["vue"]
    ),
    FrameworkDetector("angular", config_files=["angular.json"], npm_packages=["@angular/core"]),
    FrameworkDetector(
        "nextjs", config_files=["next.config.js", "next.config.mjs"], npm_packages=["next"]
    ),
    FrameworkDetector("express", npm_packages=["express"]),
    FrameworkDetector("fastify", npm_packages=["fastify"]),
    FrameworkDetector("django", pip_packages=["django"]),
    FrameworkDetector("flask", pip_packages=["flask"]),
    FrameworkDetector("fastapi", pip_packages=["fastapi"]),
    FrameworkDetector("rails", config_files=["config/routes.rb"]),
]

# Registry of project type indicators
TYPE_INDICATORS = [
    TypeIndicator("type:containerized", ["Dockerfile"]),
    TypeIndicator("type:docker-compose", ["docker-compose.yml", "docker-compose.yaml"]),
    TypeIndicator("ci:github-actions", [".github/workflows"]),
    TypeIndicator("ci:gitlab", [".gitlab-ci.yml"]),
    TypeIndicator("has-tests", ["tests", "test"]),
]

# Directories that indicate a project container
PROJECT_CONTAINER_NAMES = {"projects", "repos", "work", "workspace", "dev", "development"}

# Workspace config files that indicate a project container
WORKSPACE_CONFIG_FILES = [
    "pnpm-workspace.yaml",
    "lerna.json",
    ".workspace",
    "Cargo.toml",  # Rust workspace
    "go.work",  # Go workspace
]

# Extensions to index by default (shared with autoindex)
DEFAULT_INDEX_EXTENSIONS = {
    # Programming languages
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".kt",
    ".scala",
    ".go",
    ".rs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".fs",
    ".vb",
    ".rb",
    ".php",
    ".swift",
    ".m",
    ".mm",
    ".lua",
    ".pl",
    ".pm",
    ".r",
    ".R",
    ".ex",
    ".exs",
    ".erl",
    ".hrl",
    ".clj",
    ".cljs",
    ".cljc",
    ".hs",
    ".ml",
    ".mli",
    ".jl",
    ".nim",
    ".zig",
    ".d",
    ".v",
    ".sv",
    ".vhd",
    ".vhdl",
    # Web
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".vue",
    ".svelte",
    # Config
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".xml",
    ".plist",
    # Documentation
    ".md",
    ".rst",
    ".txt",
    ".adoc",
    # Data
    ".sql",
    ".graphql",
    ".gql",
    # Shell
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    # Templates
    ".jinja",
    ".j2",
    ".ejs",
    ".hbs",
    ".pug",
}


def discover_git_repos(
    root_dir: Path,
    max_depth: int = 5,
    ignore_patterns: set[str] | None = None,
) -> list[RepoInfo]:
    """
    Recursively discover all git repositories under a directory.

    Args:
        root_dir: Root directory to scan
        max_depth: Maximum depth to search (default: 5)
        ignore_patterns: Directory names to skip (default: common ignores)

    Returns:
        List of RepoInfo dicts with repo metadata
    """
    if ignore_patterns is None:
        ignore_patterns = {
            "node_modules",
            ".git",
            "vendor",
            "__pycache__",
            "venv",
            ".venv",
            "dist",
            "build",
            ".cache",
        }

    repos: list[RepoInfo] = []
    root_dir = root_dir.resolve()

    def _scan(current: Path, depth: int, parent_project: str | None = None) -> None:
        if depth > max_depth:
            return

        try:
            entries = list(current.iterdir())
        except PermissionError:
            return

        for entry in entries:
            if not entry.is_dir():
                continue

            if entry.name in ignore_patterns:
                continue

            if entry.name.startswith(".") and entry.name != ".git":
                continue

            # Check if this is a git repo
            if (entry / ".git").exists():
                repo_info = _analyze_repo(entry, root_dir, parent_project)
                repos.append(repo_info)
                # Don't recurse into git repos (they're self-contained)
                continue

            # If current dir looks like a project container, use it as project name
            project_name = parent_project
            if _is_project_container(entry):
                project_name = entry.name

            # Recurse into subdirectory
            _scan(entry, depth + 1, project_name)

    _scan(root_dir, 0)
    return repos


def _is_project_container(path: Path) -> bool:
    """
    Check if a directory looks like a project container (monorepo parent).

    Uses PROJECT_CONTAINER_NAMES and WORKSPACE_CONFIG_FILES registries.
    """
    if path.name.lower() in PROJECT_CONTAINER_NAMES:
        return True

    return any((path / wf).exists() for wf in WORKSPACE_CONFIG_FILES)


def _analyze_repo(repo_path: Path, root_dir: Path, parent_project: str | None) -> RepoInfo:
    """
    Analyze a git repository and extract metadata.

    Returns:
        RepoInfo with path, name, project, suggested_tags, etc.
    """
    name = repo_path.name
    rel_path = repo_path.relative_to(root_dir)

    # Determine project name
    project = parent_project
    if project is None and len(rel_path.parts) > 1:
        potential_project = rel_path.parts[0]
        if _is_project_container(root_dir / potential_project):
            project = potential_project

    # Detect tags based on repo contents
    suggested_tags = _detect_repo_tags(repo_path)

    # Get remote URL
    remote_url = None
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            remote_url = result.stdout.strip()
    except Exception:
        pass

    return RepoInfo(
        path=repo_path,
        name=name,
        project=project,
        suggested_tags=suggested_tags,
        remote_url=remote_url,
        relative_path=str(rel_path),
    )


def _detect_repo_tags(repo_path: Path) -> list[str]:
    """
    Detect tags using registered detectors.

    Uses LANGUAGE_DETECTORS, FRAMEWORK_DETECTORS, and TYPE_INDICATORS.
    """
    tags: list[str] = []

    # Detect languages
    for detector in LANGUAGE_DETECTORS:
        if detector.matches(repo_path):
            tags.append(f"lang:{detector.language}")

    # Load npm dependencies once (if package.json exists)
    npm_deps: set[str] = set()
    pkg_json = repo_path / "package.json"
    if pkg_json.exists():
        try:
            import json

            pkg = json.loads(pkg_json.read_text())
            npm_deps = set(pkg.get("dependencies", {}).keys())
            npm_deps.update(pkg.get("devDependencies", {}).keys())
        except Exception:
            pass

    # Load pip content once (requirements.txt or pyproject.toml)
    pip_content = ""
    for pyfile in [repo_path / "requirements.txt", repo_path / "pyproject.toml"]:
        if pyfile.exists():
            try:
                pip_content = pyfile.read_text().lower()
            except Exception:
                pass
            break

    # Detect frameworks
    for detector in FRAMEWORK_DETECTORS:
        if detector.matches(repo_path, npm_deps, pip_content):
            tags.append(f"framework:{detector.framework}")

    # Detect project types
    for indicator in TYPE_INDICATORS:
        if indicator.matches(repo_path):
            tags.append(indicator.tag)

    return list(set(tags))  # Deduplicate


def create_codebase_summary(repo_path: Path) -> Memory:
    """
    Create a summary memory of the codebase structure.

    Returns a single memory with high-level codebase overview.
    """
    # Count files by extension
    extension_counts: dict[str, int] = {}
    total_files = 0
    total_lines = 0

    ignore_dirs = {"node_modules", ".git", "venv", ".venv", "__pycache__", "dist", "build"}

    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue

        # Skip ignored directories
        if any(d in path.parts for d in ignore_dirs):
            continue

        ext = path.suffix.lower()
        if ext in DEFAULT_INDEX_EXTENSIONS:
            extension_counts[ext] = extension_counts.get(ext, 0) + 1
            total_files += 1

            # Count lines (sample for large repos)
            if total_files <= 100:
                try:
                    total_lines += len(path.read_text(errors="ignore").splitlines())
                except Exception:
                    pass

    # Get top directories
    top_dirs = []
    for item in sorted(repo_path.iterdir()):
        if item.is_dir() and item.name not in ignore_dirs and not item.name.startswith("."):
            top_dirs.append(item.name)

    # Build summary
    top_extensions = sorted(extension_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ext_summary = ", ".join(f"{ext}({count})" for ext, count in top_extensions)

    summary_content = f"""Codebase Summary for {repo_path.name}

Structure:
- Top-level directories: {", ".join(top_dirs[:10])}
- Total indexable files: {total_files}
- Estimated lines of code: {total_lines}

File types: {ext_summary}

This codebase was auto-indexed on {datetime.now().strftime("%Y-%m-%d %H:%M")}.
Search for specific files, functions, or patterns to explore the code."""

    return Memory(
        content=summary_content,
        type=MemoryType.FACT,
        tags=["codebase-summary", "auto-indexed", repo_path.name],
        summary=f"Codebase summary: {repo_path.name}",
        source_tool="auto-index",
        metadata={
            "total_files": total_files,
            "extensions": dict(top_extensions),
            "top_dirs": top_dirs[:10],
        },
    )
