"""Scan command implementation."""

import json
from pathlib import Path

from ..config.schema import Config
from ..core.scanner import Scanner
from ..utils.output import Output


def run_scan(
    config: Config,
    output: Output,
    target: Path | None = None,
    auto_fix: bool = False,
) -> int:
    """Run security scanning on projects.

    Args:
        config: Configuration object
        output: Output handler
        target: Specific project to scan (or None for all)
        auto_fix: Automatically fix issues (.gitignore, .env.example)

    Returns:
        Exit code (0 = success, 1 = issues found)
    """
    scanner = Scanner(config, output)
    base_dir = config.base_dir

    results = []
    issues_found = 0

    if target:
        # Scan single project
        project_path = target if target.is_absolute() else base_dir / target
        if not project_path.exists():
            output.err(f"Project not found: {project_path}")
            return 1

        output.header(f"Scanning: {project_path.name}")
        analysis = scanner.scan_project(project_path)
        results.append(analysis)
    else:
        # Scan all projects
        output.header("Security Scan")
        for analysis in scanner.scan_directory(base_dir):
            results.append(analysis)

    # Process results
    for analysis in results:
        if analysis.is_clean:
            output.ok(f"{analysis.name}: Clean")
        else:
            issues_found += 1
            output.warn(f"{analysis.name}: Issues found")

            for cred in analysis.credentials:
                output.list_item(
                    f"[ERR] Credential ({cred.credential_type}) in {cred.file_path.name}:{cred.line_number}"
                )

            for sf in analysis.sensitive_files:
                output.list_item(f"[WARN] Sensitive file: {sf.path.name}")

            for issue in analysis.issues:
                output.list_item(f"[ERR] {issue}")

            for warning in analysis.warnings:
                output.list_item(f"[WARN] {warning}")

            # Auto-fix if requested
            if auto_fix and not config.dry_run:
                if not analysis.has_gitignore:
                    output.info("  Creating .gitignore...")
                    scanner.generate_gitignore(analysis.path)

                if analysis.has_env_file and not analysis.has_env_example:
                    output.info("  Creating .env.example...")
                    scanner.create_env_example(analysis.path)

    # Summary
    output.header("Summary")
    output.plain(f"  Projects scanned: {len(results)}")
    output.plain(f"  Clean: {len(results) - issues_found}")
    output.plain(f"  With issues: {issues_found}")

    # Output based on format
    if config.output_format == "json":
        output.json_output([r.to_dict() for r in results])

    # Save report if output dir specified
    if config.output_dir:
        report_path = Path(config.output_dir) / "scan_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in results], f, indent=2, default=str)
        output.info(f"Report saved to: {report_path}")

    return 1 if issues_found > 0 else 0
