"""Verification and coherence checking."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config.schema import Config
from ..models.classification import ClassificationResult, ProjectStatus
from ..models.project import ProjectAnalysis
from ..utils.file_ops import iter_files, read_file_safe
from ..utils.git_ops import is_git_repo, has_uncommitted_changes, get_remote_url
from ..utils.output import Output


@dataclass
class VerificationResult:
    """Result of project verification."""

    project_path: Path
    project_name: str
    passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add an error and mark as failed."""
        self.errors.append(message)
        self.passed = False

    def add_warning(self, message: str) -> None:
        """Add a warning."""
        self.warnings.append(message)

    def add_info(self, message: str) -> None:
        """Add an info message."""
        self.info.append(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project": self.project_name,
            "path": str(self.project_path),
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
        }


class Verifier:
    """Verify project coherence and publication readiness."""

    def __init__(self, config: Config, output: Output | None = None):
        self.config = config
        self.output = output or Output(verbose=config.verbose)

    def verify_project(
        self,
        project_path: Path,
        analysis: ProjectAnalysis | None = None,
        classification: ClassificationResult | None = None,
    ) -> VerificationResult:
        """Verify a single project.

        Args:
            project_path: Path to the project
            analysis: Optional pre-computed analysis
            classification: Optional pre-computed classification

        Returns:
            VerificationResult with findings
        """
        result = VerificationResult(
            project_path=project_path,
            project_name=project_path.name,
        )

        # Basic structure checks
        if not project_path.exists():
            result.add_error("Project directory does not exist")
            return result

        if not project_path.is_dir():
            result.add_error("Path is not a directory")
            return result

        # Check for README
        has_readme = (
            (project_path / "README.md").exists()
            or (project_path / "README").exists()
            or (project_path / "README.txt").exists()
        )
        if not has_readme:
            result.add_warning("No README file found")

        # Check for gitignore
        if not (project_path / ".gitignore").exists():
            result.add_warning("No .gitignore file")

        # Git checks
        if is_git_repo(project_path):
            result.add_info("Git repository detected")

            if has_uncommitted_changes(project_path):
                result.add_warning("Has uncommitted changes")

            remote = get_remote_url(project_path)
            if remote:
                result.add_info(f"Remote: {remote}")
        else:
            result.add_info("Not a git repository")

        # Check for sensitive files
        if analysis and analysis.sensitive_files:
            for sf in analysis.sensitive_files:
                result.add_error(f"Sensitive file: {sf.path.name} ({sf.reason})")

        # Check for credentials
        if analysis and analysis.credentials:
            for cred in analysis.credentials:
                result.add_error(
                    f"Credential in {cred.file_path.name}:{cred.line_number} ({cred.credential_type})"
                )

        # Check classification
        if classification:
            if classification.status == ProjectStatus.DO_NOT_PUBLISH:
                result.add_error(f"Classified as DO_NOT_PUBLISH: {', '.join(classification.reasons)}")
            elif classification.status == ProjectStatus.NEEDS_CLEANUP:
                result.add_warning(f"Needs cleanup: {', '.join(classification.reasons)}")

        # Check for AI cache directories
        for ai_dir in self.config.cleanup.ai_cache_directories:
            if (project_path / ai_dir).exists():
                result.add_warning(f"AI cache directory present: {ai_dir}")

        # Check for files to remove
        for file_name in self.config.cleanup.files_to_remove:
            if (project_path / file_name).exists():
                result.add_warning(f"File should be removed: {file_name}")

        # Check .env handling
        env_path = project_path / ".env"
        env_example_path = project_path / ".env.example"
        gitignore_path = project_path / ".gitignore"

        if env_path.exists():
            if not env_example_path.exists():
                result.add_warning(".env exists but no .env.example")

            if gitignore_path.exists():
                gitignore_content = read_file_safe(gitignore_path) or ""
                if ".env" not in gitignore_content:
                    result.add_error(".env not in .gitignore")

        return result

    def verify_pre_publish(
        self,
        project_path: Path,
        analysis: ProjectAnalysis | None = None,
    ) -> VerificationResult:
        """Strict verification for publication readiness.

        Args:
            project_path: Path to the project
            analysis: Optional pre-computed analysis

        Returns:
            VerificationResult with strict checks
        """
        result = self.verify_project(project_path, analysis)

        # Additional strict checks for publication
        name = project_path.name

        # Must have README
        has_readme = (
            (project_path / "README.md").exists()
            or (project_path / "README").exists()
        )
        if not has_readme:
            result.add_error("README is required for publication")

        # Must have gitignore
        if not (project_path / ".gitignore").exists():
            result.add_error(".gitignore is required for publication")

        # Must be a git repo
        if not is_git_repo(project_path):
            result.add_warning("Should be a git repository for publication")

        # No credentials allowed
        if analysis and analysis.credentials:
            result.add_error(f"Cannot publish with {len(analysis.credentials)} credential(s)")

        # No sensitive files
        if analysis and analysis.sensitive_files:
            result.add_error(f"Cannot publish with {len(analysis.sensitive_files)} sensitive file(s)")

        # Check do_not_publish list
        if name in self.config.mappings.do_not_publish:
            result.add_error("Project is in do_not_publish list")

        return result

    def verify_coherence(
        self,
        base_dir: Path,
        analyses: dict[str, ProjectAnalysis] | None = None,
        classifications: dict[str, ClassificationResult] | None = None,
    ) -> dict[str, VerificationResult]:
        """Verify coherence of all projects in a directory.

        Args:
            base_dir: Base directory containing projects
            analyses: Optional pre-computed analyses
            classifications: Optional pre-computed classifications

        Returns:
            Dictionary of verification results keyed by project name
        """
        analyses = analyses or {}
        classifications = classifications or {}
        results = {}

        self.output.info(f"Verifying projects in: {base_dir}")

        for entry in sorted(base_dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            if entry.name in self.config.exclude_dirs:
                continue

            self.output.debug(f"Verifying: {entry.name}")

            analysis = analyses.get(entry.name)
            classification = classifications.get(entry.name)
            result = self.verify_project(entry, analysis, classification)
            results[entry.name] = result

        # Summary
        passed = sum(1 for r in results.values() if r.passed)
        failed = len(results) - passed
        self.output.info(f"Verification complete: {passed} passed, {failed} failed")

        return results

    def verify_all_pre_publish(
        self,
        base_dir: Path,
        analyses: dict[str, ProjectAnalysis] | None = None,
    ) -> dict[str, VerificationResult]:
        """Verify all projects for publication readiness.

        Args:
            base_dir: Base directory containing projects
            analyses: Optional pre-computed analyses

        Returns:
            Dictionary of verification results
        """
        analyses = analyses or {}
        results = {}

        self.output.info(f"Pre-publish verification in: {base_dir}")

        for entry in sorted(base_dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            if entry.name in self.config.exclude_dirs:
                continue

            self.output.debug(f"Checking: {entry.name}")

            analysis = analyses.get(entry.name)
            result = self.verify_pre_publish(entry, analysis)
            results[entry.name] = result

        # Summary
        ready = sum(1 for r in results.values() if r.passed)
        not_ready = len(results) - ready
        self.output.info(f"Pre-publish check: {ready} ready, {not_ready} not ready")

        return results

    def generate_report(
        self,
        results: dict[str, VerificationResult],
    ) -> str:
        """Generate a verification report.

        Args:
            results: Verification results

        Returns:
            Formatted report string
        """
        lines = [
            "# Verification Report",
            "",
            f"**Total projects:** {len(results)}",
            f"**Passed:** {sum(1 for r in results.values() if r.passed)}",
            f"**Failed:** {sum(1 for r in results.values() if not r.passed)}",
            "",
        ]

        # Failed projects
        failed = {k: v for k, v in results.items() if not v.passed}
        if failed:
            lines.append("## Failed Projects")
            lines.append("")
            for name, result in failed.items():
                lines.append(f"### {name}")
                for err in result.errors:
                    lines.append(f"- [ERR] {err}")
                for warn in result.warnings:
                    lines.append(f"- [WARN] {warn}")
                lines.append("")

        # Projects with warnings
        with_warnings = {
            k: v for k, v in results.items() if v.passed and v.warnings
        }
        if with_warnings:
            lines.append("## Projects with Warnings")
            lines.append("")
            for name, result in with_warnings.items():
                lines.append(f"### {name}")
                for warn in result.warnings:
                    lines.append(f"- [WARN] {warn}")
                lines.append("")

        # Clean projects
        clean = {
            k: v for k, v in results.items() if v.passed and not v.warnings
        }
        if clean:
            lines.append("## Clean Projects")
            lines.append("")
            for name in clean:
                lines.append(f"- [OK] {name}")
            lines.append("")

        return "\n".join(lines)
