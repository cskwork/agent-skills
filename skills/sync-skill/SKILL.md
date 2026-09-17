---
name: sync-skill
description: Deploy one skill to every coding agent (Claude Code, Codex, opencode, Hermes) by keeping ONE canonical dir and symlinking it into each agent's skills dir - one source, no drift. Use when the user says "deploy this skill", "update to .claude and .codex", "sync skill to all agents", "스킬 배포/동기화".
---

# sync-skill

One canonical skill dir -> symlinked into every agent's skills dir, so all agents share one source and an edit lands everywhere at once.

## When to use
- "deploy/install this skill to all agents", "update to .claude and .codex skill", "스킬 전부 동기화"
- After creating a skill, to wire it into every agent from a single canonical copy.

Not for: editing a skill's content (edit the canonical dir directly), or a one-agent-only install.

## Steps
1. Put the real skill dir in the canonical store: `~/.agents/skills/<name>/SKILL.md` (one source of truth, a plain real dir - not a symlink into any managed skill-manager store).
2. Symlink it into each agent dir that exists:
   - `~/.claude/skills/<name>` and `~/.codex/skills/<name>` -> relative `../../.agents/skills/<name>`
   - `~/.config/opencode/skills/<name>` and `~/.hermes/skills/<name>` -> absolute `~/.agents/skills/<name>`
3. On a name collision: show the existing target (`ls -l`) and ask before replacing; never clobber a real dir.
4. Verify: `ls -l <agent-dir>/<name>` resolves to `~/.agents/skills/<name>/SKILL.md`.

## Notes
Edit the canonical once and every agent sees it instantly - no re-sync needed. Keep the canonical a real dir (not a symlink into a managed store) so it survives independently. If an agent dir does not exist, skip it and report.
