"""
ContextFS Indexing Package.

Provides automatic indexing of repositories and files.
"""

from contextfs.indexing.autoindex import (
    DEFAULT_IGNORE_PATTERNS,
    AutoIndexer,
    IndexMode,
    IndexStatus,
)
from contextfs.indexing.discovery import (
    DEFAULT_INDEX_EXTENSIONS,
    FRAMEWORK_DETECTORS,
    LANGUAGE_DETECTORS,
    PROJECT_CONTAINER_NAMES,
    TYPE_INDICATORS,
    WORKSPACE_CONFIG_FILES,
    FrameworkDetector,
    LanguageDetector,
    RepoInfo,
    TypeIndicator,
    create_codebase_summary,
    discover_git_repos,
)

__all__ = [
    # Core classes
    "AutoIndexer",
    "IndexMode",
    "IndexStatus",
    # Discovery
    "RepoInfo",
    "LanguageDetector",
    "FrameworkDetector",
    "TypeIndicator",
    "discover_git_repos",
    "create_codebase_summary",
    # Constants
    "DEFAULT_IGNORE_PATTERNS",
    "DEFAULT_INDEX_EXTENSIONS",
    "LANGUAGE_DETECTORS",
    "FRAMEWORK_DETECTORS",
    "TYPE_INDICATORS",
    "PROJECT_CONTAINER_NAMES",
    "WORKSPACE_CONFIG_FILES",
]
