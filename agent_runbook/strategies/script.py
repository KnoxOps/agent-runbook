"""Strategy for rendering shell script steps."""

from __future__ import annotations

from agent_runbook.context import RenderContext
from agent_runbook.i18n import t
from agent_runbook.schema import Step
from agent_runbook.strategies.base import StepStrategy


class ScriptStepStrategy(StepStrategy):
    """Strategy for rendering shell script steps.

    Script steps execute commands directly without prompt-based instructions.
    The execution section contains only the command in a bash code block.
    """

    def _render_execution(self, step: Step, ctx: RenderContext) -> str:
        """Render the execution section for script steps.

        Shows the command to execute in a bash code block.

        Args:
            step: The step to render.
            ctx: The rendering context.

        Returns:
            Execution section markdown.
        """
        lang = ctx.lang
        lines = [f"## {t('execution', lang)}"]
        lines.append("")
        lines.append(t("execute_command", lang))
        lines.append("")

        if step.command:
            lines.append("```bash")
            lines.append(step.command)
            lines.append("```")

        return "\n".join(lines)
