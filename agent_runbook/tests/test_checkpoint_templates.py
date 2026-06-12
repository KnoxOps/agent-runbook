"""Tests for checkpoint script template generation."""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader


class TestCheckpointTemplates:
    """Test that checkpoint script templates render to valid Python."""

    @pytest.fixture
    def template_env(self):
        """Create Jinja2 environment pointing to templates directory."""
        templates_dir = Path(__file__).parent.parent / "templates" / "scripts"
        return Environment(loader=FileSystemLoader(str(templates_dir)))

    def test_checkpoint_init_renders_valid_python(self, template_env):
        """checkpoint_init.py.j2 should render to valid Python."""
        template = template_env.get_template("checkpoint_init.py.j2")
        rendered = template.render()

        # Validate syntax by compiling
        compile(rendered, "checkpoint_init.py", "exec")

        # Verify it has argparse and expected functions
        assert "argparse" in rendered
        assert "--input" in rendered
        assert "--key" in rendered
        assert "--output" in rendered
        assert "--verbose" in rendered
        assert "pending" in rendered

    def test_checkpoint_mark_done_renders_valid_python(self, template_env):
        """checkpoint_mark_done.py.j2 should render to valid Python."""
        template = template_env.get_template("checkpoint_mark_done.py.j2")
        rendered = template.render()

        compile(rendered, "checkpoint_mark_done.py", "exec")

        assert "argparse" in rendered
        assert "--checkpoint" in rendered
        assert "--item" in rendered
        assert "--verbose" in rendered
        assert "done" in rendered

    def test_checkpoint_pending_renders_valid_python(self, template_env):
        """checkpoint_pending.py.j2 should render to valid Python."""
        template = template_env.get_template("checkpoint_pending.py.j2")
        rendered = template.render()

        compile(rendered, "checkpoint_pending.py", "exec")

        assert "argparse" in rendered
        assert "--checkpoint" in rendered
        assert "--input" in rendered
        assert "--key" in rendered
        assert "--count" in rendered

    def test_checkpoint_merge_renders_valid_python(self, template_env):
        """checkpoint_merge.py.j2 should render to valid Python."""
        template = template_env.get_template("checkpoint_merge.py.j2")
        rendered = template.render()

        compile(rendered, "checkpoint_merge.py", "exec")

        assert "argparse" in rendered
        assert "--inputs" in rendered
        assert "--output" in rendered

    def test_checkpoint_init_executable_help(self, template_env):
        """Rendered checkpoint_init.py should execute --help."""
        template = template_env.get_template("checkpoint_init.py.j2")
        rendered = template.render()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(rendered)
            script_path = Path(f.name)

        try:
            result = subprocess.run(
                ["python3", str(script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            assert result.returncode == 0
            assert "usage:" in result.stdout
        finally:
            script_path.unlink(missing_ok=True)

    def test_checkpoint_mark_done_executable_help(self, template_env):
        """Rendered checkpoint_mark_done.py should execute --help."""
        template = template_env.get_template("checkpoint_mark_done.py.j2")
        rendered = template.render()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(rendered)
            script_path = Path(f.name)

        try:
            result = subprocess.run(
                ["python3", str(script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            assert result.returncode == 0
            assert "usage:" in result.stdout
        finally:
            script_path.unlink(missing_ok=True)

    def test_checkpoint_pending_executable_help(self, template_env):
        """Rendered checkpoint_pending.py should execute --help."""
        template = template_env.get_template("checkpoint_pending.py.j2")
        rendered = template.render()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(rendered)
            script_path = Path(f.name)

        try:
            result = subprocess.run(
                ["python3", str(script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            assert result.returncode == 0
            assert "usage:" in result.stdout
        finally:
            script_path.unlink(missing_ok=True)

    def test_checkpoint_merge_executable_help(self, template_env):
        """Rendered checkpoint_merge.py should execute --help."""
        template = template_env.get_template("checkpoint_merge.py.j2")
        rendered = template.render()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(rendered)
            script_path = Path(f.name)

        try:
            result = subprocess.run(
                ["python3", str(script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            assert result.returncode == 0
            assert "usage:" in result.stdout
        finally:
            script_path.unlink(missing_ok=True)


class TestCheckpointInitFunctionality:
    """Integration tests for checkpoint_init.py functionality."""

    @pytest.fixture
    def template_env(self):
        templates_dir = Path(__file__).parent.parent / "templates" / "scripts"
        return Environment(loader=FileSystemLoader(str(templates_dir)))

    def test_checkpoint_init_basic_flow(self, template_env):
        """checkpoint_init should read JSON and create JSONL with pending items."""
        template = template_env.get_template("checkpoint_init.py.j2")
        rendered = template.render()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create input JSON
            input_file = tmpdir / "input.json"
            input_data = [
                {"resource_id": "r1", "name": "resource-1"},
                {"resource_id": "r2", "name": "resource-2"},
            ]
            input_file.write_text(json.dumps(input_data))

            # Create and run script
            script_file = tmpdir / "script.py"
            script_file.write_text(rendered)

            checkpoint_file = tmpdir / "checkpoint.jsonl"

            result = subprocess.run(
                [
                    "python3",
                    str(script_file),
                    "--input",
                    str(input_file),
                    "--key",
                    "resource_id",
                    "--output",
                    str(checkpoint_file),
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            assert result.returncode == 0, f"stderr: {result.stderr}"
            assert checkpoint_file.exists()

            # Verify checkpoint content
            lines = checkpoint_file.read_text().strip().split("\n")
            assert len(lines) == 2

            entry1 = json.loads(lines[0])
            assert entry1["key"] == "r1"
            assert entry1["status"] == "pending"

            entry2 = json.loads(lines[1])
            assert entry2["key"] == "r2"
            assert entry2["status"] == "pending"

    def test_checkpoint_init_with_nested_key(self, template_env):
        """checkpoint_init should handle JSON with root key."""
        template = template_env.get_template("checkpoint_init.py.j2")
        rendered = template.render()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            input_file = tmpdir / "input.json"
            input_data = {
                "items": [
                    {"id": "item1", "value": 10},
                    {"id": "item2", "value": 20},
                ]
            }
            input_file.write_text(json.dumps(input_data))

            script_file = tmpdir / "script.py"
            script_file.write_text(rendered)

            checkpoint_file = tmpdir / "checkpoint.jsonl"

            result = subprocess.run(
                [
                    "python3",
                    str(script_file),
                    "--input",
                    str(input_file),
                    "--key",
                    "id",
                    "--output",
                    str(checkpoint_file),
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            assert result.returncode == 0, f"stderr: {result.stderr}"

            lines = checkpoint_file.read_text().strip().split("\n")
            assert len(lines) == 2


class TestCheckpointMarkDoneFunctionality:
    """Integration tests for checkpoint_mark_done.py functionality."""

    @pytest.fixture
    def template_env(self):
        templates_dir = Path(__file__).parent.parent / "templates" / "scripts"
        return Environment(loader=FileSystemLoader(str(templates_dir)))

    def test_checkpoint_mark_done_appends_entry(self, template_env):
        """checkpoint_mark_done should append done entry with timestamp."""
        template = template_env.get_template("checkpoint_mark_done.py.j2")
        rendered = template.render()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            checkpoint_file = tmpdir / "checkpoint.jsonl"
            checkpoint_file.write_text(
                json.dumps({"key": "r1", "status": "pending"}) + "\n"
            )

            script_file = tmpdir / "script.py"
            script_file.write_text(rendered)

            result = subprocess.run(
                [
                    "python3",
                    str(script_file),
                    "--checkpoint",
                    str(checkpoint_file),
                    "--item",
                    json.dumps({"resource_id": "r1", "result": "success"}),
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            assert result.returncode == 0, f"stderr: {result.stderr}"

            lines = checkpoint_file.read_text().strip().split("\n")
            assert len(lines) == 2

            done_entry = json.loads(lines[1])
            assert done_entry["status"] == "done"
            assert "completed_at" in done_entry
            assert "resource_id" in done_entry


class TestCheckpointPendingFunctionality:
    """Integration tests for checkpoint_pending.py functionality."""

    @pytest.fixture
    def template_env(self):
        templates_dir = Path(__file__).parent.parent / "templates" / "scripts"
        return Environment(loader=FileSystemLoader(str(templates_dir)))

    def test_checkpoint_pending_lists_pending_items(self, template_env):
        """checkpoint_pending should output JSON list of pending items."""
        template = template_env.get_template("checkpoint_pending.py.j2")
        rendered = template.render()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            checkpoint_file = tmpdir / "checkpoint.jsonl"
            checkpoint_file.write_text(
                json.dumps({"key": "r1", "status": "pending"}) + "\n"
                + json.dumps({"key": "r2", "status": "done", "completed_at": "2026-01-01T00:00:00Z"}) + "\n"
                + json.dumps({"key": "r3", "status": "pending"}) + "\n"
            )

            script_file = tmpdir / "script.py"
            script_file.write_text(rendered)

            result = subprocess.run(
                [
                    "python3",
                    str(script_file),
                    "--checkpoint",
                    str(checkpoint_file),
                    "--key",
                    "key",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            assert result.returncode == 0, f"stderr: {result.stderr}"

            pending = json.loads(result.stdout)
            assert isinstance(pending, list)
            assert len(pending) == 2
            assert all(item["status"] == "pending" for item in pending)

    def test_checkpoint_pending_count_flag(self, template_env):
        """checkpoint_pending with --count should output only count."""
        template = template_env.get_template("checkpoint_pending.py.j2")
        rendered = template.render()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            checkpoint_file = tmpdir / "checkpoint.jsonl"
            checkpoint_file.write_text(
                json.dumps({"key": "r1", "status": "pending"}) + "\n"
                + json.dumps({"key": "r2", "status": "pending"}) + "\n"
            )

            script_file = tmpdir / "script.py"
            script_file.write_text(rendered)

            result = subprocess.run(
                [
                    "python3",
                    str(script_file),
                    "--checkpoint",
                    str(checkpoint_file),
                    "--key",
                    "key",
                    "--count",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            assert result.returncode == 0, f"stderr: {result.stderr}"
            assert result.stdout.strip() == "2"


class TestCheckpointMergeFunctionality:
    """Integration tests for checkpoint_merge.py functionality."""

    @pytest.fixture
    def template_env(self):
        templates_dir = Path(__file__).parent.parent / "templates" / "scripts"
        return Environment(loader=FileSystemLoader(str(templates_dir)))

    def test_checkpoint_merge_deduplicates(self, template_env):
        """checkpoint_merge should deduplicate by key, preferring done."""
        template = template_env.get_template("checkpoint_merge.py.j2")
        rendered = template.render()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # First checkpoint: r1 pending, r2 done
            file1 = tmpdir / "checkpoint1.jsonl"
            file1.write_text(
                json.dumps({"key": "r1", "status": "pending"}) + "\n"
                + json.dumps({"key": "r2", "status": "done", "completed_at": "2026-01-01T00:00:00Z"}) + "\n"
            )

            # Second checkpoint: r1 done, r3 pending
            file2 = tmpdir / "checkpoint2.jsonl"
            file2.write_text(
                json.dumps({"key": "r1", "status": "done", "completed_at": "2026-01-02T00:00:00Z"}) + "\n"
                + json.dumps({"key": "r3", "status": "pending"}) + "\n"
            )

            script_file = tmpdir / "script.py"
            script_file.write_text(rendered)

            output_file = tmpdir / "merged.jsonl"

            result = subprocess.run(
                [
                    "python3",
                    str(script_file),
                    "--inputs",
                    f"{file1} {file2}",
                    "--output",
                    str(output_file),
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            assert result.returncode == 0, f"stderr: {result.stderr}"

            lines = output_file.read_text().strip().split("\n")
            assert len(lines) == 3

            # Verify deduplication: r1 should be marked done (from file2)
            entries = {json.loads(line)["key"]: json.loads(line) for line in lines}
            assert entries["r1"]["status"] == "done"
            assert entries["r2"]["status"] == "done"
            assert entries["r3"]["status"] == "pending"
