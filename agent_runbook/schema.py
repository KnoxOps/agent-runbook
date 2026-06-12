"""Pydantic schema models for runbook YAML parsing and validation."""

from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, model_validator


class StepType(str, Enum):
    """Supported step types."""

    INLINE = "inline"
    AGENT = "agent"
    SCRIPT = "script"


class InputParam(BaseModel):
    """A user-provided input parameter for the runbook."""

    name: str
    type: str  # string / number / boolean
    required: bool = True
    description: str = ""


class StepInputRef(BaseModel):
    """Reference to an input schema, optionally sourced from a preceding step."""

    model_config = {"protected_namespaces": ()}

    schema: str  # Required: path to schema file
    from_step: Optional[str] = None
    file: Optional[str] = None  # Optional: filename of the input file


class StepOutputDef(BaseModel):
    """Definition of a step's output: schema + file path."""

    model_config = {"protected_namespaces": ()}

    schema: str
    file: str


class ParallelConfig(BaseModel):
    """Configuration for parallel execution of a step."""

    enabled: bool = False
    max_instances: int = 1
    item_key: str = ""


class QualityCheckConfig(BaseModel):
    """Configuration for an auto-generated quality check step.

    When set on a step, the generator synthesizes a review step
    that runs after the parent step completes.

    Attributes:
        blocking: If True, the next step in the flow depends on the quality check
            passing. If False, the quality check runs in parallel with the next step.
        review_prompt: Instructions for reviewing the parent step's output.
        rules: Natural language check rules.
        output_file: Optional custom output filename for the quality check result.
    """

    blocking: bool = False
    review_prompt: Optional[str] = None
    rules: list[str] = []
    output_file: Optional[str] = None


class Step(BaseModel):
    """A single step in the runbook DAG."""

    id: str
    type: StepType = StepType.INLINE
    description: str = ""
    prompt: Optional[str] = None  # Inline prompt text (mutually exclusive with prompt_file)
    prompt_file: Optional[str] = None  # Path to prompt file (mutually exclusive with prompt)
    command: Optional[str] = None  # Required for script
    input: list[StepInputRef] = []
    output: list[StepOutputDef] = []
    depends_on: list[str]
    parallel: Optional[ParallelConfig] = None
    checkpoint: Optional[str] = None
    condition: Optional[str] = None
    quality_check: Optional[QualityCheckConfig] = None

    @model_validator(mode="after")
    def validate_step_type_requirements(self) -> "Step":
        """Validate that each step type has its required fields.

        For inline and agent steps: exactly one of prompt or prompt_file must be set.
        For script steps: command is required.
        """
        if self.type != StepType.SCRIPT:
            # Either prompt or prompt_file must be set, but not both
            if self.prompt is None and self.prompt_file is None:
                raise ValueError(
                    f"Step '{self.id}': prompt or prompt_file is required for {self.type.value} steps"
                )
            if self.prompt is not None and self.prompt_file is not None:
                raise ValueError(
                    f"Step '{self.id}': prompt and prompt_file are mutually exclusive"
                )
        if self.type == StepType.SCRIPT and self.command is None:
            raise ValueError(
                f"Step '{self.id}': command is required for script steps"
            )
        return self


class ErrorHandlingRule(BaseModel):
    """A business-level error handling rule declared in the runbook."""

    scenario: str
    handling: str


class Runbook(BaseModel):
    """Top-level runbook model representing a complete runbook definition."""

    name: str
    description: str
    input_params: list[InputParam] = []
    steps: list[Step]
    error_handling: list[ErrorHandlingRule] = []

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Runbook":
        """Parse a runbook YAML file into a Runbook model.

        Args:
            path: Path to the runbook YAML file.

        Returns:
            A validated Runbook instance.

        Raises:
            FileNotFoundError: If the YAML file does not exist.
            pydantic.ValidationError: If the YAML content fails schema validation.
        """
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            raise ValueError(f"Runbook YAML file is empty: {path}")
        return cls.model_validate(data)
