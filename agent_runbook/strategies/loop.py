"""Strategy for rendering loop steps."""

from __future__ import annotations

from agent_runbook.context import RenderContext
from agent_runbook.dag import topological_sort
from agent_runbook.i18n import t
from agent_runbook.schema import Step, StepType
from agent_runbook.strategies.base import StepStrategy


class LoopStepStrategy(StepStrategy):
    """Strategy for rendering loop steps.

    Loop steps override the base render() entirely because they have
    fundamentally different structure: a loop header, rendered body
    sub-steps, and goal evaluation logic.
    """

    def render(self, step: Step, ctx: RenderContext) -> str:
        """Render a loop step with header, body, and goal evaluation."""
        lang = ctx.lang
        lines: list[str] = []

        # Header metadata
        lines.append(f"**{t('type_label', lang)}** loop")
        if step.description:
            lines.append(f"**{t('description_label', lang)}** {step.description}")
        lines.append("")

        # Loop section header
        lines.append(f"## {t('loop_header', lang)}")
        lines.append("")
        lines.append(f"**{t('loop_goal_label', lang)}:** {step.goal}")
        lines.append(f"**{t('loop_max_label', lang)}:** {step.max_iterations}")
        lines.append("")
        lines.append(f"> {t('loop_intro', lang)}")
        lines.append("")

        # Body section
        lines.append(f"## {t('loop_body_header', lang)}")
        lines.append("")

        if step.body:
            body_sorted = topological_sort(step.body)
            for i, body_step in enumerate(body_sorted, 1):
                lines.append(f"#### Body Step {i}: {body_step.id}")
                lines.append("")
                body_content = self._render_body_step(body_step, ctx)
                lines.append(body_content)
                lines.append("")

        # Goal evaluation section
        lines.append(f"## {t('loop_goal_check', lang)}")
        lines.append("")
        lines.append(t("loop_goal_check_desc", lang))
        lines.append("")
        lines.append(f"**{t('loop_goal_label', lang)}:** {step.goal}")
        lines.append("")
        lines.append(f"1. {t('loop_done', lang)}")
        lines.append(f"2. {t('loop_continue', lang)}")
        lines.append(f"3. {t('loop_max_reached', lang)}")
        lines.append("")
        lines.append(t("loop_iteration_history", lang))

        # Progress tracking
        lines.append("")
        lines.append(self._render_progress_tracking(step, lang))

        return "\n".join(lines)

    def _render_body_step(self, step: Step, ctx: RenderContext) -> str:
        """Render a single body sub-step inline."""
        lang = ctx.lang
        lines: list[str] = []

        lines.append(f"**{t('type_label', lang)}** {step.type.value}")
        if step.description:
            lines.append(f"**{t('description_label', lang)}** {step.description}")

        # Input
        if step.input:
            lines.append("")
            lines.append(f"**{t('input_files', lang)}**")
            for input_ref in step.input:
                if input_ref.file:
                    lines.append(f"- `{input_ref.file}`")
                elif input_ref.schema:
                    lines.append(f"- schema: {input_ref.schema}")

        # Execution
        lines.append("")
        if step.type == StepType.INLINE:
            lines.append(f"**{t('execution', lang)}:** {t('follow_instructions', lang)}")
            if step.prompt:
                lines.append("")
                lines.append(step.prompt)
            elif step.prompt_file:
                lines.append(f"  File: `{step.prompt_file}`")
        elif step.type == StepType.AGENT:
            lines.append(f"**{t('execution', lang)}:** {t('launch_agent', lang)}")
            if step.prompt_file:
                lines.append(f"  `{step.prompt_file}`")
            elif step.prompt:
                lines.append("")
                lines.append(step.prompt)
        elif step.type == StepType.SCRIPT:
            lines.append(f"**{t('execution', lang)}:** {t('execute_command', lang)}")
            if step.command:
                lines.append(f"```bash\n{step.command}\n```")

        # Output
        if step.output:
            lines.append("")
            lines.append(f"**{t('output_files', lang)}**")
            for output_def in step.output:
                lines.append(f"- `{output_def.file}`")

        return "\n".join(lines)

    def _render_execution(self, step: Step, ctx: RenderContext) -> str:
        """Not used — render() is overridden."""
        return ""
