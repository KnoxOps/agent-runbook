---
name: restart-nginx
description: >-
  SSH into a server, restart Nginx, and verify it's back up
user-invocable: true
---

## Input Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| host | string | Yes | Target server hostname or IP |

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
    "restart": "pending",
    "verify": "pending"
  },
  "updated_at": "<ISO timestamp>"
}
```

Update this file after each step completes. On error, set step status to `"failed"` and overall `status` to `"failed"`.

### Step 1: restart

**Type:** agent
**Description:** SSH in and restart Nginx

## Execution
Launch an independent agent with the following prompt file:

**Dispatch instruction:**

SSH into {host} and run systemctl restart nginx

**Agent workflow:**

1. Prepare the execution environment

2. Execute the agent with the prompt

3. Write results to:
   - File: `restart_result.json`

## Output
- **Schema:** schemas/restart.schema.json
  - **File:** restart_result.json

### Progress Tracking

After completing this step, update `task_context.json`:
- Set `current_step_id` to `"restart"`
- Set `steps.restart` to `"completed"`
### Step 2: verify

**Type:** agent
**Description:** Verify Nginx is healthy

## Input Files
- `restart_result.json` (from Step restart, schema: schemas/restart.schema.json)

## Execution
Launch an independent agent with the following prompt file:

**Dispatch instruction:**

curl http://{host}/health and check the status code

**Agent workflow:**

1. Read input data from:
   - Schema: `schemas/restart.schema.json`

2. Execute the agent with the prompt

3. Write results to:
   - File: `verify_result.json`

## Output
- **Schema:** schemas/verify.schema.json
  - **File:** verify_result.json

### Progress Tracking

After completing this step, update `task_context.json`:
- Set `current_step_id` to `"verify"`
- Set `steps.verify` to `"completed"`