"""Security scanning functionality."""

import re
from pathlib import Path
from typing import Iterator

from ..config.schema import Config
from ..models.project import ProjectAnalysis, CredentialFinding, SensitiveFile
from ..utils.file_ops import iter_files, find_sensitive_files, read_file_safe
from ..utils.git_ops import is_git_repo
from ..utils.output import Output


class Scanner:
    """Security scanner for detecting credentials and sensitive files."""

    def __init__(self, config: Config, output: Output | None = None):
        self.config = config
        self.output = output or Output(verbose=config.verbose)
        self._compiled_patterns: dict[str, re.Pattern] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile credential regex patterns."""
        for name, pattern in self.config.security.credential_patterns.items():
            try:
                self._compiled_patterns[name] = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                self.output.warn(f"Invalid regex pattern for {name}: {e}")

    def scan_file(self, file_path: Path) -> list[CredentialFinding]:
        """Scan a single file for credentials.

        Args:
            file_path: Path to the file to scan

        Returns:
            List of credential findings
        """
        findings = []
        content = read_file_safe(file_path)

        if content is None:
            return findings

        lines = content.split("\n")
        for line_num, line in enumerate(lines, start=1):
            for cred_type, pattern in self._compiled_patterns.items():
                if pattern.search(line):
                    # Mask the actual credential
                    masked_line = line[:50] + "..." if len(line) > 50 else line
                    findings.append(
                        CredentialFinding(
                            file_path=file_path,
                            line_number=line_num,
                            credential_type=cred_type,
                            matched_text="[REDACTED]",
                            context=masked_line.strip(),
                        )
                    )

        return findings

    def scan_project(self, project_path: Path) -> ProjectAnalysis:
        """Scan a project for security issues.

        Args:
            project_path: Path to the project directory

        Returns:
            ProjectAnalysis with scan results
        """
        analysis = ProjectAnalysis(
            path=project_path,
            name=project_path.name,
        )

        # Check basic project structure
        analysis.has_git = is_git_repo(project_path)
        analysis.has_readme = (project_path / "README.md").exists() or (
            project_path / "README"
        ).exists()
        analysis.has_gitignore = (project_path / ".gitignore").exists()
        analysis.has_env_file = (project_path / ".env").exists()
        analysis.has_env_example = (project_path / ".env.example").exists()

        # Count files
        file_count = 0
        dir_count = 0

        # Find sensitive files
        sensitive_results = find_sensitive_files(
            project_path,
            self.config.security.sensitive_files,
            self.config.exclude_dirs,
        )

        for file_path, pattern in sensitive_results:
            analysis.sensitive_files.append(
                SensitiveFile(path=file_path, reason=f"Matches pattern: {pattern}")
            )

        # Scan code files for credentials
        code_extensions = set(self.config.security.code_extensions)

        for file_path in iter_files(
            project_path,
            exclude_dirs=self.config.exclude_dirs,
        ):
            file_count += 1

            if file_path.suffix.lower() in code_extensions:
                findings = self.scan_file(file_path)
                analysis.credentials.extend(findings)

        analysis.file_count = file_count

        # Add issues and warnings
        if analysis.credentials:
            analysis.issues.append(
                f"Found {len(analysis.credentials)} potential credentials"
            )

        if analysis.sensitive_files:
            analysis.warnings.append(
                f"Found {len(analysis.sensitive_files)} sensitive files"
            )

        if analysis.has_env_file and not analysis.has_env_example:
            analysis.warnings.append("Has .env but no .env.example")

        if not analysis.has_gitignore:
            analysis.warnings.append("No .gitignore file")

        return analysis

    def scan_directory(self, base_dir: Path) -> Iterator[ProjectAnalysis]:
        """Scan all projects in a directory.

        Args:
            base_dir: Base directory containing projects

        Yields:
            ProjectAnalysis for each project
        """
        self.output.info(f"Scanning projects in: {base_dir}")

        for entry in sorted(base_dir.iterdir()):
            if entry.is_dir() and entry.name not in self.config.exclude_dirs:
                if entry.name.startswith("."):
                    continue

                self.output.debug(f"Scanning: {entry.name}")
                yield self.scan_project(entry)

    def generate_gitignore(self, project_path: Path, dry_run: bool = False) -> str:
        """Generate a .gitignore file for a project.

        Args:
            project_path: Path to the project
            dry_run: If True, don't write the file

        Returns:
            The generated .gitignore content
        """
        existing_content = ""
        gitignore_path = project_path / ".gitignore"

        if gitignore_path.exists():
            existing_content = read_file_safe(gitignore_path) or ""

        # Merge with template
        template_lines = set(self.config.gitignore_template)
        existing_lines = set(existing_content.strip().split("\n")) if existing_content else set()

        # Combine, keeping existing structure
        merged = existing_content.strip()
        new_lines = template_lines - existing_lines

        if new_lines:
            if merged:
                merged += "\n\n# Added by project-reviewer\n"
            merged += "\n".join(sorted(new_lines))

        if not dry_run and merged:
            gitignore_path.write_text(merged + "\n", encoding="utf-8")

        return merged

    def create_env_example(self, project_path: Path, dry_run: bool = False) -> str:
        """Create a .env.example file from .env.

        Args:
            project_path: Path to the project
            dry_run: If True, don't write the file

        Returns:
            The generated .env.example content
        """
        env_path = project_path / ".env"
        example_path = project_path / ".env.example"

        if not env_path.exists():
            return ""

        content = read_file_safe(env_path)
        if not content:
            return ""

        example_lines = []
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                example_lines.append(line)
                continue

            if "=" in line:
                key = line.split("=")[0]
                placeholder = f"YOUR_{key.upper()}_HERE"
                example_lines.append(f"{key}={placeholder}")
            else:
                example_lines.append(line)

        example_content = "\n".join(example_lines)

        if not dry_run:
            example_path.write_text(example_content, encoding="utf-8")

        return example_content
