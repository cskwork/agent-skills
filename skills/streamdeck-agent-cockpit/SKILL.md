---
name: streamdeck-agent-cockpit
description: "Use when a user wants a standalone Stream Deck cockpit for Claude Code, Codex, Pi, JCode, or other terminal agents: personalize buttons, launch/focus/resume/interrupt named sessions, display trustworthy local status, create or extend a Stream Deck plugin, or map recurring local workflows to controls. The core path must work without streamdeck-mcp, any MCP server, AgentDeck, or a cloud service."
---

# Stream Deck Agent Cockpit

Build and maintain one **standalone, locally controlled** Stream Deck cockpit for terminal-based coding agents and personal automations.

## Non-negotiable architecture

The core path is:

```text
Stream Deck action or launcher
        ↓
local cockpit daemon (`cockpitd`)
        ↓
predeclared command/session adapter
        ↓
Claude Code · Codex · Pi · JCode · another CLI
```

- Do not require `streamdeck-mcp`, another MCP server, AgentDeck, or a model at runtime.
- Use the official Stream Deck SDK only when dynamic labels, icons, dials, long-press handling, or live state are needed.
- Launcher-only mode must remain usable for static tap actions without compiling a plugin.
- Own only this skill's config, daemon, launchers, plugin UUID, action instances, and optional bundled profile. Do not edit undocumented Stream Deck profile stores by default. When the user explicitly asks to edit a user-owned macOS v3 profile page, use the guarded `scripts/streamdeck_profile.py` helper after creating a backup; never edit the profile registry or unrelated pages/actions.
- Do not promise generic control of third-party Stream Deck plugins. Integrate them only through a documented plugin/service API or a user-configured Stream Deck Multi Action.
- Bind controls by stable logical `controlId`, never by physical row/column coordinates in the cockpit config.
- Execute only commands declared in local configuration. Never accept arbitrary shell text from a button press or HTTP request.
- Bind the daemon to loopback and authenticate local requests with a file-backed token.
- Never infer “thinking”, “done”, “blocked”, a percentage, or semantic progress from process presence, elapsed time, terminal title, or scraped terminal text.

## Read only what the task needs

| Need | Read |
|---|---|
| Architecture or mode selection | `references/architecture.md` |
| Configuring buttons and gestures | `references/control-model.md` |
| Claude/Codex/Pi/JCode sessions | `references/session-adapters.md` |
| Herdr workspace/tab/pane switching | `references/session-adapters.md` |
| Status and progress semantics | `references/progress-contract.md` |
| Building or extending the plugin | `references/plugin-playbook.md` |
| Security review | `references/safety.md` |
| Final checks and rollback | `references/verification.md` |

## Workflow

### 1. Orient before changing anything

Inspect the local environment and the closest existing implementation:

```bash
python3 scripts/probe_environment.py --json
```

Determine:

- OS and Stream Deck application availability.
- Device model only when it changes the design; do not assume key count or encoder support.
- Installed terminal and multiplexer: `tmux`, WezTerm, iTerm2, Terminal, Windows Terminal, or another explicit target.
- Installed agent commands and their **local** `--help` output. Do not assume resume/server flags from memory.
- Existing `.agent-cockpit/cockpit.json`, plugin source, launchers, or profile owned by this project.
- Which signals can report semantic state. If none exist, plan coarse state only.

Produce a short capability ledger:

| Capability | Available | Evidence | Chosen fallback |
|---|---:|---|---|
| Static tap action | | | |
| Named session launch | | | |
| Session focus | | | |
| Safe interrupt | | | |
| Dynamic key rendering | | | |
| Semantic state events | | | |
| Encoder support | | | |

### 2. Choose the smallest mode that satisfies the request

**Launcher-only mode**

Use Stream Deck's built-in action to open generated `.command`/`.cmd` launchers. Choose this when static tap actions are sufficient. It needs Python plus the user's terminal/session tools, but no custom plugin.

**Native-plugin mode**

Use one local generic action bound to a `controlId`. Choose this for dynamic titles/icons, state polling, long press, dial rotation, dial press, or per-control settings. The plugin talks only to `cockpitd` on loopback.

Do not choose native-plugin mode merely because it is more sophisticated.

### 3. Model the cockpit before implementing it

Create or update configuration version 3. Start from `assets/cockpit.example.json` and validate against `assets/cockpit.schema.json`.

Keep these concepts separate:

- `sessions`: named agent processes or multiplexer sessions.
- `commands`: reusable local automations.
- `controls`: button/dial identities and gesture-to-operation mappings.
- `appearance`: presentation by verified state; never execution logic.

Use IDs such as:

```text
session.claude.backend
session.codex.review
session.pi.research
session.jcode.frontend
workflow.test-current
workflow.open-dashboard
```

For every control, document:

| Control ID | Label | Tap | Hold | Dial | State source | Destructive? |
|---|---|---|---|---|---|---:|

Before writing, reject:

- Duplicate or unstable IDs.
- Physical key coordinates in config.
- Embedded API keys, passwords, bearer tokens, or copied terminal output.
- Shell-string commands such as `bash -c`, `sh -c`, `cmd /c`, or PowerShell command strings. Wrap necessary logic in a reviewed script and invoke that script as an argument array.
- An interrupt, stop, delete, deploy, merge, or kill gesture without an appropriate confirmation policy.
- A semantic state display backed only by a PID, tmux session, timer, or terminal scraping.

Validate:

```bash
python3 scripts/validate_cockpit.py path/to/cockpit.json
```

### 4. Implement the standalone local runtime

Use the bundled stdlib-only reference runtime unless the repository already has an equivalent, better-tested component:

```bash
python3 bin/cockpitd.py --config path/to/cockpit.json
python3 bin/cockpitctl.py --config path/to/cockpit.json health
python3 bin/cockpitctl.py --config path/to/cockpit.json controls
```

Runtime rules:

- The HTTP API exposes named operations, never raw command execution.
- Commands are argv arrays and execute with `shell=False`.
- Paths and environment references resolve locally at invocation time.
- Responses omit command stdout/stderr by default.
- State reports have a source, timestamp, TTL, and stale behavior.
- A failed daemon or unavailable terminal must degrade to an honest unavailable state, not a false success.

For launcher-only mode:

```bash
python3 scripts/generate_launchers.py \
  --config path/to/cockpit.json \
  --output path/to/launchers
```

Map the generated tap launcher through the Stream Deck application. For an explicit macOS page edit, follow 4a; do not touch profile storage directly outside the guarded helper.

### 4a. Edit an explicit macOS v3 profile page when the user asks

Page creation is best done in the Stream Deck application. If the application
palette cannot accept a drag through the available UI bridge, the guarded
helper can add built-in **Open** actions to one already-created page. This is a
deliberate exception for an explicitly requested, user-owned profile—not a
general profile database editor.

1. Close the Stream Deck application after it has saved the new page.
2. Read the profile root manifest and identify the exact page UUID. Do not infer
   a page from physical coordinates or edit the root `Pages` list yourself.
3. Run `scripts/streamdeck_profile.py` with the exact profile root, page UUID,
   and launcher/title pairs. It verifies the profile name, refuses occupied
   keys unless `--replace` is explicitly supplied for an existing built-in
   **Open** action or this skill's owned Agent Cockpit action, creates a
   timestamped full-profile backup, and atomically changes only that page's
   `manifest.json`. Use `--plugin-control ROW,COLUMN=CONTROL_ID|TITLE` when the
   native plugin is installed and live state must render on the key.
4. Reopen Stream Deck and verify the page and key titles in the application.

Example:

```bash
python3 scripts/streamdeck_profile.py \
  --profile-root "$HOME/Library/Application Support/com.elgato.StreamDeck/ProfilesV3/<profile-uuid>.sdProfile" \
  --page-id <page-uuid> \
  --control "0,0=$HOME/.agent-cockpit/launchers/session.claude.main.command|Claude Code" \
  --control "1,0=$HOME/.agent-cockpit/launchers/session.codex.main.command|Codex"
```

The helper does not install plugins, change smart-profile assignments, or
touch other pages. Roll back by closing Stream Deck and restoring the backup it
reports, then reopen the application.

### 5. Implement session switching conservatively

For each Claude Code, Codex, Pi, or JCode session:

1. Give it a stable session ID and terminal target.
2. Probe whether the target exists.
3. Configure `launch`, `focus`, and optional `resume` using the installed CLI's verified syntax.
4. Map tap to `focus_or_launch` by default.
5. Map interrupt to hold/explicit confirmation, not an accidental tap.
6. Keep kill/termination absent unless the user expressly requires it.
7. Verify focus behavior in the actual terminal; “process started” is not proof the desired window became active.

Prefer a multiplexer for durable sessions. `tmux` is the bundled reference adapter, not a mandatory dependency. A custom adapter must provide the same contract: probe, launch, focus, optional resume, interrupt, and evidence-backed state.

For Herdr-managed tabs or panes, run the adapter setup and focus checks from a
Herdr-managed pane (`HERDR_ENV=1`). Bind each control to a stable Herdr
workspace/tab/pane identity obtained from that environment; never infer a
target from tab order or visible title alone. See `references/session-adapters.md`.

For attached Claude/Codex slots, install the runtime update and convert only
the declared slot sessions. The adapter captures Herdr location metadata in
the hook claim but resolves the agent-session id through `herdr agent list` on
every press, so an agent that moves panes is followed safely.

```bash
python3 scripts/install_runtime.py --target ~/.agent-cockpit --update-runtime
python3 scripts/configure_herdr_sessions.py --apply
python3 scripts/migrate_herdr_claims.py --agent claude --drop-unmatched --claim-unclaimed --apply
python3 scripts/migrate_herdr_claims.py --agent codex --drop-unmatched --claim-unclaimed --apply
```

The migration commands make backups and only remove unmatched claims for the
explicit agent namespace. Run their dry-run form first when the claims also
contain ordinary, non-Herdr terminal sessions.

Ask whether the user also wants sessions they started by hand — a Claude Code tab already open in iTerm2 — to appear on the deck. Most do, and a cockpit that only drives what it launched is half a cockpit. That path is available but weaker, so keep it separate from launch controls rather than merging the two:

1. Predeclare slots (`session.<agent>.slot1` … `slotN`); an unlisted session cannot report to the daemon.
2. Bind live sessions to slots with an agent hook, never by scraping terminal titles.
3. Give slots `probe` and `focus` only. Leave interrupt to multiplexer-backed sessions.
4. On macOS, focus matches the recorded tty. Windows Terminal has no scriptable tty, so pass `focus_terminal.py --tab-title` with the tab's exact title instead.
5. Add separate launch controls for new sessions, so both needs are covered without one weakening the other.

Start from `assets/cockpit.live-sessions.example.json`, which combines four attached slots with one tmux launch control. See `references/session-adapters.md` for the ancestry and tty rules this depends on.

Claude Code uses `bin/claude_hook.py` and `bin/install_claude_hooks.py`. Codex CLI
uses the parallel `bin/codex_hook.py` and `bin/install_codex_hooks.py` path;
register its user-level `~/.codex/hooks.json`, then review and trust the new
command hook in Codex's `/hooks` screen before expecting a slot to claim.
Both bridges keep separate slot namespaces and report through the same daemon.
The daemon's `sessions` keys for attached agents must therefore be the exact
slot IDs (`session.claude.slot1`, `session.codex.slot1`, and so on), and a
friendly control ID belongs in the control's `session` field. Renaming only the
daemon session key makes hook reports return 404 and leaves the Stream Deck key
offline.

### 6. Track progress without inventing it

There are two state classes:

**Coarse state** — verified from infrastructure:

```text
offline · present · unavailable
```

**Semantic state** — accepted only from an agent hook, RPC/event adapter, workflow callback, or explicit reporter:

```text
idle · running · needs_attention · blocked · succeeded · failed
```

Hook-compatible reporting:

```bash
python3 bin/cockpitctl.py --config path/to/cockpit.json \
  report session.claude.backend running \
  --label "Running tests" --ttl 180
```

For Claude Code, `bin/claude_hook.py` is the reference bridge and
`bin/install_claude_hooks.py` registers it append-only and idempotently. By
default it maps `SessionStart`/`Stop` to `idle`, `UserPromptSubmit` to
`running`, and `Notification` to `needs_attention`. `--extended` adds the tool,
permission, elicitation, subagent, task, and compaction events, which are what
make `blocked` and `failed` reachable — at the cost of running the bridge on
every tool call. Offer it as a second step, not the default.

Confirm every hook event name against the installed harness before registering
it: a name the harness does not dispatch fails silently and looks exactly like
an idle session. Preview with `--dry-run`, back up the settings file before the
first write, and tell the user that sessions already running when the bridge is
installed stay invisible until they restart. Other agents need their own bridge;
do not assume one exists.

A percentage is allowed only when the workflow emits a real numerator/denominator or explicit percentage. Otherwise show a state label, activity, age, and source.

### 7. Build or extend the Stream Deck plugin only when required

Use the current official Stream Deck SDK scaffold. This skill now includes a
buildable generic action in `streamdeck-plugin/`; use
`templates/streamdeck-plugin/` only as the adaptation reference for a different
scaffold or UUID.

```bash
cd streamdeck-plugin
npm ci
npm test
npm run typecheck
npm run build
python3 ../scripts/install_streamdeck_plugin.py --force
```

The current official toolchain requires Node.js 24 or newer. Run the official
validator only when its network behavior is acceptable in the user's
environment.

The preferred plugin design is one generic action:

- Property Inspector setting: `controlId`.
- Optional advanced settings: daemon URL and token-file override.
- Tap/hold/dial events become named gestures sent to the daemon.
- The plugin periodically fetches the bound control state and renders title/icon/feedback.
- A missing control, invalid token, or stopped daemon visibly reports an error.
- Unrelated profiles and third-party actions remain untouched.
- Another plugin is configurable only through its documented API; otherwise provide manual Multi Action instructions rather than reverse-engineering its settings.

Do not create one compiled action per project or agent unless the user needs distinct marketplace-visible actions.

### 8. Verify behavior, safety, and rollback

Run all repository-appropriate checks plus the bundled checks:

```bash
python3 -m compileall -q bin scripts tests
python3 -m unittest discover -s tests -v
python3 scripts/validate_cockpit.py assets/cockpit.example.json
python3 scripts/smoke_test.py
```

For a plugin implementation, also run its formatter, type-checker, tests, production build, and official Stream Deck validation/package command from the installed SDK.

On-device verification must cover:

- Tap focuses an existing session.
- Tap launches a missing session and then focuses it.
- Hold does not trigger on a normal tap.
- Interrupt affects only the intended session.
- Daemon-down and invalid-control states are visible.
- Stale semantic reports fall back to coarse state.
- Button labels/icons remain legible on the actual device.
- Restarting Stream Deck, the daemon, and the terminal does not corrupt config.
- Uninstalling the plugin/runtime leaves unrelated profiles intact.

## Output contract

Return:

1. Mode selected and why.
2. Capability ledger.
3. Control map.
4. Files created or changed.
5. Exact installation/start commands.
6. Verification evidence, including what was checked on-device versus locally.
7. Known limitations and state-evidence tier.
8. Rollback/uninstall steps.

## Completion gate

The task is complete only when:

- The core workflow has no MCP or AgentDeck runtime dependency.
- Configuration version 3 validates.
- Every button invokes only a predeclared local operation.
- Existing Stream Deck data outside the owned plugin/profile remains untouched.
- Session launch/focus behavior is verified, or the unverified part is named precisely.
- Semantic status is evidence-backed and expires when stale.
- Destructive gestures are guarded.
- Automated checks pass.
- Required physical-device checks are explicitly separated from checks that were actually run.
