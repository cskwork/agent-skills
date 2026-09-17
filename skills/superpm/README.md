# /superpm

**English** | [한국어](README.ko.md)

**One PM request in, a verified artifact out - the smallest useful artifact, checked by an
independent critic against the framework and the real decision.**

A single agent skill that folds the whole PM toolbox into one workflow: it captures intent from
your request, **diverges by PM domain** into the right framework, produces the smallest useful
artifact, and runs an independent critic over it before delivery - then stops.

No extra install: clone the repo, symlink it into your skills directory, then `/superpm <ask>`.
Landing page: **[cskwork.github.io/superpm-skill](https://cskwork.github.io/superpm-skill/)**.

## What it is

`phuryn/pm-skills` is a marketplace of 68 PM skills across 9 plugins, each a separate file you
load by name. `superpm` collapses that catalog into **one skill, one repo**. You do not pick a
skill; you state the PM ask and the workflow routes it:

```
/superpm write a PRD for in-app referral
/superpm what's our TAM/SAM/SOM for SMB payroll in Korea
/superpm build an opportunity solution tree for activation
/superpm draft a pricing strategy for the pro tier
/superpm read this A/B test and tell me ship or kill
/superpm a GTM plan for the EU launch
/superpm review my PM resume against this job description
```

## How it works

The same loop runs for every domain; only the framework that loads changes.

1. **Capture** - classify the ask into a PM domain + a target artifact. If genuinely ambiguous,
   a <=5 question interview gate fires; anything answerable from your docs/data is read, not asked.
2. **Frame** - state the real decision the artifact must serve and its completion bar.
3. **Draft** - apply the domain framework. Smallest useful artifact, real inputs, assumptions
   labeled.
4. **Critic** - an independent pass red-teams the draft: missing sections, unsourced claims,
   unvalidated assumptions, dodged decisions - each emitted as a risk.
5. **Deliver** - fold the risks back in and stop, reporting what was checked.

## Domains (9 pm-skills plugins + screen-design + flow + package = 12)

The four build-planning domains form a chain on one source of truth (the 기능명세 / SPEC):
**EXECUTE -> FLOW -> STORYBOARD -> PACKAGE**, contract in [`reference/model.md`](reference/model.md).

| Domain | Covers |
|---|---|
| **DISCOVER** | ideation, risky assumptions, opportunity solution tree, feature prioritization, customer interviews, metrics |
| **STRATEGY** | strategy canvas, vision, value proposition, lean/business model, monetization, pricing, SWOT/PESTLE/Porter/Ansoff |
| **EXECUTE** | PRD, OKRs, outcome roadmap, sprint, retro, pre-mortem, stories, stakeholder map, prioritization frameworks, red-team |
| **FLOW** | user-flow graph - nodes derived from SPECs (R2), page->screen hand-off (R3), zero-dep visualization (text list + boxes) |
| **STORYBOARD** | 화면설계서/기능명세 screen design docs - wireframe (plan-first) or replica/Figma, per-element spec; runs standalone via bundled HTML, optional `storyboard-spec` accelerator |
| **PACKAGE** | integrated implementation bundle - PRD+spec+flow+wireframe under one snapshotId (R6), back-link integrity, md/json/svg/html export |
| **RESEARCH** | personas, segmentation, customer journey, market sizing (TAM/SAM/SOM), competitor analysis, sentiment - grounded in live, keyless market signal (voice of customer) |
| **ANALYTICS** | NL->SQL, cohort analysis, A/B test read-out |
| **GTM** | go-to-market, beachhead, ICP, growth loops, motions, battlecard |
| **GROWTH** | marketing ideas, positioning, value-prop statements, naming, North Star metric |
| **TOOLKIT** | resume review/tailoring, NDA, privacy policy, proofreading |
| **AI-SHIP** | shipping artifacts, intended-vs-implemented gap (cited evidence) |

## Why a critic

PM artifacts have no unit tests, so a plausible-looking draft can be wrong. `superpm` borrows
`supergoal`'s discipline: an independent reader checks the artifact against three grounds -
**framework completeness, the real decision, and the evidence behind every claim** - and names
each gap as a risk before you ship it. Unsourced numbers and dodged decisions are blockers.

## Install

This repo **is** the skill. Put it where your agent CLI finds skills:

```bash
git clone <repo-url> superpm-skill
ln -s "$(pwd)/superpm-skill" <your-agent-skills-dir>/superpm
# examples: ~/.claude/skills/superpm, ~/.codex/skills/superpm
```

Then in your agent CLI: `/superpm <your PM ask>`.

## Layout

```
SKILL.md      thin spine: principles, intent-capture table, the loop, reference map
reference/    intent · critic · signal · model · discover · strategy · execute · flow · storyboard · package · research · analytics · gtm · growth · toolkit · ai-ship
templates/    PRD · strategy canvas · opportunity solution tree · battlecard · storyboard page/board · workspace (3-tab)
docs/         DESIGN.md
```

## Credit

- PM framework catalog: **[phuryn/pm-skills](https://github.com/phuryn/pm-skills)** (MIT),
  curated by Paweł Huryn - merged here into one skill.
- Workflow + verification discipline adapted from **[cskwork/supergoal-skill](https://github.com/cskwork/supergoal-skill)** (MIT).
- Screen-design storyboard method (optional accelerator) from **[cskwork/storyboard-spec](https://github.com/cskwork/storyboard-spec)** (MIT).
- Live-signal method (optional `last30days` accelerator) from **[mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill)** (MIT).
- Keyless read techniques (Jina Reader, RSS) from **[Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach)** (MIT).

## License

MIT. See [`LICENSE`](LICENSE).
