# 2026-06-10 — Loop hardening: Intent-block contract, mechanical critic independence, follow-up turns

## What changed

A consistency-and-efficiency pass over the spine and gates so an agent can run each
intent-based workflow without guessing. No new domains, no new frameworks; the loop's contracts
were made explicit and two real contradictions were removed.

Edited:
- `SKILL.md` — Capture now always records the `Domain | Artifact | Decision` line (not only when
  the interview fires); Frame is defined as extending that line into the artifact's `## Intent`
  block (classification + decision + completion bar) — the contract the critic checks; Critic
  step names the mechanism (fresh subagent given only the Intent block + draft when the harness
  supports it, cold stance-switch otherwise); Deliver defines the response shape (artifact →
  remaining risks → what-was-checked line → one offered next artifact in the
  DISCOVER→STRATEGY→EXECUTE→STORYBOARD→GTM/GROWTH chain) and the file rule (inline by default,
  files when multi-page, storyboard always); new `## Follow-up turns` section (substantive edit →
  critic on the delta; format/tone-only → no critic; new artifact/domain → new loop). Frontmatter
  `description` tightened to procedure + triggers; added missing high-frequency triggers (user
  stories, pre-mortem, retro, release notes, interview script, ICP, battlecard, North Star).
  Principles compressed to gates, prose cut.
- `reference/intent.md` — removed the question-protocol contradiction: was "one at a time, do not
  batch" vs SKILL.md's "one round". Now one batched round, each question carrying a recommended
  answer ("go with your recommendations" is a valid one-line reply), at most one follow-up round.
  Recording section now includes the completion bar in the `## Intent` block.
- `reference/critic.md` — new "Independence - make it mechanical" section (subagent vs
  stance-switch); risk-list cap (all blockers always, total ~7, weakest polish dropped first).
- `templates/prd.md`, `strategy-canvas.md`, `opportunity-solution-tree.md`, `battlecard.md` —
  `Done bar` line added to each `## Intent` block so the critic has its bar in the artifact.
- `docs/DESIGN.md` — loop section synced; follow-up-turn rule documented.

## Decisions and why

- **The Intent block is the single contract.** The recording rule lived only in `intent.md`,
  which loads conditionally (only when ambiguous) — so clear requests silently lost the
  classification/done-bar record the critic and templates assume. Moving the contract into the
  always-read SKILL.md loop fixes the drop-out; `intent.md` keeps the detail.
- **Batched interview round over serial questions.** Serial asking ("wait for each reply") costs
  one user interruption per question and contradicted SKILL.md. One round with recommended
  answers lets the user approve everything in one reply — cheaper and matches how agent harness
  question tools batch (e.g. up to 4 questions per call).
- **Critic independence must be mechanical.** An in-context model cannot "read cold" the draft it
  just wrote; the known failure is the drafter grading its own work to green. Where subagents
  exist, a fresh context given only the Intent block + draft is real independence; the
  stance-switch is the harness-agnostic fallback. Phrased capability-conditional to stay portable
  (Claude Code, Codex, etc.).
- **Follow-up turns needed a rule.** PM sessions iterate ("shorter", "another idea", "now a
  PRD") but the skill described one shot. Without a rule, agents either re-run the full loop on a
  tone edit (waste) or skip the critic on a substantive change (unsafe). Delta-scoped critic
  re-runs were already in `critic.md`; the spine now routes to them.
- **Deliver shape + file rule remove per-run guessing.** Where the artifact goes (inline vs file)
  and what the closing report contains were undefined — the most common source of inconsistent
  output. The chain offer ("offered, not started") encodes the natural PM handoff without scope
  creep.
- **Risk cap.** An uncapped critic pads with polish items and buries the blocker; blockers are
  never dropped, polish is.
- **Kept terse for agent reading (user steer).** Description and principles compressed; rationale
  lives here, not in the skill body. Reference map and intent table left intact — cutting them
  would change routing/loading behavior.

## Verification

- Consistency: `grep -n "one round\|batched round\|one at a time"` across SKILL.md and
  reference/ shows the serial-vs-round contradiction is gone; `## Intent` contract now appears in
  SKILL.md (always-on), intent.md (detail), critic.md (input to subagent), and all four md
  templates (with `Done bar`).
- Reference integrity: all `reference/*.md` and `templates/*` paths named in SKILL.md exist;
  domain table and reference map rows unchanged (10 domains, routing intact).
- Frontmatter: `description` within skill limits and retains every prior trigger phrase plus the
  added ones.
- READMEs/landing untouched: the loop's five step names and domain counts did not change, so no
  copy drift was introduced.
