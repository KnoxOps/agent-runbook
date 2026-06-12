"""Strategy for rendering agent subprocess steps."""

from __future__ import annotations

from agent_runbook.context import RenderContext
from agent_runbook.i18n import t
from agent_runbook.schema import Step
from agent_runbook.strategies.base import StepStrategy


class AgentStepStrategy(StepStrategy):
    """Strategy for rendering agent subprocess steps.

    Agent steps launch an independent agent with a prompt file,
    read input data, execute the prompt, and write results to output.
    """

    def _render_execution(self, step: Step, ctx: RenderContext) -> str:
        """Render the execution section for agent steps.

        Describes launching an independent agent with the prompt file,
        reading input, executing, and writing output.

        Args:
            step: The step to render.
            ctx: The rendering context.

        Returns:
            Execution section markdown.
        """
        lang = ctx.lang
        lines = [f"## {t('execution', lang)}"]

        # Main heading for launching agent
        lines.append(t("launch_agent", lang))
        lines.append("")

        if step.prompt_file:
            lines.append(f"**{t('prompt_file', lang)}** `{step.prompt_file}`")
        elif step.prompt:
            lines.append(f"**{t('dispatch_instruction', lang)}**")
            lines.append("")
            lines.append(step.prompt)
            lines.append("")

        # Describe the agent workflow
        lines.append(f"**{t('agent_workflow', lang)}**")
        lines.append("")

        # Input step
        if step.input:
            lines.append("1. Read input data from:")
            for input_ref in step.input:
                lines.append(f"   - Schema: `{input_ref.schema}`")
            lines.append("")
        else:
            lines.append("1. Prepare the execution environment")
            lines.append("")

        # Execution step
        lines.append("2. Execute the agent with the prompt")
        lines.append("")

        # Output step
        if step.output:
            lines.append("3. Write results to:")
            for output_def in step.output:
                lines.append(f"   - File: `{output_def.file}`")
        else:
            lines.append("3. Complete execution")

        return "\n".join(lines)
