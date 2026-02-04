"""Configuration loading and merging."""

import json
from pathlib import Path
from typing import Any

from .schema import Config, ProjectMappings


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ConfigLoader:
    """Load and merge configuration from multiple sources."""

    def __init__(self, default_config_path: Path | None = None):
        self.default_config_path = default_config_path or self._find_default_config()

    def _find_default_config(self) -> Path:
        """Find the default configuration file."""
        # Check in package directory
        package_dir = Path(__file__).parent.parent.parent.parent.parent
        config_path = package_dir / "config" / "default_config.json"
        if config_path.exists():
            return config_path

        # Check in current directory
        cwd_config = Path("config") / "default_config.json"
        if cwd_config.exists():
            return cwd_config

        # Fall back to empty config
        return Path("default_config.json")

    def load_json(self, path: Path) -> dict[str, Any]:
        """Load a JSON file."""
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load(
        self,
        config_path: Path | None = None,
        cli_overrides: dict[str, Any] | None = None,
    ) -> Config:
        """Load configuration with merging priority: default < file < CLI."""
        # Load default config
        default_data = self.load_json(self.default_config_path)

        # Load user config if provided
        user_data = {}
        if config_path and config_path.exists():
            user_data = self.load_json(config_path)

        # Merge configs
        merged = deep_merge(default_data, user_data)

        # Apply CLI overrides
        if cli_overrides:
            for key, value in cli_overrides.items():
                if value is not None:
                    merged[key] = value

        # Create config object
        config = Config(**merged)

        # Load mappings if file exists
        mappings_path = config.mappings_file
        if not mappings_path.is_absolute():
            if config_path:
                mappings_path = config_path.parent / mappings_path
            else:
                mappings_path = Path.cwd() / mappings_path

        if mappings_path.exists():
            mappings_data = self.load_json(mappings_path)
            config.mappings = ProjectMappings(**mappings_data)

        return config


def load_config(
    config_path: Path | None = None,
    base_dir: Path | None = None,
    output_dir: Path | None = None,
    verbose: bool = False,
    dry_run: bool = False,
    output_format: str = "text",
) -> Config:
    """Convenience function to load configuration."""
    cli_overrides = {
        "verbose": verbose,
        "dry_run": dry_run,
        "output_format": output_format,
    }
    if base_dir:
        cli_overrides["base_dir"] = base_dir
    if output_dir:
        cli_overrides["output_dir"] = output_dir

    loader = ConfigLoader()
    return loader.load(config_path, cli_overrides)
