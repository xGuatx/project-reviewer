"""Execute command implementation."""

from pathlib import Path

from ..config.schema import Config
from ..core.executor import Executor
from ..utils.output import Output


def run_execute(
    config: Config,
    output: Output,
    plan_file: Path,
    stop_on_error: bool = False,
) -> int:
    """Execute an action plan.

    Args:
        config: Configuration object
        output: Output handler
        plan_file: Path to the action plan JSON file
        stop_on_error: Stop execution on first error

    Returns:
        Exit code (0 = all success, 1 = failures)
    """
    executor = Executor(config, output)

    # Load plan
    plan = executor.load_plan(plan_file)
    if not plan:
        output.err(f"Could not load plan from: {plan_file}")
        return 1

    output.header(f"Executing Plan: {plan.name}")
    output.info(f"Total actions: {len(plan.actions)}")

    if config.dry_run:
        output.warn("DRY RUN MODE - No changes will be made")

    # Confirm execution
    if not config.dry_run:
        output.plain("")
        output.warn("This will make changes to your projects.")
        try:
            response = input("Continue? [y/N] ").strip().lower()
            if response not in ("y", "yes"):
                output.info("Execution cancelled.")
                return 0
        except (EOFError, KeyboardInterrupt):
            output.plain("")
            output.info("Execution cancelled.")
            return 0

    # Execute
    success, failed = executor.execute_plan(
        plan,
        dry_run=config.dry_run,
        stop_on_error=stop_on_error,
    )

    # Save updated plan with completion status
    if not config.dry_run:
        updated_path = plan_file.with_stem(plan_file.stem + "_executed")
        import json
        with open(updated_path, "w", encoding="utf-8") as f:
            json.dump(plan.to_dict(), f, indent=2, default=str)
        output.info(f"Updated plan saved to: {updated_path}")

    return 1 if failed > 0 else 0
