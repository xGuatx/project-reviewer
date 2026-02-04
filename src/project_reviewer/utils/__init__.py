"""Utility functions."""

from .output import Output, format_status
from .file_ops import (
    iter_files,
    iter_dirs,
    count_files,
    find_sensitive_files,
    matches_pattern,
)
from .git_ops import (
    is_git_repo,
    git_init,
    git_add,
    git_status,
    is_external_clone,
)

__all__ = [
    "Output",
    "format_status",
    "iter_files",
    "iter_dirs",
    "count_files",
    "find_sensitive_files",
    "matches_pattern",
    "is_git_repo",
    "git_init",
    "git_add",
    "git_status",
    "is_external_clone",
]
