# agent-skills

Landing page: https://cskwork.github.io/agent-skills/ (the shop board; `index.html` at the repo root, built with the `impeccable` skill).

Personal library of agent skills (Claude Code, Codex, OpenCode, Pi, Hermes, ...).
This repo is the **source of truth**; `npx skills` projects it into each harness.
Domain-specific / work skills live in the private companion repo `cskwork/agent-skills-private`,
whose installer also pulls this repo, so installing the private one gives you both.

## Layout

```
skills/<name>/SKILL.md     one folder per skill (standard SKILL.md format)
profiles/core.txt          default subset
profiles/all.txt           every skill here
profiles/third-party.txt   external repos installed alongside (owner/repo skill...)
install.sh                 bootstrap wrapper around `npx skills add`
```

## New machine

```bash
gh auth login                                   # only needed for private repos
npx skills add cskwork/agent-skills -g -a claude-code codex opencode -s '*' -y
# or, with profiles + third-party list:
git clone https://github.com/cskwork/agent-skills ~/.agents/sources/cskwork/agent-skills
~/.agents/sources/cskwork/agent-skills/install.sh -p all -t
```

`npx skills` keeps a git clone in `~/.agents/sources/cskwork/agent-skills` and symlinks
`~/.claude/skills/<name>` (etc.) to it. Do not keep per-harness copies.

## Daily use

```bash
# edit in the clone, then publish
cd ~/.agents/sources/cskwork/agent-skills
git add -A && git commit -m "<skill>: ..." && git push

# other machines
npx skills update -g

# add a new skill
mkdir -p skills/my-skill && $EDITOR skills/my-skill/SKILL.md
echo my-skill >> profiles/all.txt
npx skills add cskwork/agent-skills -g -s my-skill -a claude-code codex opencode -y
```

## Notes

- `superpm`, `streamdeck-agent-cockpit`, `skill-usage-stats`, `naver-cloud-vpn`, `aside-browser`
  also exist as standalone repos (`cskwork/*-skill`). The copies here are the ones actually
  in use; the standalone repos are publishing artifacts and may lag.
- Most-used skills that also ship in `cskwork/pi-setup` (Pi harness) — `sdlc-kit`, `verification-before-completion`,
  `call-agent`, `browser-qa`, `create-verification-skill`, `verify`, `impeccable`, `gpt-image-2`, `agent-browser` —
  are canonical **here**; Claude/Codex/OpenCode link to this repo, Pi still reads its own copy in pi-setup.
  Verification artifacts (`.verify/`, `.impeccable/`) are intentionally not included.

## 한국어

이 저장소가 개인 스킬의 원본입니다. 새 PC에서는 `gh auth login` 후 위의
`npx skills add ...` 한 줄로 설치하고, 수정은 `~/.agents/sources/cskwork/agent-skills`에서
커밋·푸시하며, 다른 PC에서는 `npx skills update -g`로 받습니다.
업무용 스킬은 비공개 저장소 `agent-skills-private`에 있고, 그 설치 스크립트가 이 저장소도 함께 설치합니다.
