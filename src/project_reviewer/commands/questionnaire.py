"""Questionnaire command implementation."""

from pathlib import Path

from ..config.schema import Config
from ..core.classifier import Classifier
from ..core.questionnaire import Questionnaire
from ..utils.output import Output


def run_questionnaire(
    config: Config,
    output: Output,
    target: Path | None = None,
    responses_file: Path | None = None,
    resume: bool = True,
) -> int:
    """Run interactive project questionnaire.

    Args:
        config: Configuration object
        output: Output handler
        target: Specific project (or None for all)
        responses_file: File to save responses
        resume: Resume from existing responses

    Returns:
        Exit code (0 = success)
    """
    questionnaire = Questionnaire(config, output)
    base_dir = config.base_dir

    # Set up responses file
    if responses_file:
        questionnaire.load_responses(responses_file)
    else:
        default_responses = Path(config.output_dir) / "questionnaire_responses.json"
        default_responses.parent.mkdir(parents=True, exist_ok=True)
        questionnaire.load_responses(default_responses)

    # Get classifications for context
    classifier = Classifier(config, output)
    classifications = {}
    for result in classifier.classify_directory(base_dir):
        classifications[result.name] = result

    # Build project list
    projects = []
    if target:
        project_path = target if target.is_absolute() else base_dir / target
        if not project_path.exists():
            output.err(f"Project not found: {project_path}")
            return 1
        projects.append(project_path)
    else:
        for entry in sorted(base_dir.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                if entry.name not in config.exclude_dirs:
                    projects.append(entry)

    output.header("Project Questionnaire")
    output.info(f"Found {len(projects)} projects")

    if resume and questionnaire.responses:
        output.info(f"Resuming with {len(questionnaire.responses)} existing responses")

    try:
        questionnaire.run_batch(
            projects,
            classifications,
            skip_answered=resume,
        )
    except KeyboardInterrupt:
        output.plain("\n")
        output.info("Questionnaire interrupted. Progress saved.")

    # Show summary
    summary = questionnaire.generate_summary()

    output.header("Summary by Decision")
    output.ok(f"Publish: {len(summary['publish'])}")
    output.warn(f"Cleanup then publish: {len(summary['cleanup_then_publish'])}")
    output.info(f"Keep local: {len(summary['keep_local'])}")
    output.err(f"Delete: {len(summary['delete'])}")
    output.plain(f"  Decide later: {len(summary['decide_later'])}")

    # Output based on format
    if config.output_format == "json":
        output.json_output(questionnaire.responses)

    return 0
