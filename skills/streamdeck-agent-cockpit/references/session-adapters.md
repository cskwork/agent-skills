# Session adapters

## Contract

Every adapter must provide or explicitly omit these capabilities:

```text
probe(target)      -> coarse existence/availability evidence
launch(session)    -> start the configured agent/session
focus(session)     -> bring the intended terminal/session to the user
resume(session)    -> optional, only with locally verified CLI syntax
interrupt(session) -> graceful, scoped interrupt
report(event)      -> optional semantic state source
```

A process probe is not a semantic event source.

## Default tmux adapter

The reference config uses named tmux sessions because they survive terminal-window changes and expose a simple existence probe.

- Probe: `tmux has-session -t <target>`.
- Launch: configured `tmux new-session` argv.
- Focus: `focus_tmux.py` or another explicit terminal command.
- Interrupt: `tmux send-keys -t <target> C-c`.

`focus_tmux.py` opens or activates a compatible terminal path; verify the selected terminal in practice. A successful tmux command does not prove the intended GUI window is foreground.

## Agent-specific guidance

| Agent | Baseline session behavior | Rich state option |
|---|---|---|
| Claude Code | Start its installed CLI inside a named terminal session | Configure a reviewed local hook/event bridge when supported by the installed version |
| Codex | Start its installed CLI inside a named terminal session | Configure a reviewed notify/event bridge when supported by the installed version |
| Pi | Start the CLI normally; use the same generic session contract | A local RPC/event adapter may translate documented events into reports |
| JCode | Start or connect using syntax verified from the installed CLI | A local server/SDK adapter may translate documented lifecycle events into reports |

Do not hard-code remembered resume flags. Run each installed binary's `--help`, inspect its local configuration, and then record the exact verified command as argv.

## Generic command adapter

When tmux is unavailable, define:

- a probe command whose exit code 0 means present;
- launch/focus/interrupt command arrays;
- optional semantic reporter integration.

This supports WezTerm workspaces, iTerm automation, Windows Terminal, SSH jump hosts, or a custom session manager without changing the daemon API.

## Herdr-managed tabs and panes

Herdr is a session manager, so its installed CLI and runtime context are the
authority for tab/pane identity and focus behavior. Before configuring or
testing a Herdr adapter, verify that the calling pane is Herdr-managed:

```bash
test "${HERDR_ENV:-}" = 1
```

If that check fails, stop the Herdr-specific setup. An outside process may see
terminal processes, but it cannot safely prove which Herdr tab or pane should
receive focus.

The bundled adapter uses these verified Herdr commands:

```text
herdr agent list
herdr agent focus <pane-id>
```

`claude_hook.py` and `codex_hook.py` capture the inherited workspace/tab/pane
metadata when present. `focus_herdr.py` and `herdr_claim_probe.py` do **not**
trust that stored pane id: on each action they resolve the claim's
`agentSessionId` through the live agent list, check the agent kind, then focus
the resolved pane. This follows a moved agent and refuses to focus a pane when
the claimed agent session has ended.

Install the runtime scripts and convert only predeclared attached slots:

```bash
python3 scripts/install_runtime.py --target ~/.agent-cockpit --update-runtime
python3 scripts/configure_herdr_sessions.py --apply
```

The config uses fixed argv arrays equivalent to:

```json
{
  "probe": {
    "argv": ["/usr/bin/env", "python3", "~/.agent-cockpit/bin/herdr_claim_probe.py", "--slot", "session.claude.slot1"]
  },
  "focus": {
    "argv": ["/usr/bin/env", "python3", "~/.agent-cockpit/bin/focus_herdr.py", "--slot", "session.claude.slot1"]
  }
}
```

Use `migrate_herdr_claims.py --agent <claude|codex>` to adopt claims created
by older tty-only releases. Add `--claim-unclaimed` to attach live Herdr agents
that predate the hook bridge, and `--drop-unmatched` to remove stale claims in
only the selected agent namespace. Both changes are explicit; the default is
read-only.

Keep the Claude/Codex hook slot ID separate from the Herdr focus target. The
hook supplies semantic status; Herdr supplies navigation. Tap each control
from another tab and observe the intended pane become foreground. A zero exit
code or a running process is insufficient evidence.

Do not claim Herdr per-tab switching is configured or verified from a session
where `HERDR_ENV` is absent. Report it as configured-but-unverified until the
foreground checks above pass inside Herdr.

## Attaching to sessions the user already started

A cockpit that can only drive sessions it launched is half a cockpit. Most agent
work already runs in terminal tabs the user opened by hand. Attaching to those
is possible, but it is structurally weaker than a named multiplexer session and
the design has to admit that.

Three constraints drive the shape:

1. **The daemon rejects reports for sessions absent from `cockpit.json`.** An
   arbitrary session cannot register itself. Predeclare a fixed set of *slots*
   (`session.<agent>.slot1` … `slotN`) and let a hook bind a live session id to
   a free slot. Raising the count is a config edit, not a code change.
2. **Agent CLIs are often launchers.** Claude Code execs `node`, so walking the
   process ancestry and matching on the command name fails. Anchor liveness on
   the `login` ancestor instead: it exits exactly when the terminal pane closes.
3. **The pane tty is not always the agent tty.** A shell wrapper can allocate an
   inner pty that the terminal emulator never sees, so `iTerm2` reports
   `/dev/ttys002` while the agent runs on `/dev/ttys003`. Record the tty of the
   `login` ancestor, which is the one the emulator knows.

`slotclaims.py` implements the bookkeeping, `claim_probe.py` the coarse probe,
and `focus_terminal.py` the focus operation. Slots use the generic `command`
adapter:

```json
"adapter": {
  "type": "command",
  "probe": { "argv": ["/usr/bin/env", "python3", "~/.agent-cockpit/bin/claim_probe.py",
                      "--slot", "session.claude.slot1"] }
}
```

Never evict a live claim to make room. A key that silently switches to a
different session is worse than a session that is simply not shown.

Slot discovery is POSIX-only. Ancestry walking needs `ps` and a tty;
`slotclaims._ps` returns `None` on other platforms rather than risking a
blocking subprocess. Liveness itself is cross-platform: `pid_alive` uses
`os.kill(pid, 0)` on POSIX and `OpenProcess`/`GetExitCodeProcess` on Windows,
where `ERROR_ACCESS_DENIED` still proves the process exists.

### Windows Terminal

Windows Terminal exposes no scriptable tty, so tty matching has nothing to match
on. A tab is addressed by its exact title instead:

```text
focus_terminal.py --tab-title "Claude · Main"
```

`windows_terminal_uia.ps1` walks the UI Automation tree for a `TabItem` whose
name matches exactly, selects it, and raises the window. Matching is
case-sensitive and the script exits non-zero when nothing matches, so a stale
title fails loudly instead of focusing the wrong tab.

Because the title is supplied rather than discovered, this path does not consult
slot bookkeeping — it works whether or not a claim exists, and correspondingly
proves nothing about the session behind the tab. Set the title deliberately (the
tab title is under the user's control) and keep it unique.

### macOS terminal automation

iTerm2 and Apple Terminal both expose a documented `tty` property through
AppleScript, which is what makes tty matching viable. The iTerm2 adapter targets
the stable bundle identity `com.googlecode.iterm2`, so it also works when the
application is installed as `iTerm.app` rather than `iTerm2.app`.
`focus_terminal.py` tries each running application in turn and exits non-zero
when no pane matches, so a missing window reports an honest failure instead of a
false success.

Automation permission is requested by macOS on first use and is granted to the
*calling* process, not to the cockpit. Verify focus from the daemon's own
context, not only from an interactive shell.

Do not add an interrupt gesture to an attached slot unless the terminal offers a
supported way to send a scoped `Ctrl-C`. AppleScript `write text` is not that:
it types into the session rather than signalling it. Leaving interrupt off a
slot is the honest default; interrupt stays available on multiplexer-backed
sessions, where `tmux send-keys` is exact.

## Focus behavior

“Switch session” can mean different things:

1. Switch the active pane within an already attached multiplexer client.
2. Focus an existing terminal window/tab.
3. Open a new terminal tab attached to the durable session.

Resolve this explicitly. The reference helper chooses option 3 when a direct existing-client target is unavailable because it is deterministic. If the user requires option 1 or 2, implement the terminal's supported automation API and verify foreground focus.

## Interrupt versus kill

An interrupt should be scoped to the intended session and normally map to Ctrl-C or an agent-native cancel operation. It may still discard in-flight work, so require hold/explicit confirmation.

A process kill is a different, higher-risk operation. Do not include it by default. If required, add a separate control with stronger confirmation and a documented recovery path.
