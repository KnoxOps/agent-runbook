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

Look at the pytest failures from run_tests.
Pick ONE source file that has failing tests and fix the bugs in that file.

Rules:
  - Only modify files in src/, NEVER modify test files
  - Fix exactly ONE file, then stop immediately
  - Do NOT read or modify any other source files


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