# agent-runbook

Multi-agent skill framework: contract-based YAML runbooks compiled to Claude Code / Codex SKILL.md files. Every step declares input and output with JSON Schema — the compiler validates contract closure at build time.

## Concept

Long-running, multi-agent tasks don't fit in a single agent — context explodes, steps drift, state gets lost.

**agent-runbook** solves this by treating every step as a **contract**:

1. **Contract-first design** — each step declares its `input` (where data comes from) and `output` (what it produces, with JSON Schema). The compiler verifies contract closure at build time — missing inputs or schema mismatches are caught before any agent runs.
2. **File-passing** — agents communicate via JSON/Markdown files, not LLM context. Each step only reads its declared inputs.
3. **DAG orchestration** — declare `depends_on`, the compiler handles topological sort, parallel group detection, and auto-expands quality checks into synthetic supervisor steps.
4. **Checkpoint & resume** — each step outputs a progress file. Broken runs resume from the last checkpoint.

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

## Status

Pre-alpha. This is a program that generates Claude Code / Codex skills from runbook YAML definitions.

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

## Step Types

| Type | Description |
|------|-------------|
| `inline` | Prompt executed by the current agent. Use for orchestration steps. |
| `agent` | Dispatch an independent sub-agent with a prompt file. Use `prompt_file: prompts/xxx.agent.md`. |
| `script` | Execute a Python script. Use `checkpoint: scripts/xxx.py` for checkpoint scripts. |
| `parallel` | Run multiple agent steps concurrently. Configure with `parallel.enabled`, `max_instances`, `item_key`. |
| `branch` | Conditional branching based on step output. Use `condition` field on steps. |
| `checkpoint` | Write progress checkpoint file for pause/resume support. |
| `quality_check` | Auto-generated quality gate that dispatches @supervisor. Configure with `quality_check: { blocking: true, rules: [...] }`. |

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

## License

MIT
