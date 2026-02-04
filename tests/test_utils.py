"""Tests for utility functions."""

import tempfile
from pathlib import Path

from project_reviewer.utils.output import Output, format_status
from project_reviewer.utils.file_ops import matches_pattern, iter_files
from project_reviewer.utils.git_ops import is_git_repo


def test_output_creation():
    """Test Output class creation."""
    output = Output()
    assert output.verbose is False
    assert output.format == "text"


def test_output_verbose():
    """Test Output with verbose mode."""
    output = Output(verbose=True)
    assert output.verbose is True


def test_format_status():
    """Test format_status function."""
    assert "[OK]" in format_status("ok")
    assert "[OK]" in format_status("success")
    assert "[WARN]" in format_status("warn")
    assert "[WARN]" in format_status("warning")
    assert "[ERR]" in format_status("error")
    assert "[INFO]" in format_status("info")


def test_matches_pattern():
    """Test pattern matching."""
    assert matches_pattern("test.py", "*.py") is True
    assert matches_pattern("test.js", "*.py") is False
    assert matches_pattern(".env", ".env") is True
    assert matches_pattern(".env.local", ".env*") is True


def test_is_git_repo_false():
    """Test is_git_repo on non-git directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert is_git_repo(Path(tmpdir)) is False


def test_is_git_repo_true():
    """Test is_git_repo on git directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = Path(tmpdir) / ".git"
        git_dir.mkdir()
        assert is_git_repo(Path(tmpdir)) is True


def test_iter_files():
    """Test iter_files function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        (Path(tmpdir) / "file1.py").touch()
        (Path(tmpdir) / "file2.py").touch()
        (Path(tmpdir) / "file3.txt").touch()

        files = list(iter_files(Path(tmpdir)))
        assert len(files) == 3

        # With extension filter
        py_files = list(iter_files(Path(tmpdir), extensions=[".py"]))
        assert len(py_files) == 2


def test_iter_files_exclude_dirs():
    """Test iter_files with excluded directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create structure
        (Path(tmpdir) / "src").mkdir()
        (Path(tmpdir) / "node_modules").mkdir()
        (Path(tmpdir) / "src" / "main.py").touch()
        (Path(tmpdir) / "node_modules" / "lib.js").touch()

        files = list(iter_files(Path(tmpdir), exclude_dirs=["node_modules"]))
        assert len(files) == 1
        assert files[0].name == "main.py"
