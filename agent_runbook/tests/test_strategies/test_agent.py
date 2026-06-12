"""Tests for AgentStepStrategy."""

from __future__ import annotations

import pytest

from agent_runbook.context import RenderContext
from agent_runbook.schema import Step, StepType, StepInputRef, StepOutputDef
from agent_runbook.strategies.agent import AgentStepStrategy


class TestAgentStepStrategy:
    """Tests for AgentStepStrategy rendering."""

    def test_agent_renders_sub_agent(self):
        """Step with type=agent.

        Output should contain "independent agent" and prompt file reference.
        """
        step = Step(
            id="agent-sub",
        depends_on=[],
            type=StepType.AGENT,
            description="Run sub-agent for analysis",
            prompt="prompts/agent-analysis.md",
            input=[StepInputRef(schema="data", from_step="data-prep")],
            output=[StepOutputDef(schema="analysis", file="agent_output.json")],
        )

        ctx = RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
        )

        strategy = AgentStepStrategy()
        output = strategy.render(step, ctx)

        assert "independent agent" in output.lower()
        assert "prompts/agent-analysis.md" in output

    def test_agent_renders_io_paths(self):
        """Output should contain input file path and output file path."""
        step = Step(
            id="agent-io",
        depends_on=[],
            type=StepType.AGENT,
            description="Agent with IO",
            prompt="prompts/process.md",
            input=[StepInputRef(schema="input_data")],
            output=[StepOutputDef(schema="output_data", file="results/agent_result.json")],
        )

        ctx = RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
        )

        strategy = AgentStepStrategy()
        output = strategy.render(step, ctx)

        # Should reference prompt file
        assert "prompts/process.md" in output
        # Should reference output file
        assert "results/agent_result.json" in output
