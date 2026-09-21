#!/usr/bin/env bash
# Install cskwork/agent-skills (+ optional third-party list) into local agent harnesses via `npx skills`.
#
#   ./install.sh                  # profile "core", agents claude-code codex opencode
#   ./install.sh -p all           # every skill in this repo
#   ./install.sh -p core -t       # also install profiles/third-party.txt
#   ./install.sh -a "claude-code codex opencode pi hermes"
#
# Requirements: node >= 18 (npx), git. Private repos additionally need `gh auth login`
# (or any git credential helper for github.com).
set -euo pipefail

REPO="cskwork/agent-skills"
PROFILE="core"
AGENTS="claude-code codex opencode"
THIRD_PARTY=0
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

while getopts "p:a:th" opt; do
  case "$opt" in
    p) PROFILE="$OPTARG" ;;
    a) AGENTS="$OPTARG" ;;
    t) THIRD_PARTY=1 ;;
    h) sed -n '2,12p' "$0"; exit 0 ;;
    *) exit 2 ;;
  esac
done

read_list() { grep -vE '^\s*(#|$)' "$1"; }

# shellcheck disable=SC2086
add() { # add <owner/repo> <skill...>
  local repo="$1"; shift
  echo "==> $repo: $*"
  npx -y skills add "$repo" -g -y -a $AGENTS -s "$@" || echo "warn: install failed for $repo ($*)"
}

PROFILE_FILE="$HERE/profiles/$PROFILE.txt"
[ -f "$PROFILE_FILE" ] || { echo "no such profile: $PROFILE_FILE" >&2; exit 1; }
add "$REPO" $(read_list "$PROFILE_FILE")

if [ "$THIRD_PARTY" = 1 ]; then
  while read -r repo skills; do add "$repo" $skills; done < <(read_list "$HERE/profiles/third-party.txt")
fi

# The default profile also installs the shared writing policy when Humanizer is available.
if read_list "$PROFILE_FILE" | grep -qx humanizer; then
  if [ -s "$HOME/.agents/skills/humanizer/SKILL.md" ]; then
    node "$HERE/scripts/install-writing-rule.mjs" "$HOME/.agents/rules"
  else
    echo "warn: humanizer is unavailable; writing policy was not changed" >&2
  fi
fi

echo "done. verify with: npx skills ls -g"
