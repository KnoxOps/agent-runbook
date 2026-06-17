---
name: fix-failing-tests
description: >-
  Iteratively fix all failing tests until the test suite is green
user-invocable: true
---

## Execution Flow

### Task Context

Before starting execution, initialize `task_context.json`:

```json
{
  "task_id": "<task_id from input>",
  "current_step": 0,
  "current_step_id": null,
  "status": "running",
  "steps": {
    "fix_loop": "pending",
    "present": "pending"
  },
  "updated_at": "<ISO timestamp>"
}
```

Update this file after each step completes. On error, set step status to `"failed"` and overall `status` to `"failed"`.

### Step 1: fix_loop

**Type:** loop
**Description:** Run tests, analyze failures, fix source code, repeat until green

## Iteration Loop

**Goal:** pytest exits with 0 failures (all tests pass)
**Max Iterations:** 10

> This step executes as a loop. The body steps repeat until the goal is met or max iterations reached.

## Loop Body (repeats each iteration)

#### Body Step 1: run_tests

**Type:** script

**Execution:** Execute the following command:
```bash
cd examples/fix-loop && python3 -m pytest tests/ --tb=short 2>&1 | tail -60
```

#### Body Step 2: fix

**Type:** agent

**Execution:** Launch an independent agent with the following prompt file:

Read the pytest output from run_tests.
Analyze the tracebacks to identify root causes.

CRITICAL: Fix only ONE source file per iteration.
Some failures are SYMPTOMS of bugs in upstream modules (dependency chain).
Fix the DEEPEST root cause first — the file whose bug cascades into other modules.
After fixing one file, tests that depended on it will pass automatically.

Strategy:
  1. Look for failures that trace back to a shared upstream function
  2. Fix THAT upstream file, not the downstream callers
  3. Stop after fixing one file — re-run tests to see which failures clear on their own

Rules:
  - Only modify files in src/, NEVER modify test files
  - Fix exactly ONE file per iteration, then stop
  - Prefer fixing root causes over symptoms


## Goal Evaluation

After all body steps complete, evaluate:

**Goal:** pytest exits with 0 failures (all tests pass)

1. If goal IS met → mark this step completed, proceed to next step.
2. If goal NOT met and iterations remain → reset body steps, start next iteration.
3. If max iterations reached → mark step completed with status "max_iterations_reached", report what remains.

Append a summary to `iteration_history` after each iteration.

### Progress Tracking

After completing this step, update `task_context.json`:
- Set `current_step_id` to `"fix_loop"`
- Set `steps.fix_loop` to `"completed"`
### Step 2: present

**Type:** inline

## Execution
Follow these instructions:

Generate a markdown report summarizing the fix loop results.
Include:
  - Total iterations taken
  - What was fixed in each iteration (file + bug description)
  - Final test results
  - How cascading dependencies caused failures to clear automatically
Write the report to fix_report.md


### Progress Tracking

After completing this step, update `task_context.json`:
- Set `current_step_id` to `"present"`
- Set `steps.present` to `"completed"`