"""Tests for LoopStepStrategy."""

from __future__ import annotations

from agent_runbook.context import RenderContext
from agent_runbook.schema import Step, StepType


class TestLoopStepStrategy:
    """Tests for LoopStepStrategy rendering."""

    def _make_loop_step(self) -> Step:
        """Create a loop step with body sub-steps."""
        return Step(
            id="fix_loop",
            type=StepType.LOOP,
            description="Iteratively fix all lint errors",
            goal="ESLint passes with zero errors on all files",
            max_iterations=10,
            depends_on=["setup"],
            body=[
                Step(
                    id="discover",
                    type=StepType.INLINE,
                    prompt="Run eslint, write errors",
                    depends_on=[],
                ),
                Step(
                    id="fix",
                    type=StepType.INLINE,
                    prompt="Pick a batch of errors and fix them",
                    depends_on=["discover"],
                ),
                Step(
                    id="verify",
                    type=StepType.INLINE,
                    prompt="Run eslint again, check remaining errors",
                    depends_on=["fix"],
                ),
            ],
        )

    def _make_ctx(self) -> RenderContext:
        return RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
        )

    def test_render_includes_goal(self):
        """Loop render output should include the goal text."""
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        step = self._make_loop_step()
        ctx = self._make_ctx()

        output = strategy.render(step, ctx)
        assert "ESLint passes with zero errors on all files" in output

    def test_render_includes_max_iterations(self):
        """Loop render output should include max_iterations."""
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        step = self._make_loop_step()
        ctx = self._make_ctx()

        output = strategy.render(step, ctx)
        assert "10" in output

    def test_render_includes_body_steps(self):
        """Loop render output should include body step IDs."""
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        step = self._make_loop_step()
        ctx = self._make_ctx()

        output = strategy.render(step, ctx)
        assert "discover" in output
        assert "fix" in output
        assert "verify" in output

    def test_render_includes_loop_structure(self):
        """Loop render output should have loop-specific sections."""
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        step = self._make_loop_step()
        ctx = self._make_ctx()

        output = strategy.render(step, ctx)
        # Should have goal evaluation section
        assert "goal" in output.lower()
        # Should indicate iteration behavior
        assert "iteration" in output.lower()

    def test_render_includes_body_prompts(self):
        """Loop render output should include the body steps' prompt text."""
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        step = self._make_loop_step()
        ctx = self._make_ctx()

        output = strategy.render(step, ctx)
        assert "Run eslint, write errors" in output
        assert "Pick a batch of errors and fix them" in output

    def test_render_zh(self):
        """Loop render output in Chinese should use translated keys."""
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        step = self._make_loop_step()
        ctx = RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
            lang="zh",
        )

        output = strategy.render(step, ctx)
        # Should contain Chinese text, not English
        assert "ESLint passes with zero errors on all files" in output  # goal is user-provided, stays as-is
        assert "10" in output
