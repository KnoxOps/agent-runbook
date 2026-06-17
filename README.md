# agent-runbook

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

Multi-agent skill framework — compile contract-based YAML runbooks into Claude Code / Codex SKILL.md files. Every step declares input and output with JSON Schema. The compiler validates contract closure at build time. Broken runs resume from the last checkpoint.

## Loop Engineering

[Loop engineering](https://addyosmani.com/blog/loop-engineering/) is replacing yourself as the one who prompts the agent. You design a system that finds work, dispatches agents, checks results, and decides what comes next — then you let that system run. agent-runbook is a loop engineering framework: each runbook defines the loop, the compiler produces the SKILL.md, and agents execute it while you stay the engineer.

## Who is this for

- Developers building complex multi-step agent workflows in Claude Code or Codex
- Skill authors who need control flow beyond linear prompts: loops, parallelism, branching, checkpoints
- Teams that want agents to communicate via structured files instead of LLM context

## Install

```bash
pip install git+https://github.com/KnoxOps/agent-runbook.git
```

## Example

```yaml
# restart-nginx.runbook.yaml
name: restart-nginx
description: SSH into a server, restart Nginx, and verify it's back up

input_params:
  - name: host
    type: string
    required: true

steps:
  - id: restart
    depends_on: []
    type: agent
    description: SSH in and restart Nginx
    prompt: SSH into {host} and run systemctl restart nginx
    output:
      - file: restart_result.json
        schema: schemas/restart.schema.json    # ← contract: what I produce

  - id: verify
    type: agent
    description: Verify Nginx is healthy
    prompt: curl http://{host}/health and check the status code
    input:
      - from_step: restart                     # ← contract: where I read from
        file: restart_result.json
    output:
      - file: verify_result.json
        schema: schemas/verify.schema.json     # ← contract: what I produce
    depends_on: [restart]
```

Build it:

```bash
$ python3 -m agent_runbook generate restart-nginx.runbook.yaml -o .
```

This produces `SKILL.md` — ready for Claude Code or Codex to execute.

## How It Works

```
  runbook.yaml
       │
       ▼
  ┌──────────┐    ┌──────────┐    ┌──────────┐
  │  Parse   │───▶│ Validate │───▶│ Compose  │───▶ SKILL.md + checkpoint scripts
  └──────────┘    └──────────┘    └──────────┘
                       │
              Contract closure check:
              • Every input.from_step exists
              • Schema references resolve
              • DAG has no cycles
```

## Why Files Over Context

| | LLM Context | agent-runbook (Files) |
|------|-------------|----------------------|
| Context window | Limited, gets polluted | Unlimited, clean per step |
| Resume on crash | Start over | Read checkpoint, skip done items |
| Parallel agents | Can't share state | Read from same input file |
| Debugging | Lost after session | Files persist, inspectable |

## Step Types

| Type | Description |
|------|-------------|
| `inline` | Prompt executed by the current agent. Use for orchestration steps. |
| `agent` | Dispatch an independent sub-agent with a prompt file. Use `prompt_file: prompts/xxx.agent.md`. |
| `script` | Execute a shell command or Python script. Use `command` for shell, `checkpoint: scripts/xxx.py` for checkpoint scripts. |
| `parallel` | Run multiple agent steps concurrently. Configure with `parallel.enabled`, `max_instances`, `item_key`. |
| `branch` | Conditional branching based on step output. Use `condition` field on steps. |
| `loop` | Iteratively execute body steps until a goal is met or max iterations reached. Configure with `goal`, `max_iterations`, and `body` sub-steps. |
| `checkpoint` | Write progress checkpoint file for pause/resume support. |
| `quality_check` | Auto-generated quality gate that dispatches @supervisor. Configure with `quality_check: { blocking: true, rules: [...] }`. |

## Demo

See [`examples/fix-loop/`](examples/fix-loop/) for a working demo: a runbook that iteratively runs pytest, identifies failing tests, fixes source code one file at a time, and repeats until the test suite is green — all driven by the `loop` step type with cascading dependency resolution.

## Usage

### CLI (generic, zero coupling)

```bash
python3 -m agent_runbook generate <runbook.yaml> --output <dir> [--lang zh|en]
```

### Wrapper with directory convention

Projects should wrap the CLI with their own path convention. For example:

```bash
# From repo root — output path auto-derived from convention
python3 scripts/gen-skill rules/<agent>/<skill>/runbook.yaml --lang zh
```

**Convention**: `rules/<agent>/<skill>/runbook.yaml` → `skills/<agent>/<skill>/SKILL.md`

`scripts/gen-skill` is the only place that knows the project-specific directory layout. The CLI itself remains generic.

## Configuration

### Input Parameters
Declare typed inputs at the top level:
```yaml
input_params:
  - name: host
    type: string
    required: true
    description: Target server
```

### Output Contracts
Every step can declare output with JSON Schema:
```yaml
output:
  - schema: schemas/output.schema.json
    file: output.json
```

### Quality Checks
```yaml
quality_check:
  blocking: true
  rules:
    - "output.json schema compliance"
    - "result count > 0"
```

### Checkpoint & Resume
```yaml
steps:
  - id: long_task
    checkpoint: scripts/checkpoint_task.py
```

## Status

Active development — API may change.

## Ecosystem

**Built with agent-runbook:**

- [open-devops-skills](https://github.com/KnoxOps/open-devops-skills) — Production-ready DevOps & SRE skills: zombie resource scanning, cost optimization, K8s troubleshooting, and more for Claude Code and Codex.

*Maintained by [KnoxOps](https://knoxops.com).*

## License

[Apache 2.0](LICENSE)
