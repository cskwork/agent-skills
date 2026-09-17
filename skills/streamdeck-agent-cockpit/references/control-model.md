# Control model

## Logical identity

A control is addressed by a stable logical ID such as `session.codex.review`. Its physical location is chosen in the Stream Deck application. This avoids coupling the runtime to device geometry, pages, folders, or profile internals.

Recommended namespace:

```text
session.<agent>.<purpose>
workflow.<domain>.<action>
nav.<destination>
system.<safe-action>
```

Use lowercase ASCII letters, digits, dots, underscores, and hyphens.

## Core objects

### Sessions

A session describes:

- human label;
- agent type;
- adapter and target;
- `launch`, `focus`, optional `resume`, and `interrupt` command definitions;
- progress source and staleness policy.

### Commands

A command is a reusable, named argv definition for non-session workflows. A control references the command ID; it never provides arbitrary argv in an invocation request.

### Controls

A control binds gestures to named operations.

```json
{
  "kind": "session",
  "session": "session.codex.main",
  "title": "Codex",
  "gestures": {
    "tap": {"operation": "focus_or_launch"},
    "longPress": {
      "operation": "interrupt",
      "confirmation": "hold"
    }
  }
}
```

Supported reference operations:

| Operation | Target | Meaning |
|---|---|---|
| `focus_or_launch` | session | Probe; launch if absent; focus |
| `focus` | session | Run configured focus command |
| `launch` | session | Run configured launch command |
| `resume` | session | Run a locally verified resume command |
| `interrupt` | session | Send the configured non-kill interrupt |
| `run` | named command | Run a reusable configured command |

## Gestures

Canonical gesture names:

```text
tap · longPress · dialPress · dialLeft · dialRight
```

A plugin can translate SDK events into these names. Launcher-only mode emits `tap` only.

Use hold or explicit confirmation for any action whose accidental invocation has material impact. Examples: interrupting a live agent, deploy, merge, delete, stop service, and sending a message.

## Appearance

Appearance maps verified state to presentation. Keep it declarative:

```json
{
  "defaultTitle": "Codex",
  "showSource": true,
  "showAge": true,
  "states": {
    "running": {"titleSuffix": "RUN"},
    "needs_attention": {"titleSuffix": "CHECK"},
    "present": {"titleSuffix": "READY"},
    "offline": {"titleSuffix": "OFF"}
  }
}
```

Do not place commands, secrets, or state inference rules in appearance.

## Suggested first deck

| Control ID | Tap | Hold | State |
|---|---|---|---|
| `session.claude.main` | Focus or launch | Interrupt | Reporter, then tmux fallback |
| `session.codex.main` | Focus or launch | Interrupt | Reporter, then tmux fallback |
| `session.pi.main` | Focus or launch | Interrupt | Reporter, then tmux fallback |
| `session.jcode.main` | Focus or launch | Interrupt | Reporter, then tmux fallback |

Add project/workflow controls only after these four are reliable.
