"""Command-line interface for project-reviewer."""

import argparse
import sys
from pathlib import Path

from .config.loader import ConfigLoader
from .utils.output import Output


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="project-reviewer",
        description="CLI tool for reviewing, classifying, and preparing projects for publication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  project-reviewer scan -d /path/to/projects
  project-reviewer classify --with-scan
  project-reviewer questionnaire
  project-reviewer plan --all
  project-reviewer verify --pre-publish
  project-reviewer execute ./reports/action_plan.json
  project-reviewer clean-ascii ./my-project --preview
""",
    )

    # Global options
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Configuration file path (default: ./config.json)",
    )
    parser.add_argument(
        "-d",
        "--base-dir",
        type=Path,
        help="Base directory containing projects",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Output directory for reports",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without making them",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan command
    scan_parser = subparsers.add_parser(
        "scan",
        help="Security scanning, credentials detection",
    )
    scan_parser.add_argument(
        "target",
        nargs="?",
        type=Path,
        help="Specific project to scan (default: all)",
    )
    scan_parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="Automatically create .gitignore and .env.example",
    )

    # classify command
    classify_parser = subparsers.add_parser(
        "classify",
        help="Classify projects (SAFE/CLEANUP/REVIEW/NO_PUBLISH)",
    )
    classify_parser.add_argument(
        "target",
        nargs="?",
        type=Path,
        help="Specific project to classify (default: all)",
    )
    classify_parser.add_argument(
        "--with-scan",
        action="store_true",
        help="Also run security scan",
    )

    # questionnaire command
    questionnaire_parser = subparsers.add_parser(
        "questionnaire",
        help="Interactive project questionnaire",
    )
    questionnaire_parser.add_argument(
        "target",
        nargs="?",
        type=Path,
        help="Specific project (default: all)",
    )
    questionnaire_parser.add_argument(
        "--responses-file",
        type=Path,
        help="File to save/load responses",
    )
    questionnaire_parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Start fresh, don't skip answered projects",
    )

    # plan command
    plan_parser = subparsers.add_parser(
        "plan",
        help="Generate action plan",
    )
    plan_parser.add_argument(
        "target",
        nargs="?",
        type=Path,
        help="Specific project (default: based on mappings)",
    )
    plan_parser.add_argument(
        "--all",
        action="store_true",
        dest="all_projects",
        help="Include all projects, not just mapped ones",
    )
    plan_parser.add_argument(
        "--output-file",
        type=Path,
        help="Where to save the plan",
    )

    # verify command
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify coherence and pre-publish readiness",
    )
    verify_parser.add_argument(
        "target",
        nargs="?",
        type=Path,
        help="Specific project (default: all)",
    )
    verify_parser.add_argument(
        "--pre-publish",
        action="store_true",
        help="Use strict pre-publication checks",
    )

    # execute command
    execute_parser = subparsers.add_parser(
        "execute",
        help="Execute planned actions",
    )
    execute_parser.add_argument(
        "plan_file",
        type=Path,
        help="Path to action plan JSON file",
    )
    execute_parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop execution on first error",
    )

    # clean-ascii command
    clean_ascii_parser = subparsers.add_parser(
        "clean-ascii",
        help="Remove non-ASCII characters",
    )
    clean_ascii_parser.add_argument(
        "target",
        type=Path,
        help="File or directory to clean",
    )
    clean_ascii_parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview without making changes",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    # Load configuration
    loader = ConfigLoader()
    cli_overrides = {
        "verbose": args.verbose,
        "dry_run": args.dry_run,
        "output_format": args.format,
    }
    if args.base_dir:
        cli_overrides["base_dir"] = args.base_dir
    if args.output_dir:
        cli_overrides["output_dir"] = args.output_dir

    config = loader.load(args.config, cli_overrides)

    # Create output handler
    output = Output(verbose=config.verbose, format=config.output_format)

    # Run command
    try:
        if args.command == "scan":
            from .commands.scan import run_scan

            return run_scan(
                config,
                output,
                target=args.target,
                auto_fix=args.auto_fix,
            )

        elif args.command == "classify":
            from .commands.classify import run_classify

            return run_classify(
                config,
                output,
                target=args.target,
                with_scan=args.with_scan,
            )

        elif args.command == "questionnaire":
            from .commands.questionnaire import run_questionnaire

            return run_questionnaire(
                config,
                output,
                target=args.target,
                responses_file=args.responses_file,
                resume=not args.no_resume,
            )

        elif args.command == "plan":
            from .commands.plan import run_plan

            return run_plan(
                config,
                output,
                target=args.target,
                all_projects=args.all_projects,
                output_file=args.output_file,
            )

        elif args.command == "verify":
            from .commands.verify import run_verify

            return run_verify(
                config,
                output,
                target=args.target,
                pre_publish=args.pre_publish,
            )

        elif args.command == "execute":
            from .commands.execute import run_execute

            return run_execute(
                config,
                output,
                plan_file=args.plan_file,
                stop_on_error=args.stop_on_error,
            )

        elif args.command == "clean-ascii":
            from .commands.clean_ascii import run_clean_ascii

            return run_clean_ascii(
                config,
                output,
                target=args.target,
                preview=args.preview,
            )

        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        output.plain("\n")
        output.info("Interrupted by user")
        return 130
    except Exception as e:
        output.err(f"Error: {e}")
        if config.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
