"""Tests for LoopStepStrategy orchestrator rendering."""

from __future__ import annotations

from agent_runbook.context import RenderContext
from agent_runbook.schema import Step, StepType, QualityCheckConfig


class TestLoopOrchestratorRender:
    """Tests for LoopStepStrategy orchestrator output."""

    def _make_ctx(self, lang: str = "en") -> RenderContext:
        return RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
            lang=lang,
        )

    def _make_loop_step(self) -> Step:
        return Step(
            id="fix_loop",
            type=StepType.LOOP,
            description="Fix all lint errors",
            goal="ESLint passes with zero errors on all files",
            max_iterations=10,
            depends_on=["setup"],
            body=[
                Step(
                    id="discover",
                    type=StepType.INLINE,
                    prompt="Run eslint, write errors to eslint_output.json",
                    output=[{"schema": "schemas/eslint.schema.json", "file": "eslint_output.json"}],
                    depends_on=[],
                ),
                Step(
                    id="fix",
                    type=StepType.AGENT,
                    prompt="Pick a batch of errors and fix them",
                    depends_on=["discover"],
                    quality_check=QualityCheckConfig(
                        blocking=True,
                        rules=["Only src/ files modified", "No test files changed"],
                    ),
                ),
                Step(
                    id="verify",
                    type=StepType.SCRIPT,
                    command="eslint src/ --format json",
                    depends_on=["fix"],
                    output=[{"schema": "schemas/eslint.schema.json", "file": "eslint_output.json"}],
                ),
            ],
        )

    # -- Existing test coverage (updated) --

    def test_render_includes_goal(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "ESLint passes with zero errors on all files" in output

    def test_render_includes_max_iterations(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "10" in output

    def test_render_includes_body_step_ids(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "discover" in output
        assert "fix" in output
        assert "verify" in output

    def test_render_includes_body_prompts(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "Run eslint, write errors to eslint_output.json" in output
        assert "Pick a batch of errors and fix them" in output

    def test_render_has_orchestrator_structure(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "Loop Orchestrator" in output
        assert "Loop Config" in output
        assert "Body Steps" in output
        assert "After Each Iteration" in output
        assert "State Management" in output

    # -- New tests for dispatch instructions --

    def test_script_step_has_bash_dispatch(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "eslint src/ --format json" in output

    def test_agent_step_has_dispatch_instruction(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "Agent tool" in output

    def test_inline_step_has_handle_instruction(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "Run eslint" in output

    def test_goal_check_prompt_includes_evidence_files(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "eslint_output.json" in output

    def test_goal_check_prompt_includes_schema(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "goal_met" in output
        assert "goal-check" in output.lower()

    def test_quality_check_in_body_step(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "Only src/ files modified" in output
        assert "No test files changed" in output

    def test_state_management_in_output(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "iteration_history.json" in output

    # -- Chinese translation --

    def test_render_zh_has_translated_labels(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        step = self._make_loop_step()
        ctx = self._make_ctx(lang="zh")

        output = strategy.render(step, ctx)
        # Goal is user-provided, stays as-is
        assert "ESLint passes with zero errors on all files" in output
        # Chinese translations should appear for labels
        assert "目标" in output
        assert "最大迭代次数" in output
        assert "状态管理" in output
        assert "每次迭代后" in output

    # -- Nested loop warning --

    def test_nested_loop_emits_warning(self, caplog):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        step = Step(
            id="outer",
            type=StepType.LOOP,
            goal="done",
            max_iterations=3,
            depends_on=[],
            body=[
                Step(
                    id="inner",
                    type=StepType.LOOP,
                    goal="inner done",
                    max_iterations=2,
                    depends_on=[],
                    body=[
                        Step(id="s", type=StepType.INLINE, prompt="x", depends_on=[]),
                    ],
                ),
            ],
        )
        ctx = self._make_ctx()

        import logging
        with caplog.at_level(logging.WARNING):
            output = strategy.render(step, ctx)

        assert "Nested loop" in output
        assert "inner" in output
