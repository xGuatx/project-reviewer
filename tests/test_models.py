"""Tests for data models."""

from pathlib import Path

from project_reviewer.models.project import ProjectAnalysis, CredentialFinding
from project_reviewer.models.classification import ClassificationResult, ProjectStatus
from project_reviewer.models.action import Action, ActionPlan, ActionType


def test_project_analysis_creation():
    """Test ProjectAnalysis dataclass creation."""
    analysis = ProjectAnalysis(
        path=Path("/test/project"),
        name="test-project",
    )
    assert analysis.name == "test-project"
    assert analysis.is_clean is True
    assert analysis.has_credentials is False


def test_project_analysis_with_credentials():
    """Test ProjectAnalysis with credentials."""
    analysis = ProjectAnalysis(
        path=Path("/test/project"),
        name="test-project",
        credentials=[
            CredentialFinding(
                file_path=Path("/test/project/config.py"),
                line_number=10,
                credential_type="api_key",
                matched_text="[REDACTED]",
            )
        ],
    )
    assert analysis.has_credentials is True
    assert analysis.is_clean is False


def test_project_analysis_to_dict():
    """Test ProjectAnalysis serialization."""
    analysis = ProjectAnalysis(
        path=Path("/test/project"),
        name="test-project",
        has_git=True,
        has_readme=True,
    )
    data = analysis.to_dict()
    assert data["name"] == "test-project"
    assert data["has_git"] is True
    assert data["has_readme"] is True
    assert data["is_clean"] is True


def test_classification_result_creation():
    """Test ClassificationResult creation."""
    result = ClassificationResult(
        path=Path("/test/project"),
        name="test-project",
        status=ProjectStatus.SAFE_TO_PUBLISH,
    )
    assert result.status == ProjectStatus.SAFE_TO_PUBLISH
    assert "[OK]" in result.status_label


def test_classification_result_needs_cleanup():
    """Test ClassificationResult with NEEDS_CLEANUP status."""
    result = ClassificationResult(
        path=Path("/test/project"),
        name="test-project",
        status=ProjectStatus.NEEDS_CLEANUP,
        reasons=["Contains backup folders"],
    )
    assert result.status == ProjectStatus.NEEDS_CLEANUP
    assert "[WARN]" in result.status_label


def test_action_creation():
    """Test Action creation."""
    action = Action(
        action_type=ActionType.RENAME,
        project_path=Path("/test/project"),
        description="Rename project",
        target="new-name",
        source="old-name",
    )
    assert action.action_type == ActionType.RENAME
    assert action.completed is False


def test_action_plan_creation():
    """Test ActionPlan creation and manipulation."""
    plan = ActionPlan(
        name="Test Plan",
        description="A test plan",
    )
    assert len(plan.actions) == 0

    action = Action(
        action_type=ActionType.DELETE,
        project_path=Path("/test"),
        description="Delete file",
    )
    plan.add_action(action)
    assert len(plan.actions) == 1


def test_action_plan_to_markdown():
    """Test ActionPlan markdown generation."""
    plan = ActionPlan(
        name="Test Plan",
        description="A test plan",
    )
    plan.add_action(
        Action(
            action_type=ActionType.RENAME,
            project_path=Path("/test"),
            description="Rename project",
        )
    )
    markdown = plan.to_markdown()
    assert "# Test Plan" in markdown
    assert "Rename" in markdown
