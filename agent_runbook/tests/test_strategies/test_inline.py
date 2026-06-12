"""Tests for InlineStepStrategy."""

from __future__ import annotations

import pytest

from agent_runbook.context import RenderContext
from agent_runbook.schema import Step, StepType, StepOutputDef
from agent_runbook.strategies.inline import InlineStepStrategy


class TestInlineStepStrategy:
    """Tests for InlineStepStrategy rendering."""

    def test_inline_renders_embedded_prompt(self):
        """Step with inline prompt (multi-line text).

        Output should contain "Follow these instructions" and the prompt text.
        """
        step = Step(
            id="inline-embedded",
        depends_on=[],
            type=StepType.INLINE,
            description="Analyze a report",
            prompt="Follow these instructions:\n1. Read the file\n2. Extract key findings\n3. Summarize results",
            output=[StepOutputDef(schema="analysis", file="output.json")],
        )

        ctx = RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
        )

        strategy = InlineStepStrategy()
        output = strategy.render(step, ctx)

        assert "Follow these instructions" in output
        assert "Read the file" in output
        assert "Extract key findings" in output
        assert "Summarize results" in output
        assert "output.json" in output

    def test_inline_renders_file_prompt(self):
        """Step with prompt file path.

        Output should reference the file path.
        """
        step = Step(
            id="inline-file",
        depends_on=[],
            type=StepType.INLINE,
            description="Process with external prompt",
            prompt="prompts/analyze.md",
            output=[StepOutputDef(schema="result", file="result.json")],
        )

        ctx = RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
        )

        strategy = InlineStepStrategy()
        output = strategy.render(step, ctx)

        assert "prompts/analyze.md" in output
        assert "file" in output.lower() or "prompt" in output.lower()
