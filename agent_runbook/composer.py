"""Composer: assembles rendered step sections into a complete SKILL.md file."""

from dataclasses import dataclass, field
from typing import Any, Optional

from .i18n import t
from .schema import Runbook


def _escape_md_table(text: str) -> str:
    """Escape special characters for markdown table cell content.

    Escapes pipe characters (|) which would break markdown table structure.

    Args:
        text: The text to escape.

    Returns:
        Escaped text safe for markdown table cells.
    """
    return text.replace("|", r"\|")


@dataclass
class Section:
    """A rendered section of a step in the execution flow."""

    step_id: str
    """Unique identifier for the step."""

    order: int
    """Order of this section in the execution flow."""

    content: str
    """Rendered content (markdown) for this section."""

    is_branch_point: bool = False
    """Whether this section represents a branch decision point."""

    branches: Optional[list[Any]] = None
    """Optional list of branches (Branch objects from dag.py if available)."""

    dependencies: Optional[list[str]] = None
    """Optional list of dependencies (for parallel detection)."""


class Composer:
    """Assembles rendered step sections into a complete SKILL.md file."""

    def compose(self, runbook: Runbook, sections: list[Section], lang: str = "en") -> str:
        """Assemble a complete SKILL.md file from a runbook and sections.

        The output includes:
        1. YAML frontmatter (name, description)
        2. Overview section
        3. Input Parameters table (if any)
        4. Execution Flow (if sections provided)
        5. Error Handling section (if defined)

        Args:
            runbook: The Runbook model containing metadata and error handling rules.
            sections: List of Section objects representing rendered steps.
            lang: Language code for generated text ("en" or "zh").

        Returns:
            Complete SKILL.md content as a string.
        """
        parts = []

        # 1. Frontmatter
        parts.append(self._render_frontmatter(runbook))

        # 2. Input Parameters (if any)
        if runbook.input_params:
            parts.append(self._render_input_parameters(runbook.input_params, lang))

        # 4. Execution Flow (if sections provided)
        if sections:
            parts.append(self._render_execution_flow(sections, lang))

        # 5. Error Handling (if any)
        if runbook.error_handling:
            parts.append(self._render_error_handling(runbook.error_handling, lang))

        return "\n\n".join(parts)

    def _render_frontmatter(self, runbook: Runbook) -> str:
        """Render YAML frontmatter with runbook metadata."""
        desc = runbook.description
        # Use YAML folded block scalar (>-) to preserve plain-text description
        # without quoting issues. Multi-line descriptions get proper indentation.
        if "\n" in desc:
            desc_lines = desc.split("\n")
            desc_formatted = ">-" + "".join(f"\n  {line}" for line in desc_lines)
        else:
            desc_formatted = ">-\n  " + desc
        lines = [
            "---",
            f"name: {runbook.name}",
            f"description: {desc_formatted}",
            "user-invocable: true",
            "---",
        ]
        return "\n".join(lines)

    def _render_overview(self, runbook: Runbook, lang: str = "en") -> str:
        """Render the Overview section.

        Args:
            runbook: The runbook containing the description to render.
            lang: Language code for the section heading.

        Returns:
            Overview section markdown.
        """
        return f"## {t('overview', lang)}\n\n{runbook.description}"

    def _render_input_parameters(self, input_params: list, lang: str = "en") -> str:
        """Render the Input Parameters section as a table.

        Args:
            input_params: List of input parameters to render.
            lang: Language code for the section heading.

        Returns:
            Input Parameters section markdown.
        """
        lines = [f"## {t('input_params', lang)}\n"]
        lines.append("| Name | Type | Required | Description |")
        lines.append("|------|------|----------|-------------|")

        for param in input_params:
            required = "Yes" if param.required else "No"
            # Escape special characters in table cells
            name = _escape_md_table(param.name)
            param_type = _escape_md_table(param.type)
            description = _escape_md_table(param.description)
            lines.append(f"| {name} | {param_type} | {required} | {description} |")

        return "\n".join(lines)

    def _render_task_context_init(self, sections: list[Section], lang: str = "en") -> str:
        """Render the Task Context initialization block.

        Generates the JSON example with all step IDs pre-populated as pending.

        Args:
            sections: List of sections representing all steps.
            lang: Language code for generated text.

        Returns:
            Task Context section markdown.
        """
        sorted_sections = sorted(sections, key=lambda s: s.order)
        non_branch_sections = [s for s in sorted_sections if not s.is_branch_point]

        step_lines = []
        for section in non_branch_sections:
            step_lines.append(f'    "{section.step_id}": "pending"')
        steps_json = ",\n".join(step_lines)

        return (
            f"### {t('task_context', lang)}\n\n"
            f"{t('task_context_init', lang)}\n\n"
            "```json\n"
            "{\n"
            '  "task_id": "<task_id from input>",\n'
            '  "current_step": 0,\n'
            '  "current_step_id": null,\n'
            '  "status": "running",\n'
            '  "steps": {\n'
            f"{steps_json}\n"
            "  },\n"
            '  "updated_at": "<ISO timestamp>"\n'
            "}\n"
            "```\n\n"
            f"{t('task_context_update', lang)}"
        )

    def _render_execution_flow(self, sections: list[Section], lang: str = "en") -> str:
        """Render the Execution Flow section with all steps.

        Args:
            sections: List of sections to render in order.
            lang: Language code for generated text.

        Returns:
            Execution Flow section markdown.
        """
        lines = [f"## {t('execution_flow', lang)}\n"]

        # Task Context initialization block before the first step
        lines.append(self._render_task_context_init(sections, lang))
        lines.append("")  # blank line separator

        # Sort sections by order
        sorted_sections = sorted(sections, key=lambda s: s.order)

        # Build a map of dependency-signature → steps for detecting parallel groups.
        # Steps with identical depends_on (excluding branch points) are parallel siblings.
        from collections import defaultdict

        dep_sig_to_orders: dict[tuple, list[int]] = defaultdict(list)
        for section in sorted_sections:
            if not section.is_branch_point and section.dependencies is not None:
                sig = tuple(sorted(section.dependencies))
                if sig:  # skip empty signature (steps with no dependencies are not parallel siblings)
                    dep_sig_to_orders[sig].append(section.order)

        # Find which orders are part of parallel groups (≥2 steps sharing same depends_on)
        parallel_orders: dict[int, list[int]] = {}  # order → list of all orders in this parallel group
        for sig, orders in dep_sig_to_orders.items():
            if len(orders) > 1:
                for order in orders:
                    parallel_orders[order] = sorted(orders)

        # Track which parallel groups we've already added annotations for
        annotated_parallel_groups: set[tuple] = set()

        # Render sections in order
        for section in sorted_sections:
            # If this section is part of a parallel group and we haven't annotated it yet,
            # add the annotation before the group
            if section.order in parallel_orders:
                group_orders = tuple(parallel_orders[section.order])
                if group_orders not in annotated_parallel_groups:
                    # Find all sections in this parallel group
                    group_sections = [s for s in sorted_sections if s.order in group_orders]
                    step_ids = [(s.order, s.step_id) for s in group_sections]
                    if len(step_ids) == 2:
                        annotation = t("parallel_note", lang, o1=step_ids[0][0], id1=step_ids[0][1], o2=step_ids[1][0], id2=step_ids[1][1])
                    else:
                        step_ids_str = " and ".join(f"{t('step_label', lang, order=o, id=i)} ({i})" for o, i in step_ids)
                        annotation = t("parallel_note_multi", lang, steps=step_ids_str)
                    lines.append(f"> **{t('note_label', lang)}:** {annotation}\n")
                    annotated_parallel_groups.add(group_orders)

            if section.is_branch_point:
                lines.append(f"### {t('branch_decision_header', lang, id=section.step_id)}\n")
                lines.append(section.content)
            else:
                lines.append(f"### {t('step_header', lang, order=section.order, id=section.step_id)}\n")
                lines.append(section.content)

        return "\n".join(lines)

    def _render_error_handling(self, error_handling: list, lang: str = "en") -> str:
        """Render the Error Handling section."""
        lines = [f"## {t('error_handling', lang)}\n"]

        for rule in error_handling:
            lines.append(f"### {rule.scenario}\n")
            lines.append(f"{rule.handling}\n")

        return "\n".join(lines)
