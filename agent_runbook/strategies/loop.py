"""Strategy for rendering loop steps as orchestrator dispatch instructions."""

from __future__ import annotations

import logging

from agent_runbook.context import RenderContext
from agent_runbook.dag import topological_sort
from agent_runbook.i18n import t
from agent_runbook.schema import Step, StepType
from agent_runbook.strategies.base import StepStrategy

logger = logging.getLogger(__name__)


class LoopStepStrategy(StepStrategy):
    """Strategy for rendering loop steps as orchestrator instructions.

    The main agent acts as scheduler: it iterates over body steps
    and dispatches each one according to its type (script→Bash,
    inline→self, agent→Agent tool). A goal-check sub-agent is
    dispatched after each iteration to evaluate the loop goal.
    """

    def render(self, step: Step, ctx: RenderContext) -> str:
        """Render a loop step as orchestrator dispatch instructions."""
        lang = ctx.lang
        parts: list[str] = []

        # Header metadata
        parts.append(self._render_header(step, ctx))

        # Orchestrator intro
        parts.append(self._render_orchestrator_intro(step, lang))

        # Body steps dispatch
        parts.append(self._render_body_dispatch(step, ctx))

        # After each iteration
        parts.append(self._render_post_iteration(step, ctx))

        # State management
        parts.append(self._render_state_management(step, lang))

        # Progress tracking
        parts.append(self._render_progress_tracking(step, lang))

        return "\n\n".join(parts)

    # -- Section renderers --

    def _render_orchestrator_intro(self, step: Step, lang: str) -> str:
        """Render the orchestrator role and loop config."""
        lines = [
            "## Loop Orchestrator",
            "",
            t("loop_orchestrator_intro", lang),
            "",
            "### Loop Config",
            "",
            f"**{t('loop_goal_label', lang)}:** {step.goal}",
            f"**{t('loop_max_label', lang)}:** {step.max_iterations}",
        ]
        return "\n".join(lines)

    def _render_body_dispatch(self, step: Step, ctx: RenderContext) -> str:
        """Render body steps as dispatch instructions, sorted by depends_on."""
        lang = ctx.lang
        lines: list[str] = []

        if not step.body:
            return ""

        body_sorted = topological_sort(step.body)

        lines.append("### Body Steps")
        lines.append("")
        lines.append(
            "Execute the following steps in order each iteration. "
            "Steps with the same dependencies may run in parallel."
        )
        lines.append("")

        for i, body_step in enumerate(body_sorted, 1):
            lines.append(
                f"#### Body Step {i}: {body_step.id} ({body_step.type.value})"
            )
            lines.append("")
            if body_step.description:
                lines.append(f"**{t('description_label', lang)}** {body_step.description}")
                lines.append("")

            # Input files
            input_block = self._render_body_step_input(body_step, lang)
            if input_block:
                lines.append(input_block)

            # Type-specific dispatch
            lines.append(self._render_body_step_dispatch(body_step, lang))

            # Output
            output_block = self._render_body_step_output(body_step, lang)
            if output_block:
                lines.append(output_block)

            # Quality check (for agent steps)
            if body_step.quality_check:
                lines.append(self._render_body_step_quality_check(body_step, lang))

            # Parallel note
            if body_step.parallel and body_step.parallel.enabled:
                lines.append(
                    f"> **{t('note_label', lang)}:** "
                    f"This step may run in parallel with up to "
                    f"{body_step.parallel.max_instances} instances."
                )
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _render_body_step_input(self, step: Step, lang: str) -> str:
        """Render input files for a body step."""
        if not step.input:
            return ""
        lines = [f"**{t('input_files', lang)}**"]
        for input_ref in step.input:
            if input_ref.file:
                lines.append(f"- `{input_ref.file}`")
            elif input_ref.schema:
                lines.append(f"- schema: {input_ref.schema}")
        lines.append("")
        return "\n".join(lines)

    def _render_body_step_dispatch(self, step: Step, lang: str) -> str:
        """Render dispatch instruction based on step type."""
        if step.type == StepType.SCRIPT:
            lines = [f"**{t('loop_body_script_via_bash', lang)}**", ""]
            if step.command:
                lines.append(f"```bash\n{step.command}\n```")
            lines.append("")
            return "\n".join(lines)

        elif step.type == StepType.AGENT:
            lines = [f"**{t('loop_body_agent_dispatch', lang)}**", ""]
            if step.prompt_file:
                lines.append(f"Prompt file: `{step.prompt_file}`")
            elif step.prompt:
                lines.append(step.prompt)
            lines.append("")
            return "\n".join(lines)

        elif step.type == StepType.INLINE:
            lines = [f"**{t('loop_body_inline_handle', lang)}**", ""]
            if step.prompt_file:
                lines.append(f"Follow instructions in: `{step.prompt_file}`")
            elif step.prompt:
                lines.append(step.prompt)
            lines.append("")
            return "\n".join(lines)

        elif step.type == StepType.LOOP:
            logger.warning(
                f"Nested loop in body step '{step.id}' is not supported — skipping."
            )
            return f"> Nested loop not supported — skipping step '{step.id}'.\n\n"

        return ""

    def _render_body_step_output(self, step: Step, lang: str) -> str:
        """Render output files for a body step."""
        if not step.output:
            return ""
        lines = [f"**{t('output_files', lang)}**"]
        for output_def in step.output:
            lines.append(f"- `{output_def.file}` (schema: {output_def.schema})")
        lines.append("")
        return "\n".join(lines)

    def _render_body_step_quality_check(self, step: Step, lang: str) -> str:
        """Render quality check as inline gate for a body step."""
        qc = step.quality_check
        if qc is None:
            return ""
        blocking_label = (
            t("quality_check_blocking", lang)
            if qc.blocking
            else t("quality_check_non_blocking", lang)
        )
        lines = [f"**Quality Check ({blocking_label}):**"]
        if qc.review_prompt:
            lines.append(qc.review_prompt)
        if qc.rules:
            for rule in qc.rules:
                lines.append(f"- {rule}")
        if qc.blocking:
            lines.append("")
            lines.append("> Do NOT proceed past this body step until quality check passes.")
        lines.append("")
        return "\n".join(lines)

    def _render_post_iteration(self, step: Step, ctx: RenderContext) -> str:
        """Render the post-iteration goal-check and loop control rules."""
        lang = ctx.lang
        lines = [
            f"### {t('loop_after_each_header', lang)}",
            "",
            t("loop_goal_check_dispatch", lang),
            "",
            self._render_goal_check_prompt(step, ctx),
            "",
            "**Loop control:**",
            "",
            f"1. {t('loop_goal_met_action', lang)}",
            f"2. {t('loop_goal_not_met_action', lang)}",
            f"3. {t('loop_max_reached_action', lang)}",
            "",
            t("loop_iteration_history", lang),
        ]
        return "\n".join(lines)

    def _render_goal_check_prompt(self, step: Step, ctx: RenderContext) -> str:
        """Render the goal-check sub-agent prompt template."""
        lang = ctx.lang

        # Collect evidence files from body step outputs
        evidence_lines: list[str] = []
        if step.body:
            for body_step in topological_sort(step.body):
                if body_step.output:
                    for out in body_step.output:
                        evidence_lines.append(
                            f"- Read `{out.file}` (schema: `{out.schema}`)"
                        )

        evidence = (
            "\n".join(evidence_lines)
            if evidence_lines
            else "- Review all output files from body steps"
        )

        return f"""```
You are a goal evaluator. Determine if the loop goal has been met.

**Goal:** {step.goal}

**Evidence files:**
{evidence}

**Instructions:**
1. Read the evidence files
2. Check if the goal condition is definitively satisfied
3. Return a structured verdict:

{t('loop_goal_check_schema', lang)}

**Rules:**
- Only conclude goal_met: true when the condition is definitively satisfied
- Be specific in summary — mention counts, file names, error types
```"""

    def _render_state_management(self, step: Step, lang: str) -> str:
        """Render iteration_history.json state management instructions."""
        return f"""### {t('loop_state_header', lang)}

**iteration_history.json** — maintain this file throughout the loop:

1. {t('loop_state_init', lang)}
2. {t('loop_state_inject', lang)}
3. {t('loop_state_append', lang)}
4. {t('loop_state_keep', lang)}"""

    def _render_execution(self, step: Step, ctx: RenderContext) -> str:
        """Not used — render() is overridden."""
        return ""
