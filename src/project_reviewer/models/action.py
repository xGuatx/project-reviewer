"""Action planning models."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ActionType(Enum):
    """Types of actions that can be performed."""

    RENAME = "rename"
    SPLIT = "split"
    MERGE = "merge"
    DELETE = "delete"
    CLEANUP = "cleanup"
    ADD_GITIGNORE = "add_gitignore"
    CREATE_ENV_EXAMPLE = "create_env_example"
    REMOVE_CREDENTIALS = "remove_credentials"
    REMOVE_SENSITIVE_FILE = "remove_sensitive_file"
    REMOVE_AI_CACHE = "remove_ai_cache"
    ADD_README = "add_readme"
    GIT_INIT = "git_init"
    CLEAN_ASCII = "clean_ascii"


@dataclass
class Action:
    """A single action to perform on a project."""

    action_type: ActionType
    project_path: Path
    description: str
    target: str = ""
    source: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    completed: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.action_type.value,
            "project": str(self.project_path),
            "description": self.description,
            "target": self.target,
            "source": self.source,
            "details": self.details,
            "completed": self.completed,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Action":
        """Create action from dictionary."""
        return cls(
            action_type=ActionType(data["type"]),
            project_path=Path(data["project"]),
            description=data.get("description", ""),
            target=data.get("target", ""),
            source=data.get("source", ""),
            details=data.get("details", {}),
            completed=data.get("completed", False),
            error=data.get("error", ""),
        )


@dataclass
class ActionPlan:
    """A complete action plan for multiple projects."""

    name: str
    description: str = ""
    actions: list[Action] = field(default_factory=list)
    created_at: str = ""

    def add_action(self, action: Action) -> None:
        """Add an action to the plan."""
        self.actions.append(action)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "actions": [a.to_dict() for a in self.actions],
            "created_at": self.created_at,
            "total_actions": len(self.actions),
            "completed": sum(1 for a in self.actions if a.completed),
            "failed": sum(1 for a in self.actions if a.error),
        }

    def to_markdown(self) -> str:
        """Generate markdown representation of the plan."""
        lines = [
            f"# {self.name}",
            "",
            self.description,
            "",
            f"**Total actions:** {len(self.actions)}",
            "",
            "## Actions",
            "",
        ]

        # Group by action type
        by_type: dict[ActionType, list[Action]] = {}
        for action in self.actions:
            if action.action_type not in by_type:
                by_type[action.action_type] = []
            by_type[action.action_type].append(action)

        for action_type, actions in by_type.items():
            lines.append(f"### {action_type.value.replace('_', ' ').title()}")
            lines.append("")
            for action in actions:
                status = "[x]" if action.completed else "[ ]"
                lines.append(f"- {status} {action.description}")
                if action.target:
                    lines.append(f"  - Target: `{action.target}`")
                if action.error:
                    lines.append(f"  - [ERR] {action.error}")
            lines.append("")

        return "\n".join(lines)
