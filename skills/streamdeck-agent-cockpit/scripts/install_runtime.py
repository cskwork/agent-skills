#!/usr/bin/env python3
"""Install the standalone Agent Cockpit runtime into a user-owned directory."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
MANAGED_BIN = [
    ROOT / "bin/cockpitd.py",
    ROOT / "bin/cockpitctl.py",
    ROOT / "bin/focus_tmux.py",
    ROOT / "bin/report_state.py",
    ROOT / "bin/slotclaims.py",
    ROOT / "bin/claim_probe.py",
    ROOT / "bin/herdr_agent.py",
    ROOT / "bin/herdr_claim_probe.py",
    ROOT / "bin/focus_herdr.py",
    ROOT / "bin/focus_terminal.py",
    ROOT / "bin/windows_terminal_uia.ps1",
    ROOT / "bin/claude_hook.py",
    ROOT / "bin/install_claude_hooks.py",
    ROOT / "bin/codex_hook.py",
    ROOT / "bin/install_codex_hooks.py",
    ROOT / "scripts/validate_cockpit.py",
    ROOT / "scripts/generate_launchers.py",
    ROOT / "scripts/probe_environment.py",
]


def backup_path(target: Path, stamp: str) -> Path:
    return target.parent / "backups" / stamp / target.name


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default="~/.agent-cockpit")
    parser.add_argument("--config-template", default=str(ROOT / "assets/cockpit.example.json"))
    parser.add_argument("--force", action="store_true", help="Back up and replace managed files, including config")
    parser.add_argument("--update-runtime", action="store_true", help="Replace managed binaries but preserve existing config")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    target = Path(os.path.expandvars(os.path.expanduser(args.target))).resolve()
    bin_dir = target / "bin"
    config_target = target / "cockpit.json"
    template = Path(os.path.expandvars(os.path.expanduser(args.config_template))).resolve()
    if not template.exists():
        print(f"error: config template not found: {template}", file=sys.stderr)
        return 2

    destinations = [(source, bin_dir / source.name) for source in MANAGED_BIN]
    destinations.append((ROOT / "assets/cockpit.schema.json", target / "cockpit.schema.json"))
    existing_runtime = [dest for _, dest in destinations if dest.exists()]
    config_exists = config_target.exists()

    if (existing_runtime or config_exists) and not (args.force or args.update_runtime):
        print("error: managed runtime/config already exists; use --update-runtime or --force", file=sys.stderr)
        for path in existing_runtime + ([config_target] if config_exists else []):
            print(f"  {path}", file=sys.stderr)
        return 1

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    actions: list[str] = []

    for source, destination in destinations:
        if destination.exists():
            backup = backup_path(destination, stamp)
            actions.append(f"backup {destination} -> {backup}")
            if not args.dry_run:
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, backup)
        actions.append(f"copy {source} -> {destination}")
        if not args.dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copy2(source, destination)
            destination.chmod(0o755)

    replace_config = args.force or not config_exists
    if replace_config:
        if config_exists:
            backup = backup_path(config_target, stamp)
            actions.append(f"backup {config_target} -> {backup}")
            if not args.dry_run:
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(config_target, backup)
        actions.append(f"copy {template} -> {config_target}")
        if not args.dry_run:
            target.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copy2(template, config_target)
            config_target.chmod(0o600)
    else:
        actions.append(f"preserve {config_target}")

    readme_target = target / "README.txt"
    readme = (
        "Stream Deck Agent Cockpit standalone runtime\n\n"
        "Validate: bin/validate_cockpit.py cockpit.json\n"
        "Start:    bin/cockpitd.py --config cockpit.json\n"
        "Inspect:  bin/cockpitctl.py --config cockpit.json health\n"
        "Launchers: bin/generate_launchers.py --config cockpit.json --output launchers\n"
        "\nThe daemon creates a private token file on first start.\n"
    )
    actions.append(f"write {readme_target}")
    if not args.dry_run:
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        readme_target.write_text(readme, encoding="utf-8")
        try:
            target.chmod(0o700)
        except OSError:
            pass

    for action in actions:
        print(action)
    print("DRY RUN" if args.dry_run else f"Installed runtime at {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
