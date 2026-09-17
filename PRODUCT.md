# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack
static HTML/CSS: one `index.html` at the repo root, served by GitHub Pages, no build step (stated in the brief).

## Users
[inferred] Primary: the owner (GitHub `cskwork`) on a fresh machine or a new agent harness, wanting to reinstall the library in one command and recall what is in it. Secondary: developers who land on the repo from GitHub or skills.sh and want to judge in seconds whether to install one skill or the set.

## Product Purpose
A single public source of truth for personal agent skills (Claude Code, Codex, OpenCode, Pi, Hermes). `npx skills add cskwork/agent-skills` projects it into every harness; `npx skills update -g` keeps machines in sync. The landing page succeeds when a visitor knows what the library is, sees the actual skills, and copies the install line.

## Positioning
One canonical repo, no per-harness copies, with profiles (`core`, `all`, `third-party`) and a private companion repo whose installer pulls this one too. The skills are the owner's daily tools, not a curated showcase: usage counts from the owner's own session logs exist for them.

## Operating Context
Terminal-first. Install: `npx skills add cskwork/agent-skills -g -a claude-code codex opencode -s '*' -y`, or `install.sh -p <profile> -t`. Clone lives at `~/.agents/sources/cskwork/agent-skills`; edits are committed there and pushed; other machines run `npx skills update -g`. Skills follow the standard `skills/<name>/SKILL.md` layout.

## Capabilities and Constraints
- 23 skills at launch (2026-09-17), each with a `SKILL.md` whose frontmatter `description` is the authoritative one-line summary.
- Profiles: `core` (14 default), `all` (23), `third-party` (17 external repos).
- No analytics, no external JS dependencies, no build tooling; page must work as a single file.
- [inferred] Bilingual audience: owner reads Korean, README carries a Korean section; page copy in English with the install line universal.
- Undecided: custom domain (none), OG image (none yet).

## Brand Commitments
Name: `agent-skills` under `cskwork`. Voice of the README: terse, procedural, no marketing adjectives. No logo, palette, or type commitments exist.

## Evidence on Hand
- Skill names and descriptions: `skills/*/SKILL.md` frontmatter.
- Owner's 90-day usage counts (2026-06-19 to 2026-09-17) from `skill-usage-stats`: verification-before-completion 78, gh-release 37, unslop 17, call-agent 17, browser-qa 11, diagnose 11, superpm 9, create-verification-skill 7, refine-skill-terse 6, impeccable 5, sdlc-kit 5, verify 5, gpt-image-2 4, agent-browser 3, sync-skill 2, aside-browser 1, streamdeck-agent-cockpit 1. These are the owner's own numbers and must be labeled as such.
- Absent, do not fabricate: GitHub stars, downloads, testimonials, third-party users, benchmarks.

## Product Principles
- The install line is the product; it must be visible and copyable in the first viewport.
- Show the real skills, from real descriptions; nothing on the page that the repo does not contain.
- The page is a static file that the repo can carry forever without maintenance tooling.
- Truth over promotion: owner's usage counts are the only proof, and they are labeled as the owner's.
