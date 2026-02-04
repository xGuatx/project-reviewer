"""Project analysis data models."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CredentialFinding:
    """A detected credential in a file."""

    file_path: Path
    line_number: int
    credential_type: str
    matched_text: str
    context: str = ""


@dataclass
class SensitiveFile:
    """A sensitive file detected in a project."""

    path: Path
    reason: str


@dataclass
class ProjectAnalysis:
    """Complete analysis of a project."""

    path: Path
    name: str
    has_git: bool = False
    has_readme: bool = False
    has_gitignore: bool = False
    file_count: int = 0
    dir_count: int = 0
    credentials: list[CredentialFinding] = field(default_factory=list)
    sensitive_files: list[SensitiveFile] = field(default_factory=list)
    has_env_file: bool = False
    has_env_example: bool = False
    main_language: str = ""
    frameworks: list[str] = field(default_factory=list)
    functionality_score: int = 0
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_credentials(self) -> bool:
        """Check if any credentials were found."""
        return len(self.credentials) > 0

    @property
    def has_sensitive_files(self) -> bool:
        """Check if any sensitive files were found."""
        return len(self.sensitive_files) > 0

    @property
    def is_clean(self) -> bool:
        """Check if project has no security issues."""
        return not self.has_credentials and not self.has_sensitive_files

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": str(self.path),
            "name": self.name,
            "has_git": self.has_git,
            "has_readme": self.has_readme,
            "has_gitignore": self.has_gitignore,
            "file_count": self.file_count,
            "dir_count": self.dir_count,
            "credentials": [
                {
                    "file": str(c.file_path),
                    "line": c.line_number,
                    "type": c.credential_type,
                    "context": c.context,
                }
                for c in self.credentials
            ],
            "sensitive_files": [
                {"path": str(f.path), "reason": f.reason} for f in self.sensitive_files
            ],
            "has_env_file": self.has_env_file,
            "has_env_example": self.has_env_example,
            "main_language": self.main_language,
            "frameworks": self.frameworks,
            "functionality_score": self.functionality_score,
            "issues": self.issues,
            "warnings": self.warnings,
            "is_clean": self.is_clean,
        }
