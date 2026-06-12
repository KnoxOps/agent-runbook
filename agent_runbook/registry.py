"""Registry that maps step types to rendering strategies."""

from __future__ import annotations

from agent_runbook.schema import Step, StepType
from agent_runbook.strategies.agent import AgentStepStrategy
from agent_runbook.strategies.base import StepStrategy
from agent_runbook.strategies.checkpoint import CheckpointScriptStrategy
from agent_runbook.strategies.inline import InlineStepStrategy
from agent_runbook.strategies.script import ScriptStepStrategy


class StrategyRegistry:
    """Registry that maps step types to their rendering strategies.

    This registry is responsible for selecting the appropriate strategy
    (or strategies) for a given step based on its type and configuration.

    Strategies are registered by class type and can be queried by step.
    If a step has a checkpoint, both the step's type strategy and the
    CheckpointScriptStrategy will be returned.
    """

    def __init__(self) -> None:
        """Initialize an empty strategy registry."""
        self._strategies: dict[type, StepStrategy] = {}

    def register(self, strategy: StepStrategy) -> None:
        """Register a strategy in the registry.

        Args:
            strategy: The strategy instance to register.
                     Will be stored by its class type as the key.
        """
        self._strategies[type(strategy)] = strategy

    def select(self, step: Step) -> list[StepStrategy]:
        """Select strategies for a step.

        Returns the strategy for the step's type. If the step has a
        checkpoint, also includes CheckpointScriptStrategy.

        Args:
            step: The step to select strategies for.

        Returns:
            A list of strategies applicable to this step.
            Usually contains 1 strategy (the type's strategy),
            or 2 if the step has a checkpoint.
        """
        strategies: list[StepStrategy] = []

        # Map step type to its strategy
        if step.type == StepType.INLINE:
            strategies.append(self._strategies[InlineStepStrategy])
        elif step.type == StepType.AGENT:
            strategies.append(self._strategies[AgentStepStrategy])
        elif step.type == StepType.SCRIPT:
            strategies.append(self._strategies[ScriptStepStrategy])

        # Add checkpoint strategy if step has a checkpoint
        if step.checkpoint and CheckpointScriptStrategy in self._strategies:
            strategies.append(self._strategies[CheckpointScriptStrategy])

        return strategies


def default_registry() -> StrategyRegistry:
    """Create and return a pre-configured registry with all strategies.

    This is the convenience function for creating a fully initialized
    registry ready for use.

    Returns:
        A StrategyRegistry with all four strategies registered:
        - InlineStepStrategy
        - AgentStepStrategy
        - ScriptStepStrategy
        - CheckpointScriptStrategy
    """
    registry = StrategyRegistry()
    registry.register(InlineStepStrategy())
    registry.register(AgentStepStrategy())
    registry.register(ScriptStepStrategy())
    registry.register(CheckpointScriptStrategy())
    return registry
