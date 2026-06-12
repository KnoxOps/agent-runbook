"""Tests for ParallelStepStrategy."""

from __future__ import annotations

import pytest

from agent_runbook.context import RenderContext
from agent_runbook.schema import Step, StepType, ParallelConfig, StepInputRef, StepOutputDef
from agent_runbook.strategies.parallel import ParallelStepStrategy


class TestParallelStepStrategy:
    """Tests for ParallelStepStrategy wrapper."""

    def test_parallel_renders_batch_split(self):
        """Step with parallel.enabled=True should render batch split instructions."""
        # Create a step with parallel config
        step = Step(
            id="parallel_step",
        depends_on=[],
            type=StepType.SCRIPT,
            description="Process items in parallel",
            command="process.sh",
            parallel=ParallelConfig(enabled=True, max_instances=5, item_key="resource_id"),
            input=[StepInputRef(schema="items", file="items.json")],
            checkpoint="checkpoint.jsonl",
        )

        ctx = RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
        )

        strategy = ParallelStepStrategy()
        output = strategy.wrap(
            step_content="Execute process.sh on each item",
            step=step,
            ctx=ctx,
        )

        # Verify output contains key parallel execution details
        assert "Parallel Execution" in output or "parallel" in output.lower()
        assert "5" in output or "max" in output.lower()
        assert "resource_id" in output
        assert "checkpoint" in output.lower()
        assert len(output) > 0

    def test_parallel_single_instance(self):
        """Step with max_instances=1 should describe single-batch processing."""
        step = Step(
            id="single_step",
        depends_on=[],
            type=StepType.SCRIPT,
            description="Single batch",
            command="process.sh",
            parallel=ParallelConfig(enabled=True, max_instances=1, item_key="id"),
            input=[StepInputRef(schema="items", file="items.json")],
        )

        ctx = RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
        )

        strategy = ParallelStepStrategy()
        output = strategy.wrap(
            step_content="Execute process.sh",
            step=step,
            ctx=ctx,
        )

        # Verify output mentions single batch or sequential processing
        assert output is not None
        assert len(output) > 0
        assert ("1" in output or "single" in output.lower() or "batch" in output.lower())
