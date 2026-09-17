# 2026-06-09 — SIGNAL: live market & customer signal (keyless, read-only) cross-cutting layer

## What changed

Added **SIGNAL**, a cross-cutting evidence source (like `intent.md` / `critic.md`, not a domain)
that grounds market/customer claims in real, recent, engagement-ranked signal — so RESEARCH,
DISCOVER, and GTM cite evidence instead of asserting it. An essential PM reads what people
actually say, do, and pay for; this is the mechanism for it.

New:
- `reference/signal.md` — the layer. Method (parse → resolve where → search ~30d → score by
  engagement → pull real voice → cluster → cited brief), keyless source list (Reddit public JSON,
  Hacker News, GitHub, Polymarket, Jina Reader `r.jina.ai`, public RSS, WebSearch/WebFetch), a
  hard safety boundary, the optional `last30days` delegation block, the framework bridge, and
  critic completeness anchors.

Edited (surgical, 1–3 lines each):
- `SKILL.md` — "Ground claims in evidence" principle now points to signal.md; a cross-cutting note
  under the intent table; a `reference/signal.md` row in the reference map; signal triggers in the
  frontmatter `description`.
- `reference/research.md` — `live-market-signal` section + a sentiment-analysis pointer + a critic anchor.
- `reference/discover.md` — signal hooks on `brainstorm-ideas` lenses and `opportunity-solution-tree`.
- `reference/gtm.md` — signal grounding on `ideal-customer-profile` and `competitive-battlecard`.
- `docs/DESIGN.md` — layout line, a "SIGNAL: live market evidence" section, two credits.
- `README.md`, `README.ko.md` — RESEARCH row note, layout reference line, two credits.
- `docs/index.html` — RESEARCH mode-card copy, a `reference/signal.md` file-chip, footer credit.
  **Counts untouched** (signal is not a domain): "9 plugins / 10 domains / 68 frameworks" intact.

## Decisions and why

- **Cross-cutting evidence source, not a new domain.** signal feeds RESEARCH/DISCOVER/GTM; it is
  an input, not a deliverable. Modeled on `intent.md`/`critic.md`. This keeps the routing table
  clean and avoids a dishonest domain-count bump across README/landing.
- **Bundle the method, delegate the engine (storyboard precedent).** superpm runs the signal brief
  standalone on its own `WebSearch`/`WebFetch`; if the `last30days` skill is installed it delegates
  the deeper keyed work (detected at `~/.claude/skills/last30days/SKILL.md`). Vendoring last30days'
  Python engine + API keys + test suite was rejected as heavy duplication that would drift — same
  reasoning that kept storyboard-spec an optional accelerator.
- **superpm functions independently (user requirement).** No hard dependency: absent last30days,
  the keyless bundle still produces real, sourced signal.
- **Keyless by default (user requirement).** The bundle uses only zero-config public sources
  (Reddit/HN/GitHub/Polymarket/Jina Reader/RSS). Key/cookie sources (X, YouTube transcripts, etc.)
  live only behind the user's own installed `last30days` accelerator — superpm never asks for keys.
- **Agent-Reach: safe keyless read techniques only.** Adopted Jina Reader (`r.jina.ai`) and public
  RSS read patterns. Rejected its posting/outreach (tweet/comment/like = outward + contacts real
  accounts), cookie-based scraping (account-ban risk per its own README), and toolchain install —
  failed the "if possible and safe" gate. signal.md states a hard read-only / no-outreach boundary
  consistent with superpm's "irreversible/outward step needs explicit consent" principle.
- **Kept terse for agent reading (user steer).** signal.md and the hooks are procedure-first,
  prose-minimal; rationale lives here, not in the skill body.

## Verification

- Reference integrity: `grep` confirms `signal.md` is referenced from `SKILL.md`,
  `reference/research.md`, `reference/discover.md`, `reference/gtm.md`, `docs/DESIGN.md`, both
  READMEs, and `docs/index.html`; no broken links.
- Honesty check: the "9 / 10 / 68" count copy in `docs/index.html` and the READMEs is unchanged
  (signal is cross-cutting, not a domain). `last30days` (mvanhorn) and `Agent-Reach` (Panniantong)
  both credited MIT in DESIGN, both READMEs, and the landing footer.
- Critic self-review of `reference/signal.md` against `reference/critic.md`: completeness (method +
  sources + safety + delegate + bridge + anchors), evidence (every cited path exists), decision-fit
  (drives evidence-grounding for market/customer claims), assumption-surface (keyless/read-only and
  delegate-vs-bundle logic explicit). No blockers.
- **Live source test (curl + WebSearch, 2026-06-09).** Confirmed keyless-direct: Hacker News
  Algolia (JSON, points/comments), GitHub search API (stars, 60/hr unauth), Polymarket gamma
  (live odds), Jina Reader `r.jina.ai` (any non-blocked page -> markdown), generic public RSS
  (hnrss, Verge). **Correction applied:** Reddit's anonymous access is now fully gated -
  `www`/`old` `.json`, `.rss`, and Jina-on-reddit all return 403 / a "log in or use developer
  token" block, so the original "Reddit public JSON, keyless" claim was wrong. `signal.md`,
  `research.md`, and `DESIGN.md` were corrected: Reddit's consumer voice is reached keyless via
  `WebSearch "site:reddit.com <topic>"` (search-indexed threads + upvote-weighted sentiment), and
  full thread/comment depth via the `last30days` accelerator on the user's own access. End-to-end
  dry run (topic "Claude Code") produced a cited, engagement-ranked brief from HN + web-surfaced
  Reddit + GitHub signals.

---

# 2026-06-09 — STORYBOARD domain: 화면설계서/기능명세 via bridge to storyboard-spec

## What changed

Added a 10th PM domain, **STORYBOARD**, that turns a validated direction (discovery/research/PRD)
into a storyboard-style 화면설계서 (screen design document) whose per-element table doubles as the
기능명세 (functional spec).

New:
- `reference/storyboard.md` — the domain framework (upstream contract, Mode A/B, element-extraction
  checklist, storyboard structure, production decision block, critic completeness anchors).
- `templates/storyboard-page.html` — self-contained one-screen page (inline CSS/JS, zero external
  deps). Left = wireframe/replica with numbered callouts; right = the 5-column element table.
- `templates/storyboard-board.html` — self-contained thumbnail/index board using live `<iframe>`
  thumbnails (no screenshot tooling needed).

Edited (surgical):
- `SKILL.md` — STORYBOARD row in the intent table, reference-map row, templates note, and the
  frontmatter `description` (added screen-design / 화면설계서 triggers so the route actually fires).
- `docs/DESIGN.md` — layout tree + a section on the bridge/standalone integration + credit.
- `README.md`, `README.ko.md` — domain table row, layout lines, credit; "9 → 10" route count.
- `docs/index.html` — a STORYBOARD mode-card (color `--blue`) and the "nine/9 → ten/10" count
  copy across hero/marquee/metric/headings/CTA (EN+KO). Left "68 PM skills across 9 plugins"
  (an upstream fact) and the 68→9 compression claim intact, noting screen-design is additive.

## Decisions and why

- **Bridge + delegate, standalone by default (not absorb, not hard-dependency).** The user
  requires superpm to work with `storyboard-spec` absent. So superpm renders the full 화면설계서
  from bundled self-contained HTML, and only *delegates the heavy rendering* (Figma REST
  auto-extraction, headless thumbnails, themeable CSS) to `storyboard-spec` when it is installed
  (detected at `~/.claude/skills/storyboard-spec/SKILL.md`). This matches DESIGN.md's existing
  "no runtime dependency" principle. Absorbing storyboard-spec's ~500-line playbook + scripts was
  rejected as duplication that would drift out of sync.

- **The right-pane element table IS the 기능명세 (one artifact, not two).** Per superpm's
  "smallest useful artifact" principle: each element row carries 동작(event) / 데이터(data) /
  예외(exception) / 상태(state), which is exactly a per-screen functional spec. No separate
  functional-spec document.

- **Standalone output is a self-contained single HTML, not markdown.** 화면설계서 is inherently a
  visual document; a markdown-only fallback would lose the side-by-side storyboard. The bundled
  templates use the same `{{...}}` / `sb-mark` / `sb-cue` / `sb-notes` contract as storyboard-spec,
  so a doc started standalone upgrades cleanly if that skill is added later.

- **Live `<iframe>` thumbnails for the board.** storyboard-spec's board relies on `shoot.sh`
  (headless-Chrome PNGs). To stay dependency-free, the bundled board scales each page in an
  `<iframe>` instead — real thumbnails, zero build step. (A commented `<img src="thumbs/*.png">`
  alternative is left in for when storyboard-spec/shoot.sh is present.)

- **Domain name STORYBOARD, placed after EXECUTE.** Lifecycle order: discovery/research → PRD →
  screen design → build. User chose the name; "SCREENS"/"DESIGN-SPEC" were the alternatives.

## Verification

- Rendered `templates/storyboard-page.html` and `templates/storyboard-board.html` in headless
  Chrome from a temp dir (no network): page shows the login wireframe with 4 numbered callouts
  mapped 1:1 to the 4 tagged element rows; board shows two cards with live iframe thumbnails of the
  actual pages. Both fully self-contained.
- `grep` confirmed zero external `http(s)://`, `<link rel=stylesheet>`, or `<script src>` in either
  template — only local relative links/iframes.
- Critic self-review of `reference/storyboard.md` against `reference/critic.md`'s four checks:
  completeness (all framework sections + anchors present), evidence (every referenced path now
  exists), decision-fit (drives the 화면설계서/기능명세 deliverable), assumption-surface (the
  standalone-vs-delegate logic is explicit). No blockers.

---

# 2026-06-09 — DISCOVER: idea-proposal house style (decision-grade brainstorm output)

## What changed

`reference/discover.md` `brainstorm-ideas` — added an **Idea-proposal format** as the default
output when the user wants a recommendation (not a 10-20 divergent list). The existing lenses and
divergent output are preserved (relabeled "Divergent output").

The new format encodes a reproducible house style:
- Batch header naming the round's axis theme; 3 bets each on a *distinct customer/model axis*;
  "another / different one" jumps to a genuinely new axis, not a re-skin of the last round.
- Per-idea skeleton: `X. concept (customer+model tag) <- 추천` + 누가→무엇 / 무료 미끼 /
  수익화 / 차별화(복제난이도) / 왜 지금(winner) · 주의(runners-up).
- Comparison table (revenue ceiling | fit | marketing-CAC | copy-difficulty | validation speed),
  one decisive pick with a punchy one-line why, timeboxed cheapest validation (experiment /
  numeric threshold / decision rule), compact critic, next-move offer.
- Principle baked in: *lucrative lives in distribution and moat, not the product*; never assert a
  market size / revenue figure as fact.

## Decisions and why

- **Additive, not replacing.** Kept the 10-20 divergent menu for pure ideation; added the
  convergent decision-grade format as the default for "what should we bet on" requests. Surgical
  edit to one section.
- **Codified from a user-approved gold sample.** The format mirrors a P/Q/R "model-shift" idea set
  the user explicitly flagged as the desired feel (punchy titles, per-idea 왜지금/주의 asymmetry,
  memorable economic framing, timeboxed validation).
- **Critic kept but compact.** superpm's independent-critic gate stays; when per-idea 주의 already
  carries the two-sided risks, the trailing Critic stays short (market numbers / competitor claims
  must still be labeled assumptions).

## Verification

- Edit applied to `reference/discover.md`; `brainstorm-experiments` and other sections untouched.
- Format derived from an in-session sample the user confirmed; no runtime/scripted component to test.

---

# 2026-06-09 — STORYBOARD: 화면 목차 (TOC) rail on by default

## What changed

Storyboard pages now carry a left **화면 목차 (TOC)** rail by default — a sticky sidebar listing
all screens (grouped), with the current screen highlighted and planned screens dimmed, so a reader
jumps screen-to-screen without returning to the board. Modeled on the ExamBank storyboard
(`.sb-toc` / `.sb-layout`).

- `templates/storyboard-page.html` — restructured to `nav → .sb-layout(aside.sb-toc + main.sb-main)`;
  added TOC CSS, example TOC entries (`a.t.current` + dimmed `span.t.plan`), and a scroll-to-current
  script. Single-file, still zero external deps.
- `reference/storyboard.md` — TOC added to "Storyboard structure", the bundled production note, and
  the critic completeness anchors ("every page carries the same 화면 목차 with the current screen marked").
- `examples/verified-content-api/` — applied the TOC to `storyboard.css` + `sb-01`/`sb-02` to demo it.

## Decisions and why

- **TOC vs board are complementary, both kept.** Board (`index.html`) = visual thumbnail overview;
  TOC = per-page text quick-jump. The user pointed at ExamBank, which has both; the TOC was the
  missing piece, so it became the page default.
- **Same TOC block on every page; only `current` moves.** Matches the ExamBank convention and keeps
  the rail a stable, predictable index. Documented as a completeness anchor.
- **Planned screens shown dimmed/unlinked (`span.t.plan`).** Lets a draft list the full intended set
  in the TOC without 404s to pages that aren't built yet.

## Verification

- Rendered the bundled `templates/storyboard-page.html` and `examples/.../sb-01-benchmark.html` in
  headless Chrome: left "화면 목차" rail shows grouped entries with the current screen highlighted and
  planned screens dimmed; main content (header + screen/spec split) renders beside it. Still no
  external requests.

---

# 2026-06-09 — STORYBOARD: viewer controls (font size · zoom · view-original · opacity · pager)

## What changed

Ported the ExamBank/storyboard-spec viewer controls into superpm's bundled storyboard page so they
are on by default:
- **글자 크기** (A-/A/A+ → `--sb-fz`, scales the spec table text; localStorage, cross-tab sync)
- **콜아웃 번호 진하기** (opacity slider → `--sb-cue-op`)
- **화면 확대/축소** (`.sb-zoom`/`.sb-stage`: wheel-zoom at cursor, ＋/－/맞춤 buttons, drag-pan,
  double-click reset)
- **원본 보기** (full-screen lightbox)
- **이전/다음 pager**

Files:
- `templates/storyboard-page.html` — added the control bar (nav), zoom controls + 원본 보기 (screen
  caption), wrapped the screen in `.sb-zoom > .sb-stage`, added the lightbox markup, and inlined
  three scripts (settings / zoom / lightbox). Still a single self-contained file, zero external deps.
- `reference/storyboard.md` — "Viewer controls (on by default)" bullet in Storyboard structure.
- `examples/verified-content-api/` — same controls via shared `storyboard.css` + new `storyboard.js`,
  applied to `sb-01`/`sb-02`.

## Decisions and why

- **Lightbox clones the `.sb-stage` (mode-agnostic).** storyboard-spec's lightbox opens an image
  (Mode A only). To make 원본 보기 work for Mode B wireframes too, the bundled lightbox clones the
  screen stage DOM and fits it to the viewport — so it works whether the stage holds a wireframe or
  an `<img class="sb-screen-img">`.
- **Controls default ON.** The user wants ExamBank parity; the controls degrade gracefully (no image
  needed) and add no external dependency.
- **`--sb-cue-op` default 100 (solid).** ExamBank defaults the slider lower for dense screenshots;
  for wireframes the callouts should read solid by default.

## Verification

- Headless-Chrome functional test on `examples/.../sb-01-benchmark.html` (programmatic clicks):
  `fz=1.12` (font + worked), `op=0.40` (opacity slider worked), `zoom=ok` (screen got a scale
  transform), `lb=open` + `clone=ok` (원본 보기 opened the lightbox with the cloned stage).
- No JS console errors on load (`--enable-logging` grep for uncaught/SEVERE → empty).
