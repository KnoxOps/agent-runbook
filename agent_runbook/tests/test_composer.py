"""Tests for the Composer module that assembles SKILL.md files."""

import pytest

from agent_runbook.composer import Composer, Section
from agent_runbook.schema import ErrorHandlingRule, InputParam, Runbook, Step, StepType


@pytest.fixture
def basic_runbook():
    """Create a basic runbook for testing."""
    return Runbook(
        name="test-runbook",
        description="Test description",
        steps=[],
    )


@pytest.fixture
def runbook_with_params():
    """Create a runbook with input parameters."""
    return Runbook(
        name="test-runbook",
        description="Test description",
        input_params=[
            InputParam(
                name="run_dir",
                type="string",
                required=True,
                description="Workspace root",
            ),
            InputParam(
                name="timeout",
                type="number",
                required=False,
                description="Execution timeout in seconds",
            ),
        ],
        steps=[],
    )


@pytest.fixture
def runbook_with_error_handling():
    """Create a runbook with error handling rules."""
    return Runbook(
        name="test-runbook",
        description="Test description",
        error_handling=[
            ErrorHandlingRule(scenario="Network timeout", handling="Retry with exponential backoff"),
            ErrorHandlingRule(scenario="Invalid input", handling="Return error to user"),
        ],
        steps=[],
    )


def test_compose_includes_frontmatter(basic_runbook):
    """Test that compose includes YAML frontmatter with name and description."""
    composer = Composer()
    output = composer.compose(basic_runbook, sections=[])

    assert output.startswith("---\n")
    assert "name: test-runbook\n" in output
    assert "description: Test description\n" in output
    assert output.count("---") >= 2  # Opening and closing frontmatter markers


def test_compose_includes_execution_flow():
    """Test that compose includes execution flow section with steps in order."""
    runbook = Runbook(name="test-runbook", description="Test", steps=[])

    sections = [
        Section(step_id="step1", order=1, content="Step 1 content"),
        Section(step_id="step2", order=2, content="Step 2 content"),
        Section(step_id="step3", order=3, content="Step 3 content"),
    ]

    composer = Composer()
    output = composer.compose(runbook, sections=sections)

    # Check for execution flow heading
    assert "## Execution Flow" in output

    # Check that all step contents appear
    assert "Step 1 content" in output
    assert "Step 2 content" in output
    assert "Step 3 content" in output

    # Check order (simple text position check)
    pos1 = output.find("Step 1 content")
    pos2 = output.find("Step 2 content")
    pos3 = output.find("Step 3 content")
    assert pos1 < pos2 < pos3, "Steps should appear in order"


def test_compose_includes_branch_sections():
    """Test that compose includes branch decision sections with step IDs."""
    runbook = Runbook(name="test-runbook", description="Test", steps=[])

    sections = [
        Section(step_id="decision", order=1, content="Branch decision here", is_branch_point=True),
        Section(step_id="branch_a", order=2, content="Branch A content"),
    ]

    composer = Composer()
    output = composer.compose(runbook, sections=sections)

    # Check for branch point indication with step ID
    assert "### Branch Decision: decision" in output
    assert "Branch decision here" in output


def test_compose_includes_error_handling(runbook_with_error_handling):
    """Test that compose includes error handling section."""
    composer = Composer()
    output = composer.compose(runbook_with_error_handling, sections=[])

    assert "## Error Handling" in output
    assert "Network timeout" in output
    assert "Retry with exponential backoff" in output
    assert "Invalid input" in output
    assert "Return error to user" in output


def test_compose_includes_input_params(runbook_with_params):
    """Test that compose includes input parameters table."""
    composer = Composer()
    output = composer.compose(runbook_with_params, sections=[])

    assert "## Input Parameters" in output
    assert "run_dir" in output
    assert "string" in output
    assert "Workspace root" in output
    assert "timeout" in output
    assert "number" in output
    assert "Execution timeout in seconds" in output


def test_compose_section_order():
    """Test that sections appear in correct order: frontmatter → params → flow → error handling."""
    runbook = Runbook(
        name="test-runbook",
        description="Test description",
        input_params=[InputParam(name="param1", type="string", required=True, description="Test param")],
        error_handling=[ErrorHandlingRule(scenario="Error", handling="Handle it")],
        steps=[],
    )

    sections = [
        Section(step_id="step1", order=1, content="Step content"),
    ]

    composer = Composer()
    output = composer.compose(runbook, sections=sections)

    # Find positions of key sections
    frontmatter_start = output.find("---")
    frontmatter_end = output.find("---", frontmatter_start + 3)
    params_pos = output.find("## Input Parameters")
    flow_pos = output.find("## Execution Flow")
    error_pos = output.find("## Error Handling")

    # Verify order
    assert frontmatter_start >= 0, "Frontmatter should be present"
    assert frontmatter_end > frontmatter_start, "Closing frontmatter should exist"

    if params_pos >= 0 and flow_pos >= 0:
        assert flow_pos > params_pos, "Execution Flow should come after Input Parameters"
    if error_pos >= 0 and flow_pos >= 0:
        assert error_pos > flow_pos, "Error Handling should come after Execution Flow"


def test_compose_escapes_pipe_in_param_descriptions():
    """Test that pipe characters in parameter descriptions are escaped for markdown tables."""
    runbook = Runbook(
        name="test-runbook",
        description="Test description",
        input_params=[
            InputParam(
                name="config|value",
                type="string|map",
                required=True,
                description="Configuration with | separator | example",
            ),
        ],
        steps=[],
    )

    composer = Composer()
    output = composer.compose(runbook, sections=[])

    assert "## Input Parameters" in output
    # Check that pipes are escaped with backslash
    assert r"config\|value" in output
    assert r"string\|map" in output
    assert r"Configuration with \| separator \| example" in output

    # Verify table structure is intact (unescaped pipes should only be in header separators)
    lines = output.split("\n")
    table_lines = [l for l in lines if l.startswith("|")]
    assert len(table_lines) >= 3  # Header, separator, data row


def test_compose_with_empty_sections_but_params_and_error_handling():
    """Test compose with empty sections list but with input params and error handling."""
    runbook = Runbook(
        name="test-runbook",
        description="Test description",
        input_params=[
            InputParam(name="param1", type="string", required=True, description="Test param"),
        ],
        error_handling=[
            ErrorHandlingRule(scenario="Timeout", handling="Retry operation"),
        ],
        steps=[],
    )

    composer = Composer()
    output = composer.compose(runbook, sections=[])

    # Should include all sections except execution flow
    assert "## Input Parameters" in output
    assert "param1" in output
    assert "## Error Handling" in output
    assert "Timeout" in output

    # Should NOT include execution flow section
    assert "## Execution Flow" not in output


def test_compose_step_headers_use_i18n_english():
    """Test that step headers use i18n and render in English by default."""
    runbook = Runbook(name="test-runbook", description="Test", steps=[])

    sections = [
        Section(step_id="step1", order=1, content="Step 1 content"),
        Section(step_id="step2", order=2, content="Step 2 content"),
    ]

    composer = Composer()
    output = composer.compose(runbook, sections=sections, lang="en")

    # Check for English step headers
    assert "### Step 1: step1" in output
    assert "### Step 2: step2" in output


def test_compose_step_headers_use_i18n_chinese():
    """Test that step headers use i18n and render in Chinese when lang='zh'."""
    runbook = Runbook(name="test-runbook", description="Test", steps=[])

    sections = [
        Section(step_id="step1", order=1, content="Step 1 content"),
        Section(step_id="step2", order=2, content="Step 2 content"),
    ]

    composer = Composer()
    output = composer.compose(runbook, sections=sections, lang="zh")

    # Check for Chinese step headers
    assert "### 步骤 1: step1" in output
    assert "### 步骤 2: step2" in output


def test_compose_branch_decision_headers_use_i18n_english():
    """Test that branch decision headers use i18n and render in English by default."""
    runbook = Runbook(name="test-runbook", description="Test", steps=[])

    sections = [
        Section(step_id="decision", order=1, content="Branch decision here", is_branch_point=True),
        Section(step_id="branch_a", order=2, content="Branch A content"),
    ]

    composer = Composer()
    output = composer.compose(runbook, sections=sections, lang="en")

    # Check for English branch decision header
    assert "### Branch Decision: decision" in output


def test_compose_branch_decision_headers_use_i18n_chinese():
    """Test that branch decision headers use i18n and render in Chinese when lang='zh'."""
    runbook = Runbook(name="test-runbook", description="Test", steps=[])

    sections = [
        Section(step_id="decision", order=1, content="Branch decision here", is_branch_point=True),
        Section(step_id="branch_a", order=2, content="Branch A content"),
    ]

    composer = Composer()
    output = composer.compose(runbook, sections=sections, lang="zh")

    # Check for Chinese branch decision header
    assert "### 分支决策: decision" in output

