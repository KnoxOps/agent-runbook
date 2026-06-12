"""Tests for CheckpointScriptStrategy."""

from __future__ import annotations

import pytest

from agent_runbook.context import RenderContext
from agent_runbook.schema import Step, StepType
from agent_runbook.strategies.checkpoint import CheckpointScriptStrategy, CheckpointScript


class TestCheckpointScriptStrategy:
    """Tests for CheckpointScriptStrategy."""

    def test_checkpoint_generates_script_strings(self):
        """Step with checkpoint should generate list of CheckpointScript objects."""
        step = Step(
            id="process_items",
        depends_on=[],
            type=StepType.SCRIPT,
            description="Process items with checkpoint",
            command="process.sh",
            checkpoint="checkpoint.jsonl",
        )

        ctx = RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
        )

        strategy = CheckpointScriptStrategy()
        scripts = strategy.generate_scripts(step, ctx)

        # Should return a non-empty list of CheckpointScript objects
        assert isinstance(scripts, list)
        assert len(scripts) > 0

        # Each item should be a CheckpointScript
        for script in scripts:
            assert isinstance(script, CheckpointScript)
            assert script.filename is not None
            assert len(script.filename) > 0
            assert script.content is not None
            assert len(script.content) > 0

        # Should have 4 checkpoint scripts (init, pending, mark_done, merge)
        assert len(scripts) == 4

        # Verify filenames are reasonable
        filenames = {s.filename for s in scripts}
        assert any("init" in f for f in filenames)
        assert any("pending" in f for f in filenames)
        assert any("mark_done" in f for f in filenames)
        assert any("merge" in f for f in filenames)

    def test_no_checkpoint_returns_empty(self):
        """Step without checkpoint field should return empty list."""
        step = Step(
            id="simple_step",
        depends_on=[],
            type=StepType.SCRIPT,
            description="Simple step",
            command="simple.sh",
            # No checkpoint field
        )

        ctx = RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
        )

        strategy = CheckpointScriptStrategy()
        scripts = strategy.generate_scripts(step, ctx)

        # Should return empty list
        assert isinstance(scripts, list)
        assert len(scripts) == 0
