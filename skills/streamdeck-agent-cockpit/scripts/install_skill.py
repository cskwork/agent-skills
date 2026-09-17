#!/usr/bin/env python3
"""Install this skill for Claude Code, Codex/Pi-compatible agents, or JCode."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Sequence

SOURCE = Path(__file__).resolve().parents[1]
TARGETS = {
    "claude": Path("~/.claude/skills/streamdeck-agent-cockpit"),
    "agents": Path("~/.agents/skills/streamdeck-agent-cockpit"),
    "jcode": Path("~/.jcode/skills/streamdeck-agent-cockpit"),
}
IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    ".DS_Store",
    ".git",
    "node_modules",
    "logs",
)


def expand(path: Path | str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(path)))).resolve()


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        action="append",
        choices=["claude", "agents", "jcode", "all"],
        required=False,
        help="Repeat to install to multiple harness locations",
    )
    parser.add_argument("--destination", help="Install to one explicit directory instead of named targets")
    parser.add_argument("--mode", choices=["copy", "symlink"], default="copy")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def resolve_destinations(args: argparse.Namespace) -> list[Path]:
    if args.destination:
        return [expand(args.destination)]
    names: list[str] = []
    for target in (args.target or []):
        if target == "all":
            names.extend(TARGETS)
        else:
            names.append(target)
    result: list[Path] = []
    seen: set[Path] = set()
    for name in names:
        destination = expand(TARGETS[name])
        if destination not in seen:
            seen.add(destination)
            result.append(destination)
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    destinations = resolve_destinations(args)
    if not destinations:
        print("error: no destination resolved", file=sys.stderr)
        return 2

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    for destination in destinations:
        if destination == SOURCE or SOURCE in destination.parents:
            print(f"error: refusing recursive install into source: {destination}", file=sys.stderr)
            return 2
        if destination.exists() or destination.is_symlink():
            if not args.force:
                print(f"error: destination exists: {destination}; use --force", file=sys.stderr)
                return 1
            backup = destination.with_name(destination.name + f".backup-{stamp}")
            print(f"backup {destination} -> {backup}")
            if not args.dry_run:
                if backup.exists() or backup.is_symlink():
                    print(f"error: backup destination already exists: {backup}", file=sys.stderr)
                    return 1
                destination.rename(backup)

        print(f"install ({args.mode}) {SOURCE} -> {destination}")
        if args.dry_run:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if args.mode == "symlink":
            destination.symlink_to(SOURCE, target_is_directory=True)
        else:
            shutil.copytree(SOURCE, destination, ignore=IGNORE)

    print("DRY RUN" if args.dry_run else f"Installed to {len(destinations)} destination(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
