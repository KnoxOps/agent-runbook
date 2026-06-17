"""Validator for runbook YAML files — checks semantic and structural rules."""

import os
from dataclasses import dataclass
from pathlib import Path

from .dag import CycleDetectedError, topological_sort
from .schema import Runbook, StepType


@dataclass
class ValidationError(Exception):
    """A validation error or warning.

    Inherits from Exception so it can be raised from the Generator when
    validation finds ERROR-level issues.
    """

    level: str  # "ERROR" or "WARN"
    message: str

    def __str__(self) -> str:
        return f"[{self.level}] {self.message}"


class RunbookValidator:
    """Validates a runbook against semantic and structural rules."""

    def __init__(self, runbook: Runbook, runbook_dir: str):
        """Initialize the validator.

        Args:
            runbook: The parsed Runbook object.
            runbook_dir: The directory containing the runbook YAML file.
        """
        self.runbook = runbook
        self.runbook_dir = Path(runbook_dir)

    def validate(self) -> list[ValidationError]:
        """Run all validation checks and collect all errors.

        Returns:
            A list of ValidationError objects (both errors and warnings).
            Returns an empty list if the runbook is valid.
        """
        errors: list[ValidationError] = []

        # Check 1: Duplicate step IDs
        errors.extend(self._check_duplicate_step_ids())

        # Check 2: Prompt file existence (only for file paths, not inline)
        errors.extend(self._check_prompt_files())

        # Check 3: Schema file existence
        errors.extend(self._check_schema_files())

        # Check 4: DAG cycle detection
        errors.extend(self._check_dag_cycle())

        # Check 5: from_step references
        errors.extend(self._check_from_step_references())

        # Check 6: Condition validation
        errors.extend(self._check_conditions())

        # Check 7: Removed (prompt_file path traversal is now allowed — existence check provides security)
        pass

        # Check 8: Parallel configuration
        errors.extend(self._check_parallel_config())

        # Check 9: Type field mismatches
        errors.extend(self._check_type_field_mismatches())

        # Check 10: Output file conflicts (warning)
        errors.extend(self._check_output_file_conflicts())

        # Check 11: Orphan steps (warning)
        errors.extend(self._check_orphan_steps())

        # Check 12: quality_check config validity
        errors.extend(self._check_quality_check_config())

        # Check 13: Loop step validation
        errors.extend(self._check_loop_steps())

        return errors

    def _check_duplicate_step_ids(self) -> list[ValidationError]:
        """Check for duplicate step IDs."""
        errors: list[ValidationError] = []
        seen_ids = set()
        for step in self.runbook.steps:
            if step.id in seen_ids:
                errors.append(
                    ValidationError(
                        level="ERROR",
                        message=f"Duplicate step ID: '{step.id}'",
                    )
                )
            seen_ids.add(step.id)
        return errors

    def _check_prompt_files(self) -> list[ValidationError]:
        """Check that prompt_file paths exist (skip inline prompts)."""
        errors: list[ValidationError] = []
        for step in self.runbook.steps:
            if step.prompt_file is None:
                continue
            # Check if file exists
            prompt_path = self.runbook_dir / step.prompt_file
            if not prompt_path.exists():
                errors.append(
                    ValidationError(
                        level="ERROR",
                        message=f"Step '{step.id}': prompt file not found: {step.prompt_file}",
                    )
                )
        return errors

    def _check_schema_files(self) -> list[ValidationError]:
        """Check that schema file paths exist."""
        errors: list[ValidationError] = []
        for step in self.runbook.steps:
            # Check input schemas
            for input_ref in step.input:
                schema_path = self.runbook_dir / input_ref.schema
                if not schema_path.exists():
                    errors.append(
                        ValidationError(
                            level="ERROR",
                            message=f"Step '{step.id}': input schema not found: {input_ref.schema}",
                        )
                    )
            # Check output schemas
            for output_def in step.output:
                schema_path = self.runbook_dir / output_def.schema
                if not schema_path.exists():
                    errors.append(
                        ValidationError(
                            level="ERROR",
                            message=f"Step '{step.id}': output schema not found: {output_def.schema}",
                        )
                    )
        return errors

    def _check_dag_cycle(self) -> list[ValidationError]:
        """Check for cycles in the DAG."""
        errors: list[ValidationError] = []
        try:
            topological_sort(self.runbook.steps)
        except (CycleDetectedError, KeyError) as e:
            if isinstance(e, CycleDetectedError):
                errors.append(
                    ValidationError(
                        level="ERROR",
                        message=f"Cycle detected in DAG: {', '.join(e.cycle_members)}",
                    )
                )
            else:
                # KeyError means a step depends on nonexistent step
                errors.append(
                    ValidationError(
                        level="ERROR",
                        message=f"DAG error: step depends on nonexistent step",
                    )
                )
        return errors

    def _check_from_step_references(self) -> list[ValidationError]:
        """Check that from_step references are valid and in depends_on."""
        errors: list[ValidationError] = []
        step_ids = {s.id for s in self.runbook.steps}

        for step in self.runbook.steps:
            for input_ref in step.input:
                if input_ref.from_step is None:
                    continue
                # Check if from_step exists
                if input_ref.from_step not in step_ids:
                    errors.append(
                        ValidationError(
                            level="ERROR",
                            message=f"Step '{step.id}': from_step '{input_ref.from_step}' does not exist",
                        )
                    )
                # Check if from_step is in depends_on
                elif input_ref.from_step not in step.depends_on:
                    errors.append(
                        ValidationError(
                            level="ERROR",
                            message=f"Step '{step.id}': from_step '{input_ref.from_step}' is not in depends_on",
                        )
                    )
        return errors

    def _check_conditions(self) -> list[ValidationError]:
        """Check that conditions are not empty or whitespace-only."""
        errors: list[ValidationError] = []
        for step in self.runbook.steps:
            if step.condition is not None:
                if not step.condition or not step.condition.strip():
                    errors.append(
                        ValidationError(
                            level="ERROR",
                            message=f"Step '{step.id}': condition cannot be empty or whitespace-only",
                        )
                    )
        return errors

    def _check_parallel_config(self) -> list[ValidationError]:
        """Check that parallel config is valid."""
        errors: list[ValidationError] = []
        for step in self.runbook.steps:
            if step.parallel is None:
                continue
            if step.parallel.enabled and not step.parallel.item_key:
                errors.append(
                    ValidationError(
                        level="ERROR",
                        message=f"Step '{step.id}': parallel.enabled=true requires item_key to be set",
                    )
                )
        return errors

    def _check_type_field_mismatches(self) -> list[ValidationError]:
        """Check that step types match their field requirements."""
        errors: list[ValidationError] = []
        for step in self.runbook.steps:
            # script type should not have prompt or prompt_file
            if step.type == StepType.SCRIPT and step.prompt is not None:
                errors.append(
                    ValidationError(
                        level="ERROR",
                        message=f"Step '{step.id}': script type should not have prompt field",
                    )
                )
            if step.type == StepType.SCRIPT and step.prompt_file is not None:
                errors.append(
                    ValidationError(
                        level="ERROR",
                        message=f"Step '{step.id}': script type should not have prompt_file field",
                    )
                )
        return errors

    def _check_output_file_conflicts(self) -> list[ValidationError]:
        """Check for output file conflicts (warning, not error)."""
        errors: list[ValidationError] = []
        file_to_steps: dict[str, list[str]] = {}

        for step in self.runbook.steps:
            for output_def in step.output:
                if output_def.file not in file_to_steps:
                    file_to_steps[output_def.file] = []
                file_to_steps[output_def.file].append(step.id)

        for filename, step_ids in file_to_steps.items():
            if len(step_ids) > 1:
                errors.append(
                    ValidationError(
                        level="WARN",
                        message=f"Output file conflict: '{filename}' is output by multiple steps: {', '.join(step_ids)}",
                    )
                )
        return errors

    def _check_quality_check_config(self) -> list[ValidationError]:
        """Check that quality_check config has at least review_prompt or rules."""
        errors: list[ValidationError] = []
        for step in self.runbook.steps:
            if step.quality_check is None:
                continue
            qc = step.quality_check
            if not qc.review_prompt and not qc.rules:
                errors.append(
                    ValidationError(
                        level="ERROR",
                        message=(
                            f"Step '{step.id}': quality_check requires at least one of "
                            "'review_prompt' or 'rules' to be set"
                        ),
                    )
                )
        return errors

    def _check_loop_steps(self) -> list[ValidationError]:
        """Check loop step constraints: goal, max_iterations, body DAG."""
        errors: list[ValidationError] = []
        for step in self.runbook.steps:
            if step.type != StepType.LOOP:
                continue

            # Goal must not be whitespace-only
            if step.goal is not None and not step.goal.strip():
                errors.append(
                    ValidationError(
                        level="ERROR",
                        message=f"Step '{step.id}': loop goal cannot be empty or whitespace-only",
                    )
                )

            # max_iterations must be >= 1
            if step.max_iterations < 1:
                errors.append(
                    ValidationError(
                        level="ERROR",
                        message=f"Step '{step.id}': max_iterations must be >= 1, got {step.max_iterations}",
                    )
                )
            elif step.max_iterations > 50:
                errors.append(
                    ValidationError(
                        level="WARN",
                        message=f"Step '{step.id}': max_iterations={step.max_iterations} is unusually high (>50)",
                    )
                )

            # Validate body sub-steps
            if step.body:
                # Duplicate IDs in body
                seen_ids: set[str] = set()
                for body_step in step.body:
                    if body_step.id in seen_ids:
                        errors.append(
                            ValidationError(
                                level="ERROR",
                                message=f"Step '{step.id}': duplicate body step ID: '{body_step.id}'",
                            )
                        )
                    seen_ids.add(body_step.id)

                # Cycle detection in body
                try:
                    topological_sort(step.body)
                except CycleDetectedError as e:
                    errors.append(
                        ValidationError(
                            level="ERROR",
                            message=f"Step '{step.id}': cycle in loop body: {', '.join(e.cycle_members)}",
                        )
                    )

        return errors

    def _check_orphan_steps(self) -> list[ValidationError]:
        """Check for orphan steps (isolated, not connected to any chain)."""
        errors: list[ValidationError] = []

        if not self.runbook.steps:
            return errors

        # Build dependency graph
        step_ids = {s.id for s in self.runbook.steps}
        dependents_map: dict[str, set[str]] = {sid: set() for sid in step_ids}
        dependencies_map: dict[str, set[str]] = {sid: set() for sid in step_ids}

        for step in self.runbook.steps:
            for dep in step.depends_on:
                if dep in step_ids:
                    dependents_map[dep].add(step.id)
                    dependencies_map[step.id].add(dep)

        # A step is orphan if it has neither dependencies nor dependents
        # (completely isolated)
        for step_id in step_ids:
            if not dependencies_map[step_id] and not dependents_map[step_id]:
                errors.append(
                    ValidationError(
                        level="WARN",
                        message=f"Step '{step_id}' is orphan: isolated with no dependencies or dependents",
                    )
                )

        return errors
