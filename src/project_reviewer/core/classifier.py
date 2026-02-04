"""Project classification functionality."""

from pathlib import Path
from typing import Iterator

from ..config.schema import Config
from ..models.classification import ClassificationResult, ProjectStatus
from ..models.project import ProjectAnalysis
from ..utils.file_ops import iter_files, iter_dirs, read_file_safe
from ..utils.git_ops import is_git_repo, is_external_clone
from ..utils.output import Output


class Classifier:
    """Classify projects for publication readiness."""

    def __init__(self, config: Config, output: Output | None = None):
        self.config = config
        self.output = output or Output(verbose=config.verbose)

    def is_backup_project(self, name: str) -> bool:
        """Check if project name suggests it's a backup."""
        name_lower = name.lower()
        for keyword in self.config.classification.backup_keywords:
            if keyword in name_lower:
                return True
        return False

    def has_old_backup_folders(self, project_path: Path) -> list[str]:
        """Find backup/old folders in a project."""
        backup_folders = []
        backup_keywords = self.config.classification.backup_keywords

        for dir_path in iter_dirs(project_path, self.config.exclude_dirs, max_depth=2):
            dir_name_lower = dir_path.name.lower()
            for keyword in backup_keywords:
                if keyword in dir_name_lower:
                    backup_folders.append(str(dir_path.relative_to(project_path)))
                    break

        return backup_folders

    def has_production_data(self, project_path: Path) -> list[str]:
        """Check for production data files."""
        production_patterns = [
            "prod.*",
            "*.prod.*",
            "production.*",
            "*.production.*",
            "credentials.json",
            "passwords.txt",
            "database.sql",
            "dump.sql",
            "*.dump",
        ]

        found = []
        for file_path in iter_files(
            project_path, self.config.exclude_dirs, max_depth=3
        ):
            name_lower = file_path.name.lower()
            for pattern in production_patterns:
                if pattern.startswith("*"):
                    if pattern[1:] in name_lower:
                        found.append(str(file_path.relative_to(project_path)))
                        break
                elif pattern.endswith("*"):
                    if name_lower.startswith(pattern[:-1]):
                        found.append(str(file_path.relative_to(project_path)))
                        break
                elif name_lower == pattern:
                    found.append(str(file_path.relative_to(project_path)))
                    break

        return found

    def calculate_functionality_score(self, project_path: Path) -> int:
        """Calculate a functionality score for a project.

        Higher score = more functional/complete project.
        """
        score = 0

        # Has README
        if (project_path / "README.md").exists() or (project_path / "README").exists():
            score += 2

        # Has src or app directory
        if (project_path / "src").exists() or (project_path / "app").exists():
            score += 2

        # Has main file
        for main_file in self.config.classification.main_files:
            if (project_path / main_file).exists():
                score += 3
                break

        # Has Docker
        if (project_path / "Dockerfile").exists() or (
            project_path / "docker-compose.yml"
        ).exists():
            score += 2

        # Has package config
        package_files = [
            "package.json",
            "pyproject.toml",
            "setup.py",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
        ]
        for pkg_file in package_files:
            if (project_path / pkg_file).exists():
                score += 1
                break

        # Penalty for very few files
        file_count = sum(1 for _ in iter_files(project_path, self.config.exclude_dirs))
        if file_count < 5:
            score -= 3

        return max(0, score)

    def classify_project(
        self, project_path: Path, analysis: ProjectAnalysis | None = None
    ) -> ClassificationResult:
        """Classify a single project.

        Args:
            project_path: Path to the project
            analysis: Optional pre-computed analysis

        Returns:
            ClassificationResult with status and recommendations
        """
        result = ClassificationResult(
            path=project_path,
            name=project_path.name,
            status=ProjectStatus.UNKNOWN,
        )

        # Check if in do_not_publish list
        if project_path.name in self.config.mappings.do_not_publish:
            result.status = ProjectStatus.DO_NOT_PUBLISH
            result.reasons.append("Listed in do_not_publish configuration")
            return result

        # Check if it's a backup
        if self.is_backup_project(project_path.name):
            result.is_backup = True
            result.reasons.append("Project name suggests backup")

        # Check if external clone
        if is_git_repo(project_path):
            if is_external_clone(project_path):
                result.is_git_clone = True
                result.reasons.append("External git clone detected")

        # Check for old/backup folders
        old_folders = self.has_old_backup_folders(project_path)
        if old_folders:
            result.has_old_folders = True
            result.reasons.append(f"Contains backup folders: {', '.join(old_folders[:3])}")

        # Check for production data
        prod_files = self.has_production_data(project_path)
        if prod_files:
            result.has_production_data = True
            result.reasons.append(f"Contains production data: {', '.join(prod_files[:3])}")

        # Calculate functionality score
        result.functionality_score = self.calculate_functionality_score(project_path)

        # Determine final status
        if result.is_backup or result.is_git_clone or result.has_production_data:
            result.status = ProjectStatus.DO_NOT_PUBLISH
        elif result.has_old_folders:
            result.status = ProjectStatus.NEEDS_CLEANUP
            result.recommended_actions.append("Remove backup folders")
        elif result.functionality_score < self.config.classification.min_functionality_score:
            result.status = ProjectStatus.NEEDS_REVIEW
            result.reasons.append(f"Low functionality score: {result.functionality_score}")
        elif result.functionality_score >= self.config.classification.safe_functionality_score:
            result.status = ProjectStatus.SAFE_TO_PUBLISH
            if not result.reasons:
                result.reasons.append("Meets all criteria")
        else:
            result.status = ProjectStatus.NEEDS_REVIEW

        # Add analysis-based recommendations
        if analysis:
            if analysis.credentials:
                result.status = ProjectStatus.NEEDS_CLEANUP
                result.recommended_actions.append("Remove exposed credentials")
            if analysis.sensitive_files:
                result.recommended_actions.append("Review sensitive files")
            if not analysis.has_gitignore:
                result.recommended_actions.append("Add .gitignore")
            if not analysis.has_readme:
                result.recommended_actions.append("Add README.md")

        return result

    def classify_directory(
        self, base_dir: Path, analyses: dict[str, ProjectAnalysis] | None = None
    ) -> Iterator[ClassificationResult]:
        """Classify all projects in a directory.

        Args:
            base_dir: Base directory containing projects
            analyses: Optional pre-computed analyses keyed by project name

        Yields:
            ClassificationResult for each project
        """
        analyses = analyses or {}
        self.output.info(f"Classifying projects in: {base_dir}")

        for entry in sorted(base_dir.iterdir()):
            if entry.is_dir() and entry.name not in self.config.exclude_dirs:
                if entry.name.startswith("."):
                    continue

                self.output.debug(f"Classifying: {entry.name}")
                analysis = analyses.get(entry.name)
                yield self.classify_project(entry, analysis)
