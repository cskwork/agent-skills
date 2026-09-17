# Standalone architecture

## Decision

The skill's default implementation has no MCP dependency and no agent-dashboard dependency. Stream Deck is the presentation and input device; a local daemon is the policy and execution boundary.

```text
              optional dynamic UI
Stream Deck ─────────────────────────► local SDK plugin
    │                                      │
    │ launcher-only tap                    │ HTTP on 127.0.0.1 + bearer token
    ▼                                      ▼
generated launcher ─────────────────► cockpitd
                                           │
                  predeclared operation ───┼──► terminal/multiplexer
                                           ├──► agent CLI
                  evidence report ─────────┘
```

## Components

### Cockpit config

Configuration version 3 defines sessions, reusable commands, controls, gesture mappings, and appearance. It does not encode physical key positions. The Stream Deck application remains responsible for where action instances are placed.

### `cockpitd`

The daemon:

- binds to loopback;
- loads the local config;
- generates/reads a file-backed token;
- exposes only named controls and state-report endpoints;
- executes configured argv arrays with `shell=False`;
- checks coarse adapter presence;
- retains semantic reports with timestamps and TTLs;
- never needs an LLM, cloud API, MCP server, or terminal-output scraper.

### `cockpitctl`

The CLI is the human/test/hook client. It can list controls, inspect state, invoke a gesture, and report semantic state. It sends the same API calls as the plugin.

### Launcher-only UI

Generated launchers call `cockpitctl invoke <controlId> --gesture tap`. The user maps a launcher with the built-in Stream Deck Open action. This is the minimum-dependency path.

### Native plugin UI

One generic local action stores a `controlId`. It polls state and sends gesture events. A Property Inspector edits the binding. The plugin contains no terminal or agent-specific logic.

## Ownership boundary

Owned:

- `.agent-cockpit` configuration and state;
- generated launchers;
- the Agent Cockpit plugin UUID and its action instances;
- an optional bundled profile explicitly shipped with this plugin.

Not owned:

- Stream Deck's internal profile database;
- unrelated profiles, pages, folders, actions, and third-party plugin settings;
- arbitrary invocation or reconfiguration of another plugin without a documented API;
- agent configuration outside explicit hook snippets requested by the user;
- terminal history or pane output.

Never reverse-engineer profile storage merely to automate layout. Ask the user to place the generic action, or produce an optional profile through supported SDK tooling.

## Mode selection

| Requirement | Launcher-only | Native plugin |
|---|---:|---:|
| Tap launch/focus | Yes | Yes |
| Static custom icon in Stream Deck app | Yes | Yes |
| Dynamic title/icon | No | Yes |
| Semantic state display | No | Yes |
| Long press | No | Yes |
| Dial rotation/press | No | Yes, when implemented from current encoder scaffold |
| Property Inspector | No | Yes |
| MCP required | No | No |

Prefer launcher-only until a dynamic requirement is concrete.

## Failure behavior

- Daemon unavailable: launcher exits non-zero; plugin displays unavailable/error.
- Token mismatch: request rejected; plugin displays unauthorized rather than retrying with no auth.
- Missing session: `focus_or_launch` invokes configured launch, then focus.
- Stale semantic report: falls back to coarse adapter state.
- Unknown control ID: rejected without executing anything.
- Command timeout/failure: returned as an operation failure; never rendered as success.
