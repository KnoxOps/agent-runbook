"""ParallelStepStrategy: wraps step content with batch-split logic for parallel execution."""

from __future__ import annotations

from agent_runbook.context import RenderContext
from agent_runbook.schema import Step


class ParallelStepStrategy:
    """Strategy for wrapping step content with parallel execution instructions.

    This strategy is not a StepStrategy subclass; instead it wraps the output of
    another strategy's render() method with batch-split and checkpoint logic.
    """

    def wrap(self, step_content: str, step: Step, ctx: RenderContext) -> str:
        """Wrap step content with parallel execution instructions.

        Args:
            step_content: The original step execution content.
            step: The step being rendered.
            ctx: The rendering context.

        Returns:
            Step content wrapped with parallel execution instructions.
        """
        if not step.parallel or not step.parallel.enabled:
            return step_content

        max_instances = step.parallel.max_instances
        item_key = step.parallel.item_key

        # Build parallel execution section
        lines = [
            "#### Parallel Execution (max {} concurrent)\n".format(max_instances),
            "1. Read input file containing items array\n",
            "2. Read checkpoint file, skip already completed items\n",
            "3. Split remaining items by '{}' into at most {} batches\n".format(
                item_key, max_instances
            ),
            "4. Process each batch in parallel\n",
            "5. Merge checkpoint entries from all batches\n",
        ]

        if step.checkpoint:
            lines.append("6. Persist merged checkpoint to {}\n".format(step.checkpoint))

        wrapped_output = (
            "".join(lines)
            + "\n"
            + step_content
        )

        return wrapped_output
