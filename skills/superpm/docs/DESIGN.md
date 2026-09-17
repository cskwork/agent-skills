# superpm - design

One PM request in, a decision-ready artifact out - the smallest useful artifact,
checked by an independent critic against the framework and the real decision.

## Why this exists

`phuryn/pm-skills` is a marketplace of 68 PM skills across 9 plugins. Every skill is a
separate file you load by name. `superpm` folds that catalog into **one skill**: the model
captures intent from the request, the workflow **diverges by PM domain** into the right
framework, and an independent critic verifies the result before it ships.

The verification discipline is adapted 1:1 from `supergoal` (baseline-first delivery).

## The supergoal -> superpm mapping

| supergoal (code) | superpm (PM) |
|---|---|
| Verify against ground truth (re-run REAL tests) | Verify against **framework completeness + the real decision** (independent critic/red-team) |
| Smallest correct change | **Smallest useful artifact** - answer the actual decision, no filler frameworks |
| Surface hidden requirements as FAILING tests | Surface **hidden assumptions as risks** the critic flags |
| Ambiguity-gated <=5 question interview | Same intent-capture interview gate |
| Modes: greenfield / debug / legacy / learn / ... | **PM domains**: discover / strategy / execute / research / analytics / gtm / growth / toolkit / ai-ship |
| Never optimize to a self-graded proxy | Never let a framework template stand in for the user's real decision context |

## Core decision: one workflow, domain-routed divergence

The "diverging workflow" is **not** nine different loops. It is one loop whose divergence is
*which reference (domain framework) gets loaded*. Intent capture picks the domain and the
artifact; the loop is universal:

```
Capture -> Frame -> Draft -> Critic -> Deliver
```

1. **Capture** - classify the PM ask and always record the `Domain | Artifact | Decision`
   line. If genuinely ambiguous, run `reference/intent.md` (<=5 questions, one batched round,
   a recommended answer per question); resolve doc/code-answerable questions by reading, not
   asking.
2. **Frame** - extend that line into the artifact's `## Intent` block: the real decision plus
   the completion bar. That block is the contract the critic checks against.
3. **Draft** - apply the domain framework from `reference/<domain>.md`. Smallest useful
   artifact; no filler frameworks bolted on.
4. **Critic (independent)** - run `reference/critic.md`. Independence is mechanical: a fresh
   subagent given only the Intent block + draft where the harness supports it, a cold
   stance-switch otherwise. Red-team for missing sections, unsupported claims, and unvalidated
   assumptions; emit them as risks (all blockers, list capped at ~7).
5. **Deliver** - fold the surfaced risks back in, then stop. Response shape: artifact ->
   remaining risks -> what was checked -> the one natural next artifact in the chain (offered,
   not started). Inline by default; files when multi-page (storyboard always).
   Any irreversible/outward step (publish, send, post to a tracker) needs explicit consent.

Follow-up turns re-enter the loop at the right depth: substantive edits re-run the critic on
the delta only, format/tone-only edits skip it, and a new artifact or domain restarts at
Capture. The loop is per-artifact, not per-message.

## Layout

```
SKILL.md          thin spine: principles, intent-capture table, the loop, reference map
reference/
  intent.md       intent classification + <=5 question interview gate
  critic.md       independent critic / red-team verification gate
  signal.md       live market & customer signal (voice of customer) - keyless, read-only; delegates to last30days if installed
  model.md        shared data contract (SSOT) - identifiers, entities, sync rules R1-R6, validation codes (cross-cutting)
  discover.md     pm-product-discovery frameworks
  strategy.md     pm-product-strategy frameworks
  execute.md      pm-execution frameworks
  flow.md         user-flow graph - nodes derived from SPECs (R2), page->screen hand-off (R3), zero-dep visualization
  storyboard.md   화면설계서/기능명세 storyboard - bundled-standalone, delegates to storyboard-spec if installed
  package.md      integrated implementation bundle - one snapshotId over PRD+spec+flow+wireframe (R6), back-link integrity, export
  research.md     pm-market-research frameworks
  analytics.md    pm-data-analytics frameworks
  gtm.md          pm-go-to-market frameworks
  growth.md       pm-marketing-growth frameworks
  toolkit.md      pm-toolkit utilities
  ai-ship.md      pm-ai-shipping frameworks (ties back to supergoal's verification ethos)
templates/        high-value artifact templates (PRD, strategy canvas, OST, battlecard, ...)
  storyboard-page.html   self-contained one-screen 화면설계서 page (inline CSS, no deps)
  storyboard-board.html  self-contained thumbnail/index board (live iframe thumbs)
  workspace.html         self-contained 3-tab workspace (기능명세/유저플로우/와이어프레임) - embedded SSOT JSON, live validation, no deps
docs/DESIGN.md    this file
```

## Self-containment

The 68 upstream skills are compressed into the 9 domain references at a usable depth - no
runtime dependency on `phuryn/pm-skills`. References name the canonical framework so a reader
can go deeper upstream if wanted, but `superpm` runs standalone.

## STORYBOARD domain: bridge to storyboard-spec, standalone by default

The STORYBOARD domain produces 화면설계서/기능명세 (screen design documents): per the
self-containment principle above, superpm renders the full document with **zero external
dependency**, using two bundled self-contained HTML templates (`templates/storyboard-page.html`,
`templates/storyboard-board.html`) - inline CSS/JS only, opens straight in a browser.

`cskwork/storyboard-spec` is a separate, richer skill for the same artifact (Figma REST
auto-extraction, headless-Chrome thumbnails, themeable CSS). It is treated as an **optional
accelerator, never a hard dependency**: `reference/storyboard.md` detects it
(`~/.claude/skills/storyboard-spec/SKILL.md`) and, only if present, delegates the heavy rendering
to it. The bundled templates use the same `{{...}}` / `sb-mark` / `sb-cue` / `sb-notes` contract
as storyboard-spec, so a document started standalone upgrades cleanly if that skill is later
installed.

The artifact also folds 기능명세 into the same deliverable: the right-pane per-element table
(action / data / exception / state) *is* the functional spec - one document, not two. The critic
gate extends to screens via `reference/storyboard.md`'s completeness anchors (no dead-end screens,
1:1 callout-to-row, sourced data contracts, non-happy states covered).

## The implementation chain: EXECUTE -> FLOW -> STORYBOARD -> PACKAGE

When the ask is "help me plan what I want to build" - not a single PM doc - four domains form a
chain that hands a developer-ready package off at the end. The **PLAN session**
(`reference/plan.md`) runs this chain stepwise - one stage per turn, gated for the user after each.
They share one source of truth, the
**Specification (기능명세)**, so the documents never drift apart:

- **EXECUTE** settles requirements (PRD) and the SPECs under them.
- **FLOW** (`reference/flow.md`) derives the user-flow graph from those SPECs (R2) - a page/action
  node that links to no SPEC is never invented.
- **STORYBOARD** turns each flow `page` node into a screen (R3); each callout back-links to its
  SPEC (R4), so the screen and the spec read the same contract from either side.
- **PACKAGE** (`reference/package.md`) bundles PRD + SPEC + flow + wireframe under one
  `snapshotId` (R6) - the 기획서 산출물 a developer or coding agent implements from.

`reference/model.md` is the **cross-cutting data contract** (like intent/critic/signal - no
domain count change): it names the identifiers (`SPEC-NN`, `FLOW-NN`, `SCREEN-NN`), the sync rules
R1-R6, and the validation codes (`ORPHAN_NODE`, `UNMAPPED_SCREEN`, `ORPHAN_CALLOUT`, ...). The
critic checks these as **traceability**. `templates/workspace.html` is a self-contained 3-tab
viewer (기능명세 / 유저플로우 / 와이어프레임) that renders an embedded SSOT JSON and runs those
validation codes **live in the browser** - the blocker gate, with no backend.

## SIGNAL: live market evidence, keyless + standalone

`reference/signal.md` is a **cross-cutting evidence source** (like intent/critic), not a domain -
no count change. It grounds market/customer claims in real, recent, engagement-ranked signal so
RESEARCH/DISCOVER/GTM cite evidence instead of asserting it. Same pattern as STORYBOARD: runs
standalone on superpm's own `WebSearch`/`WebFetch` over **keyless, read-only** public sources
(HN, GitHub, Polymarket, Jina Reader, web search, RSS; Reddit's anonymous API is now blocked, so
its content is reached keyless via web search), and delegates to the `last30days` skill
(`~/.claude/skills/last30days/SKILL.md`) for deeper keyed sources only if installed. Hard boundary:
read-only, no keys, no posting or outreach.

## Credit

- PM framework catalog: `phuryn/pm-skills` (MIT), curated by Pawel Huryn.
- Workflow + verification discipline: `cskwork/supergoal-skill` (MIT).
- Screen-design storyboard method (optional accelerator + bundled-template contract):
  `cskwork/storyboard-spec` (MIT).
- Live-signal method (optional `last30days` accelerator): `mvanhorn/last30days-skill` (MIT).
- Keyless read techniques (Jina Reader, RSS): `Panniantong/Agent-Reach` (MIT).
