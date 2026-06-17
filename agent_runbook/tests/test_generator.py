"""E2E tests for the Generator module."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from agent_runbook.composer import Composer
from agent_runbook.generator import GeneratedOutput, Generator
from agent_runbook.registry import default_registry
from agent_runbook.validator import ValidationError

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestGenerateCreatesSkillMd:
    """Generate from simple-3-step fixture, assert SKILL.md created."""

    def test_generate_creates_skill_md(self):
        """Generate should create SKILL.md containing the runbook name."""
        runbook_path = FIXTURES_DIR / "simple-3-step" / "runbook.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            generator = Generator(default_registry(), Composer())
            result = generator.generate(str(runbook_path), output_dir)

            skill_md = Path(output_dir) / "SKILL.md"
            assert skill_md.exists(), f"Expected {skill_md} to exist"
            content = skill_md.read_text()
            assert "zombie-resource-scan" in content
            assert isinstance(result, GeneratedOutput)
            assert result.skill_path == str(skill_md)


class TestGenerateCreatesScriptsDir:
    """Fixture with checkpoint step -> scripts/ directory with .py files."""

    def test_generate_creates_scripts_dir(self):
        """Generate from a fixture with checkpoints should create scripts/ directory."""
        runbook_path = FIXTURES_DIR / "simple-3-step" / "runbook.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            generator = Generator(default_registry(), Composer())
            result = generator.generate(str(runbook_path), output_dir)

            scripts_dir = Path(output_dir) / "scripts"
            assert scripts_dir.exists(), f"Expected {scripts_dir} to exist"
            assert any(scripts_dir.iterdir()), "scripts/ should not be empty"

            py_files = list(scripts_dir.glob("*.py"))
            assert len(py_files) >= 4, f"Expected at least 4 checkpoint scripts, got {len(py_files)}"
            assert len(result.scripts) >= 4

    def test_generate_no_checkpoint_no_scripts_dir(self):
        """Fixture without checkpoint steps should NOT create scripts directory."""
        runbook_path = FIXTURES_DIR / "no-checkpoint" / "runbook.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            generator = Generator(default_registry(), Composer())
            result = generator.generate(str(runbook_path), output_dir)

            scripts_dir = Path(output_dir) / "scripts"
            assert not scripts_dir.exists(), "scripts/ should not be created for no-checkpoint runbook"
            assert result.scripts == []


class TestGenerateInvalidRunbook:
    """Fixture with cycle -> ValidationError raised, no output."""

    def test_generate_invalid_runbook_raises(self):
        """Cycle fixture should raise ValidationError."""
        runbook_path = FIXTURES_DIR / "invalid" / "cycle.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            generator = Generator(default_registry(), Composer())
            with pytest.raises(ValidationError) as exc_info:
                generator.generate(str(runbook_path), output_dir)
            assert "Cycle" in str(exc_info.value), f"Expected cycle message, got: {exc_info.value}"


class TestGenerateAllStepTypes:
    """Fixture with inline+agent+script steps -> output contains correct patterns."""

    def test_generate_all_step_types_rendered(self):
        """In+agent+script fixture should contain correct markdown patterns for each type."""
        runbook_path = FIXTURES_DIR / "all-types" / "runbook.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            generator = Generator(default_registry(), Composer())
            result = generator.generate(str(runbook_path), output_dir)

            content = Path(output_dir, "SKILL.md").read_text()

            # inline step content
            assert "This is an inline prompt." in content
            # agent step content
            assert "independent agent" in content.lower()
            # script step content
            assert "```bash" in content
            assert "processing data" in content

    def test_generate_output_has_correct_path(self):
        """Generated output skill_path should point to correct file."""
        runbook_path = FIXTURES_DIR / "all-types" / "runbook.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            generator = Generator(default_registry(), Composer())
            result = generator.generate(str(runbook_path), output_dir)
            assert result.skill_path.endswith("SKILL.md")
            assert Path(result.skill_path).exists()


class TestGenerateBranchRendered:
    """Fixture with branch pattern -> output has branch decision section."""

    def test_generate_branch_rendered(self):
        """Branch fixture should produce branch decision content."""
        runbook_path = FIXTURES_DIR / "branch" / "runbook.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            generator = Generator(default_registry(), Composer())
            result = generator.generate(str(runbook_path), output_dir)

            content = Path(output_dir, "SKILL.md").read_text()

            assert "Branch Decision" in content
            assert "healthy" in content
            assert "unhealthy" in content


class TestGenerateParallelSteps:
    """Fixture with parallel steps → output has correct step numbering and annotations."""

    def test_parallel_steps_have_unique_order_numbers(self):
        """Parallel steps should have sequential order numbers (not shared)."""
        runbook_path = FIXTURES_DIR / "parallel" / "runbook.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            generator = Generator(default_registry(), Composer())
            result = generator.generate(str(runbook_path), output_dir)

            content = Path(output_dir, "SKILL.md").read_text()

            # Steps process_a, process_b, process_c all depend on init
            # They should have different step numbers: Step 2, Step 3, Step 4
            assert "### Step 2: process_a" in content
            assert "### Step 3: process_b" in content
            assert "### Step 4: process_c" in content

    def test_parallel_steps_have_parallel_annotation(self):
        """Parallel steps should have a 'must run in parallel' annotation."""
        runbook_path = FIXTURES_DIR / "parallel" / "runbook.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            generator = Generator(default_registry(), Composer())
            result = generator.generate(str(runbook_path), output_dir)

            content = Path(output_dir, "SKILL.md").read_text()

            # Should have a note about parallel execution
            assert "must run in parallel" in content
            assert "Step 2" in content and "Step 3" in content and "Step 4" in content


class TestGenerateLoopStep:
    """Fixture with loop step -> output has loop structure."""

    def test_generate_loop_creates_skill_md(self):
        """Loop fixture should generate SKILL.md successfully."""
        runbook_path = FIXTURES_DIR / "loop" / "runbook.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            generator = Generator(default_registry(), Composer())
            result = generator.generate(str(runbook_path), output_dir)

            skill_md = Path(output_dir) / "SKILL.md"
            assert skill_md.exists()
            content = skill_md.read_text()
            assert "fix-lint-errors" in content

    def test_generate_loop_contains_goal(self):
        """Generated SKILL.md should contain the loop goal."""
        runbook_path = FIXTURES_DIR / "loop" / "runbook.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            generator = Generator(default_registry(), Composer())
            result = generator.generate(str(runbook_path), output_dir)

            content = Path(output_dir, "SKILL.md").read_text()
            assert "ESLint passes with zero errors on all files" in content

    def test_generate_loop_contains_body_steps(self):
        """Generated SKILL.md should contain the loop body step content."""
        runbook_path = FIXTURES_DIR / "loop" / "runbook.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            generator = Generator(default_registry(), Composer())
            result = generator.generate(str(runbook_path), output_dir)

            content = Path(output_dir, "SKILL.md").read_text()
            assert "discover" in content
            assert "fix" in content
            assert "verify" in content

    def test_generate_loop_contains_iteration_logic(self):
        """Generated SKILL.md should contain iteration/goal evaluation logic."""
        runbook_path = FIXTURES_DIR / "loop" / "runbook.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            generator = Generator(default_registry(), Composer())
            result = generator.generate(str(runbook_path), output_dir)

            content = Path(output_dir, "SKILL.md").read_text()
            assert "iteration" in content.lower()
            assert "10" in content  # max_iterations
