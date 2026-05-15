# Roadmap

## v1.0 line — foundation refactor

### v1.0.0rc1 (current — 2026-05-15)

- ✅ MCP three-primitive idiom refactor (tools / resources / prompts as separate packages)
- ✅ 4 new resources surfaced: `queue://pending`, `queue://history`, `session://activity`, `session://last-user-action-age`
- ✅ 4 new prompts: `hitl_architectural_fork`, `hitl_destructive_action`, `hitl_scope_clarification`, `hitl_panel_vote_summary`
- ✅ Property-based tests via hypothesis (queue invariants)
- ✅ Test stack: pytest + pytest-asyncio + pytest-textual-snapshot + hypothesis + schemathesis + tox

### v1.0 GA (when no breakage reported on rc)

- Bump to `1.0.0`. No code changes vs rc1 unless rc surfaces blockers.

## v1.1 — Elicitation + timeout-then-poll

- MCP elicitation surface (form mode with JSON Schema, URL mode for browser callbacks). Targets CC v2.1.76+ Elicitation hooks.
- Timeout-then-poll state machine: tools return `{"status": "timeout", "question_id": "...", "poll_url": "queue://question/<id>", "retry_after": ...}` on expiry; agent re-blocks via `hitl_poll`.
- Configurable wait-time settings: env `HITL_DEFAULT_WAIT_MIN`, `HITL_MIN_WAIT_MIN`, `HITL_MAX_WAIT_MIN`; per-call `max_wait_minutes` clamped within env range.
- User-availability resource: `session://user-availability` declaring user's "available for ≤N min" cap.
- Coverage gate raised to 80% line / 60% branch.

## v1.2 — auq feature parity + A2A

- auq-mcp-server feature parity:
  - Native OS notifications via `notify-send` / `osascript` / win32 native.
  - Question rejection with explanation (`{"status": "rejected_question", "reason": "..."}`).
  - Elaboration requesting from caller agent.
  - Quick recommendations auto-selection on time-pressed questions.
  - Agent-skills companion in `.claude/skills/hitl-mcp-usage/`.
- A2A v1.0 endpoint:
  - `POST /a2a/v1/tasks` for cross-agent question routing.
  - AgentCard at `/.well-known/agent.json` declaring `hitl-relay` capability.
  - `TaskStatusUpdateEvent` push semantics; first-event-is-task per a2aproject/A2A#716.
- phraseturner integration: every README / docstring / CHANGELOG change runs through phraseturner before commit.

## Post-1.2 (tracked, no committed schedule)

- Mobile-app HITL surface (HITL Relay-style; e2e encryption).
- Multi-host federation (hub + spoke pattern when N>5 agents).
- SQLite-WAL append-only event store (Beads-pattern) for cross-session question persistence.
- Schemathesis CI gate against the MCP JSON Schema spec.
