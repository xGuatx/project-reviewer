"""Git operation utilities."""

import subprocess
from pathlib import Path


def run_git(
    args: list[str],
    cwd: Path | None = None,
    capture: bool = True,
) -> tuple[int, str, str]:
    """Run a git command.

    Args:
        args: Git command arguments (without 'git')
        cwd: Working directory
        capture: Whether to capture output

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=capture,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout, result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return 1, "", str(e)


def is_git_repo(path: Path) -> bool:
    """Check if a path is a git repository."""
    git_dir = path / ".git"
    return git_dir.exists() and git_dir.is_dir()


def git_init(path: Path, dry_run: bool = False) -> bool:
    """Initialize a git repository.

    Args:
        path: Directory to initialize
        dry_run: If True, don't actually initialize

    Returns:
        True if successful
    """
    if dry_run:
        return True

    code, _, _ = run_git(["init"], cwd=path)
    return code == 0


def git_add(path: Path, files: list[str] | None = None, dry_run: bool = False) -> bool:
    """Add files to git staging.

    Args:
        path: Repository path
        files: Specific files to add (None = all)
        dry_run: If True, don't actually add

    Returns:
        True if successful
    """
    if dry_run:
        return True

    args = ["add"]
    if files:
        args.extend(files)
    else:
        args.append(".")

    code, _, _ = run_git(args, cwd=path)
    return code == 0


def git_status(path: Path) -> dict[str, list[str]]:
    """Get git status of a repository.

    Returns:
        Dictionary with 'staged', 'modified', 'untracked' lists
    """
    result = {
        "staged": [],
        "modified": [],
        "untracked": [],
    }

    if not is_git_repo(path):
        return result

    code, stdout, _ = run_git(["status", "--porcelain"], cwd=path)
    if code != 0:
        return result

    for line in stdout.strip().split("\n"):
        if not line:
            continue
        status = line[:2]
        filename = line[3:]

        if status[0] in "MADRC":
            result["staged"].append(filename)
        if status[1] == "M":
            result["modified"].append(filename)
        if status == "??":
            result["untracked"].append(filename)

    return result


def get_remote_url(path: Path) -> str | None:
    """Get the remote URL of a git repository."""
    if not is_git_repo(path):
        return None

    code, stdout, _ = run_git(["remote", "get-url", "origin"], cwd=path)
    if code == 0:
        return stdout.strip()
    return None


def is_external_clone(path: Path, owner_patterns: list[str] | None = None) -> bool:
    """Check if a repository is a clone from an external source.

    Args:
        path: Repository path
        owner_patterns: Patterns that indicate ownership (e.g., ['myuser'])

    Returns:
        True if the repo appears to be cloned from elsewhere
    """
    remote_url = get_remote_url(path)
    if not remote_url:
        return False

    # If no owner patterns specified, any remote means external
    if not owner_patterns:
        return True

    # Check if the URL contains any owner pattern
    remote_lower = remote_url.lower()
    for pattern in owner_patterns:
        if pattern.lower() in remote_lower:
            return False

    # Remote exists but doesn't match owner patterns
    return True


def get_branch(path: Path) -> str | None:
    """Get the current branch name."""
    if not is_git_repo(path):
        return None

    code, stdout, _ = run_git(["branch", "--show-current"], cwd=path)
    if code == 0:
        return stdout.strip()
    return None


def has_uncommitted_changes(path: Path) -> bool:
    """Check if there are uncommitted changes."""
    status = git_status(path)
    return bool(status["staged"] or status["modified"] or status["untracked"])
