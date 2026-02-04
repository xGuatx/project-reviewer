"""Output formatting utilities."""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO


@dataclass
class Output:
    """Handles formatted output with different verbosity levels."""

    verbose: bool = False
    format: str = "text"
    stream: TextIO = sys.stdout

    def ok(self, message: str) -> None:
        """Print success message."""
        self._print(f"[OK] {message}")

    def warn(self, message: str) -> None:
        """Print warning message."""
        self._print(f"[WARN] {message}")

    def err(self, message: str) -> None:
        """Print error message."""
        self._print(f"[ERR] {message}", file=sys.stderr)

    def info(self, message: str) -> None:
        """Print info message."""
        self._print(f"[INFO] {message}")

    def debug(self, message: str) -> None:
        """Print debug message (only in verbose mode)."""
        if self.verbose:
            self._print(f"[DEBUG] {message}")

    def plain(self, message: str) -> None:
        """Print plain message without prefix."""
        self._print(message)

    def header(self, title: str) -> None:
        """Print a section header."""
        self._print("")
        self._print("=" * 60)
        self._print(f"  {title}")
        self._print("=" * 60)

    def subheader(self, title: str) -> None:
        """Print a subsection header."""
        self._print("")
        self._print(f"--- {title} ---")

    def list_item(self, item: str, indent: int = 0) -> None:
        """Print a list item."""
        prefix = "  " * indent
        self._print(f"{prefix}- {item}")

    def json_output(self, data: Any) -> None:
        """Output data as JSON."""
        self._print(json.dumps(data, indent=2, default=str))

    def markdown_output(self, content: str) -> None:
        """Output markdown content."""
        self._print(content)

    def _print(self, message: str, file: TextIO | None = None) -> None:
        """Internal print function."""
        target = file or self.stream
        print(message, file=target)

    def result(self, data: Any, text_formatter: callable = None) -> None:
        """Output result in the configured format."""
        if self.format == "json":
            self.json_output(data)
        elif self.format == "markdown":
            if hasattr(data, "to_markdown"):
                self.markdown_output(data.to_markdown())
            elif text_formatter:
                self.markdown_output(text_formatter(data))
            else:
                self.json_output(data)
        else:
            if text_formatter:
                self._print(text_formatter(data))
            elif hasattr(data, "to_dict"):
                self.json_output(data.to_dict())
            else:
                self._print(str(data))


def format_status(status: str) -> str:
    """Format a status string with appropriate prefix."""
    status_map = {
        "safe": "[OK]",
        "ok": "[OK]",
        "success": "[OK]",
        "warning": "[WARN]",
        "warn": "[WARN]",
        "cleanup": "[WARN]",
        "error": "[ERR]",
        "err": "[ERR]",
        "fail": "[ERR]",
        "failed": "[ERR]",
        "info": "[INFO]",
        "review": "[INFO]",
    }
    prefix = status_map.get(status.lower(), "[?]")
    return f"{prefix} {status}"


def write_report(
    path: Path,
    content: str | dict[str, Any],
    format: str = "text",
) -> None:
    """Write a report to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if format == "json" and isinstance(content, dict):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, default=str)
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(content))
