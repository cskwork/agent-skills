---
name: gh-release
description: Cut a versioned GitHub release for a repo - tag, push, and publish release notes from the changelog. Use when the user says "do a release", "release vX", "릴리스 해줘", "cut a release", or "publish to GitHub releases".
---

# gh-release

Tag -> push -> publish: turn the current release branch into a versioned GitHub release with notes.

## When to use
- "do a vX.Y.Z release", "release this", "릴리스 해줘", "cut a release"
- After changes are merged to the release branch and you want a tagged, published release.

Not for: pushing ordinary commits (just `git push`), or pre-release WIP that should not be tagged.

## Steps
1. Confirm version + clean tree: `git status` (no uncommitted changes); read latest `log/changelog-*.md` for notes.
2. Tag: `git tag vX.Y.Z` (annotated if the repo uses annotated tags).
3. Push the tag: `git push origin vX.Y.Z`.
4. Publish: `gh release create vX.Y.Z --title "vX.Y.Z" --notes-file <notes>` (or `--notes "<summary>"`).
5. Verify: `gh release view vX.Y.Z` shows the release; report the URL.

## Notes
Stop and ask before tagging if `git status` is dirty or the version already exists (`git tag -l vX.Y.Z`).
