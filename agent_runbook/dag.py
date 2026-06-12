"""Kahn DAG processor: topological sort, cycle detection, and branch detection."""

from collections import deque
from dataclasses import dataclass, field

from .schema import Step


class CycleDetectedError(Exception):
    """Raised when topological_sort detects a cycle in the DAG."""

    def __init__(self, cycle_members: list[str]) -> None:
        self.cycle_members = cycle_members
        members_str = ", ".join(cycle_members)
        super().__init__(f"Cycle detected in DAG: {members_str}")


@dataclass
class Branch:
    """A single branch in a BranchGroup with its condition and steps."""

    condition: str
    steps: list[Step] = field(default_factory=list)


@dataclass
class BranchGroup:
    """A set of branches that diverge from a common branch_point step."""

    branch_point: str
    branches: list[Branch] = field(default_factory=list)


def topological_sort(steps: list[Step]) -> list[Step]:
    """Sort steps into a topological order using Kahn's algorithm.

    Args:
        steps: The steps to sort.

    Returns:
        A list of steps in valid topological order (dependencies before dependents).

    Raises:
        CycleDetectedError: If a cycle exists in the dependency graph.
    """
    step_map: dict[str, Step] = {s.id: s for s in steps}
    in_degree: dict[str, int] = {s.id: 0 for s in steps}
    adjacency: dict[str, list[str]] = {s.id: [] for s in steps}

    for s in steps:
        for dep in s.depends_on:
            adjacency[dep].append(s.id)
            in_degree[s.id] += 1

    # Kahn's BFS: start with all nodes that have in-degree 0
    queue: deque[str] = deque()
    for sid, deg in in_degree.items():
        if deg == 0:
            queue.append(sid)

    sorted_ids: list[str] = []
    while queue:
        current = queue.popleft()
        sorted_ids.append(current)
        for neighbor in adjacency.get(current, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Cycle detection: if we did not visit every node, remaining nodes form a cycle
    if len(sorted_ids) != len(steps):
        remaining = [s.id for s in steps if in_degree[s.id] > 0]
        # Defensive edge case: if remaining is empty (shouldn't happen), report all steps
        raise CycleDetectedError(remaining if remaining else [s.id for s in steps])

    return [step_map[sid] for sid in sorted_ids]


def detect_branches(steps: list[Step]) -> list[BranchGroup]:
    """Detect branching points in the DAG.

    A branch occurs when a step has multiple dependents that all carry a
    `condition` field, indicating they are mutually exclusive execution paths.

    Steps with multiple dependents that lack conditions are treated as parallel
    dependencies, not branches.

    Note: This function collects only immediate dependents (direct children),
    not full subtrees. Each branch captures its direct child step.

    Args:
        steps: The steps to analyze.

    Returns:
        A list of BranchGroup objects, each describing a branch point and its branches.
    """
    # Build a map: step_id -> list of steps that depend on it
    dependents_map: dict[str, list[Step]] = {}
    for s in steps:
        for dep in s.depends_on:
            if dep not in dependents_map:
                dependents_map[dep] = []
            dependents_map[dep].append(s)

    branch_groups: list[BranchGroup] = []
    for branch_point, children in dependents_map.items():
        if len(children) < 2:
            continue
        # A branch group requires ALL children to have a condition
        if all(child.condition is not None for child in children):
            branches = [Branch(condition=c.condition, steps=[c]) for c in children]  # type: ignore[arg-type]
            branch_groups.append(BranchGroup(branch_point=branch_point, branches=branches))

    return branch_groups
