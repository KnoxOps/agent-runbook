"""Tests for BranchingStrategy."""

from __future__ import annotations

import pytest

from agent_runbook.context import RenderContext
from agent_runbook.schema import Step, StepType
from agent_runbook.dag import BranchGroup, Branch
from agent_runbook.strategies.branch import BranchingStrategy


class TestBranchingStrategy:
    """Tests for BranchingStrategy."""

    def test_branch_renders_conditions(self):
        """BranchGroup with 2 branches should render conditions and references."""
        # Create two branches with different conditions
        step_aws = Step(
            id="deploy_aws",
        depends_on=[],
            type=StepType.SCRIPT,
            description="Deploy to AWS",
            command="deploy_aws.sh",
            condition="provider is aws",
        )

        step_k8s = Step(
            id="deploy_k8s",
        depends_on=[],
            type=StepType.SCRIPT,
            description="Deploy to K8s",
            command="deploy_k8s.sh",
            condition="provider is k8s",
        )

        branch_group = BranchGroup(
            branch_point="choose_provider",
            branches=[
                Branch(condition="provider is aws", steps=[step_aws]),
                Branch(condition="provider is k8s", steps=[step_k8s]),
            ],
        )

        ctx = RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
        )

        strategy = BranchingStrategy(branch_group)
        output = strategy.render(ctx)

        # Verify output contains both conditions and step references
        assert "provider is aws" in output
        assert "provider is k8s" in output
        assert "deploy_aws" in output or "aws" in output.lower()
        assert "deploy_k8s" in output or "k8s" in output.lower()
        assert len(output) > 0

    def test_branch_renders_branch_point_file(self):
        """BranchingStrategy should reference the decision file."""
        step1 = Step(
            id="step1",
        depends_on=[],
            type=StepType.SCRIPT,
            command="cmd1.sh",
            condition="condition_a",
        )

        step2 = Step(
            id="step2",
        depends_on=[],
            type=StepType.SCRIPT,
            command="cmd2.sh",
            condition="condition_b",
        )

        branch_group = BranchGroup(
            branch_point="decision_point",
            branches=[
                Branch(condition="condition_a", steps=[step1]),
                Branch(condition="condition_b", steps=[step2]),
            ],
        )

        ctx = RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
        )

        strategy = BranchingStrategy(branch_group)
        output = strategy.render(ctx)

        # Should reference the branch point file (decision_point.json or similar)
        assert "decision_point" in output or ".json" in output
        assert "Branch Decision" in output or "branch" in output.lower()
