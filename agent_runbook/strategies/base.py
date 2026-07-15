"""Abstract base class for step rendering strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod

from agent_runbook.context import RenderContext
from agent_runbook.i18n import t
from agent_runbook.schema import Step


class StepStrategy(ABC):
    """Abstract base class for rendering different step types.

    Each step type (inline, agent, script) has a concrete strategy that
    implements step-specific rendering logic.
    """

    def render(self, step: Step, ctx: RenderContext) -> str:
        """Render a step into a markdown document.

        Joins all sections (header, input, execution, output, checkpoint)
        into a single markdown document.

        Args:
            step: The step to render.
            ctx: The rendering context.

        Returns:
            Rendered step content as a markdown string.
        """
        sections = []

        # Header section (always present)
        header = self._render_header(step, ctx)
        if header:
            sections.append(header)

        # Input section (present if step has inputs)
        input_section = self._render_input(step, ctx)
        if input_section:
            sections.append(input_section)

        # Execution section (always present, subclass-specific)
        execution = self._render_execution(step, ctx)
        if execution:
            sections.append(execution)

        # Output section (present if step has outputs)
        output_section = self._render_output(step, ctx)
        if output_section:
            sections.append(output_section)

        # Checkpoint section (present if step has checkpoint)
        checkpoint_section = self._render_checkpoint(step, ctx)
        if checkpoint_section:
            sections.append(checkpoint_section)

        # Quality Check section (present if step has quality_check)
        quality_check_section = self._render_quality_check(step, ctx)
        if quality_check_section:
            sections.append(quality_check_section)

        # Progress tracking section (always present)
        sections.append(self._render_progress_tracking(step, ctx.lang))

        return "\n\n".join(sections)

    def _render_header(self, step: Step, ctx: RenderContext) -> str:
        """Render the header section with step metadata.

        Note: The step heading (### Step: {id}) is rendered by the Composer,
        not by the strategy. This method renders only metadata content.

        Args:
            step: The step to render.
            ctx: The rendering context.

        Returns:
            Header metadata markdown or empty string.
        """
        parts = []

        if step.type:
            parts.append(f"**{t('type_label', ctx.lang)}** {step.type.value}")

        if step.description:
            parts.append(f"**{t('description_label', ctx.lang)}** {step.description}")

        return "\n".join(parts)

    def _render_input(self, step: Step, ctx: RenderContext) -> str:
        """Render the input section.

        Only rendered if the step has input references.

        Args:
            step: The step to render.
            ctx: The rendering context.

        Returns:
            Input section markdown or empty string.
        """
        if not step.input:
            return ""

        lines = [f"## {t('input_files', ctx.lang)}"]
        for input_ref in step.input:
            if input_ref.file:
                if input_ref.from_step and input_ref.schema:
                    from_label = t("from_step", ctx.lang, step_id=input_ref.from_step)
                    lines.append(
                        f"- `{input_ref.file}` ({from_label},"
                        f" schema: {input_ref.schema})"
                    )
                elif input_ref.from_step:
                    from_label = t("from_step", ctx.lang, step_id=input_ref.from_step)
                    lines.append(f"- `{input_ref.file}` ({from_label})")
                else:
                    lines.append(f"- `{input_ref.file}`")
            else:
                if input_ref.schema:
                    lines.append(f"- **{t('schema_label', ctx.lang)}** {input_ref.schema}")
                if input_ref.from_step:
                    from_label = t("from_step", ctx.lang, step_id=input_ref.from_step)
                    lines.append(f"  - {from_label}")

        return "\n".join(lines)

    @abstractmethod
    def _render_execution(self, step: Step, ctx: RenderContext) -> str:
        """Render the execution section (step-type specific).

        This method must be implemented by subclasses.

        Args:
            step: The step to render.
            ctx: The rendering context.

        Returns:
            Execution section markdown.
        """

    def _render_output(self, step: Step, ctx: RenderContext) -> str:
        """Render the output section.

        Only rendered if the step has outputs. Instructs the agent to read the
        schema file first and produce output that strictly conforms to it
        (exact field names, required fields, no extra fields).

        Args:
            step: The step to render.
            ctx: The rendering context.

        Returns:
            Output section markdown or empty string.
        """
        if not step.output:
            return ""

        lines = ["## Output"]
        lines.append("")
        lines.append(t("output_schema_instruction", ctx.lang))
        lines.append("")
        for output_def in step.output:
            lines.append(f"- **{t('schema_label', ctx.lang)}** {output_def.schema}")
            lines.append(f"  - **{t('file_label', ctx.lang)}** {output_def.file}")
            lines.append(f"  - {t('validate_command', ctx.lang, file=output_def.file, schema=output_def.schema)}")

        return "\n".join(lines)

    def _render_checkpoint(self, step: Step, ctx: RenderContext) -> str:
        """Render the checkpoint section.

        Only rendered if the step has a checkpoint defined.

        Args:
            step: The step to render.
            ctx: The rendering context.

        Returns:
            Checkpoint section markdown or empty string.
        """
        if not step.checkpoint:
            return ""

        return f"## Checkpoint\n\n{step.checkpoint}"

    def _render_progress_tracking(self, step: Step, lang: str = "en") -> str:
        """Render the progress tracking section.

        Always rendered to instruct the agent to update task_context.json
        after completing the step.

        Args:
            step: The step to render.
            lang: Language code for generated text.

        Returns:
            Progress tracking section markdown.
        """
        heading = t("progress_tracking", lang)
        instruction = t("progress_instruction", lang)
        set_step = t("progress_set_step", lang)
        set_status = t("progress_set_status", lang, step_id=step.id)
        return (
            f"### {heading}\n\n"
            f"{instruction}\n"
            f'- {set_step} `"{step.id}"`\n'
            f'- {set_status} `"completed"`'
        )

    def _render_quality_check(self, step: Step, ctx: RenderContext) -> str:
        """Render the quality check section inline within the parent step.

        Only rendered if the step has a quality_check defined.
        The quality check is presented as a sub-section within the parent
        step's content, not as a separate step.

        Args:
            step: The step to render.
            ctx: The rendering context.

        Returns:
            Quality Check section markdown or empty string.
        """
        if step.quality_check is None:
            return ""

        qc = step.quality_check
        lang = ctx.lang
        output_file = qc.output_file or f"quality_report_{step.id}.json"

        lines = [f"#### {t('quality_check_heading', lang)}"]

        # Review instructions
        if qc.review_prompt:
            lines.append(qc.review_prompt)

        # Check rules
        if qc.rules:
            lines.append("")
            rules_text = "\n".join(f"  - {r}" for r in qc.rules)
            lines.append(f"{t('check_rules', lang)}\n{rules_text}")

        # Output
        lines.append("")
        lines.append(
            f"Output: `{output_file}` with result: passed/warning/issues"
        )

        # Blocking / non-blocking note
        lines.append("")
        if qc.blocking:
            lines.append(f"> **{t('quality_check_blocking', lang)}**: {t('qc_blocking_note', lang)}")
        else:
            lines.append(f"> **{t('quality_check_non_blocking', lang)}**: {t('qc_non_blocking_note', lang)}")

        return "\n".join(lines)
