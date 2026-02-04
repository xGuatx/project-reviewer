# Project Reviewer

A CLI tool for reviewing, classifying, and preparing projects for publication on GitHub.

## Features

- **Security Scanning**: Detect credentials, API keys, and sensitive files
- **Project Classification**: Automatically classify projects as safe, needs cleanup, needs review, or do not publish
- **Interactive Questionnaire**: Make decisions about each project interactively
- **Action Planning**: Generate comprehensive action plans for project reorganization
- **Verification**: Verify project coherence and publication readiness
- **ASCII Cleanup**: Remove non-ASCII characters for cross-platform compatibility

## Installation

### From Source

```bash
git clone https://github.com/xGuatx/project-reviewer.git
cd project-reviewer
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### Requirements

- Python 3.10+
- pydantic >= 2.0

## Quick Start

```bash
# Scan projects for security issues
project-reviewer -d /path/to/projects scan

# Classify all projects
project-reviewer -d /path/to/projects classify --with-scan

# Generate an action plan
project-reviewer -d /path/to/projects plan --all

# Verify before publication
project-reviewer -d /path/to/projects verify --pre-publish
```

## Commands

### `scan` - Security Scanning

Detect credentials, API keys, and sensitive files in projects.

```bash
# Scan all projects in a directory
project-reviewer -d /path/to/projects scan

# Scan a specific project
project-reviewer scan /path/to/project

# Auto-fix: create .gitignore and .env.example
project-reviewer -d /path/to/projects scan --auto-fix

# Preview changes without modifying files
project-reviewer -d /path/to/projects --dry-run scan
```

**Detected patterns include:**
- GitHub tokens (`ghp_...`)
- OpenAI API keys (`sk-proj-...`)
- Anthropic API keys (`sk-ant-...`)
- JWT tokens
- Generic API keys and passwords

### `classify` - Project Classification

Classify projects based on their publication readiness.

```bash
# Classify all projects
project-reviewer -d /path/to/projects classify

# Include security scan in classification
project-reviewer -d /path/to/projects classify --with-scan
```

**Classification levels:**
- `[OK] Safe to publish` - Ready for publication
- `[WARN] Needs cleanup` - Requires cleanup before publication
- `[INFO] Needs review` - Manual review recommended
- `[ERR] Do not publish` - Should not be published (backups, clones, sensitive data)

### `questionnaire` - Interactive Questionnaire

Make decisions about each project interactively.

```bash
# Run questionnaire for all projects
project-reviewer -d /path/to/projects questionnaire

# Start fresh (don't skip previously answered)
project-reviewer -d /path/to/projects questionnaire --no-resume

# Use custom responses file
project-reviewer questionnaire --responses-file ./my-responses.json
```

### `plan` - Action Plan Generation

Generate a comprehensive action plan for project reorganization.

```bash
# Generate plan based on configuration mappings
project-reviewer -d /path/to/projects plan

# Include all projects
project-reviewer -d /path/to/projects plan --all

# Save to custom location
project-reviewer plan --output-file ./my-plan
```

### `verify` - Verification

Verify project coherence and publication readiness.

```bash
# Basic coherence verification
project-reviewer -d /path/to/projects verify

# Strict pre-publication checks
project-reviewer -d /path/to/projects verify --pre-publish
```

### `execute` - Execute Action Plan

Execute actions from a generated plan.

```bash
# Preview execution (dry run)
project-reviewer --dry-run execute ./reports/action_plan.json

# Execute the plan
project-reviewer execute ./reports/action_plan.json

# Stop on first error
project-reviewer execute ./reports/action_plan.json --stop-on-error
```

### `clean-ascii` - ASCII Cleanup

Remove non-ASCII characters from files for cross-platform compatibility.

```bash
# Preview non-ASCII characters in a file
project-reviewer clean-ascii /path/to/file.py --preview

# Clean a directory
project-reviewer clean-ascii /path/to/project

# Dry run
project-reviewer --dry-run clean-ascii /path/to/project
```

## Global Options

| Option | Description |
|--------|-------------|
| `-c, --config PATH` | Configuration file path |
| `-d, --base-dir PATH` | Base directory containing projects |
| `-o, --output-dir PATH` | Output directory for reports |
| `-f, --format FORMAT` | Output format: `text`, `json`, `markdown` |
| `-v, --verbose` | Enable verbose output |
| `--dry-run` | Preview changes without making them |
| `--version` | Show version number |

## Configuration

### config.json

Create a `config.json` file to customize behavior:

```json
{
  "base_dir": "/path/to/projects",
  "output_dir": "./reports",
  "mappings_file": "./project_mappings.json",
  "exclude_dirs": ["node_modules", "venv", ".git"],
  "security": {
    "credential_patterns": {
      "github_token": "ghp_[a-zA-Z0-9]{36}",
      "custom_api_key": "my-prefix-[a-zA-Z0-9]{32}"
    }
  },
  "cleanup": {
    "ai_cache_directories": [".claude", ".codex", ".cursor"],
    "files_to_remove": ["agent.md"]
  }
}
```

### project_mappings.json

Define project transformations:

```json
{
  "renamings": {
    "old-project-name": "new-descriptive-name"
  },
  "splits": {
    "monorepo": {
      "extracted-service": {
        "files": ["services/auth/*"],
        "description": "Authentication service"
      }
    }
  },
  "merges": {
    "combined-project": ["project-a", "project-b"]
  },
  "do_not_publish": ["private-project", "backup-data"]
}
```

## Workflow Example

```bash
# 1. Initial security scan
project-reviewer -d ~/projects -o ./reports scan

# 2. Classify projects
project-reviewer -d ~/projects classify --with-scan

# 3. Interactive decisions
project-reviewer -d ~/projects questionnaire

# 4. Generate action plan
project-reviewer -d ~/projects plan --all

# 5. Preview plan execution
project-reviewer --dry-run execute ./reports/action_plan.json

# 6. Execute plan
project-reviewer execute ./reports/action_plan.json

# 7. Final verification
project-reviewer -d ~/projects verify --pre-publish
```

## Output Format

The tool uses consistent prefixes for messages:

| Prefix | Meaning |
|--------|---------|
| `[OK]` | Success |
| `[WARN]` | Warning |
| `[ERR]` | Error |
| `[INFO]` | Information |
| `[DEBUG]` | Debug (verbose mode) |

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
