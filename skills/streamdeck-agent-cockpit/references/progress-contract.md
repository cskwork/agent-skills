# Progress and state contract

## Principle

Display only what the evidence supports. The UI must preserve the difference between infrastructure presence and agent lifecycle state.

## Evidence tiers

| Tier | Source | Allowed claims |
|---|---|---|
| `reported` | Agent hook, RPC/event adapter, workflow callback, explicit reporter | Exact reported semantic state and optional explicit progress |
| `coarse` | tmux/process/probe exit code | Present, offline, or unavailable only |
| `stale` | Expired semantic report plus current probe | Coarse state, with last report marked stale |
| `unknown` | No valid report and no working probe | Unknown/unavailable |

## Semantic states

Accepted reference states:

```text
idle
running
needs_attention
blocked
succeeded
failed
```

Reports may carry:

- a short label;
- a redaction-safe detail;
- explicit progress from 0 through 100;
- TTL in seconds;
- source metadata.

Do not report prompt text, generated code, terminal output, tokens, secrets, customer data, or file contents to a key label.

## Coarse states

```text
present
offline
unavailable
```

`present` means only that the configured session/probe exists. It must not be renamed to “working”, “idle”, or “ready for input” unless a semantic event says so.

## TTL and staleness

Every semantic report expires. After expiration:

1. preserve its timestamp as historical metadata;
2. mark it stale;
3. run the coarse adapter probe;
4. render only the coarse result.

This prevents a key from remaining “running” after an agent, hook, daemon, or terminal failure.

## Claude Code hook mapping

`claude_hook.py` is the reference event source. Every state it reports comes
from a hook event; terminal titles are never scraped. A title may look like a
usable signal — Claude Code writes a spinner and the current task into it — but
it cannot distinguish "thinking" from "waiting for approval", and a wrong green
light is worse than no light.

Registered by default:

| Hook event | State | TTL | Meaning |
|---|---|---|---|
| `SessionStart` | `idle` | 7200 | Session exists, not working |
| `UserPromptSubmit` | `running` | 1800 | A turn is in flight |
| `Notification` | see below | 3600 | Usually blocked on the user |
| `Stop` | `idle` | 7200 | Turn finished, user's move |
| `SessionEnd` | — | — | Releases the slot; key falls back to coarse |

`Stop` means the turn ended, not that the user's task succeeded, so it reports
`idle` rather than a success state.

Added by `install_claude_hooks.py --extended`:

| Hook event | State | TTL |
|---|---|---|
| `PreToolUse`, `PostToolUse`, `PostToolUseFailure` | `running` | 1800 |
| `PermissionRequest` | `needs_attention` | 3600 |
| `PermissionDenied` | `blocked` | 3600 |
| `Elicitation` | `needs_attention` | 3600 |
| `ElicitationResult` | `running` | 1800 |
| `SubagentStart`, `SubagentStop` | `running` | 1800 |
| `TaskCreated`, `TaskCompleted` | `running` | 1800 |
| `PreCompact`, `PostCompact` | `running` | 1800 |
| `StopFailure` | `failed` | 3600 |

These are opt-in because they run the bridge on every tool call. `blocked` and
`failed` are only reachable with them registered.

`Notification` carries a documented `notification_type`; match it exactly when
present and fall back to the message text otherwise. `permission_prompt`,
`idle_prompt`, `agent_needs_input`, and `elicitation_dialog` mean
`needs_attention`; `elicitation_complete` means `running`; `agent_completed`
means `idle`.

**Verify event names against the installed build, never from memory.** A hook
registered under a name the harness does not dispatch fails silently — the key
simply never updates, which is indistinguishable from an idle session. The names
above were each confirmed in the hook reference Claude Code ships or by its
dispatcher symbol.

The label carries the project directory name, not prompt text, file contents, or
model output. See the redaction rule above.

Two consequences worth stating to the user:

- **A turn longer than the `running` TTL falls back to coarse state.** That is
  correct behaviour, not a bug: the last evidence has expired. Raise the TTL
  only if long turns are routine.
- **Hooks are read when a session starts.** Sessions already running when the
  bridge is installed are not visible until they restart.

Register the bridge with `install_claude_hooks.py`, which is append-only and
idempotent. Other agents need their own bridge: the slot and focus machinery is
agent-neutral, only the event mapping is not.

## Percentages

A progress percentage is valid only when explicitly emitted from a measurable workflow, such as 27 of 40 tests or 8 of 10 files processed. Never derive it from elapsed time, token count, terminal activity, number of log lines, or model prose.

## Recommended rendering

| State | Primary title | Secondary metadata |
|---|---|---|
| `running` | Configured short label | Activity label, age |
| `needs_attention` | `CHECK` | Session label |
| `blocked` | `BLOCKED` | Redaction-safe reason |
| `succeeded` | `DONE` | Age; expires to coarse state |
| `failed` | `FAILED` | Age; details remain off-device |
| `present` | Session label | `present · coarse` |
| `offline` | Session label | `offline` |
| `unavailable` | `NO LINK` | Daemon/adapter source |

The source tier should be inspectable in the Property Inspector or CLI even when omitted from the small key display.
