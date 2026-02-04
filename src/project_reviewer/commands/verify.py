"""Verify command implementation."""

import json
from pathlib import Path

from ..config.schema import Config
from ..core.scanner import Scanner
from ..core.verifier import Verifier
from ..utils.output import Output


def run_verify(
    config: Config,
    output: Output,
    target: Path | None = None,
    pre_publish: bool = False,
) -> int:
    """Run project verification.

    Args:
        config: Configuration object
        output: Output handler
        target: Specific project (or None for all)
        pre_publish: Use strict pre-publication checks

    Returns:
        Exit code (0 = all passed, 1 = failures)
    """
    verifier = Verifier(config, output)
    base_dir = config.base_dir

    # Run security scan for context
    scanner = Scanner(config, output)
    analyses = {}

    output.info("Running security scan...")
    for analysis in scanner.scan_directory(base_dir):
        analyses[analysis.name] = analysis

    if target:
        # Verify single project
        project_path = target if target.is_absolute() else base_dir / target
        if not project_path.exists():
            output.err(f"Project not found: {project_path}")
            return 1

        output.header(f"Verifying: {project_path.name}")
        analysis = analyses.get(project_path.name)

        if pre_publish:
            result = verifier.verify_pre_publish(project_path, analysis)
        else:
            result = verifier.verify_project(project_path, analysis)

        results = {project_path.name: result}
    else:
        # Verify all projects
        mode = "Pre-Publication" if pre_publish else "Coherence"
        output.header(f"{mode} Verification")

        if pre_publish:
            results = verifier.verify_all_pre_publish(base_dir, analyses)
        else:
            results = verifier.verify_coherence(base_dir, analyses)

    # Display results
    passed = 0
    failed = 0

    for name, result in results.items():
        if result.passed:
            passed += 1
            if result.warnings:
                output.warn(f"{name}: Passed with warnings")
                for warning in result.warnings:
                    output.list_item(warning, indent=1)
            else:
                output.ok(f"{name}: Passed")
        else:
            failed += 1
            output.err(f"{name}: Failed")
            for error in result.errors:
                output.list_item(f"[ERR] {error}", indent=1)
            for warning in result.warnings:
                output.list_item(f"[WARN] {warning}", indent=1)

    # Summary
    output.header("Verification Summary")
    output.ok(f"Passed: {passed}")
    if failed:
        output.err(f"Failed: {failed}")

    # Generate report
    report = verifier.generate_report(results)

    if config.output_format == "markdown":
        output.markdown_output(report)

    # Save report
    if config.output_dir:
        suffix = "_pre_publish" if pre_publish else ""
        report_path = Path(config.output_dir) / f"verification_report{suffix}.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        output.info(f"Report saved to: {report_path}")

        # Also save JSON
        json_path = report_path.with_suffix(".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {name: r.to_dict() for name, r in results.items()},
                f,
                indent=2,
                default=str,
            )

    return 1 if failed > 0 else 0
