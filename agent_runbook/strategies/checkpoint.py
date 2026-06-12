"""CheckpointScriptStrategy: generates checkpoint management scripts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from agent_runbook.context import RenderContext
from agent_runbook.schema import Step


@dataclass
class CheckpointScript:
    """A checkpoint script with filename and content."""

    filename: str
    content: str


class CheckpointScriptStrategy:
    """Strategy for generating checkpoint management scripts.

    Uses Jinja2 templates from the templates/scripts/ directory to render
    the 4 checkpoint scripts: init, pending, mark_done, and merge.
    """

    def __init__(self) -> None:
        """Initialize the checkpoint script strategy."""
        # Set up Jinja2 environment to load templates
        template_dir = Path(__file__).parent.parent / "templates" / "scripts"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,
        )

    def generate_scripts(self, step: Step, ctx: RenderContext) -> list[CheckpointScript]:
        """Generate checkpoint scripts for a step.

        Args:
            step: The step to generate checkpoint scripts for.
            ctx: The rendering context.

        Returns:
            A list of CheckpointScript objects. Empty if step has no checkpoint.
        """
        if not step.checkpoint:
            return []

        checkpoint_file = step.checkpoint
        item_key = ""
        if step.parallel and step.parallel.item_key:
            item_key = step.parallel.item_key

        # Template context
        template_context = {
            "checkpoint_file": checkpoint_file,
            "item_key": item_key,
            "step_id": step.id,
        }

        scripts = []

        # Load and render the 4 checkpoint templates
        template_files = [
            ("checkpoint_init.py.j2", "checkpoint_init.py"),
            ("checkpoint_pending.py.j2", "checkpoint_pending.py"),
            ("checkpoint_mark_done.py.j2", "checkpoint_mark_done.py"),
            ("checkpoint_merge.py.j2", "checkpoint_merge.py"),
        ]

        for template_name, output_name in template_files:
            try:
                template = self.env.get_template(template_name)
                content = template.render(**template_context)
                # Prefix with step_id to avoid filename collisions across steps
                scripts.append(CheckpointScript(filename=f"{step.id}_{output_name}", content=content))
            except Exception:
                # If template rendering fails, still include a placeholder
                scripts.append(
                    CheckpointScript(
                        filename=f"{step.id}_{output_name}",
                        content=f"# Placeholder script: {output_name}\n"
                        f"# Could not render template {template_name}",
                    )
                )

        return scripts
