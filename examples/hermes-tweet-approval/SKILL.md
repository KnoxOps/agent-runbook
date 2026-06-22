---
name: hermes-tweet-approval
description: >-
  Install Hermes Tweet, gather read-only X context, and prepare an approval packet before any action.
user-invocable: true
---

## Input Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| objective | string | Yes | The social workflow goal, such as launch monitoring or reply drafting. |
| runtime_host | string | No | Hermes runtime host where plugins execute. |

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
    "install": "pending",
    "read_context": "pending",
    "approval_packet": "pending"
  },
  "updated_at": "<ISO timestamp>"
}
```

Update this file after each step completes. On error, set step status to `"failed"` and overall `status` to `"failed"`.

### Step 1: install

**Type:** inline
**Description:** Install and enable Hermes Tweet on the Hermes runtime host.

## Execution
Follow these instructions:

Install Hermes Tweet on {runtime_host} if it is not already present.

Commands to prefer:
- hermes plugins install Xquik-dev/hermes-tweet --enable
- hermes plugins enable hermes-tweet
- hermes plugins list
- hermes tools list

Do not print, request, or store API key values in chat. If XQUIK_API_KEY is missing, tell the human to set it in the runtime environment or ~/.hermes/.env.


### Progress Tracking

After completing this step, update `task_context.json`:
- Set `current_step_id` to `"install"`
- Set `steps.install` to `"completed"`
### Step 2: read_context

**Type:** agent
**Description:** Gather read-only X context through Hermes Tweet.

## Execution
Launch an independent agent with the following prompt file:

**Dispatch instruction:**

Use Hermes Tweet for objective: {objective}

Required sequence:
1. Use tweet_explore to find relevant search, trend, account, or monitor routes.
2. Use tweet_read only when XQUIK_API_KEY is configured.
3. Do not call tweet_action.
4. Write a short markdown summary to read_context.md with route names, evidence gathered, gaps, and recommended next action.


**Agent workflow:**

1. Prepare the execution environment

2. Execute the agent with the prompt

3. Complete execution

### Progress Tracking

After completing this step, update `task_context.json`:
- Set `current_step_id` to `"read_context"`
- Set `steps.read_context` to `"completed"`
### Step 3: approval_packet

**Type:** inline
**Description:** Prepare an explicit approval packet for any requested X action.

## Execution
Follow these instructions:

Read read_context.md and create approval_packet.md.

The packet must include:
- Objective and target account or route.
- Evidence summary from read-only calls.
- Exact proposed tweet, reply, DM, follow, monitor, media, or webhook change.
- Required environment gate: HERMES_TWEET_ENABLE_ACTIONS=true.
- Human approval checkbox.
- A rule that action calls must not be retried after auth, policy, or permission errors.

Do not enable actions. Do not call tweet_action.


### Progress Tracking

After completing this step, update `task_context.json`:
- Set `current_step_id` to `"approval_packet"`
- Set `steps.approval_packet` to `"completed"`