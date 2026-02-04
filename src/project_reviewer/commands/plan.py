"""Plan command implementation."""

from pathlib import Path

from ..config.schema import Config
from ..core.classifier import Classifier
from ..core.planner import Planner
from ..core.scanner import Scanner
from ..utils.output import Output


def run_plan(
    config: Config,
    output: Output,
    target: Path | None = None,
    all_projects: bool = False,
    output_file: Path | None = None,
) -> int:
    """Generate action plan for projects.

    Args:
        config: Configuration object
        output: Output handler
        target: Specific project (or None for all with mappings)
        all_projects: Include all projects, not just mapped ones
        output_file: Where to save the plan

    Returns:
        Exit code (0 = success)
    """
    planner = Planner(config, output)
    base_dir = config.base_dir

    output.header("Action Plan Generation")

    # Run analysis
    scanner = Scanner(config, output)
    classifier = Classifier(config, output)

    analyses = {}
    classifications = {}

    output.info("Analyzing projects...")
    for analysis in scanner.scan_directory(base_dir):
        analyses[analysis.name] = analysis

    for result in classifier.classify_directory(base_dir, analyses):
        classifications[result.name] = result

    # Generate plan
    if target:
        # Single project plan
        project_path = target if target.is_absolute() else base_dir / target
        if not project_path.exists():
            output.err(f"Project not found: {project_path}")
            return 1

        plan = planner.create_plan(
            name=f"Plan for {project_path.name}",
            description=f"Actions for project: {project_path.name}",
        )

        classification = classifications.get(project_path.name)
        analysis = analyses.get(project_path.name)

        if classification:
            for action in planner.plan_from_classification(classification, analysis):
                plan.add_action(action)
    else:
        # Full plan
        if all_projects:
            plan = planner.generate_full_plan(base_dir, classifications, analyses)
        else:
            # Only projects with mappings
            plan = planner.create_plan(
                name="Project Reorganization Plan",
                description="Actions based on configuration mappings",
            )

            # Add configured actions
            for action in planner.plan_splits():
                plan.add_action(action)

            for action in planner.plan_merges():
                plan.add_action(action)

            for action in planner.plan_renames():
                plan.add_action(action)

            # Add global cleanup
            for action in planner.plan_global_cleanup(base_dir):
                plan.add_action(action)

    # Display plan
    output.header("Generated Plan")
    output.plain(f"Name: {plan.name}")
    output.plain(f"Total actions: {len(plan.actions)}")

    # Group by type
    by_type: dict[str, int] = {}
    for action in plan.actions:
        type_name = action.action_type.value
        by_type[type_name] = by_type.get(type_name, 0) + 1

    output.subheader("Actions by Type")
    for type_name, count in sorted(by_type.items()):
        output.plain(f"  {type_name}: {count}")

    # Show preview
    if config.verbose:
        output.subheader("Action Preview")
        for i, action in enumerate(plan.actions[:20], 1):
            output.plain(f"  {i}. [{action.action_type.value}] {action.description}")
        if len(plan.actions) > 20:
            output.plain(f"  ... and {len(plan.actions) - 20} more")

    # Save plan
    if output_file:
        plan_path = output_file
    else:
        plan_path = Path(config.output_dir) / "action_plan"

    planner.save_plan(plan, plan_path)

    # Output based on format
    if config.output_format == "json":
        output.json_output(plan.to_dict())
    elif config.output_format == "markdown":
        output.markdown_output(plan.to_markdown())

    return 0
