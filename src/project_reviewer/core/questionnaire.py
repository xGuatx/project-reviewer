"""Interactive project questionnaire."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config.schema import Config
from ..models.classification import ClassificationResult, ProjectStatus
from ..utils.output import Output


class Questionnaire:
    """Interactive questionnaire for project classification decisions."""

    def __init__(self, config: Config, output: Output | None = None):
        self.config = config
        self.output = output or Output(verbose=config.verbose)
        self.responses: dict[str, dict[str, Any]] = {}
        self.responses_file: Path | None = None

    def load_responses(self, file_path: Path) -> None:
        """Load existing responses from file."""
        self.responses_file = file_path
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.responses = json.load(f)
                self.output.info(f"Loaded {len(self.responses)} existing responses")
            except (json.JSONDecodeError, IOError) as e:
                self.output.warn(f"Could not load responses: {e}")
                self.responses = {}

    def save_responses(self) -> None:
        """Save responses to file."""
        if self.responses_file:
            with open(self.responses_file, "w", encoding="utf-8") as f:
                json.dump(self.responses, f, indent=2, ensure_ascii=False)

    def ask_question(
        self,
        question: str,
        options: list[str] | None = None,
        default: str | None = None,
    ) -> str:
        """Ask a question and get user input.

        Args:
            question: The question to ask
            options: Optional list of valid options
            default: Default value if user presses Enter

        Returns:
            User's response
        """
        self.output.plain("")
        self.output.plain(question)

        if options:
            for i, opt in enumerate(options, 1):
                self.output.plain(f"  {i}. {opt}")

        prompt = "> "
        if default:
            prompt = f"> [{default}] "

        while True:
            try:
                response = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                self.output.plain("")
                return default or ""

            if not response and default:
                return default

            if options:
                # Accept number or exact text
                if response.isdigit():
                    idx = int(response) - 1
                    if 0 <= idx < len(options):
                        return options[idx]
                elif response in options:
                    return response
                self.output.warn("Invalid option. Please try again.")
            else:
                return response

    def ask_yes_no(self, question: str, default: bool = False) -> bool:
        """Ask a yes/no question.

        Args:
            question: The question to ask
            default: Default value

        Returns:
            True for yes, False for no
        """
        default_str = "Y/n" if default else "y/N"
        self.output.plain(f"{question} [{default_str}]")

        try:
            response = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return default

        if not response:
            return default
        return response in ("y", "yes", "oui", "o")

    def questionnaire_project(
        self,
        project_path: Path,
        classification: ClassificationResult | None = None,
    ) -> dict[str, Any]:
        """Run questionnaire for a single project.

        Args:
            project_path: Path to the project
            classification: Optional pre-computed classification

        Returns:
            Dictionary of responses
        """
        name = project_path.name

        # Check for existing response
        if name in self.responses:
            if not self.ask_yes_no(f"Re-do questionnaire for {name}?"):
                return self.responses[name]

        self.output.header(f"Project: {name}")

        if classification:
            self.output.info(f"Current status: {classification.status_label}")
            if classification.reasons:
                for reason in classification.reasons:
                    self.output.list_item(reason)

        response: dict[str, Any] = {
            "project": name,
            "path": str(project_path),
            "date": datetime.now().isoformat(),
        }

        # Nature of project
        response["nature"] = self.ask_question(
            "What is the nature of this project?",
            options=[
                "original",
                "fork",
                "clone",
                "backup",
                "library",
                "poc",
                "deployment",
            ],
        )

        # Current state
        response["state"] = self.ask_question(
            "What is the current state?",
            options=[
                "functional",
                "in_progress",
                "paused",
                "abandoned",
                "unknown",
            ],
        )

        # Usage frequency
        response["usage"] = self.ask_question(
            "How often is this used?",
            options=[
                "production",
                "regular",
                "occasional",
                "planned",
                "unused",
            ],
        )

        # Security questions
        self.output.subheader("Security")
        response["has_production_data"] = self.ask_yes_no(
            "Does it contain production data?"
        )
        response["has_hardcoded_secrets"] = self.ask_yes_no(
            "Does it have hardcoded secrets?"
        )
        response["secrets_separable"] = (
            self.ask_yes_no("Can secrets be separated/removed?")
            if response["has_hardcoded_secrets"]
            else True
        )

        # Publication intent
        self.output.subheader("Publication")
        response["intent"] = self.ask_question(
            "What do you want to do with this project?",
            options=[
                "publish",
                "cleanup_then_publish",
                "keep_local",
                "delete",
                "decide_later",
            ],
        )

        # Additional info based on intent
        if response["intent"] in ("publish", "cleanup_then_publish"):
            response["has_readme"] = self.ask_yes_no("Does it have a good README?")
            response["cleanup_level"] = self.ask_question(
                "How much cleanup needed?",
                options=["none", "minimal", "moderate", "extensive"],
                default="minimal",
            )

        # Notes
        response["description"] = self.ask_question(
            "Brief description (optional):",
            default="",
        )
        response["notes"] = self.ask_question(
            "Any additional notes (optional):",
            default="",
        )

        # Save response
        self.responses[name] = response
        self.save_responses()

        return response

    def run_batch(
        self,
        projects: list[Path],
        classifications: dict[str, ClassificationResult] | None = None,
        skip_answered: bool = True,
    ) -> dict[str, dict[str, Any]]:
        """Run questionnaire for multiple projects.

        Args:
            projects: List of project paths
            classifications: Optional pre-computed classifications
            skip_answered: Skip projects with existing responses

        Returns:
            Dictionary of all responses
        """
        classifications = classifications or {}
        total = len(projects)

        for i, project_path in enumerate(projects, 1):
            name = project_path.name

            if skip_answered and name in self.responses:
                self.output.info(f"Skipping {name} (already answered)")
                continue

            self.output.plain(f"\n[{i}/{total}] Processing {name}")

            try:
                classification = classifications.get(name)
                self.questionnaire_project(project_path, classification)
            except KeyboardInterrupt:
                self.output.plain("\n")
                if self.ask_yes_no("Save and exit?", default=True):
                    self.save_responses()
                    break

        return self.responses

    def generate_summary(self) -> dict[str, list[str]]:
        """Generate summary grouped by intent.

        Returns:
            Dictionary mapping intent to list of project names
        """
        summary: dict[str, list[str]] = {
            "publish": [],
            "cleanup_then_publish": [],
            "keep_local": [],
            "delete": [],
            "decide_later": [],
        }

        for name, response in self.responses.items():
            intent = response.get("intent", "decide_later")
            if intent in summary:
                summary[intent].append(name)

        return summary
