"""File operation utilities."""

import fnmatch
import os
from pathlib import Path
from typing import Iterator


def iter_files(
    root: Path,
    exclude_dirs: list[str] | None = None,
    extensions: list[str] | None = None,
    max_depth: int | None = None,
) -> Iterator[Path]:
    """Iterate over files in a directory tree.

    Args:
        root: Root directory to scan
        exclude_dirs: Directory names to skip
        extensions: File extensions to include (e.g., ['.py', '.js'])
        max_depth: Maximum depth to traverse (None = unlimited)

    Yields:
        Path objects for each matching file
    """
    exclude_dirs = exclude_dirs or []
    root = Path(root)

    def _walk(current: Path, depth: int) -> Iterator[Path]:
        if max_depth is not None and depth > max_depth:
            return

        try:
            entries = list(current.iterdir())
        except PermissionError:
            return

        for entry in entries:
            if entry.is_dir():
                if entry.name not in exclude_dirs:
                    yield from _walk(entry, depth + 1)
            elif entry.is_file():
                if extensions is None or entry.suffix.lower() in extensions:
                    yield entry

    yield from _walk(root, 0)


def iter_dirs(
    root: Path,
    exclude_dirs: list[str] | None = None,
    max_depth: int = 1,
) -> Iterator[Path]:
    """Iterate over directories.

    Args:
        root: Root directory to scan
        exclude_dirs: Directory names to skip
        max_depth: Maximum depth to traverse

    Yields:
        Path objects for each directory
    """
    exclude_dirs = exclude_dirs or []
    root = Path(root)

    def _walk(current: Path, depth: int) -> Iterator[Path]:
        if depth > max_depth:
            return

        try:
            entries = list(current.iterdir())
        except PermissionError:
            return

        for entry in entries:
            if entry.is_dir() and entry.name not in exclude_dirs:
                yield entry
                yield from _walk(entry, depth + 1)

    yield from _walk(root, 0)


def count_files(
    root: Path,
    exclude_dirs: list[str] | None = None,
) -> tuple[int, int]:
    """Count files and directories in a path.

    Returns:
        Tuple of (file_count, dir_count)
    """
    file_count = 0
    dir_count = 0
    exclude_dirs = exclude_dirs or []

    for entry in iter_files(root, exclude_dirs):
        file_count += 1

    for entry in iter_dirs(root, exclude_dirs):
        dir_count += 1

    return file_count, dir_count


def find_sensitive_files(
    root: Path,
    patterns: list[str],
    exclude_dirs: list[str] | None = None,
) -> list[tuple[Path, str]]:
    """Find files matching sensitive patterns.

    Args:
        root: Root directory to scan
        patterns: Glob patterns for sensitive files
        exclude_dirs: Directory names to skip

    Returns:
        List of (path, matched_pattern) tuples
    """
    found = []
    exclude_dirs = exclude_dirs or []

    for file_path in iter_files(root, exclude_dirs):
        for pattern in patterns:
            if matches_pattern(file_path.name, pattern):
                found.append((file_path, pattern))
                break

    return found


def matches_pattern(name: str, pattern: str) -> bool:
    """Check if a name matches a glob pattern."""
    return fnmatch.fnmatch(name, pattern)


def read_file_safe(path: Path, encoding: str = "utf-8") -> str | None:
    """Read a file safely, returning None on error."""
    try:
        return path.read_text(encoding=encoding)
    except (PermissionError, UnicodeDecodeError, FileNotFoundError):
        return None


def write_file_safe(path: Path, content: str, encoding: str = "utf-8") -> bool:
    """Write a file safely, returning success status."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
        return True
    except (PermissionError, OSError):
        return False


def file_exists(path: Path) -> bool:
    """Check if a file exists."""
    return path.exists() and path.is_file()


def dir_exists(path: Path) -> bool:
    """Check if a directory exists."""
    return path.exists() and path.is_dir()


def safe_delete(path: Path, dry_run: bool = False) -> bool:
    """Safely delete a file or directory.

    Args:
        path: Path to delete
        dry_run: If True, don't actually delete

    Returns:
        True if deleted (or would be deleted in dry_run)
    """
    if not path.exists():
        return False

    if dry_run:
        return True

    try:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            import shutil
            shutil.rmtree(path)
        return True
    except (PermissionError, OSError):
        return False
