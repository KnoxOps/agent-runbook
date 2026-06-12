"""Tests for ScriptStepStrategy."""

from __future__ import annotations

import pytest

from agent_runbook.context import RenderContext
from agent_runbook.schema import Step, StepType, StepInputRef, StepOutputDef
from agent_runbook.strategies.script import ScriptStepStrategy


class TestScriptStepStrategy:
    """Tests for ScriptStepStrategy rendering."""

    def test_script_renders_command(self):
        """Step with type=script, command="python3 x.py".

        Output should contain bash code block with the command.
        """
        step = Step(
            id="script-python",
        depends_on=[],
            type=StepType.SCRIPT,
            description="Run data processing script",
            command="python3 process_data.py --input data.json --output results.json",
            input=[StepInputRef(schema="data", from_step="fetch-data")],
            output=[StepOutputDef(schema="results", file="results.json")],
        )

        ctx = RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
        )

        strategy = ScriptStepStrategy()
        output = strategy.render(step, ctx)

        assert "```bash" in output
        assert "python3 process_data.py --input data.json --output results.json" in output
        assert "```" in output

    def test_script_has_no_prompt_section(self):
        """Script step should have no prompt/output section for instructions.

        Only commands, no redundant instruction sections.
        """
        step = Step(
            id="script-basic",
        depends_on=[],
            type=StepType.SCRIPT,
            description="Simple shell command",
            command="ls -la /tmp",
            output=[StepOutputDef(schema="listing", file="listing.txt")],
        )

        ctx = RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
        )

        strategy = ScriptStepStrategy()
        output = strategy.render(step, ctx)

        # Should contain the command in bash block
        assert "```bash" in output
        assert "ls -la /tmp" in output

        # Should NOT have redundant "Follow these instructions" or similar
        assert "Follow these instructions" not in output
        assert "independent agent" not in output.lower()
