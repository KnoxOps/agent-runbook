"""Tests for schema.py — Pydantic models for runbook YAML."""

import tempfile
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

# We import the module under test — these imports will FAIL until schema.py is created
# The actual import happens inside each test to allow progressive implementation


class TestParseMinimalRunbook:
    """Step 1: Parse a minimal runbook with only required fields."""

    def test_parse_minimal_runbook(self):
        """A runbook with just name, description, and empty steps should parse."""
        from agent_runbook.schema import Runbook

        data = {
            "name": "test",
            "description": "desc",
            "steps": [],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            result = Runbook.from_yaml(path)
            assert result.name == "test"
            assert result.description == "desc"
            assert result.steps == []
        finally:
            path.unlink(missing_ok=True)


class TestParseFullRunbook:
    """Step 2: Parse the full simple-3-step fixture."""

    @pytest.fixture
    def fixture_path(self):
        return Path(__file__).parent / "fixtures" / "simple-3-step" / "runbook.yaml"

    def test_parse_full_runbook(self, fixture_path):
        """All 3 steps should parse with correct fields."""
        from agent_runbook.schema import Runbook, StepType

        result = Runbook.from_yaml(fixture_path)
        assert len(result.steps) == 3

        step1, step2, step3 = result.steps

        # Step 1: scan — type=agent, prompt_file, output file
        assert step1.id == "scan"
        assert step1.type == StepType.AGENT
        assert step1.prompt_file == "prompts/cost-ranking.agent.md"
        assert step1.prompt is None
        assert step1.depends_on == []
        assert len(step1.output) == 1
        assert step1.output[0].file == "scan_result.json"

        # Step 2: classify — type=inline, inline prompt, depends_on=[scan]
        assert step2.id == "classify"
        assert step2.type == StepType.INLINE
        assert step2.prompt is not None
        assert "\n" in step2.prompt  # inline prompt has newlines
        assert step2.depends_on == ["scan"]
        assert len(step2.input) == 1
        assert step2.input[0].from_step == "scan"
        assert len(step2.output) == 1
        assert step2.output[0].file == "classification.json"

        # Step 3: recommend — type=agent, depends_on=[classify], parallel enabled
        assert step3.id == "recommend"
        assert step3.type == StepType.AGENT
        assert step3.prompt_file == "prompts/cost-advisor.agent.md"
        assert step3.depends_on == ["classify"]
        assert step3.parallel is not None
        assert step3.parallel.enabled is True
        assert step3.parallel.max_instances == 5
        assert step3.parallel.item_key == "resource_id"
        assert step3.checkpoint == "recommend_checkpoint.jsonl"


class TestMissingRequiredFields:
    """Step 3: Missing required fields should raise ValidationError."""

    def test_missing_name_raises(self):
        """YAML without 'name' should raise ValidationError."""
        from agent_runbook.schema import Runbook

        data = {
            "description": "desc",
            "steps": [],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            with pytest.raises(ValidationError):
                Runbook.from_yaml(path)
        finally:
            path.unlink(missing_ok=True)

    def test_missing_description_raises(self):
        """YAML without 'description' should raise ValidationError."""
        from agent_runbook.schema import Runbook

        data = {
            "name": "test",
            "steps": [],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            with pytest.raises(ValidationError):
                Runbook.from_yaml(path)
        finally:
            path.unlink(missing_ok=True)


class TestInvalidStepType:
    """Step 4: Invalid step type should raise error."""

    def test_invalid_step_type_raises(self):
        """step with type: unknown_type should raise ValidationError."""
        from agent_runbook.schema import Runbook

        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "s1",
                    "type": "unknown_type",
                    "description": "bad step",
                }
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            with pytest.raises(ValidationError):
                Runbook.from_yaml(path)
        finally:
            path.unlink(missing_ok=True)


class TestScriptStepWithoutCommand:
    """Step 5: script step without command should raise error."""

    def test_script_without_command_raises(self):
        """step with type: script, no command should raise ValidationError."""
        from agent_runbook.schema import Runbook

        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "s1",
                    "type": "script",
                    "description": "bad script step",
                }
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            with pytest.raises(Exception):
                Runbook.from_yaml(path)
        finally:
            path.unlink(missing_ok=True)


class TestPromptFileField:
    """Step 6: prompt_file field and prompt/prompt_file mutual exclusivity."""

    def test_prompt_file_parsed_correctly(self):
        """prompt_file should be parsed and prompt should be None when using file ref."""
        from agent_runbook.schema import Runbook

        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "s1",
                    "type": "agent",
                    "description": "scan",
                    "prompt_file": "prompts/my-prompt.agent.md",
                    "depends_on": [],
                }
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            result = Runbook.from_yaml(path)
            step = result.steps[0]
            assert step.prompt_file == "prompts/my-prompt.agent.md"
            assert step.prompt is None
        finally:
            path.unlink(missing_ok=True)

    def test_prompt_and_prompt_file_mutually_exclusive(self):
        """Setting both prompt and prompt_file should raise ValidationError."""
        from agent_runbook.schema import Runbook

        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "s1",
                    "type": "inline",
                    "description": "bad step",
                    "prompt": "inline text",
                    "prompt_file": "prompts/file.md",
                    "depends_on": [],
                }
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            with pytest.raises(ValidationError):
                Runbook.from_yaml(path)
        finally:
            path.unlink(missing_ok=True)

    def test_neither_prompt_nor_prompt_file_raises(self):
        """Neither prompt nor prompt_file set for inline/agent step should raise."""
        from agent_runbook.schema import Runbook

        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "s1",
                    "type": "inline",
                    "description": "bad step",
                    "depends_on": [],
                }
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            with pytest.raises(Exception):
                Runbook.from_yaml(path)
        finally:
            path.unlink(missing_ok=True)


class TestStepWithCondition:
    """Step 7: condition field parsing."""

    def test_step_with_condition_field(self):
        """step with condition field should parse correctly."""
        from agent_runbook.schema import Runbook

        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "s1",
                    "type": "inline",
                    "description": "detect cloud",
                    "prompt": "Check the environment",
                    "depends_on": [],
                },
                {
                    "id": "s2",
                    "type": "agent",
                    "description": "scan aws",
                    "prompt_file": "prompts/scan-aws.agent.md",
                    "condition": "provider is aws",
                    "depends_on": ["s1"],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            result = Runbook.from_yaml(path)
            assert result.steps[1].condition == "provider is aws"
        finally:
            path.unlink(missing_ok=True)


class TestErrorHandling:
    """Step 8: error_handling parsing."""

    def test_empty_yaml_file(self):
        """Parsing a completely empty YAML file should raise an error."""
        from agent_runbook.schema import Runbook

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")  # Write nothing to create an empty file
            path = Path(f.name)

        try:
            with pytest.raises(ValueError):
                Runbook.from_yaml(path)
        finally:
            path.unlink(missing_ok=True)

    def test_error_handling_optional(self):
        """Runbook without error_handling should parse to empty list."""
        from agent_runbook.schema import Runbook

        data = {
            "name": "test",
            "description": "desc",
            "steps": [],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            result = Runbook.from_yaml(path)
            assert result.error_handling == []
        finally:
            path.unlink(missing_ok=True)

    def test_error_handling_parsed(self):
        """Runbook with error_handling entries should parse correctly."""
        from agent_runbook.schema import Runbook

        data = {
            "name": "test",
            "description": "desc",
            "steps": [],
            "error_handling": [
                {
                    "scenario": "Layer A returns 0 candidates",
                    "handling": "Normal termination: no zombies found.",
                },
                {
                    "scenario": "All MCP tools unavailable",
                    "handling": "Return HIL signal mcp_unavailable",
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            result = Runbook.from_yaml(path)
            assert len(result.error_handling) == 2
            assert result.error_handling[0].scenario == "Layer A returns 0 candidates"
            assert result.error_handling[0].handling == "Normal termination: no zombies found."
            assert result.error_handling[1].scenario == "All MCP tools unavailable"
            assert result.error_handling[1].handling == "Return HIL signal mcp_unavailable"
        finally:
            path.unlink(missing_ok=True)
