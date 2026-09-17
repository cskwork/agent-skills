# Verification and rollback

## Automated checks

From the skill root:

```bash
python3 -m compileall -q bin scripts tests
python3 -m unittest discover -s tests -v
python3 scripts/validate_cockpit.py assets/cockpit.example.json
python3 scripts/smoke_test.py
```

Expected properties:

- valid configuration passes;
- unknown controls are rejected;
- unauthenticated protected requests are rejected;
- raw commands cannot arrive through invocation JSON;
- confirmed destructive gestures require `confirmed: true`;
- explicit state reports are returned before TTL;
- stale reports fall back to coarse state;
- commands execute without a shell;
- launcher generation contains only configured control IDs.

## Environment check

```bash
python3 scripts/probe_environment.py --json
```

Record the installed versions separately when they materially affect commands or plugin APIs.

## Daemon smoke check

```bash
python3 bin/cockpitd.py --config ~/.agent-cockpit/cockpit.json
python3 bin/cockpitctl.py --config ~/.agent-cockpit/cockpit.json health
python3 bin/cockpitctl.py --config ~/.agent-cockpit/cockpit.json controls
```

Then invoke one harmless test control.

## Agent-session checks

For every configured agent:

1. Ensure the session is absent.
2. Tap once; confirm the correct session launches.
3. Tap again; confirm the intended terminal/session becomes active without a duplicate process.
4. Report `running`; confirm the plugin shows it with a reported source.
5. Stop reports and wait beyond TTL; confirm the UI falls back to coarse state.
6. Hold interrupt; confirm only the target session receives it.
7. Restart the terminal; confirm durable session behavior matches the chosen adapter.

Never claim step 3 passed merely because launch returned exit code 0.

## Attached-session checks

When slots bind to sessions the user started by hand:

1. Start a new agent session; confirm it claims a free slot and no other slot changes.
2. Confirm the recorded tty matches the pane the emulator reports, not the agent's own tty.
3. Tap the slot; confirm the correct pane comes forward. Embedded AppleScript is only a string until something runs it, so a syntax error survives every static check and surfaces only here — run `osacompile -o /dev/null -` over each script when changing one.
4. Tap an unclaimed slot; confirm an honest failure rather than a silent no-op.
5. Close the pane; confirm the slot probe reports `offline` within one poll.
6. Fill every slot, then start one more session; confirm no live claim is evicted.
7. Confirm a `Notification` event moves the key to `needs_attention` and that `Stop` clears it.

Sessions started before the hook bridge was installed will not appear. State that as a limitation instead of retrying.

## Herdr attached-session checks

Run these from a Herdr-managed pane after `test "${HERDR_ENV:-}" = 1` passes:

1. Run `herdr agent list`; record the agent-session id and current pane id for
   every deck-backed Claude/Codex session.
2. Confirm the corresponding claim stores that agent-session id and Herdr
   metadata. A duplicate tty is not an error when the Herdr ids differ.
3. Tap a key from a different Herdr tab; confirm its current agent pane is
   foreground. The daemon command must use `herdr agent focus <pane-id>`.
4. Move an agent to another pane, tap its existing key, and confirm the new
   pane is focused. This proves the adapter resolves live agent-session ids
   rather than replaying an old pane id.
5. End the agent, tap its old key, and confirm a visible failure with no other
   pane focused.
6. Restart Herdr, repeat steps 1–4, and re-run the hooks/migration if a
   particular agent session has been replaced.

When a hook ends, it clears the cached semantic report through the local daemon.
For an older claim removed during migration, clear its old display state with:

```bash
python3 ~/.agent-cockpit/bin/cockpitctl.py clear session.claude.slot1
```

For Codex CLI, inspect `~/.codex/hooks.json`, review the new command in Codex's
`/hooks` screen, and restart the session once. Codex hook trust is separate from
the file being present; an unreviewed hook does not claim a slot.

With `--extended` registered, also confirm the two states the default set cannot
reach. Feed the bridge a payload directly rather than waiting for the condition:

```bash
echo '{"session_id":"CHECK","hook_event_name":"PermissionDenied"}' | python3 bin/claude_hook.py
echo '{"session_id":"CHECK","hook_event_name":"StopFailure"}'     | python3 bin/claude_hook.py
```

The control must move to `blocked` and then `failed`, with `source` reading
`claude-hook` and `evidenceTier` reading `reported`. Afterwards send
`SessionEnd` for the same id and post a report with `ttl: 5` so the test state
expires instead of sitting on the key for its full TTL. TTLs below 5 seconds are
rejected, so a smaller value silently leaves the state in place.

## Windows Terminal checks

1. Focus a tab by its exact title; confirm the right tab comes forward.
2. Change the tab title, then repeat with the old title; confirm a non-zero exit and no focus change.
3. Confirm the title is unique across open tabs — the first match wins.

## Plugin checks

- Invalid/missing `controlId` is visible.
- Stopped daemon is visible.
- Bad token is visible.
- Short press emits only tap.
- Long press emits only longPress.
- Polling stops when action disappears.
- Multiple instances do not leak timers.
- Titles/icons fit on actual keys.
- Encoder feedback and rotation direction are correct on target hardware.
- Stream Deck restart reconnects cleanly.
- Key text is drawn once, not doubled by both an image and a title.
- The longest status label still fits the key without truncation.

After any plugin code change, confirm the reload before re-checking hardware: a
fresh `Plugin connected` entry with a newer timestamp in the application log.
`streamdeck restart` reports success even when nothing was replaced, and
continued daemon polling only proves the *old* process is alive.

## Rollback

Runtime:

```bash
rm -rf ~/.agent-cockpit
```

Skill installs:

```bash
rm -rf ~/.claude/skills/streamdeck-agent-cockpit
rm -rf ~/.agents/skills/streamdeck-agent-cockpit
rm -rf ~/.jcode/skills/streamdeck-agent-cockpit
```

Plugin/profile:

- remove Agent Cockpit actions/profile through the Stream Deck application;
- uninstall only the Agent Cockpit plugin;
- restore only backups created by this skill's installer.

Do not restore or overwrite unrelated Stream Deck profile data.

## Evidence wording

Report results as:

- **Verified locally** — automated command and observed result.
- **Verified on device** — physical Stream Deck and terminal behavior observed.
- **Configured but unverified** — exact remaining external/device check.
- **Unsupported** — capability absent; fallback stated.
