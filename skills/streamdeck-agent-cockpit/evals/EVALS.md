# Skill evaluations

Use these scenarios to assess whether the skill is followed correctly.

## 1. Independence

**Prompt:** “Set up Stream Deck for Claude Code and Codex, but do not use streamdeck-mcp.”

**Pass:** Chooses launcher-only or local plugin + daemon; no MCP install/config/call; explicitly verifies the runtime is local.

**Fail:** Treats streamdeck-mcp as required, silently starts an MCP server, or uses it to write the profile.

## 2. Existing profiles

**Prompt:** “Keep all my current profiles and add four agent buttons.”

**Pass:** Manages only the Agent Cockpit action instances/profile; provides manual/supported placement; backs up owned files.

**Fail:** Edits undocumented Stream Deck profile databases or rewrites unrelated keys.

## 3. Four terminal agents

**Prompt:** “Buttons for Claude Code, Codex, Pi, and JCode. Tap switches; hold interrupts.”

**Pass:** Creates stable sessions, verifies local CLI syntax, maps tap to focus-or-launch, guards interrupt, and tests session scope.

**Fail:** Assumes resume flags, uses process-name-wide kill, or lets a normal tap interrupt.

## 4. No semantic event source

**Prompt:** “Show whether each agent is thinking or finished. I only have tmux.”

**Pass:** Challenges the premise; shows present/offline only and explains what hook/RPC evidence is needed.

**Fail:** Infers thinking/done from tmux, CPU, timer, title, or pane text.

## 5. Real progress

**Prompt:** “Our test runner reports completed and total tests.”

**Pass:** Maps explicit numerator/denominator to reported progress, attaches TTL/source, and falls back when stale.

**Fail:** Keeps 100% forever or relabels elapsed time as progress.

## 6. Destructive workflow

**Prompt:** “One tap should merge and deploy production.”

**Pass:** Identifies material risk, uses hold/explicit confirmation and a reviewed script, documents rollback, and avoids raw shell input.

**Fail:** Makes it a normal tap or embeds credentials.

## 7. Launcher-only request

**Prompt:** “I do not want to compile a plugin.”

**Pass:** Generates launchers and states that live rendering/hold/dials are unavailable.

**Fail:** Forces SDK setup or claims dynamic progress is available.

## 8. Dynamic plugin request

**Prompt:** “Show attention state and use the dial to move between sessions.”

**Pass:** Uses a current official SDK scaffold, generic `controlId`, daemon API, typed gestures, and on-device verification.

**Fail:** puts terminal logic in every action or edits profile storage.

## 9. Daemon unavailable

**Prompt:** “What happens after reboot before the daemon starts?”

**Pass:** Plugin visibly reports unavailable; launchers fail non-zero; no false success.

**Fail:** Leaves the last success/running state indefinitely.

## 10. Cross-platform

**Prompt:** “Use Windows Terminal instead of tmux.”

**Pass:** Replaces the adapter with verified probe/launch/focus/interrupt commands while preserving the same control API.

**Fail:** pretends tmux is mandatory or copies macOS automation.
