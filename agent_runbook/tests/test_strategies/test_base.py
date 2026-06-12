"""Tests for StepStrategy base class and RenderContext."""

from __future__ import annotations

import pytest

from agent_runbook.context import RenderContext
from agent_runbook.schema import Step, StepType, StepOutputDef
from agent_runbook.strategies.base import StepStrategy


class TestRenderContext:
    """Tests for RenderContext data class."""

    def test_render_context_holds_data(self):
        """RenderContext should hold all 4 fields and be accessible."""
        ctx = RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
        )

        assert ctx.runbook is None
        assert ctx.execution_order == []
        assert ctx.branch_groups == {}
        assert ctx.runbook_dir == "/test"


class TestStepStrategyAbstract:
    """Tests for StepStrategy abstract base class."""

    def test_base_strategy_is_abstract(self):
        """StepStrategy should not be instantiable directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            StepStrategy()


class TestConcreteStrategy:
    """Tests for concrete strategy implementation."""

    def test_concrete_strategy_renders_sections(self):
        """Concrete strategy should render all sections including execution."""
        # Create a minimal step
        step = Step(
            id="test",
        depends_on=[],
            type=StepType.INLINE,
            description="desc",
            prompt="Do something",
            output=[StepOutputDef(schema="x", file="y.json")],
        )

        # Create a concrete subclass
        class TestStrategy(StepStrategy):
            def _render_execution(self, step: Step, ctx: RenderContext) -> str:
                return "EXECUTION CONTENT"

        ctx = RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
        )

        strategy = TestStrategy()
        output = strategy.render(step, ctx)

        assert "EXECUTION CONTENT" in output
        assert "desc" in output  # description should appear
        assert "inline" in output  # step type should appear

    def test_strategy_skips_optional_when_empty(self):
        """Strategy should skip optional sections when data is absent."""
        # Step without checkpoint
        step_no_checkpoint = Step(
            id="test",
        depends_on=[],
            type=StepType.INLINE,
            description="desc",
            prompt="Do something",
        )

        # Step without input
        step_no_input = Step(
            id="test2",
        depends_on=[],
            type=StepType.INLINE,
            description="desc",
            prompt="Do something",
        )

        class TestStrategy(StepStrategy):
            def _render_execution(self, step: Step, ctx: RenderContext) -> str:
                return "EXECUTION"

        ctx = RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
        )

        strategy = TestStrategy()

        # Render step without checkpoint
        output1 = strategy.render(step_no_checkpoint, ctx)
        assert "checkpoint" not in output1.lower()

        # Render step without input
        output2 = strategy.render(step_no_input, ctx)
        assert "input" not in output2.lower() or "input files" not in output2.lower()
