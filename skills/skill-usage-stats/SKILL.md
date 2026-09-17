---
name: skill-usage-stats
description: "Generate an HTML dashboard of Claude/Codex skill and prompt usage, including counts, last-used dates, session reach, and disk size. Use for skill audits or 스킬 사용 통계."
---

# Skill Usage Stats

Scans local Claude Code (`~/.claude/projects/**/*.jsonl`) and Codex (`~/.codex/sessions/**/*.jsonl`) transcripts, joins against the installed skill/prompt catalog, and writes an interactive HTML dashboard to `~/.claude/skill-stats.html`.

## When to use

- User asks which skills they actually use, or wants to clean up unused skills.
- User wants a usage report comparing global vs. project-level skills.
- User mentions auditing Claude Code or Codex skills.

## Files in this skill

- `analyze.py` — scans transcripts, writes the HTML dashboard, opens browser.
- `summary.py` — terminal-only views (top/zero/stale/overview) from the same HTML.

## How to run

Generate the HTML dashboard (default: scan all transcripts, write to `~/.claude/skill-stats.html`, open browser):

```bash
python3 ~/.claude/skills/skill-usage-stats/analyze.py
```

`analyze.py` flags:
- `--days N` — only count invocations in the last N days (default: all time).
- `--project <substr>` — restrict to transcripts whose cwd matches.
- `--out <path>` — output HTML path (default: `~/.claude/skill-stats.html`).
- `--no-open` — generate but don't open the browser.

Terminal views (after the HTML exists):

```bash
python3 ~/.claude/skills/skill-usage-stats/summary.py overview         # per-source totals
python3 ~/.claude/skills/skill-usage-stats/summary.py top -n 20        # top 20 most-used
python3 ~/.claude/skills/skill-usage-stats/summary.py zero             # 0-use skills (cleanup list)
python3 ~/.claude/skills/skill-usage-stats/summary.py stale --days 90  # >90d unused or never
```

`summary.py` accepts `--source claude-global|claude-project|codex-global-skill|codex-global-prompt` and `--html <path>`.

## Detection rules

Covers **both explicit slash-command calls and auto-triggered loads** (the harness loads SKILL.md on its own when a description matches user intent).

- **Claude Code — explicit `Skill` tool**: `tool_use` with `name="Skill"`, `input.skill=<name>`.
- **Claude Code — slash command**: `<command-name>/name</command-name>` tag in user messages.
- **Claude Code — auto-trigger via `Read`**: `tool_use` with `name="Read"`, `file_path` ending in `/skills/<name>/SKILL.md` (this is how `using-superpowers`, `using-symphony`, etc. actually get activated).
- **Claude Code — auto-trigger via `Bash`**: `tool_use` with `name="Bash"`, command containing `/skills/<name>/SKILL.md` (e.g. `cat`, `sed`).
- **Codex — slash command**: user `input_text` whose first non-blank line is `/<name>`.
- **Codex — auto-trigger via shell**: `function_call` events with `name` in `{exec_command, shell, apply_patch}` whose arguments contain `/skills/<name>/SKILL.md` (Codex reads skills via shell, not a Read tool).

Each `tool_use` / `function_call` event credits the skill once. Source is decided by the path containing `.claude` vs `.codex`.

**Catalog sources** (where the SKILL.md lives on disk):
- `claude-global`: `~/.claude/skills/*/SKILL.md`
- `claude-project`: `<repo>/.claude/skills/*/SKILL.md` (discovered from transcript cwds)
- `codex-global-skill`: `~/.codex/skills/*/SKILL.md`
- `codex-global-prompt`: `~/.codex/prompts/*.md`

## Output columns

`name | source | count | sessions | first_used | last_used | days_since | size_kb | path`

Sortable, filterable. Stale skills (>90 days unused) and zero-use skills are highlighted.
