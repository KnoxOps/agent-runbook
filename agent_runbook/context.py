"""RenderContext for step rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_runbook.schema import Runbook, Step, BranchGroup


@dataclass
class RenderContext:
    """Context passed to step rendering strategies.

    Attributes:
        runbook: The parent Runbook being rendered (may be None during testing).
        execution_order: List of steps in execution order.
        branch_groups: Mapping of branch group names to their definitions.
        runbook_dir: Directory path where the runbook is located.
        lang: Language code for generated text ("en" or "zh"). Defaults to "en".
    """

    runbook: Runbook | None
    execution_order: list[Step]
    branch_groups: dict[str, BranchGroup]
    runbook_dir: str
    lang: str = "en"
