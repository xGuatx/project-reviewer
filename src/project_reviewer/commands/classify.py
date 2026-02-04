"""Classify command implementation."""

import json
from pathlib import Path

from ..config.schema import Config
from ..core.classifier import Classifier
from ..core.scanner import Scanner
from ..models.classification import ProjectStatus
from ..utils.output import Output


def run_classify(
    config: Config,
    output: Output,
    target: Path | None = None,
    with_scan: bool = False,
) -> int:
    """Run project classification.

    Args:
        config: Configuration object
        output: Output handler
        target: Specific project to classify (or None for all)
        with_scan: Also run security scan

    Returns:
        Exit code (0 = success)
    """
    classifier = Classifier(config, output)
    base_dir = config.base_dir

    # Optionally run scan first
    analyses = {}
    if with_scan:
        scanner = Scanner(config, output)
        output.info("Running security scan first...")
        for analysis in scanner.scan_directory(base_dir):
            analyses[analysis.name] = analysis

    results = []
    stats = {
        "safe": 0,
        "cleanup": 0,
        "review": 0,
        "do_not_publish": 0,
        "unknown": 0,
    }

    if target:
        # Classify single project
        project_path = target if target.is_absolute() else base_dir / target
        if not project_path.exists():
            output.err(f"Project not found: {project_path}")
            return 1

        output.header(f"Classifying: {project_path.name}")
        analysis = analyses.get(project_path.name)
        result = classifier.classify_project(project_path, analysis)
        results.append(result)
    else:
        # Classify all projects
        output.header("Project Classification")
        for result in classifier.classify_directory(base_dir, analyses):
            results.append(result)

    # Process and display results
    for result in results:
        # Update stats
        if result.status == ProjectStatus.SAFE_TO_PUBLISH:
            stats["safe"] += 1
        elif result.status == ProjectStatus.NEEDS_CLEANUP:
            stats["cleanup"] += 1
        elif result.status == ProjectStatus.NEEDS_REVIEW:
            stats["review"] += 1
        elif result.status == ProjectStatus.DO_NOT_PUBLISH:
            stats["do_not_publish"] += 1
        else:
            stats["unknown"] += 1

        # Display result
        output.plain("")
        output.plain(f"{result.status_label} {result.name}")

        if result.reasons:
            for reason in result.reasons:
                output.list_item(reason, indent=1)

        if result.recommended_actions:
            output.plain("  Recommended:")
            for action in result.recommended_actions:
                output.list_item(action, indent=2)

    # Summary
    output.header("Classification Summary")
    output.ok(f"Safe to publish: {stats['safe']}")
    output.warn(f"Needs cleanup: {stats['cleanup']}")
    output.info(f"Needs review: {stats['review']}")
    output.err(f"Do not publish: {stats['do_not_publish']}")
    if stats["unknown"]:
        output.plain(f"  Unknown: {stats['unknown']}")

    # Output based on format
    if config.output_format == "json":
        output.json_output([r.to_dict() for r in results])

    # Save report
    if config.output_dir:
        report_path = Path(config.output_dir) / "classification_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "summary": stats,
                    "projects": [r.to_dict() for r in results],
                },
                f,
                indent=2,
                default=str,
            )
        output.info(f"Report saved to: {report_path}")

    return 0
