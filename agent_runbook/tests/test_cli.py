"""Tests for the CLI module."""

import subprocess
import sys
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestCliHelp:
    """Test CLI help and argument parsing."""

    def test_cli_help(self):
        """python -m agent_runbook --help should exit 0 and contain 'generate'."""
        result = subprocess.run(
            [sys.executable, "-m", "agent_runbook", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "generate" in result.stdout, f"stdout: {result.stdout}"


class TestCliGenerateMissingArg:
    """Test CLI generate command with missing arguments."""

    def test_cli_generate_missing_arg(self):
        """python -m agent_runbook generate with no arg should exit non-zero."""
        result = subprocess.run(
            [sys.executable, "-m", "agent_runbook", "generate"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0


class TestCliGenerateRunbook:
    """Test CLI generate command with a valid runbook."""

    def test_cli_generate_runbook(self):
        """python -m agent_runbook generate <fixture> --output <tmp> should exit 0 and create SKILL.md."""
        import tempfile

        runbook_path = FIXTURES_DIR / "simple-3-step" / "runbook.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "agent_runbook",
                    "generate",
                    str(runbook_path),
                    "--output",
                    output_dir,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
            assert "Generated:" in result.stdout
            assert (Path(output_dir) / "SKILL.md").exists()


class TestCliSubcommandHelp:
    """Test CLI subcommand help."""

    def test_cli_generate_help(self):
        """python -m agent_runbook generate --help should show args."""
        result = subprocess.run(
            [sys.executable, "-m", "agent_runbook", "generate", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "runbook" in result.stdout
        assert "--output" in result.stdout
        assert "-o" in result.stdout
