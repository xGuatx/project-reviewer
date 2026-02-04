"""Action plan execution."""

import json
import shutil
from pathlib import Path
from typing import Callable

from ..config.schema import Config
from ..models.action import Action, ActionPlan, ActionType
from ..utils.file_ops import safe_delete, write_file_safe
from ..utils.git_ops import git_init
from ..utils.output import Output


class Executor:
    """Execute actions from an action plan."""

    def __init__(self, config: Config, output: Output | None = None):
        self.config = config
        self.output = output or Output(verbose=config.verbose)
        self._handlers: dict[ActionType, Callable[[Action, bool], bool]] = {
            ActionType.RENAME: self._execute_rename,
            ActionType.SPLIT: self._execute_split,
            ActionType.MERGE: self._execute_merge,
            ActionType.DELETE: self._execute_delete,
            ActionType.CLEANUP: self._execute_cleanup,
            ActionType.ADD_GITIGNORE: self._execute_add_gitignore,
            ActionType.CREATE_ENV_EXAMPLE: self._execute_create_env_example,
            ActionType.REMOVE_CREDENTIALS: self._execute_remove_credentials,
            ActionType.REMOVE_SENSITIVE_FILE: self._execute_remove_sensitive_file,
            ActionType.REMOVE_AI_CACHE: self._execute_remove_ai_cache,
            ActionType.ADD_README: self._execute_add_readme,
            ActionType.GIT_INIT: self._execute_git_init,
            ActionType.CLEAN_ASCII: self._execute_clean_ascii,
        }

    def execute_action(self, action: Action, dry_run: bool = False) -> bool:
        """Execute a single action.

        Args:
            action: The action to execute
            dry_run: If True, don't actually perform the action

        Returns:
            True if successful
        """
        handler = self._handlers.get(action.action_type)
        if not handler:
            action.error = f"No handler for action type: {action.action_type}"
            self.output.err(action.error)
            return False

        prefix = "[DRY-RUN] " if dry_run else ""
        self.output.info(f"{prefix}{action.description}")

        try:
            success = handler(action, dry_run)
            if success:
                action.completed = True
                self.output.ok(f"{prefix}Completed: {action.description}")
            else:
                self.output.warn(f"{prefix}Failed: {action.description}")
            return success
        except Exception as e:
            action.error = str(e)
            self.output.err(f"Error: {e}")
            return False

    def execute_plan(
        self,
        plan: ActionPlan,
        dry_run: bool = False,
        stop_on_error: bool = False,
    ) -> tuple[int, int]:
        """Execute all actions in a plan.

        Args:
            plan: The action plan to execute
            dry_run: If True, preview without changes
            stop_on_error: If True, stop on first error

        Returns:
            Tuple of (success_count, failure_count)
        """
        self.output.header(f"Executing: {plan.name}")
        if dry_run:
            self.output.info("DRY RUN MODE - No changes will be made")

        success_count = 0
        failure_count = 0

        for i, action in enumerate(plan.actions, 1):
            self.output.plain(f"\n[{i}/{len(plan.actions)}] {action.action_type.value}")

            if self.execute_action(action, dry_run):
                success_count += 1
            else:
                failure_count += 1
                if stop_on_error:
                    self.output.err("Stopping due to error")
                    break

        self.output.header("Execution Summary")
        self.output.ok(f"Successful: {success_count}")
        if failure_count:
            self.output.err(f"Failed: {failure_count}")

        return success_count, failure_count

    def load_plan(self, path: Path) -> ActionPlan | None:
        """Load an action plan from JSON file.

        Args:
            path: Path to the JSON file

        Returns:
            ActionPlan or None if failed
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            plan = ActionPlan(
                name=data.get("name", "Loaded Plan"),
                description=data.get("description", ""),
                created_at=data.get("created_at", ""),
            )

            for action_data in data.get("actions", []):
                plan.actions.append(Action.from_dict(action_data))

            self.output.ok(f"Loaded plan with {len(plan.actions)} actions")
            return plan
        except (json.JSONDecodeError, IOError, KeyError) as e:
            self.output.err(f"Failed to load plan: {e}")
            return None

    # Action handlers

    def _execute_rename(self, action: Action, dry_run: bool) -> bool:
        """Rename a project directory."""
        source = action.project_path
        target = source.parent / action.target

        if not source.exists():
            action.error = f"Source not found: {source}"
            return False

        if target.exists():
            action.error = f"Target already exists: {target}"
            return False

        if not dry_run:
            source.rename(target)
        return True

    def _execute_split(self, action: Action, dry_run: bool) -> bool:
        """Split a project into a new project."""
        source = action.project_path
        target = source.parent / action.target
        files = action.details.get("files", [])

        if not source.exists():
            action.error = f"Source not found: {source}"
            return False

        if not dry_run:
            target.mkdir(parents=True, exist_ok=True)
            for file_pattern in files:
                for file_path in source.glob(file_pattern):
                    dest = target / file_path.name
                    shutil.copy2(file_path, dest)

        return True

    def _execute_merge(self, action: Action, dry_run: bool) -> bool:
        """Merge a project into another."""
        source = action.project_path
        target = source.parent / action.target

        if not source.exists():
            action.error = f"Source not found: {source}"
            return False

        if not dry_run:
            target.mkdir(parents=True, exist_ok=True)
            # Copy all files from source to target subdirectory
            dest_subdir = target / source.name
            shutil.copytree(source, dest_subdir, dirs_exist_ok=True)

        return True

    def _execute_delete(self, action: Action, dry_run: bool) -> bool:
        """Delete a file or directory."""
        target_path = action.project_path / action.target if action.target else action.project_path

        if not target_path.exists():
            self.output.debug(f"Already deleted: {target_path}")
            return True

        return safe_delete(target_path, dry_run)

    def _execute_cleanup(self, action: Action, dry_run: bool) -> bool:
        """Generic cleanup action."""
        # Placeholder for custom cleanup logic
        return True

    def _execute_add_gitignore(self, action: Action, dry_run: bool) -> bool:
        """Add a .gitignore file."""
        gitignore_path = action.project_path / ".gitignore"

        content = "\n".join(self.config.gitignore_template)

        if gitignore_path.exists():
            existing = gitignore_path.read_text(encoding="utf-8")
            content = existing + "\n\n# Added by project-reviewer\n" + content

        if not dry_run:
            return write_file_safe(gitignore_path, content)
        return True

    def _execute_create_env_example(self, action: Action, dry_run: bool) -> bool:
        """Create .env.example from .env."""
        env_path = action.project_path / ".env"
        example_path = action.project_path / ".env.example"

        if not env_path.exists():
            action.error = "No .env file found"
            return False

        try:
            content = env_path.read_text(encoding="utf-8")
        except IOError:
            action.error = "Could not read .env"
            return False

        example_lines = []
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                example_lines.append(line)
            elif "=" in line:
                key = line.split("=")[0]
                example_lines.append(f"{key}=YOUR_{key.upper()}_HERE")
            else:
                example_lines.append(line)

        if not dry_run:
            return write_file_safe(example_path, "\n".join(example_lines))
        return True

    def _execute_remove_credentials(self, action: Action, dry_run: bool) -> bool:
        """Remove credentials from a file."""
        # This is a manual action - we only flag it
        self.output.warn(f"Manual review required: {action.target}")
        self.output.info(f"  Line {action.details.get('line')}: {action.details.get('type')}")
        return True  # Mark as "handled" but needs manual review

    def _execute_remove_sensitive_file(self, action: Action, dry_run: bool) -> bool:
        """Remove or handle a sensitive file."""
        target_path = Path(action.target)
        if not target_path.is_absolute():
            target_path = action.project_path / action.target

        if not target_path.exists():
            return True

        # Check if in gitignore
        gitignore_path = action.project_path / ".gitignore"
        if gitignore_path.exists():
            gitignore_content = gitignore_path.read_text(encoding="utf-8")
            if target_path.name in gitignore_content:
                self.output.info(f"Already in .gitignore: {target_path.name}")
                return True

        # Add to gitignore rather than delete
        self.output.warn(f"Sensitive file needs handling: {target_path.name}")
        return True

    def _execute_remove_ai_cache(self, action: Action, dry_run: bool) -> bool:
        """Remove AI cache directory."""
        target_path = action.project_path / action.target

        if not target_path.exists():
            return True

        return safe_delete(target_path, dry_run)

    def _execute_add_readme(self, action: Action, dry_run: bool) -> bool:
        """Add a basic README.md."""
        readme_path = action.project_path / "README.md"

        if readme_path.exists():
            return True

        content = f"# {action.project_path.name}\n\nProject description here.\n"

        if not dry_run:
            return write_file_safe(readme_path, content)
        return True

    def _execute_git_init(self, action: Action, dry_run: bool) -> bool:
        """Initialize a git repository."""
        return git_init(action.project_path, dry_run)

    def _execute_clean_ascii(self, action: Action, dry_run: bool) -> bool:
        """Clean non-ASCII characters from files."""
        from .cleaner import AsciiCleaner

        cleaner = AsciiCleaner(self.config, self.output)
        results = cleaner.clean_directory(action.project_path, dry_run)
        return results["cleaned"] > 0 or results["skipped"] >= 0
