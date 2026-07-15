"""Generator: orchestrates the full flow from YAML runbook to SKILL.md and scripts."""

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from agent_runbook.composer import Composer, Section
from agent_runbook.context import RenderContext
from agent_runbook.dag import BranchGroup, detect_branches, topological_sort
from agent_runbook.registry import StrategyRegistry
from agent_runbook.schema import Runbook, Step
from agent_runbook.strategies.base import StepStrategy
from agent_runbook.strategies.branch import BranchingStrategy
from agent_runbook.strategies.checkpoint import CheckpointScript, CheckpointScriptStrategy
from agent_runbook.strategies.parallel import ParallelStepStrategy
from agent_runbook.validator import RunbookValidator, ValidationError

# Bundled schema validator script (stdlib only, vendored for agent runtime use).
VALIDATE_SCHEMA_SCRIPT = Path(__file__).parent / "templates" / "scripts" / "validate_schema.py"


@dataclass
class GeneratedOutput:
    """Result of generating a SKILL.md from a runbook.

    Attributes:
        skill_path: Absolute path to the generated SKILL.md file.
        scripts: List of absolute paths to generated checkpoint scripts.
    """

    skill_path: str
    scripts: list[str] = field(default_factory=list)


class Generator:
    """Orchestrates the full flow from YAML runbook to SKILL.md and scripts.

    The generator parses, validates, topologically sorts steps, detects
    branches, renders each step via registered strategies, composes the
    final SKILL.md, and generates checkpoint scripts.
    """

    def __init__(self, registry: StrategyRegistry, composer: Composer) -> None:
        """Initialize the generator.

        Args:
            registry: StrategyRegistry mapping step types to rendering strategies.
            composer: Composer for assembling the final SKILL.md output.
        """
        self.registry = registry
        self.composer = composer

    def generate(self, runbook_path: str, output_dir: str, lang: str = "en") -> GeneratedOutput:
        """Generate SKILL.md and scripts from a runbook YAML file.

        Args:
            runbook_path: Path to the runbook YAML file.
            output_dir: Directory to write SKILL.md and scripts/ into.
            lang: Language code for generated text ("en" or "zh"). Defaults to "en".

        Returns:
            GeneratedOutput with paths to the generated files.

        Raises:
            ValidationError: If the runbook fails validation.
            FileNotFoundError: If the runbook file does not exist.
        """
        runbook_path = Path(runbook_path)
        output_dir = Path(output_dir)

        # 1. Parse
        runbook = Runbook.from_yaml(runbook_path)

        # 2. Validate the runbook (quality_check is validated as an inline attribute
        # of the parent step; no synthetic steps are created).
        validator = RunbookValidator(runbook, str(runbook_path.parent))
        errors = validator.validate()
        error_errors = [e for e in errors if e.level == "ERROR"]
        if error_errors:
            error_messages = "; ".join(e.message for e in error_errors)
            raise ValidationError(level="ERROR", message=error_messages)

        # 3. Topo sort
        sorted_steps = topological_sort(runbook.steps)

        # 4. Branch detect
        branch_groups = detect_branches(runbook.steps)

        # 5. Build RenderContext
        branch_groups_map: dict[str, BranchGroup] = {}
        for bg in branch_groups:
            branch_groups_map[bg.branch_point] = bg

        ctx = RenderContext(
            runbook=runbook,
            execution_order=sorted_steps,
            branch_groups=branch_groups_map,
            runbook_dir=str(runbook_path.parent),
            lang=lang,
        )

        # 6. Collect step IDs that belong to branches (to skip in main loop)
        branch_step_ids: set[str] = set()
        for bg in branch_groups:
            for branch in bg.branches:
                for s in branch.steps:
                    branch_step_ids.add(s.id)

        parallel_strategy = ParallelStepStrategy()
        sections: list[Section] = []
        order = 0

        # Build a map of dependency-signature → steps for detecting parallel groups.
        # Two non-branch steps sharing identical depends_on sets (and no condition)
        # are parallel siblings.
        from collections import defaultdict

        dep_sig_to_steps: dict[tuple, list[Step]] = defaultdict(list)
        for step in sorted_steps:
            if step.id in branch_step_ids:
                continue
            if step.condition is not None:
                continue
            sig = tuple(sorted(step.depends_on))
            dep_sig_to_steps[sig].append(step)

        # Each step gets a unique sequential order number (1, 2, 3, ...).
        # Parallel groups are detected later in the composer based on depends_on.

        # Render regular (non-branch) steps
        for step in sorted_steps:
            if step.id in branch_step_ids:
                continue
            order += 1
            step_order = order
            content = self._render_step(step, ctx, parallel_strategy)
            # Store step's depends_on for parallel detection in composer
            sections.append(
                Section(
                    step_id=step.id,
                    order=step_order,
                    content=content,
                    dependencies=step.depends_on,
                )
            )

        # 7. Handle branch groups: render branch decision + branch steps
        for bg in branch_groups:
            order += 1
            branching = BranchingStrategy(bg)
            branch_content = branching.render(ctx)
            sections.append(
                Section(
                    step_id=bg.branch_point,
                    order=order,
                    content=branch_content,
                    is_branch_point=True,
                )
            )

            # Render each branch's steps
            for branch in bg.branches:
                for step in branch.steps:
                    order += 1
                    content = self._render_step(step, ctx, parallel_strategy)
                    sections.append(
                        Section(step_id=step.id, order=order, content=content)
                    )

        # 8. Render checkpoint scripts
        checkpoint_strategy = CheckpointScriptStrategy()
        all_scripts: list[CheckpointScript] = []

        for step in runbook.steps:
            if step.checkpoint:
                scripts = checkpoint_strategy.generate_scripts(step, ctx)
                all_scripts.extend(scripts)

        # 9. Compose SKILL.md
        skill_content = self.composer.compose(runbook, sections, lang=lang)

        # 10. Write output
        output_dir.mkdir(parents=True, exist_ok=True)

        skill_path = output_dir / "SKILL.md"
        skill_path.write_text(skill_content, encoding="utf-8")

        script_paths: list[str] = []
        if all_scripts:
            scripts_dir = output_dir / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            for script in all_scripts:
                script_file = scripts_dir / script.filename
                script_file.write_text(script.content, encoding="utf-8")
                script_paths.append(str(script_file))

        # 10b. Bundle the schema validator if any step has an output schema.
        # The validator is referenced by the "validate output" instructions
        # injected into each step's output section.
        if self._has_output_schemas(runbook) and VALIDATE_SCHEMA_SCRIPT.exists():
            scripts_dir = output_dir / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            validator_path = scripts_dir / "validate_schema.py"
            shutil.copy2(VALIDATE_SCHEMA_SCRIPT, validator_path)
            script_paths.append(str(validator_path))

        return GeneratedOutput(
            skill_path=str(skill_path),
            scripts=script_paths,
        )

    @staticmethod
    def _has_output_schemas(runbook: Runbook) -> bool:
        """Return True if any step (including loop body steps) has output schemas."""
        def _step_has(step: Step) -> bool:
            if step.output:
                return True
            if step.body:
                return any(_step_has(s) for s in step.body)
            return False
        return any(_step_has(s) for s in runbook.steps)

    def _render_step(
        self,
        step: Step,
        ctx: RenderContext,
        parallel_strategy: ParallelStepStrategy,
    ) -> str:
        """Render a single step via its type strategy, optionally wrapping for parallel execution.

        Args:
            step: The step to render.
            ctx: The rendering context.
            parallel_strategy: Strategy for wrapping parallel execution instructions.

        Returns:
            Rendered step content as a markdown string.
        """
        strategies = self.registry.select(step)

        # Filter to StepStrategy instances only (not CheckpointScriptStrategy)
        type_strategies = [s for s in strategies if isinstance(s, StepStrategy)]

        if not type_strategies:
            return ""

        content = type_strategies[0].render(step, ctx)

        # If parallel is enabled, wrap the content with parallel execution instructions
        if step.parallel and step.parallel.enabled:
            content = parallel_strategy.wrap(content, step, ctx)

        return content
