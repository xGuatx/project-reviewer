"""Tests for CLI functionality."""

import pytest
from project_reviewer.cli import create_parser, main


def test_parser_creation():
    """Test that parser is created successfully."""
    parser = create_parser()
    assert parser is not None
    assert parser.prog == "project-reviewer"


def test_help_exits_zero():
    """Test that --help returns exit code 0."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0


def test_version_exits_zero():
    """Test that --version returns exit code 0."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0


def test_no_command_returns_zero():
    """Test that running without a command returns 0."""
    result = main([])
    assert result == 0


def test_scan_help():
    """Test scan subcommand help."""
    with pytest.raises(SystemExit) as exc_info:
        main(["scan", "--help"])
    assert exc_info.value.code == 0


def test_classify_help():
    """Test classify subcommand help."""
    with pytest.raises(SystemExit) as exc_info:
        main(["classify", "--help"])
    assert exc_info.value.code == 0


def test_verify_help():
    """Test verify subcommand help."""
    with pytest.raises(SystemExit) as exc_info:
        main(["verify", "--help"])
    assert exc_info.value.code == 0
