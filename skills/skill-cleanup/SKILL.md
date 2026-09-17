---
name: skill-cleanup
description: "Archive unused or stale Claude/Codex skills based on skill usage stats without deleting content. Use for clean up skills, archive unused skills, or 스킬 정리."
---

# Skill Cleanup

Companion to `skill-usage-stats`. Reads the same HTML report and **archives** skills marked DELETE (or matching user-chosen criteria) without deleting any files.

## How archiving works

For each chosen skill directory:

1. Move it under `~/.claude/skills-archive/<source>/<skill-name>/`  (or `~/.codex/skills-archive/...`)
2. Inside the archived directory, rename `SKILL.md` → `SKILL.md.archived` so the harness no longer treats it as an active skill (the harness only auto-discovers `SKILL.md`).
3. Write a `.archived-meta.json` next to it recording original path, archive date, and the reason from the stats report.

Reverse: `restore <name>` moves it back and renames `SKILL.md.archived` → `SKILL.md`.

## How to run

```bash
# 1. Generate fresh stats first
python3 ~/.claude/skills/skill-usage-stats/analyze.py --no-open

# 2. Dry-run (default) — print what would be archived
python3 ~/.claude/skills/skill-cleanup/archive.py

# 3. Apply
python3 ~/.claude/skills/skill-cleanup/archive.py --apply

# Useful flags
#   --verdict DELETE       only archive DELETE-classified skills (default)
#   --verdict DELETE,REVIEW
#   --days 90              also archive count>0 but stale >N days
#   --source claude-global only archive from one source
#   --dry-run              never actually move (default)

# Restore
python3 ~/.claude/skills/skill-cleanup/archive.py restore <name>
python3 ~/.claude/skills/skill-cleanup/archive.py list-archive
```

## Safety

- Default mode is dry-run.
- Never deletes; archive is fully reversible.
- Skips any skill not in the stats report (so you can't accidentally archive an unscanned skill).
- Refuses to operate on plugin cache paths (`~/.claude/plugins/cache/...`) — those are managed by the plugin marketplace and a rename there would just be re-installed.
