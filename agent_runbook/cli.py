"""CLI for agent-runbook: generate SKILL.md from runbook YAML files."""

import argparse
import sys

from agent_runbook.composer import Composer
from agent_runbook.generator import Generator
from agent_runbook.registry import default_registry


def main() -> None:
    """Entry point for the agent-runbook CLI."""
    parser = argparse.ArgumentParser(
        prog="agent-runbook",
        description="Convert YAML runbook definitions into Claude Code SKILL.md files",
    )
    subparsers = parser.add_subparsers(dest="command")

    gen_parser = subparsers.add_parser(
        "generate", help="Generate SKILL.md from a runbook YAML"
    )
    gen_parser.add_argument(
        "runbook",
        help="Path to runbook YAML file",
    )
    gen_parser.add_argument(
        "--output",
        "-o",
        default=".",
        help="Output directory (default: current directory)",
    )
    gen_parser.add_argument(
        "--lang",
        choices=["en", "zh"],
        default="en",
        help="Language for generated text (default: en)",
    )

    args = parser.parse_args()

    if args.command == "generate":
        generator = Generator(default_registry(), Composer())
        result = generator.generate(args.runbook, args.output, lang=args.lang)
        print(f"Generated: {result.skill_path}")
        if result.scripts:
            print(f"Scripts: {len(result.scripts)} files")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
