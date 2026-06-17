"""Tests for validator.py — Runbook validation rules."""

import tempfile
from pathlib import Path

import pytest
import yaml

from agent_runbook.schema import Runbook, StepType
from agent_runbook.validator import RunbookValidator, ValidationError


class TestValidRunbook:
    """Test 1: Valid runbook should pass validation."""

    @pytest.fixture
    def fixture_path(self):
        return Path(__file__).parent / "fixtures" / "simple-3-step" / "runbook.yaml"

    def test_valid_runbook_passes(self, fixture_path):
        """Load simple-3-step fixture, validate returns empty errors list."""
        runbook = Runbook.from_yaml(fixture_path)
        runbook_dir = fixture_path.parent
        validator = RunbookValidator(runbook, str(runbook_dir))
        errors = validator.validate()
        assert errors == []


class TestDuplicateStepId:
    """Test 2: Duplicate step IDs should error."""

    def test_duplicate_step_id(self):
        """Two steps with same id → ERROR."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "inline",
                    "prompt": "Do something",
                    "depends_on": [],
                },
                {
                    "id": "step1",  # duplicate
                    "type": "inline",
                    "prompt": "Do something else",
                    "depends_on": [],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            assert len(errors) > 0
            assert any("duplicate" in str(e).lower() for e in errors)
        finally:
            path.unlink(missing_ok=True)


class TestPromptFileNotFound:
    """Test 3: File-path prompt pointing to nonexistent file → ERROR."""

    def test_prompt_file_not_found(self):
        """File-path prompt_file pointing to nonexistent file → ERROR."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "agent",
                    "prompt_file": "prompts/nonexistent.md",
                    "depends_on": [],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            assert len(errors) > 0
            assert any("not found" in str(e).lower() for e in errors)
        finally:
            path.unlink(missing_ok=True)

    def test_inline_prompt_no_error(self):
        """Inline prompts (with \\n) should NOT trigger file-not-found error."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "inline",
                    "prompt": "Line 1\nLine 2",  # inline, has newline
                    "depends_on": [],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            # Should not have file-not-found errors for inline prompts
            assert not any("not found" in str(e).lower() for e in errors)
        finally:
            path.unlink(missing_ok=True)


class TestSchemaFileNotFound:
    """Test 4: Input/output schema path nonexistent → ERROR."""

    def test_schema_file_not_found(self):
        """Input/output schema path nonexistent → ERROR."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "inline",
                    "prompt": "Do something",
                    "depends_on": [],
                    "input": [
                        {
                            "schema": "schemas/nonexistent.schema.json",
                        }
                    ],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            assert len(errors) > 0
            assert any("schema" in str(e).lower() and "not found" in str(e).lower() for e in errors)
        finally:
            path.unlink(missing_ok=True)


class TestDAGCycle:
    """Test 5: Cycle in DAG → ERROR."""

    def test_dag_cycle(self):
        """A→B→C→A cycle → ERROR."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "a",
                    "type": "inline",
                    "prompt": "Step A",
                    "depends_on": ["c"],
                },
                {
                    "id": "b",
                    "type": "inline",
                    "prompt": "Step B",
                    "depends_on": ["a"],
                },
                {
                    "id": "c",
                    "type": "inline",
                    "prompt": "Step C",
                    "depends_on": ["b"],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            assert len(errors) > 0
            assert any("cycle" in str(e).lower() for e in errors)
        finally:
            path.unlink(missing_ok=True)


class TestFromStepNotInDependsOn:
    """Test 6: from_step points to step not in depends_on → ERROR."""

    def test_from_step_not_in_depends_on(self):
        """from_step points to step not in depends_on → ERROR."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "inline",
                    "prompt": "Step 1",
                    "depends_on": [],
                },
                {
                    "id": "step2",
                    "type": "inline",
                    "prompt": "Step 2",
                    "input": [
                        {
                            "schema": "schemas/test.schema.json",
                            "from_step": "step1",  # from_step but step1 not in depends_on
                        }
                    ],
                    "depends_on": [],  # missing step1
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            assert len(errors) > 0
            assert any("from_step" in str(e).lower() for e in errors)
        finally:
            path.unlink(missing_ok=True)


class TestFromStepNonexistent:
    """Test 7: from_step points to nonexistent step id → ERROR."""

    def test_from_step_nonexistent(self):
        """from_step points to nonexistent step id → ERROR."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "inline",
                    "prompt": "Step 1",
                    "input": [
                        {
                            "schema": "schemas/test.schema.json",
                            "from_step": "nonexistent",  # nonexistent step
                        }
                    ],
                    "depends_on": [],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            assert len(errors) > 0
            assert any("nonexistent" in str(e).lower() or "not found" in str(e).lower() for e in errors)
        finally:
            path.unlink(missing_ok=True)


class TestConditionEmpty:
    """Test 8: condition="" → ERROR."""

    def test_condition_empty_raises(self):
        """condition="" → ERROR."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "inline",
                    "prompt": "Step 1",
                    "depends_on": [],
                },
                {
                    "id": "step2",
                    "type": "inline",
                    "prompt": "Step 2",
                    "depends_on": [],
                    "condition": "",  # empty condition
                    "depends_on": ["step1"],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            assert len(errors) > 0
            assert any("condition" in str(e).lower() and "empty" in str(e).lower() for e in errors)
        finally:
            path.unlink(missing_ok=True)


class TestConditionWhitespace:
    """Test 9: condition="   " → ERROR."""

    def test_condition_whitespace_raises(self):
        """condition="   " → ERROR."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "inline",
                    "prompt": "Step 1",
                    "depends_on": [],
                },
                {
                    "id": "step2",
                    "type": "inline",
                    "prompt": "Step 2",
                    "depends_on": [],
                    "condition": "   ",  # whitespace-only condition
                    "depends_on": ["step1"],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            assert len(errors) > 0
            assert any("condition" in str(e).lower() for e in errors)
        finally:
            path.unlink(missing_ok=True)


class TestPromptPathTraversal:
    """Test 10: prompt_file with ".." now allowed — expect not-found error instead."""

    def test_prompt_path_traversal(self):
        """prompt_file contains ".." → allowed, but file won't exist → not-found error."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "agent",
                    "prompt_file": "../../../etc/passwd",  # path traversal (now allowed)
                    "depends_on": [],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            assert len(errors) > 0
            assert any("not found" in str(e).lower() for e in errors)
        finally:
            path.unlink(missing_ok=True)


class TestParallelMissingItemKey:
    """Test 11: parallel.enabled=true but item_key empty → ERROR."""

    def test_parallel_missing_item_key(self):
        """parallel.enabled=true but item_key empty → ERROR."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "inline",
                    "prompt": "Step 1",
                    "depends_on": [],
                    "parallel": {
                        "enabled": True,
                        "max_instances": 5,
                        "item_key": "",  # empty item_key
                    },
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            assert len(errors) > 0
            assert any("item_key" in str(e).lower() for e in errors)
        finally:
            path.unlink(missing_ok=True)


class TestTypeFieldMismatch:
    """Test 12: type=script with prompt set → ERROR; type=agent without prompt → ERROR."""

    def test_script_with_prompt(self):
        """type=script with prompt set → ERROR."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "script",
                    "command": "echo hello",
                    "depends_on": [],
                    "prompt": "This should not be here",  # script shouldn't have prompt
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            assert len(errors) > 0
            assert any("script" in str(e).lower() and "prompt" in str(e).lower() for e in errors)
        finally:
            path.unlink(missing_ok=True)

    def test_script_with_prompt_file(self):
        """type=script with prompt_file set → ERROR."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "script",
                    "command": "echo hello",
                    "depends_on": [],
                    "prompt_file": "prompts/not-allowed.md",
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            assert len(errors) > 0
            assert any("script" in str(e).lower() and "prompt_file" in str(e).lower() for e in errors)
        finally:
            path.unlink(missing_ok=True)


class TestOutputFileConflict:
    """Test 13: Two steps output same filename → WARN (not error)."""

    def test_output_file_conflict_warns(self):
        """Two steps output same filename → WARN (not error)."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "inline",
                    "prompt": "Step 1",
                    "depends_on": [],
                    "output": [
                        {
                            "schema": "schemas/test.schema.json",
                            "file": "output.json",
                        }
                    ],
                },
                {
                    "id": "step2",
                    "type": "inline",
                    "prompt": "Step 2",
                    "output": [
                        {
                            "schema": "schemas/test.schema.json",
                            "file": "output.json",  # same filename
                        }
                    ],
                    "depends_on": ["step1"],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            # Should have warnings, not errors
            warnings = [e for e in errors if e.level == "WARN"]
            assert len(warnings) > 0
            assert any("output" in str(w).lower() or "file" in str(w).lower() for w in warnings)
        finally:
            path.unlink(missing_ok=True)


class TestOrphanStepWarns:
    """Test 14: Step not in any dependency chain → WARN."""

    def test_orphan_step_warns(self):
        """Step not in any dependency chain → WARN."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "inline",
                    "prompt": "Step 1",
                    "depends_on": [],
                },
                {
                    "id": "step2",
                    "type": "inline",
                    "prompt": "Step 2",
                    "depends_on": ["step1"],
                },
                {
                    "id": "orphan",
                    "type": "inline",
                    "prompt": "Orphan step",
                    "depends_on": [],
                    # no depends_on, and nothing depends on it
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            # Should have warnings
            warnings = [e for e in errors if e.level == "WARN"]
            assert len(warnings) > 0
            assert any("orphan" in str(w).lower() or "unreachable" in str(w).lower() for w in warnings)
        finally:
            path.unlink(missing_ok=True)


class TestSchemaPathTraversal:
    """Test 15: Schema paths with ".." now allowed — expect not-found errors instead."""

    def test_input_schema_path_traversal(self):
        """Input schema contains ".." → allowed, file won't exist → not-found error."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "inline",
                    "prompt": "Step 1",
                    "depends_on": [],
                    "input": [
                        {
                            "schema": "../../../etc/passwd",  # path traversal (now allowed)
                        }
                    ],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            assert len(errors) > 0
            assert any("not found" in str(e).lower() for e in errors)
        finally:
            path.unlink(missing_ok=True)

    def test_output_schema_path_traversal(self):
        """Output schema contains ".." → allowed, file won't exist → not-found error."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "inline",
                    "prompt": "Step 1",
                    "depends_on": [],
                    "output": [
                        {
                            "schema": "../../../etc/passwd",  # path traversal (now allowed)
                            "file": "output.json",
                        }
                    ],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            assert len(errors) > 0
            assert any("not found" in str(e).lower() for e in errors)
        finally:
            path.unlink(missing_ok=True)


class TestFromStepOrphaned:
    """Test 16: from_step specified but step has empty input: [] → WARN/ERROR."""

    def test_from_step_with_empty_input(self):
        """from_step specified but input: [] is empty → should report issue."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [
                {
                    "id": "step1",
                    "type": "inline",
                    "prompt": "Step 1\nSome action",
                    "depends_on": [],
                },
                {
                    "id": "step2",
                    "type": "inline",
                    "prompt": "Step 2\nAnother action",
                    "input": [],  # empty input, no from_step to attach to
                    "depends_on": ["step1"],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            # Empty input with depends_on is valid (can depend on step but not consume input from it)
            # So we expect this to pass without errors
            assert errors == []
        finally:
            path.unlink(missing_ok=True)


class TestEmptyRunbook:
    """Test 17: Empty runbook (steps: []) should pass validation."""

    def test_empty_runbook_passes(self):
        """Empty runbook (steps: []) → should pass validation."""
        data = {
            "name": "test",
            "description": "desc",
            "steps": [],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            assert errors == []
        finally:
            path.unlink(missing_ok=True)


class TestLoopStepValidation:
    """Test 18: Loop step validation rules."""

    def _make_loop_runbook(self, loop_step_overrides: dict) -> dict:
        """Helper to build a runbook dict with a loop step."""
        loop_step = {
            "id": "my_loop",
            "type": "loop",
            "goal": "All tests pass",
            "max_iterations": 5,
            "depends_on": [],
            "body": [
                {
                    "id": "work",
                    "type": "inline",
                    "prompt": "Do work",
                    "depends_on": [],
                },
            ],
        }
        loop_step.update(loop_step_overrides)
        return {
            "name": "test",
            "description": "desc",
            "steps": [loop_step],
        }

    def test_valid_loop_passes(self):
        """A well-formed loop step should pass validation."""
        data = self._make_loop_runbook({})
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            error_errors = [e for e in errors if e.level == "ERROR"]
            assert error_errors == []
        finally:
            path.unlink(missing_ok=True)

    def test_whitespace_goal_raises_error(self):
        """Loop step with whitespace-only goal should produce ERROR."""
        data = self._make_loop_runbook({"goal": "   "})
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            error_errors = [e for e in errors if e.level == "ERROR"]
            assert len(error_errors) == 1
            assert "goal" in error_errors[0].message.lower()
        finally:
            path.unlink(missing_ok=True)

    def test_max_iterations_zero_raises_error(self):
        """Loop step with max_iterations=0 should produce ERROR."""
        data = self._make_loop_runbook({"max_iterations": 0})
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            error_errors = [e for e in errors if e.level == "ERROR"]
            assert len(error_errors) == 1
            assert "max_iterations" in error_errors[0].message
        finally:
            path.unlink(missing_ok=True)

    def test_max_iterations_negative_raises_error(self):
        """Loop step with max_iterations=-1 should produce ERROR."""
        data = self._make_loop_runbook({"max_iterations": -1})
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            error_errors = [e for e in errors if e.level == "ERROR"]
            assert len(error_errors) == 1
            assert "max_iterations" in error_errors[0].message
        finally:
            path.unlink(missing_ok=True)

    def test_max_iterations_over_50_warns(self):
        """Loop step with max_iterations > 50 should produce WARN."""
        data = self._make_loop_runbook({"max_iterations": 100})
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            warns = [e for e in errors if e.level == "WARN"]
            assert any("max_iterations" in w.message for w in warns)
        finally:
            path.unlink(missing_ok=True)

    def test_body_cycle_raises_error(self):
        """Loop body with cyclic depends_on should produce ERROR."""
        data = self._make_loop_runbook({
            "body": [
                {
                    "id": "a",
                    "type": "inline",
                    "prompt": "Step A",
                    "depends_on": ["b"],
                },
                {
                    "id": "b",
                    "type": "inline",
                    "prompt": "Step B",
                    "depends_on": ["a"],
                },
            ],
        })
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            error_errors = [e for e in errors if e.level == "ERROR"]
            assert any("cycle" in e.message.lower() for e in error_errors)
        finally:
            path.unlink(missing_ok=True)

    def test_body_duplicate_ids_raises_error(self):
        """Loop body with duplicate step IDs should produce ERROR."""
        data = self._make_loop_runbook({
            "body": [
                {
                    "id": "work",
                    "type": "inline",
                    "prompt": "First",
                    "depends_on": [],
                },
                {
                    "id": "work",
                    "type": "inline",
                    "prompt": "Duplicate",
                    "depends_on": [],
                },
            ],
        })
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            runbook = Runbook.from_yaml(path)
            validator = RunbookValidator(runbook, str(path.parent))
            errors = validator.validate()
            error_errors = [e for e in errors if e.level == "ERROR"]
            assert any("duplicate" in e.message.lower() for e in error_errors)
        finally:
            path.unlink(missing_ok=True)
