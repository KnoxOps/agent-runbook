---
name: host-health-loop
description: >-
  Ansible health check discovers host issues → fix one by one (write ops require human approval) → re-inspect → repeat until all healthy → generate HTML report
user-invocable: true
---

## Input Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| inventory | string | No | Path to Ansible inventory file, defaults to ansible/inventory.ini |
| playbook | string | No | Path to health check playbook, defaults to ansible/health_check.yml |

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
    "inspect": "pending",
    "fix_loop": "pending",
    "generate_report": "pending"
  },
  "updated_at": "<ISO timestamp>"
}
```

Update this file after each step completes. On error, set step status to `"failed"` and overall `status` to `"failed"`.

### Step 1: inspect

**Type:** script
**Description:** Run Ansible playbook to inspect all hosts and generate an issue list

## Execution

Execute the following command:

```bash
ansible-playbook -i {inventory} {playbook} 2>&1
mv /tmp/host_issues.json host_issues.json

```

## Output
- **Schema:** schemas/host_issues.schema.json
  - **File:** host_issues.json

### Progress Tracking

After completing this step, update `task_context.json`:
- Set `current_step_id` to `"inspect"`
- Set `steps.inspect` to `"completed"`
### Step 2: fix_loop

**Type:** loop
**Description:** Fix loop: each iteration picks the most critical issue, produces a remediation plan, waits for human approval on write operations, executes the fix, then re-inspects all hosts. Repeats until no issues remain or max iterations reached.


## Iteration Loop

**Goal:** host_issues.json has total_issues equal to 0 (all hosts healthy, no issues found)
**Max Iterations:** 10

> This step executes as a loop. The body steps repeat until the goal is met or max iterations reached.

## Loop Body (repeats each iteration)

#### Body Step 1: select_issue

**Type:** inline
**Description:** Select the single most critical issue from host_issues.json

**Execution:** Follow these instructions:

Read host_issues.json and schemas/selected_issue.schema.json.

Pick the SINGLE most critical issue using this priority order:
1. critical disk (highest priority)
2. critical service_down
3. critical memory
4. critical load
5. warning disk
6. warning service_down
7. warning memory
8. warning load (lowest priority)

Write the selected issue to selected_issue.json following the schema.

If host_issues.json has total_issues == 0, write {"done": true} instead.


**Output Files**
- `selected_issue.json`

#### Body Step 2: plan_action

**Type:** agent
**Description:** Analyze the selected issue and create a concrete remediation plan (no execution)

**Execution:** Launch an independent agent with the following prompt file:

Read selected_issue.json and schemas/pending_action.schema.json.

STEP 1 — Investigate: SSH to the target host and check the actual situation.
Understand the root cause before writing any plan. Do NOT guess or write generic commands.

STEP 2 — Plan: Based on your findings, write a concrete remediation plan
to pending_action.json following the schema.

Do NOT execute anything. Only investigate and write the JSON file.
If selected_issue.json contains {"done": true}, write {"done": true} to pending_action.json instead.


**Output Files**
- `pending_action.json`

#### Body Step 3: approve

**Type:** inline
**Description:** Human approval gate — present the remediation plan and wait for confirmation before executing

**Execution:** Follow these instructions:

Read pending_action.json.

If it contains {"done": true}, skip this step.

Otherwise, PRESENT the remediation plan from pending_action.json to the human:

---
## Awaiting Approval
Present the host, issue, risk level, and commands from pending_action.json.

Type "approve" to execute, or "reject" to skip this issue.
---

WAIT for the human to respond. Do NOT proceed without explicit approval.
If approved, copy pending_action.json to approved_action.json.
If rejected, write skip_action.json with {"status": "rejected", "reason": "rejected by human"}.


#### Body Step 4: execute

**Type:** agent
**Description:** Execute the approved remediation

**Execution:** Launch an independent agent with the following prompt file:

Check for approved_action.json. If it exists, read it.

If skip_action.json exists instead, do NOT execute — write execute_result.json following schemas/execute_result.schema.json with status "skipped".

Execute the remediation: SSH into the target host and run the commands listed in approved_action.json.

Rules:
- Use the exact commands from the plan, do not improvise
- If a command fails, do NOT retry
- After execution, verify the result (e.g., check service status, check disk usage)
- Write execute_result.json following schemas/execute_result.schema.json

If pending_action.json had {"done": true}, write {"status": "all_done"} to execute_result.json.


**Output Files**
- `execute_result.json`

#### Body Step 5: re_inspect

**Type:** script
**Description:** Re-run inspection to refresh the issue list

**Execution:** Execute the following command:
```bash
ansible-playbook -i {inventory} {playbook} 2>&1
mv /tmp/host_issues.json host_issues.json

```

**Output Files**
- `host_issues.json`

## Goal Evaluation

After all body steps complete, evaluate:

**Goal:** host_issues.json has total_issues equal to 0 (all hosts healthy, no issues found)

1. If goal IS met → mark this step completed, proceed to next step.
2. If goal NOT met and iterations remain → reset body steps, start next iteration.
3. If max iterations reached → mark step completed with status "max_iterations_reached", report what remains.

Append a summary to `iteration_history` after each iteration.

### Progress Tracking

After completing this step, update `task_context.json`:
- Set `current_step_id` to `"fix_loop"`
- Set `steps.fix_loop` to `"completed"`
### Step 3: generate_report

**Type:** agent
**Description:** Generate a polished HTML inspection and remediation report

## Execution
Launch an independent agent with the following prompt file:

**Dispatch instruction:**

Read the final host_issues.json to get the current health status.
Also read all execute_result.json files from the workspace to understand what was fixed.

Generate a single, self-contained, beautiful HTML report: health_report.html

The report should include:
- Overall health status (ALL CLEAR or ISSUES REMAINING)
- Summary stats: hosts checked, total issues found & resolved
- Remediation timeline: each iteration with host, issue, investigation findings,
  commands executed, and before/after comparison
- Final per-host status

Design requirements:
- Dark theme, modern dashboard style
- Use CSS grid/flexbox, no external dependencies
- Mobile-responsive
- Professional and visually impressive — this is a production report
- Include all CSS inline in a <style> tag


**Agent workflow:**

1. Prepare the execution environment

2. Execute the agent with the prompt

3. Complete execution

### Progress Tracking

After completing this step, update `task_context.json`:
- Set `current_step_id` to `"generate_report"`
- Set `steps.generate_report` to `"completed"`
