#!/usr/bin/env python3
"""Archive zero-use or stale skills (reversible — no deletion)."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

HOME = Path.home()
DEFAULT_HTML = HOME / ".claude" / "skill-stats.html"
ARCHIVE_ROOT_CLAUDE = HOME / ".claude" / "skills-archive"
ARCHIVE_ROOT_CODEX = HOME / ".codex" / "skills-archive"


def archive_root(source: str) -> Path:
    return ARCHIVE_ROOT_CODEX if source.startswith("codex") else ARCHIVE_ROOT_CLAUDE


def load_rows(html: Path) -> list[dict]:
    text = html.read_text(encoding="utf-8")
    m = re.search(r"const ROWS = (\[.*?\]);", text, re.S)
    if not m:
        raise SystemExit(f"could not find ROWS array in {html}")
    return json.loads(m.group(1))


def is_protected(path: Path) -> bool:
    p = str(path).replace("\\", "/")
    return "/plugins/cache/" in p or "/skills-archive/" in p


def collect_candidates(
    rows: list[dict],
    verdicts: set[str],
    days: int | None,
    source_filter: str | None,
) -> list[dict]:
    chosen: list[dict] = []
    for r in rows:
        if source_filter and source_filter not in (r.get("sources") or []):
            continue
        # decision logic
        is_match = r.get("verdict") in verdicts
        if days is not None and r.get("count", 0) > 0:
            ds = r.get("days_since", -1)
            if ds is not None and ds > days:
                is_match = True
        if not is_match:
            continue
        # iterate each on-disk path
        paths = r.get("paths") or [r.get("path", "")]
        sources = r.get("sources") or [r.get("source", "claude-global")]
        for path_str, src in zip(paths, sources):
            p = Path(path_str)
            if not p.exists() or is_protected(p):
                continue
            chosen.append({
                "name": r["name"],
                "source": src,
                "path": p,
                "verdict": r.get("verdict"),
                "reason": r.get("reason"),
                "count": r.get("count", 0),
                "days_since": r.get("days_since", -1),
            })
    return chosen


def _meta(item: dict, src_path: Path, extra: dict | None = None) -> dict:
    meta = {
        "original_path": str(src_path),
        "archived_at": datetime.now().isoformat(timespec="seconds"),
        "source": item["source"],
        "verdict": item["verdict"],
        "reason": item["reason"],
        "count_at_archive": item["count"],
        "days_since_at_archive": item["days_since"],
    }
    if extra:
        meta.update(extra)
    return meta


def _archive_single_file(item: dict, src_path: Path, dry_run: bool) -> tuple[bool, str]:
    """Archive a single-file skill (e.g. ~/.codex/prompts/<name>.md).

    Wraps the file in a directory so the archive layout matches directory skills:
        <archive_root>/<source>/<stem>/<name>.md.archived
        <archive_root>/<source>/<stem>/.archived-meta.json
    """
    name = src_path.stem
    dest_dir = archive_root(item["source"]) / item["source"] / name
    archived_file = dest_dir / f"{src_path.name}.archived"
    if dest_dir.exists():
        return (False, f"archive target exists: {dest_dir}")
    if dry_run:
        return (True, f"[dry-run] move {src_path}  ->  {archived_file}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_path), str(archived_file))
    meta = _meta(item, src_path, {"kind": "single-file", "archived_filename": f"{src_path.name}.archived"})
    (dest_dir / ".archived-meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return (True, f"archived {src_path.name} -> {archived_file}")


def archive_one(item: dict, dry_run: bool) -> tuple[bool, str]:
    src_path: Path = item["path"]
    if src_path.is_symlink():
        return (False, f"symlink (not archiving): {src_path} -> {src_path.readlink()}")
    if src_path.is_file() and src_path.suffix == ".md":
        return _archive_single_file(item, src_path, dry_run)
    skill_md = src_path / "SKILL.md"
    if not skill_md.exists():
        return (False, f"no SKILL.md in {src_path}")
    dest_root = archive_root(item["source"]) / item["source"]
    dest = dest_root / src_path.name
    if dest.exists():
        return (False, f"archive target exists: {dest}")
    if dry_run:
        return (True, f"[dry-run] move {src_path}  ->  {dest}; rename SKILL.md -> SKILL.md.archived")
    dest_root.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_path), str(dest))
    (dest / "SKILL.md").rename(dest / "SKILL.md.archived")
    meta = _meta(item, src_path)
    (dest / ".archived-meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return (True, f"archived {src_path.name} -> {dest}")


def cmd_archive(args) -> int:
    html = Path(args.html).expanduser()
    if not html.exists():
        print(f"missing stats report: {html}", file=sys.stderr)
        print("  run: python3 ~/.claude/skills/skill-usage-stats/analyze.py --no-open", file=sys.stderr)
        return 1
    rows = load_rows(html)
    verdicts = set(v.strip() for v in args.verdict.split(","))
    candidates = collect_candidates(rows, verdicts, args.days, args.source)
    if not candidates:
        print("nothing matched the criteria.")
        return 0
    print(f"matched {len(candidates)} skill directories (verdicts={','.join(sorted(verdicts))}"
          f"{', stale>'+str(args.days)+'d' if args.days else ''}"
          f"{', source='+args.source if args.source else ''}):\n")
    moved = 0
    skipped = 0
    for c in candidates:
        ok, msg = archive_one(c, dry_run=not args.apply)
        prefix = "  ✓ " if ok else "  · "
        print(f"{prefix}{c['verdict'] or '-':6s}  {c['source']:22s}  {c['name'][:36]:36s}  {msg}")
        if ok:
            moved += 1
        else:
            skipped += 1
    if not args.apply:
        print(f"\nDRY-RUN: {moved} would be archived, {skipped} skipped. Re-run with --apply to commit.")
    else:
        print(f"\ndone: {moved} archived, {skipped} skipped.")
    return 0


def cmd_restore(args) -> int:
    target_name = args.name
    found = []
    for root in (ARCHIVE_ROOT_CLAUDE, ARCHIVE_ROOT_CODEX):
        if not root.exists():
            continue
        for meta in root.rglob(".archived-meta.json"):
            if meta.parent.name == target_name or target_name in str(meta.parent):
                found.append(meta)
    if not found:
        print(f"no archive entry matched: {target_name}")
        return 1
    if len(found) > 1:
        print("multiple matches — be more specific:")
        for m in found:
            print(f"  {m.parent}")
        return 2
    meta_path = found[0]
    meta = json.loads(meta_path.read_text())
    archived_dir = meta_path.parent
    original = Path(meta["original_path"])
    if original.exists():
        print(f"original path already exists: {original}", file=sys.stderr)
        return 3
    # single-file archive: move <name>.md.archived back to its original path
    if meta.get("kind") == "single-file":
        archived_file = archived_dir / meta.get("archived_filename", "")
        if not archived_file.exists():
            print(f"missing archived file: {archived_file}", file=sys.stderr)
            return 4
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(archived_file), str(original))
        meta_path.unlink()
        try:
            archived_dir.rmdir()
        except OSError:
            pass
        print(f"restored {archived_dir.name} -> {original}")
        return 0
    # standard directory archive: rename SKILL.md.archived back, drop meta, move
    skill_archived = archived_dir / "SKILL.md.archived"
    if skill_archived.exists():
        skill_archived.rename(archived_dir / "SKILL.md")
    meta_path.unlink()
    original.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(archived_dir), str(original))
    print(f"restored {archived_dir.name} -> {original}")
    return 0


def cmd_list(args) -> int:
    _ = args
    roots = [ARCHIVE_ROOT_CLAUDE, ARCHIVE_ROOT_CODEX]
    total = 0
    for root in roots:
        if not root.exists():
            continue
        entries = list(root.rglob(".archived-meta.json"))
        if not entries:
            continue
        print(f"\n{root}:")
        for meta_path in sorted(entries):
            try:
                meta = json.loads(meta_path.read_text())
            except Exception:
                continue
            print(f"  {meta_path.parent.name:36s}  "
                  f"archived {meta.get('archived_at','')[:10]}  "
                  f"src={meta.get('source','')}  "
                  f"reason={meta.get('reason','')}")
            total += 1
    if total == 0:
        print("archive is empty.")
    return 0


def main(argv: list[str] | None = None) -> int:
    # default subcommand is "archive" when first arg doesn't match a known one
    raw = sys.argv[1:] if argv is None else argv
    known = {"archive", "restore", "list-archive", "-h", "--help"}
    if raw and raw[0] not in known:
        raw = ["archive"] + raw
    elif not raw:
        raw = ["archive"]

    p = argparse.ArgumentParser(description="archive (reversible) Claude/Codex skills")
    sub = p.add_subparsers(dest="cmd")

    a = sub.add_parser("archive", help="archive skills matching criteria (default)")
    a.add_argument("--html", default=str(DEFAULT_HTML))
    a.add_argument("--verdict", default="DELETE", help="comma-separated verdicts (DELETE,REVIEW,KEEP)")
    a.add_argument("--days", type=int, default=None, help="also archive count>0 stale >N days")
    a.add_argument("--source", default=None, help="restrict to one source")
    a.add_argument("--apply", action="store_true", help="actually move (default is dry-run)")

    r = sub.add_parser("restore", help="restore a previously archived skill")
    r.add_argument("name")

    sub.add_parser("list-archive", help="list archived skills")

    args = p.parse_args(raw)
    cmd = args.cmd or "archive"
    if cmd == "archive":
        return cmd_archive(args)
    if cmd == "restore":
        return cmd_restore(args)
    if cmd == "list-archive":
        return cmd_list(args)
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
