"""Clean ASCII command implementation."""

from pathlib import Path

from ..config.schema import Config
from ..core.cleaner import AsciiCleaner
from ..utils.output import Output


def run_clean_ascii(
    config: Config,
    output: Output,
    target: Path,
    preview: bool = False,
) -> int:
    """Clean non-ASCII characters from files.

    Args:
        config: Configuration object
        output: Output handler
        target: File or directory to clean
        preview: Only preview, don't make changes

    Returns:
        Exit code (0 = success)
    """
    cleaner = AsciiCleaner(config, output)

    if not target.exists():
        output.err(f"Target not found: {target}")
        return 1

    output.header("ASCII Cleanup")

    if target.is_file():
        # Single file
        if preview:
            output.info(f"Previewing: {target}")
            cleaner.preview_file(target)
        else:
            output.info(f"Cleaning: {target}")
            result = cleaner.clean_file(target, dry_run=config.dry_run)

            if result.get("error"):
                output.err(f"Error: {result['error']}")
                return 1
            elif result.get("had_non_ascii"):
                if result.get("cleaned"):
                    output.ok(f"Cleaned {result['chars_removed']} non-ASCII characters")
                else:
                    output.warn("Had non-ASCII but cleaning failed")
            else:
                output.ok("No non-ASCII characters found")
    else:
        # Directory
        if preview:
            output.info(f"Previewing directory: {target}")
            # Just scan and report
            for file_path in target.rglob("*"):
                if file_path.is_file() and not cleaner.should_skip_file(file_path):
                    # Check parent directories
                    skip = False
                    for parent in file_path.relative_to(target).parents:
                        if parent.name and cleaner.should_skip_dir(parent.name):
                            skip = True
                            break
                    if skip:
                        continue

                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if cleaner.has_non_ascii(content):
                        non_ascii = cleaner.find_non_ascii_chars(content)
                        output.warn(f"{file_path.relative_to(target)}: {len(non_ascii)} non-ASCII chars")
        else:
            output.info(f"Cleaning directory: {target}")
            result = cleaner.clean_directory(target, dry_run=config.dry_run)

            if config.output_format == "json":
                output.json_output(result)

    return 0
