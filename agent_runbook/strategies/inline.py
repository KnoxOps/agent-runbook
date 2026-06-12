"""Strategy for rendering inline prompt steps."""

from __future__ import annotations

from agent_runbook.context import RenderContext
from agent_runbook.i18n import t
from agent_runbook.schema import Step
from agent_runbook.strategies.base import StepStrategy


class InlineStepStrategy(StepStrategy):
    """Strategy for rendering inline prompt steps.

    Inline steps contain instructions that are either embedded directly
    in the step definition or referenced via a file path.
    """

    def _render_execution(self, step: Step, ctx: RenderContext) -> str:
        """Render the execution section for inline prompt steps.

        If the prompt is multi-line, it's treated as embedded instructions.
        Otherwise, it's treated as a file path reference.

        Args:
            step: The step to render.
            ctx: The rendering context.

        Returns:
            Execution section markdown.
        """
        lang = ctx.lang
        lines = [f"## {t('execution', lang)}"]

        if step.prompt_file:
            # File path reference
            lines.append(f"Follow the instructions in the prompt file `{step.prompt_file}`.")
        elif step.prompt:
            # Embedded inline prompt text
            lines.append(f"{t('follow_instructions', lang)}\n")
            lines.append(step.prompt)

        if step.output:
            lines.append("\nWrite the output to the specified output file.")

        return "\n".join(lines)
