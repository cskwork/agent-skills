#!/usr/bin/env python3
"""Terminal summary of an existing skill-stats.html report.

Reads the embedded ROWS JSON from the HTML and prints top-N, zero-use, and stale
lists without needing a browser. Run analyze.py first to generate the HTML.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HOME = Path.home()
DEFAULT_HTML = HOME / ".claude" / "skill-stats.html"


def load_rows(html_path: Path) -> list[dict]:
    text = html_path.read_text(encoding="utf-8")
    m = re.search(r"const ROWS = (\[.*?\]);", text, re.S)
    if not m:
        raise SystemExit(f"could not find ROWS array in {html_path}")
    return json.loads(m.group(1))


def src_label(r: dict) -> str:
    return ",".join(r.get("sources") or [r.get("source", "?")])


def row_matches_source(r: dict, source: str | None) -> bool:
    if not source:
        return True
    return source in (r.get("sources") or [r.get("source")])


def fmt_row(r: dict) -> str:
    last = (r.get("last_used") or "")[:10] or "—"
    days = r.get("days_since")
    days_s = "never" if r.get("count", 0) == 0 else f"{days}d"
    return (
        f"{r['count']:5d}  "
        f"{r.get('verdict','-'):7s}  "
        f"{src_label(r)[:30]:30s}  "
        f"{r['name'][:36]:36s}  "
        f"last={last:10s}  "
        f"{days_s:>6s}  "
        f"{r['size_kb']:6.1f} KB"
    )


def cmd_top(rows: list[dict], n: int, source: str | None) -> None:
    filtered = [r for r in rows if row_matches_source(r, source)]
    filtered.sort(key=lambda r: -r["count"])
    print(f"\nTop {n} most-used skills" + (f" ({source})" if source else "") + ":\n")
    for r in filtered[:n]:
        print(fmt_row(r))


def cmd_zero(rows: list[dict], source: str | None) -> None:
    filtered = [r for r in rows if r["count"] == 0 and row_matches_source(r, source)]
    filtered.sort(key=lambda r: (src_label(r), r["name"].lower()))
    print(f"\nZero-use skills ({len(filtered)} total):\n")
    for r in filtered:
        paths = (r.get("paths") or [r.get("path", "")])[0]
        print(f"  {r.get('verdict','-'):7s}  {src_label(r)[:28]:28s}  {r['name'][:46]:46s}  {r['size_kb']:6.1f} KB  {paths}")


def cmd_stale(rows: list[dict], days: int, source: str | None) -> None:
    filtered = [
        r for r in rows
        if row_matches_source(r, source)
        and (r["count"] == 0 or (r.get("days_since", -1) > days))
    ]
    filtered.sort(key=lambda r: (-(r.get("days_since") or 0), r["name"].lower()))
    print(f"\nStale skills (>{days}d or never used, {len(filtered)} total):\n")
    for r in filtered:
        last = (r.get("last_used") or "")[:10] or "never"
        days_s = "never" if r["count"] == 0 else f"{r['days_since']}d"
        print(f"  {days_s:>6s}  last={last:10s}  {r.get('verdict','-'):7s}  {src_label(r)[:28]:28s}  {r['name']}")


def cmd_overview(rows: list[dict]) -> None:
    by_source: dict[str, dict] = {}
    by_verdict: dict[str, int] = {"KEEP": 0, "REVIEW": 0, "DELETE": 0}
    for r in rows:
        source_counts = r.get("source_counts") or {}
        sources = r.get("sources") or [r.get("source") or "?"]
        for src in sources:
            src_str = str(src)
            s = by_source.setdefault(src_str, {"count": 0, "used": 0, "total_calls": 0})
            s["count"] += 1
            # use per-source breakdown when available; falls back to total
            per_src = source_counts.get(src_str, r["count"] if len(sources) == 1 else 0)
            s["total_calls"] += per_src
            if per_src > 0:
                s["used"] += 1
        v = r.get("verdict")
        if isinstance(v, str) and v in by_verdict:
            by_verdict[v] += 1
    print("\nOverview by source (a skill in N sources shows in N rows; calls attributed per source):\n")
    print(f"  {'source':22s}  {'skills':>6s}  {'used':>6s}  {'invocations':>12s}")
    for src, s in sorted(by_source.items()):
        print(f"  {src:22s}  {s['count']:6d}  {s['used']:6d}  {s['total_calls']:12d}")
    total = len(rows)
    used = sum(1 for r in rows if r["count"] > 0)
    print(f"\n  unique skills: {total}    used at least once: {used}    zero-use: {total - used}")
    print(f"  verdicts: KEEP={by_verdict['KEEP']}  REVIEW={by_verdict['REVIEW']}  DELETE={by_verdict['DELETE']}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="terminal summary of skill-stats.html")
    p.add_argument("--html", default=str(DEFAULT_HTML), help="path to generated HTML")
    p.add_argument("--source", default=None,
                   choices=["claude-global", "claude-project",
                            "codex-global-skill", "codex-global-prompt"],
                   help="restrict to one catalog source")
    sub = p.add_subparsers(dest="cmd", required=False)
    s_top = sub.add_parser("top", help="show top-N most-used skills (default)")
    s_top.add_argument("-n", type=int, default=20)
    sub.add_parser("zero", help="list skills never invoked")
    s_stale = sub.add_parser("stale", help="list skills unused for >N days")
    s_stale.add_argument("--days", type=int, default=90)
    sub.add_parser("overview", help="aggregate stats per source")
    args = p.parse_args(argv)

    html_path = Path(args.html).expanduser()
    if not html_path.exists():
        print(f"not found: {html_path}\n  run: python3 {Path(__file__).parent / 'analyze.py'}",
              file=sys.stderr)
        return 1
    rows = load_rows(html_path)

    cmd = args.cmd or "top"
    if cmd == "top":
        cmd_top(rows, args.n, args.source)
    elif cmd == "zero":
        cmd_zero(rows, args.source)
    elif cmd == "stale":
        cmd_stale(rows, args.days, args.source)
    elif cmd == "overview":
        cmd_overview(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
