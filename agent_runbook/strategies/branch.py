"""BranchingStrategy: renders branch decision logic for conditional execution."""

from __future__ import annotations

from agent_runbook.context import RenderContext
from agent_runbook.dag import BranchGroup


class BranchingStrategy:
    """Strategy for rendering branch decision logic.

    This strategy is not a StepStrategy subclass; it takes a BranchGroup
    and renders the decision logic and conditional branches.
    """

    def __init__(self, branch_group: BranchGroup) -> None:
        """Initialize the branching strategy.

        Args:
            branch_group: The BranchGroup defining the branches.
        """
        self.branch_group = branch_group

    def render(self, ctx: RenderContext) -> str:
        """Render the branch decision logic.

        Args:
            ctx: The rendering context.

        Returns:
            Rendered branch decision markdown.
        """
        lines = [
            "### Branch Decision\n",
            "Based on `{}.json`:\n".format(self.branch_group.branch_point),
        ]

        for branch in self.branch_group.branches:
            # Extract step names from the branch
            step_names = ", ".join([s.id for s in branch.steps])

            lines.append(
                "- If {}: Run Step {}\n".format(branch.condition, step_names)
            )

        return "".join(lines)
