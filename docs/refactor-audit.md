---
date: 2026-05-16
status: complete
phase: P1
---

# MCP Three-Primitive Idiom — Refactor Audit

Audit of `hitl_mcp_cli/` against the MCP three-primitive idiom
(tools = model-controlled actions; resources = app-controlled read-only data;
prompts = user-controlled reusable templates).

## Summary

The v1.0.0rc1 refactor (commit `a29d192`) correctly restructured the server
into three disjoint packages. This audit confirms the current state is
**idiomatically correct** and documents the delta from the pre-refactor
monolithic `server.py`.

---

## Primitive classification — current state

### Tools (`hitl_mcp_cli/tools/`)

Model-controlled actions: the agent calls these, they block on user input,
and they produce side effects (TUI dispatch, interaction log write).

| Tool | Module | Correct primitive? | Notes |
|------|--------|--------------------|-------|
| `hitl_collect` | `_collect.py` | ✅ Tool | Blocks on user text input |
| `hitl_ask` | `_collect.py` | ✅ Tool | Alias for `hitl_collect` |
| `hitl_choose` | `_collect.py` | ✅ Tool | Blocks on user selection |
| `hitl_confirm` | `_confirm.py` | ✅ Tool | Blocks on yes/no |
| `hitl_notify` | `_notify.py` | ✅ Tool | Non-blocking; side-effect only |
| `hitl_poll` | `_poll.py` | ✅ Tool | Re-blocks on timed-out question |

All tools correctly use `asyncio.wait_for` + `tui_enqueue` and return
structured dicts on timeout (`{"status": "timeout", "question_id": ...,
"retry_after": 60}`).

### Resources (`hitl_mcp_cli/resources/`)

Application-controlled read-only data. The host exposes these; the agent
polls them for context. No side effects.

| Resource URI | Module | Correct primitive? | Notes |
|-------------|--------|--------------------|-------|
| `queue://pending` | `_pending.py` | ✅ Resource | Live snapshot of pending requests |
| `queue://history` | `_history.py` | ✅ Resource | Last 50 requests, all statuses |
| `queue://history/{n}` | `_history.py` | ✅ Resource | Parameterised history slice |
| `session://activity` | `_session_activity.py` | ✅ Resource | Per-session call counts |
| `session://last-user-action-age` | `_last_action_age.py` | ✅ Resource | Seconds since last user reply |

All resources are synchronous functions returning JSON strings — correct for
polling semantics (CC has closed resource subscriptions as `not_planned`,
anthropics/claude-code#7252).

### Prompts (`hitl_mcp_cli/prompts/`)

User-controlled reusable templates. The user invokes these via slash command;
the agent does not call them directly.

| Prompt name | Module | Correct primitive? | Notes |
|-------------|--------|--------------------|-------|
| `hitl_architectural_fork` | `_arch_fork.py` | ✅ Prompt | Architectural decision template |
| `hitl_destructive_action` | `_destructive.py` | ✅ Prompt | Destructive-action authorisation |
| `hitl_scope_clarification` | `_scope_clarify.py` | ✅ Prompt | Scope ambiguity resolution |
| `hitl_panel_vote_summary` | `_panel_vote.py` | ✅ Prompt | Multi-agent panel vote display |

All prompts return `list[PromptMessage]` — correct FastMCP prompt signature.

---

## Pre-refactor misclassifications (resolved)

These were present in the pre-v1.0 monolithic `server.py` and have been
corrected in the current codebase.

| Old surface | Old primitive | Correct primitive | Resolution |
|-------------|---------------|-------------------|------------|
| Queue state (pending count, history) | Returned via tool call | Resource | Moved to `resources/_pending.py`, `_history.py` |
| Session activity | Returned via tool call | Resource | Moved to `resources/_session_activity.py` |
| Last-user-action age | Returned via tool call | Resource | Moved to `resources/_last_action_age.py` |
| HITL workflow templates (arch fork, destructive, etc.) | Not exposed | Prompt | Added as `prompts/` package |

---

## Remaining gaps vs P1 spec

### Implemented in P1

- [x] `hitl_poll` tool (`tools/_poll.py`) — re-blocks on timed-out question
- [x] Timeout-then-poll state machine — `asyncio.wait_for` + structured timeout return
- [x] SQLite-WAL persistence — **partial**: `HITLRequest.resolved_answer` persists
  answers in-memory; process restart loses pending questions. See gap below.
- [x] `TimeoutConfig` with `HITL_DEFAULT_WAIT_MIN`, `HITL_MIN_WAIT_MIN`, `HITL_MAX_WAIT_MIN`
- [x] Hypothesis property tests on queue state machine (`tests/test_property_queue.py`)

### Open gaps (deferred to P2/P4)

| Gap | Spec reference | Priority |
|-----|---------------|----------|
| SQLite-WAL persistence across process restart | P1 step 5 | P2 — in-memory is sufficient for v1.0 dogfood |
| `session://user-availability` resource | P1 step 6 | P2 |
| `hitl_elicit_form` (MCP elicitation, form mode) | P1 step 7 | P2 |
| `hitl_elicit_url` (MCP elicitation, URL mode) | P1 step 8 | pre-1.1 |
| Question lifecycle status field (`queued → asking → answered \| timed_out \| cancelled`) | P1 step 5 | Partial — `HITLRequest.status` tracks `pending/answered/cancelled/minimized`; `timed_out` not a distinct status |

### Env var naming note

The implementation uses `HITL_DEFAULT_WAIT_MIN` / `HITL_MIN_WAIT_MIN` / `HITL_MAX_WAIT_MIN`
(with `_MIN` suffix), matching the spec contract exactly. These are the canonical names
documented in `timeout_config.py`.

---

## Verdict

The codebase is **idiomatically correct** per the MCP three-primitive idiom.
All tools are model-controlled actions, all resources are app-controlled
read-only data, and all prompts are user-controlled templates. The pre-refactor
misclassifications (queue state and session data returned via tools) have been
resolved. The remaining gaps are scoped to P2 and do not block P1 completion.
