"""ASCII cleanup functionality."""

import unicodedata
from pathlib import Path
from typing import Any

from ..config.schema import Config
from ..utils.file_ops import iter_files, read_file_safe
from ..utils.output import Output


class AsciiCleaner:
    """Clean non-ASCII characters from files."""

    def __init__(self, config: Config, output: Output | None = None):
        self.config = config
        self.output = output or Output(verbose=config.verbose)

    def clean_text(self, text: str) -> str:
        """Convert non-ASCII characters to ASCII equivalents.

        Uses Unicode NFD normalization to decompose characters,
        then encodes to ASCII, dropping characters that can't be converted.

        Args:
            text: Input text

        Returns:
            ASCII-safe text
        """
        # Normalize to decomposed form (NFD)
        normalized = unicodedata.normalize("NFD", text)
        # Encode to ASCII, ignoring characters that can't be converted
        ascii_bytes = normalized.encode("ascii", "ignore")
        # Decode back to string
        return ascii_bytes.decode("ascii")

    def has_non_ascii(self, text: str) -> bool:
        """Check if text contains non-ASCII characters.

        Args:
            text: Text to check

        Returns:
            True if non-ASCII characters are present
        """
        try:
            text.encode("ascii")
            return False
        except UnicodeEncodeError:
            return True

    def find_non_ascii_chars(self, text: str) -> list[tuple[int, str, str]]:
        """Find all non-ASCII characters in text.

        Args:
            text: Text to scan

        Returns:
            List of (position, character, unicode_name) tuples
        """
        findings = []
        for i, char in enumerate(text):
            if ord(char) > 127:
                try:
                    name = unicodedata.name(char, "UNKNOWN")
                except ValueError:
                    name = "UNKNOWN"
                findings.append((i, char, name))
        return findings

    def is_binary_file(self, path: Path) -> bool:
        """Check if a file is binary based on extension.

        Args:
            path: File path

        Returns:
            True if file is binary
        """
        return path.suffix.lower() in self.config.ascii_cleanup.binary_extensions

    def should_skip_file(self, path: Path) -> bool:
        """Check if a file should be skipped.

        Args:
            path: File path

        Returns:
            True if file should be skipped
        """
        if self.is_binary_file(path):
            return True

        if path.name in self.config.ascii_cleanup.ignore_files:
            return True

        return False

    def should_skip_dir(self, dir_name: str) -> bool:
        """Check if a directory should be skipped.

        Args:
            dir_name: Directory name

        Returns:
            True if directory should be skipped
        """
        return dir_name in self.config.ascii_cleanup.ignore_dirs

    def clean_file(self, file_path: Path, dry_run: bool = False) -> dict[str, Any]:
        """Clean non-ASCII characters from a single file.

        Args:
            file_path: Path to the file
            dry_run: If True, don't write changes

        Returns:
            Dictionary with cleaning results
        """
        result = {
            "path": str(file_path),
            "had_non_ascii": False,
            "cleaned": False,
            "chars_removed": 0,
            "error": None,
        }

        if self.should_skip_file(file_path):
            result["skipped"] = True
            return result

        content = read_file_safe(file_path)
        if content is None:
            result["error"] = "Could not read file"
            return result

        if not self.has_non_ascii(content):
            return result

        result["had_non_ascii"] = True

        # Find non-ASCII characters
        non_ascii = self.find_non_ascii_chars(content)
        result["chars_removed"] = len(non_ascii)

        if self.config.verbose:
            for pos, char, name in non_ascii[:5]:
                self.output.debug(f"  Found: '{char}' ({name}) at position {pos}")
            if len(non_ascii) > 5:
                self.output.debug(f"  ... and {len(non_ascii) - 5} more")

        # Clean the content
        cleaned_content = self.clean_text(content)

        if not dry_run:
            try:
                file_path.write_text(cleaned_content, encoding="utf-8")
                result["cleaned"] = True
            except IOError as e:
                result["error"] = str(e)
        else:
            result["cleaned"] = True  # Would have been cleaned

        return result

    def clean_directory(
        self,
        directory: Path,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Clean non-ASCII characters from all files in a directory.

        Args:
            directory: Directory to clean
            dry_run: If True, don't write changes

        Returns:
            Summary of cleaning results
        """
        summary = {
            "directory": str(directory),
            "total_files": 0,
            "files_with_non_ascii": 0,
            "cleaned": 0,
            "skipped": 0,
            "errors": 0,
            "files": [],
        }

        self.output.info(f"Cleaning directory: {directory}")
        if dry_run:
            self.output.info("DRY RUN - No changes will be made")

        # Build exclude dirs list
        exclude_dirs = list(self.config.ascii_cleanup.ignore_dirs)

        for file_path in iter_files(directory, exclude_dirs):
            summary["total_files"] += 1

            if self.should_skip_file(file_path):
                summary["skipped"] += 1
                continue

            result = self.clean_file(file_path, dry_run)

            if result.get("error"):
                summary["errors"] += 1
                self.output.warn(f"Error: {file_path.name} - {result['error']}")
            elif result.get("had_non_ascii"):
                summary["files_with_non_ascii"] += 1
                if result.get("cleaned"):
                    summary["cleaned"] += 1
                    self.output.ok(f"Cleaned: {file_path.name} ({result['chars_removed']} chars)")
                    summary["files"].append(result)

        # Summary
        self.output.subheader("Summary")
        self.output.plain(f"  Total files scanned: {summary['total_files']}")
        self.output.plain(f"  Files with non-ASCII: {summary['files_with_non_ascii']}")
        self.output.plain(f"  Files cleaned: {summary['cleaned']}")
        self.output.plain(f"  Files skipped: {summary['skipped']}")
        if summary["errors"]:
            self.output.plain(f"  Errors: {summary['errors']}")

        return summary

    def preview_file(self, file_path: Path) -> None:
        """Preview non-ASCII characters in a file without cleaning.

        Args:
            file_path: Path to the file
        """
        if not file_path.exists():
            self.output.err(f"File not found: {file_path}")
            return

        content = read_file_safe(file_path)
        if content is None:
            self.output.err(f"Could not read file: {file_path}")
            return

        non_ascii = self.find_non_ascii_chars(content)

        if not non_ascii:
            self.output.ok(f"No non-ASCII characters in: {file_path.name}")
            return

        self.output.info(f"Found {len(non_ascii)} non-ASCII characters in: {file_path.name}")

        # Show context for each finding
        lines = content.split("\n")
        current_line = 0
        char_pos = 0
        shown_lines = set()

        for pos, char, name in non_ascii:
            # Find which line this character is on
            while char_pos + len(lines[current_line]) + 1 <= pos and current_line < len(lines) - 1:
                char_pos += len(lines[current_line]) + 1
                current_line += 1

            if current_line not in shown_lines:
                line_num = current_line + 1
                line_content = lines[current_line]
                # Truncate long lines
                if len(line_content) > 80:
                    line_content = line_content[:77] + "..."
                self.output.plain(f"  Line {line_num}: {line_content}")
                self.output.plain(f"          Character: '{char}' ({name})")
                shown_lines.add(current_line)

            if len(shown_lines) >= 10:
                remaining = len(non_ascii) - len(shown_lines)
                if remaining > 0:
                    self.output.plain(f"  ... and {remaining} more occurrences")
                break
