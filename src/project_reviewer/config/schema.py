"""Pydantic models for configuration validation."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SecurityConfig(BaseModel):
    """Security scanning configuration."""

    credential_patterns: dict[str, str] = Field(default_factory=dict)
    sensitive_files: list[str] = Field(default_factory=list)
    code_extensions: list[str] = Field(default_factory=list)


class ClassificationConfig(BaseModel):
    """Project classification configuration."""

    backup_keywords: list[str] = Field(default_factory=list)
    main_files: list[str] = Field(default_factory=list)
    min_functionality_score: int = 3
    safe_functionality_score: int = 5


class CleanupConfig(BaseModel):
    """Cleanup configuration."""

    ai_cache_directories: list[str] = Field(default_factory=list)
    files_to_remove: list[str] = Field(default_factory=list)


class AsciiCleanupConfig(BaseModel):
    """ASCII cleanup configuration."""

    ignore_dirs: list[str] = Field(default_factory=list)
    ignore_files: list[str] = Field(default_factory=list)
    binary_extensions: list[str] = Field(default_factory=list)


class SplitProject(BaseModel):
    """Split project definition."""

    files: list[str] = Field(default_factory=list)
    description: str = ""


class ProjectMappings(BaseModel):
    """Project mappings configuration."""

    renamings: dict[str, str] = Field(default_factory=dict)
    splits: dict[str, dict[str, SplitProject]] = Field(default_factory=dict)
    merges: dict[str, list[str]] = Field(default_factory=dict)
    do_not_publish: list[str] = Field(default_factory=list)
    notes: dict[str, str] = Field(default_factory=dict)


class AppConfig(BaseModel):
    """Main configuration model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    base_dir: Path = Field(default=Path("."))
    output_dir: Path = Field(default=Path("./reports"))
    mappings_file: Path = Field(default=Path("./project_mappings.json"))
    exclude_dirs: list[str] = Field(default_factory=list)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    cleanup: CleanupConfig = Field(default_factory=CleanupConfig)
    ascii_cleanup: AsciiCleanupConfig = Field(default_factory=AsciiCleanupConfig)
    gitignore_template: list[str] = Field(default_factory=list)

    # Runtime options (set from CLI)
    verbose: bool = False
    dry_run: bool = False
    output_format: str = "text"

    # Loaded mappings
    mappings: ProjectMappings = Field(default_factory=ProjectMappings)


# Alias for backwards compatibility
Config = AppConfig
