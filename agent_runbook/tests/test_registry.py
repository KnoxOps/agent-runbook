"""Tests for the StrategyRegistry that maps step types to strategies."""

import pytest

from agent_runbook.context import RenderContext
from agent_runbook.registry import StrategyRegistry, default_registry
from agent_runbook.schema import Step, StepType
from agent_runbook.strategies.agent import AgentStepStrategy
from agent_runbook.strategies.checkpoint import CheckpointScriptStrategy
from agent_runbook.strategies.inline import InlineStepStrategy
from agent_runbook.strategies.script import ScriptStepStrategy


@pytest.fixture
def registry():
    """Create a default registry for testing."""
    return default_registry()


def test_select_inline_step(registry):
    """Test selecting strategy for inline step without checkpoint."""
    step = Step(
        id="step-1",
        type=StepType.INLINE,
        depends_on=[],
        prompt="This is an inline prompt",
    )

    strategies = registry.select(step)

    assert len(strategies) == 1
    assert isinstance(strategies[0], InlineStepStrategy)


def test_select_agent_step(registry):
    """Test selecting strategy for agent step."""
    step = Step(
        id="step-2",
        type=StepType.AGENT,
        depends_on=[],
        prompt="path/to/prompt.md",
    )

    strategies = registry.select(step)

    assert len(strategies) == 1
    assert isinstance(strategies[0], AgentStepStrategy)


def test_select_script_step(registry):
    """Test selecting strategy for script step."""
    step = Step(
        id="step-3",
        type=StepType.SCRIPT,
        depends_on=[],
        command="echo 'hello'",
    )

    strategies = registry.select(step)

    assert len(strategies) == 1
    assert isinstance(strategies[0], ScriptStepStrategy)


def test_select_with_checkpoint(registry):
    """Test selecting strategies for step with checkpoint."""
    step = Step(
        id="step-4",
        type=StepType.SCRIPT,
        depends_on=[],
        command="echo 'hello'",
        checkpoint="checkpoints.jsonl",
    )

    strategies = registry.select(step)

    assert len(strategies) == 2
    assert isinstance(strategies[0], ScriptStepStrategy)
    assert isinstance(strategies[1], CheckpointScriptStrategy)


def test_registry_register():
    """Test manually registering a strategy."""
    registry = StrategyRegistry()
    inline_strategy = InlineStepStrategy()

    registry.register(inline_strategy)

    assert InlineStepStrategy in registry._strategies
    assert registry._strategies[InlineStepStrategy] is inline_strategy


def test_default_registry_has_all_strategies():
    """Test that default_registry() returns a fully configured registry."""
    registry = default_registry()

    # All four strategy types should be registered
    assert InlineStepStrategy in registry._strategies
    assert AgentStepStrategy in registry._strategies
    assert ScriptStepStrategy in registry._strategies
    assert CheckpointScriptStrategy in registry._strategies
