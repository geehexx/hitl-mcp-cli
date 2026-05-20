---
name: hitl-mcp-usage
description: Use hitl-mcp-cli tools correctly in multi-agent workflows. Covers when to call each tool, how to handle return values (timeout, cancel, elaborate, reject), and ergonomic patterns for orchestrators.
activation:
  - when: agent needs human input, confirmation, or approval
  - when: agent is about to take a destructive or irreversible action
  - when: agent receives {"action": "elaborate"} from a previous hitl call
  - when: agent receives {"status": "timeout"} and needs to re-block
  - when: orchestrator wants to pre-select a default for a time-sensitive decision
---

# hitl-mcp-usage skill

## Tool selection guide

| Situation | Tool |
|-----------|------|
| Need a text/path/multiline answer | `hitl_collect` or `hitl_ask` (alias) |
| Need user to pick from a list | `hitl_choose` |
| Need yes/no approval | `hitl_confirm` |
| Send a status update (non-blocking) | `hitl_notify` |
| Re-block on a timed-out question | `hitl_poll` |
| Question was malformed / unanswerable | `hitl_reject_question` |
| User asked for more context ("elaborate") | `hitl_request_elaboration` |
| Pre-select a default, user has 30s to override | `hitl_recommend` |

## Handling return values

Every blocking tool can return one of these sentinels — always check before using the value:

```python
result = await hitl_collect(message="Which branch?")

if isinstance(result, dict):
    match result.get("status") or result.get("action"):
        case "timeout":
            # Re-block: hitl_poll(question_id=result["question_id"])
            pass
        case "elaborate":
            # User wants more context — call hitl_request_elaboration
            pass
        case "cancel" | "rejected_question":
            # Abort or reformulate
            pass
        case "deferred":
            # Non-blocking question deferred to morning-batch JSONL
            pass
else:
    # result is the user's answer string
    use(result)
```

## Elaboration flow

```python
result = await hitl_collect(message="Which deployment target?", agent_name="deploy-agent")

if isinstance(result, dict) and result.get("action") == "elaborate":
    result = await hitl_request_elaboration(
        original_message="Which deployment target?",
        elaboration="Available targets: staging (us-east-1), prod (us-east-1, eu-west-1). "
                    "Staging is safe; prod requires approval from two reviewers.",
        question_id=result.get("question_id"),
        agent_name="deploy-agent",
    )
```

## Timeout + poll flow

```python
result = await hitl_confirm(
    message="Deploy to production?",
    severity="high",
    max_wait_minutes=5,
)

if isinstance(result, dict) and result.get("status") == "timeout":
    # Re-block for another 5 minutes
    result = await hitl_poll(
        question_id=result["question_id"],
        wait_minutes=5,
    )
```

## Quick recommendation (time-sensitive)

```python
result = await hitl_recommend(
    message="CI is green. Merge feat/my-feature to main?",
    recommendation="yes",
    choices=["yes", "no", "defer-24h"],
    override_seconds=30,
    agent_name="ci-orchestrator",
)
# result["status"] == "auto_accepted" | "user_selected" | "cancelled"
# result["value"] == the chosen option
```

## Rejecting a malformed question

```python
# Agent receives a question it cannot answer
result = await hitl_reject_question(
    reason="The question references 'the previous PR' but no PR context was provided. "
           "Please include the PR number or URL.",
    original_message=original_question,
    agent_name="reviewer-agent",
)
# Orchestrator sees {"status": "rejected_question", "reason": "..."}
```

## Urgency + morning-batch deferral

- `urgency="blocking"` (default) — always waits for user, even if TUI is unavailable.
- `urgency="soon"` — defers to `~/.local/state/hitl-deferred-questions.jsonl` when TUI is unavailable.
- `urgency="fyi"` — same as `"soon"` but lower priority.

Use `"soon"` / `"fyi"` for non-critical questions that can wait until the user is back.

## OS desktop notifications

`hitl_notify` and all blocking tools automatically fire a best-effort OS desktop
notification (via `notify-send` on Linux, `osascript` on macOS) when a question
is queued. No extra configuration needed.

## Severity levels for hitl_confirm

- `"low"` — informational, default yes
- `"medium"` — standard confirmation (default)
- `"high"` — red warning banner, requires typed confirmation; use for destructive/irreversible actions
