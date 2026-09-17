---
name: refine-skill-terse
description: Tighten a SKILL.md so agents (not humans) read it fast - cut prose, keep the procedure, move rationale out. Use when the user says "make the skill succinct", "skill improvement keep it minimal", "스킬 간결하게/개선", or a SKILL.md body has grown wordy.
---

# refine-skill-terse

A skill is read by agents on every load; trim it to the minimum that still drives the procedure correctly.

## When to use
- "make skill improvement, keep succinct - agents use it not humans", "스킬 간결하게 다듬어"
- A SKILL.md body is wordy, repeats itself, or carries rationale that belongs in a changelog.

Not for: writing a brand-new skill (use the skill template), or changing what the skill does.

## Steps
1. Read the target `SKILL.md`. Note its required procedure and trigger phrases (do not lose these).
2. Cut: filler sentences, restated context, motivation/rationale prose, duplicated lines.
3. Keep: imperative steps, the gate/stop conditions, and the trigger phrases in `description`.
4. Move rationale ("why we chose X") to a `log/changelog-*.md` entry, not the body.
5. Keep body <~5k tokens; push long reference/data to a sibling file loaded on demand.
6. Re-check: the directory-name command still resolves; `description`+`when_to_use` <=1536 chars.

## Notes
Terseness is for the agent's token budget, not style. If cutting a line could change behavior, keep it.
