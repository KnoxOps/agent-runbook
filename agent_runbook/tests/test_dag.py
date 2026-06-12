"""Tests for DAG processor: topological sort, cycle detection, branch detection."""

import pytest

from agent_runbook.dag import (
    Branch,
    BranchGroup,
    CycleDetectedError,
    detect_branches,
    topological_sort,
)
from agent_runbook.schema import Step, StepType


def make_step(step_id: str, depends_on: list[str] | None = None, condition: str | None = None) -> Step:
    """Create a minimal Step for DAG testing."""
    return Step(
        id=step_id,
        type=StepType.INLINE,
        prompt="test prompt",
        depends_on=depends_on or [],
        condition=condition,
    )


class TestTopologicalSort:
    """Tests for topological_sort via Kahn's algorithm."""

    def test_empty_graph_sort(self):
        """Empty graph should return empty list."""
        result = topological_sort([])
        assert result == []

    def test_serial_chain_sort(self):
        """A -> B -> C linear chain should return [A, B, C]."""
        A = make_step("A")
        B = make_step("B", depends_on=["A"])
        C = make_step("C", depends_on=["B"])

        result = topological_sort([A, B, C])
        ids = [s.id for s in result]

        assert ids == ["A", "B", "C"]

    def test_parallel_deps_sort(self):
        """A has no deps; B and C both depend on A. A must come first."""
        A = make_step("A")
        B = make_step("B", depends_on=["A"])
        C = make_step("C", depends_on=["A"])

        result = topological_sort([A, B, C])
        ids = [s.id for s in result]

        assert ids[0] == "A"
        assert set(ids[1:]) == {"B", "C"}

    def test_cycle_detection(self):
        """A -> B -> C -> A cycle raises CycleDetectedError with cycle members."""
        A = make_step("A", depends_on=["C"])
        B = make_step("B", depends_on=["A"])
        C = make_step("C", depends_on=["B"])

        with pytest.raises(CycleDetectedError) as exc_info:
            topological_sort([A, B, C])

        assert "cycle" in str(exc_info.value).lower()
        # All three members should be listed
        for sid in ("A", "B", "C"):
            assert sid in str(exc_info.value)

    def test_self_reference_is_cycle(self):
        """A depending on itself is a cycle."""
        A = make_step("A", depends_on=["A"])

        with pytest.raises(CycleDetectedError):
            topological_sort([A])

    def test_multi_subgraph(self):
        """Two unrelated chains A->B and C->D should both appear, in-order."""
        A = make_step("A")
        B = make_step("B", depends_on=["A"])
        C = make_step("C")
        D = make_step("D", depends_on=["C"])

        result = topological_sort([A, B, C, D])
        ids = [s.id for s in result]

        # Each chain must have its predecessor before successor
        assert ids.index("A") < ids.index("B")
        assert ids.index("C") < ids.index("D")
        # All four must be present
        assert set(ids) == {"A", "B", "C", "D"}


class TestDetectBranches:
    """Tests for branch detection in the DAG."""

    def test_empty_graph_branches(self):
        """Empty graph should return empty list."""
        result = detect_branches([])
        assert result == []

    def test_detect_branches(self):
        """detect -> scan_aws (condition), scan_k8s (condition) -> summarize."""
        detect = make_step("detect")
        scan_aws = make_step("scan_aws", depends_on=["detect"], condition="provider is aws")
        scan_k8s = make_step("scan_k8s", depends_on=["detect"], condition="provider is k8s")
        summarize = make_step("summarize", depends_on=["scan_aws", "scan_k8s"])

        result = detect_branches([detect, scan_aws, scan_k8s, summarize])

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], BranchGroup)
        assert result[0].branch_point == "detect"
        assert len(result[0].branches) == 2

        branch_conditions = {b.condition for b in result[0].branches}
        assert branch_conditions == {"provider is aws", "provider is k8s"}

        branch_steps = {b.steps[0].id for b in result[0].branches}
        assert branch_steps == {"scan_aws", "scan_k8s"}

    def test_no_branch_without_conditions(self):
        """A -> B and A -> C without conditions is parallel deps, not branches."""
        A = make_step("A")
        B = make_step("B", depends_on=["A"])
        C = make_step("C", depends_on=["A"])

        result = detect_branches([A, B, C])

        assert result == []
