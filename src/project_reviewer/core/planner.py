"""Action plan generation."""

from datetime import datetime
from pathlib import Path
from typing import Any

from ..config.schema import Config
from ..models.action import Action, ActionPlan, ActionType
from ..models.classification import ClassificationResult, ProjectStatus
from ..models.project import ProjectAnalysis
from ..utils.file_ops import iter_dirs
from ..utils.output import Output


class Planner:
    """Generate action plans for project reorganization."""

    def __init__(self, config: Config, output: Output | None = None):
        self.config = config
        self.output = output or Output(verbose=config.verbose)

    def create_plan(
        self,
        name: str = "Project Reorganization Plan",
        description: str = "",
    ) -> ActionPlan:
        """Create a new action plan.

        Args:
            name: Plan name
            description: Plan description

        Returns:
            New ActionPlan instance
        """
        return ActionPlan(
            name=name,
            description=description,
            created_at=datetime.now().isoformat(),
        )

    def plan_from_classification(
        self,
        classification: ClassificationResult,
        analysis: ProjectAnalysis | None = None,
    ) -> list[Action]:
        """Generate actions from classification result.

        Args:
            classification: Project classification
            analysis: Optional project analysis

        Returns:
            List of recommended actions
        """
        actions = []
        project_path = classification.path

        # Check for rename in mappings
        if classification.name in self.config.mappings.renamings:
            new_name = self.config.mappings.renamings[classification.name]
            actions.append(
                Action(
                    action_type=ActionType.RENAME,
                    project_path=project_path,
                    description=f"Rename to {new_name}",
                    target=new_name,
                    source=classification.name,
                )
            )

        # Handle based on status
        if classification.status == ProjectStatus.NEEDS_CLEANUP:
            # Add cleanup actions
            if classification.has_old_folders:
                for folder in self._find_old_folders(project_path):
                    actions.append(
                        Action(
                            action_type=ActionType.DELETE,
                            project_path=project_path,
                            description=f"Remove old folder: {folder}",
                            target=folder,
                        )
                    )

        # Add actions from analysis
        if analysis:
            # Credentials
            if analysis.credentials:
                for cred in analysis.credentials:
                    actions.append(
                        Action(
                            action_type=ActionType.REMOVE_CREDENTIALS,
                            project_path=project_path,
                            description=f"Remove {cred.credential_type} from {cred.file_path.name}",
                            target=str(cred.file_path),
                            details={
                                "line": cred.line_number,
                                "type": cred.credential_type,
                            },
                        )
                    )

            # Sensitive files
            for sensitive in analysis.sensitive_files:
                actions.append(
                    Action(
                        action_type=ActionType.REMOVE_SENSITIVE_FILE,
                        project_path=project_path,
                        description=f"Handle sensitive file: {sensitive.path.name}",
                        target=str(sensitive.path),
                        details={"reason": sensitive.reason},
                    )
                )

            # Missing gitignore
            if not analysis.has_gitignore:
                actions.append(
                    Action(
                        action_type=ActionType.ADD_GITIGNORE,
                        project_path=project_path,
                        description="Add .gitignore file",
                    )
                )

            # Missing env example
            if analysis.has_env_file and not analysis.has_env_example:
                actions.append(
                    Action(
                        action_type=ActionType.CREATE_ENV_EXAMPLE,
                        project_path=project_path,
                        description="Create .env.example from .env",
                    )
                )

        # Check for AI cache directories
        for ai_dir in self.config.cleanup.ai_cache_directories:
            ai_path = project_path / ai_dir
            if ai_path.exists():
                actions.append(
                    Action(
                        action_type=ActionType.REMOVE_AI_CACHE,
                        project_path=project_path,
                        description=f"Remove AI cache directory: {ai_dir}",
                        target=ai_dir,
                    )
                )

        # Check for files to remove
        for file_name in self.config.cleanup.files_to_remove:
            file_path = project_path / file_name
            if file_path.exists():
                actions.append(
                    Action(
                        action_type=ActionType.DELETE,
                        project_path=project_path,
                        description=f"Remove file: {file_name}",
                        target=file_name,
                    )
                )

        return actions

    def _find_old_folders(self, project_path: Path) -> list[str]:
        """Find old/backup folders in a project."""
        old_folders = []
        for dir_path in iter_dirs(project_path, self.config.exclude_dirs, max_depth=2):
            name_lower = dir_path.name.lower()
            for keyword in self.config.classification.backup_keywords:
                if keyword in name_lower:
                    old_folders.append(str(dir_path.relative_to(project_path)))
                    break
        return old_folders

    def plan_splits(self) -> list[Action]:
        """Generate actions for configured project splits.

        Returns:
            List of split actions
        """
        actions = []

        for source_name, splits in self.config.mappings.splits.items():
            source_path = self.config.base_dir / source_name
            if not source_path.exists():
                self.output.warn(f"Split source not found: {source_name}")
                continue

            for new_name, split_config in splits.items():
                actions.append(
                    Action(
                        action_type=ActionType.SPLIT,
                        project_path=source_path,
                        description=f"Split {source_name} -> {new_name}",
                        target=new_name,
                        source=source_name,
                        details={
                            "files": split_config.files,
                            "description": split_config.description,
                        },
                    )
                )

        return actions

    def plan_merges(self) -> list[Action]:
        """Generate actions for configured project merges.

        Returns:
            List of merge actions
        """
        actions = []

        for target_name, sources in self.config.mappings.merges.items():
            target_path = self.config.base_dir / target_name

            for source_name in sources:
                source_path = self.config.base_dir / source_name
                if not source_path.exists():
                    self.output.warn(f"Merge source not found: {source_name}")
                    continue

                actions.append(
                    Action(
                        action_type=ActionType.MERGE,
                        project_path=source_path,
                        description=f"Merge {source_name} into {target_name}",
                        target=target_name,
                        source=source_name,
                    )
                )

        return actions

    def plan_renames(self) -> list[Action]:
        """Generate actions for configured renames.

        Returns:
            List of rename actions
        """
        actions = []

        for old_name, new_name in self.config.mappings.renamings.items():
            old_path = self.config.base_dir / old_name
            if not old_path.exists():
                self.output.debug(f"Rename source not found: {old_name}")
                continue

            actions.append(
                Action(
                    action_type=ActionType.RENAME,
                    project_path=old_path,
                    description=f"Rename {old_name} -> {new_name}",
                    target=new_name,
                    source=old_name,
                )
            )

        return actions

    def plan_global_cleanup(self, base_dir: Path) -> list[Action]:
        """Generate global cleanup actions for all projects.

        Args:
            base_dir: Base directory containing projects

        Returns:
            List of cleanup actions
        """
        actions = []

        for entry in sorted(base_dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            if entry.name in self.config.exclude_dirs:
                continue

            # Check for AI cache directories
            for ai_dir in self.config.cleanup.ai_cache_directories:
                ai_path = entry / ai_dir
                if ai_path.exists():
                    actions.append(
                        Action(
                            action_type=ActionType.REMOVE_AI_CACHE,
                            project_path=entry,
                            description=f"Remove {ai_dir} from {entry.name}",
                            target=ai_dir,
                        )
                    )

            # Check for files to remove
            for file_name in self.config.cleanup.files_to_remove:
                file_path = entry / file_name
                if file_path.exists():
                    actions.append(
                        Action(
                            action_type=ActionType.DELETE,
                            project_path=entry,
                            description=f"Remove {file_name} from {entry.name}",
                            target=file_name,
                        )
                    )

        return actions

    def generate_full_plan(
        self,
        base_dir: Path,
        classifications: dict[str, ClassificationResult] | None = None,
        analyses: dict[str, ProjectAnalysis] | None = None,
    ) -> ActionPlan:
        """Generate a comprehensive action plan.

        Args:
            base_dir: Base directory containing projects
            classifications: Optional pre-computed classifications
            analyses: Optional pre-computed analyses

        Returns:
            Complete ActionPlan
        """
        classifications = classifications or {}
        analyses = analyses or {}

        plan = self.create_plan(
            name="Full Project Reorganization",
            description="Generated action plan for project cleanup and reorganization",
        )

        # Global cleanup first
        self.output.info("Planning global cleanup...")
        for action in self.plan_global_cleanup(base_dir):
            plan.add_action(action)

        # Splits
        self.output.info("Planning splits...")
        for action in self.plan_splits():
            plan.add_action(action)

        # Merges
        self.output.info("Planning merges...")
        for action in self.plan_merges():
            plan.add_action(action)

        # Renames
        self.output.info("Planning renames...")
        for action in self.plan_renames():
            plan.add_action(action)

        # Per-project cleanup
        self.output.info("Planning per-project cleanup...")
        for name, classification in classifications.items():
            analysis = analyses.get(name)
            for action in self.plan_from_classification(classification, analysis):
                plan.add_action(action)

        self.output.ok(f"Generated plan with {len(plan.actions)} actions")
        return plan

    def save_plan(self, plan: ActionPlan, output_path: Path) -> None:
        """Save action plan to file.

        Args:
            plan: The action plan to save
            output_path: Path to save to
        """
        import json

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save JSON
        json_path = output_path.with_suffix(".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(plan.to_dict(), f, indent=2, default=str)

        # Save Markdown
        md_path = output_path.with_suffix(".md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(plan.to_markdown())

        self.output.ok(f"Saved plan to {json_path} and {md_path}")
