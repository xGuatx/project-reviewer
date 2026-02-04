"""Project classification models."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ProjectStatus(Enum):
    """Project publication status."""

    SAFE_TO_PUBLISH = "safe_to_publish"
    NEEDS_CLEANUP = "needs_cleanup"
    NEEDS_REVIEW = "needs_review"
    DO_NOT_PUBLISH = "do_not_publish"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    """Result of project classification."""

    path: Path
    name: str
    status: ProjectStatus
    reasons: list[str] = field(default_factory=list)
    functionality_score: int = 0
    is_git_clone: bool = False
    is_backup: bool = False
    has_production_data: bool = False
    has_old_folders: bool = False
    recommended_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": str(self.path),
            "name": self.name,
            "status": self.status.value,
            "reasons": self.reasons,
            "functionality_score": self.functionality_score,
            "is_git_clone": self.is_git_clone,
            "is_backup": self.is_backup,
            "has_production_data": self.has_production_data,
            "has_old_folders": self.has_old_folders,
            "recommended_actions": self.recommended_actions,
        }

    @property
    def status_label(self) -> str:
        """Get human-readable status label."""
        labels = {
            ProjectStatus.SAFE_TO_PUBLISH: "[OK] Safe to publish",
            ProjectStatus.NEEDS_CLEANUP: "[WARN] Needs cleanup",
            ProjectStatus.NEEDS_REVIEW: "[INFO] Needs review",
            ProjectStatus.DO_NOT_PUBLISH: "[ERR] Do not publish",
            ProjectStatus.UNKNOWN: "[?] Unknown",
        }
        return labels.get(self.status, "[?] Unknown")
