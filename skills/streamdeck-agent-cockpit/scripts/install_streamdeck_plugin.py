#!/usr/bin/env python3
"""Install one built, owned Agent Cockpit Stream Deck plugin on macOS."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_UUID = "com.cskwork.agent-cockpit"
ACTION_UUID = f"{PLUGIN_UUID}.control"
PLUGIN_DIRNAME = f"{PLUGIN_UUID}.sdPlugin"
DEFAULT_SOURCE = ROOT / "streamdeck-plugin" / PLUGIN_DIRNAME
DEFAULT_DESTINATION = (
    Path("~/Library/Application Support/com.elgato.StreamDeck/Plugins").expanduser()
    / PLUGIN_DIRNAME
)


def manifest(path: Path) -> dict:
    try:
        value = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"invalid plugin manifest at {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("UUID") != PLUGIN_UUID:
        raise RuntimeError(f"refusing plugin with unexpected UUID at {path}")
    actions = value.get("Actions")
    action_ids = {
        action.get("UUID") for action in actions or [] if isinstance(action, dict)
    }
    if ACTION_UUID not in action_ids:
        raise RuntimeError(f"plugin does not declare owned action {ACTION_UUID}")
    return value


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    source = args.source.expanduser().resolve()
    destination = args.destination.expanduser()
    if destination.name != PLUGIN_DIRNAME:
        print(f"error: destination must end with {PLUGIN_DIRNAME}", file=sys.stderr)
        return 2
    try:
        manifest(source)
        if not (source / "bin" / "plugin.js").is_file():
            raise RuntimeError("plugin is not built; run npm ci && npm run build first")
        destination.parent.mkdir(parents=True, exist_ok=True)
        backup = None
        if destination.exists() or destination.is_symlink():
            manifest(destination.resolve())
            if not args.force:
                raise RuntimeError(f"destination exists: {destination}; use --force")
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            backup = destination.with_name(f"{destination.name}.backup-{stamp}")
            destination.rename(backup)
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns("logs", "*.log", ".DS_Store"),
        )
        os.chmod(destination / "bin" / "plugin.js", 0o755)
    except (OSError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "ok": True,
        "installed": str(destination),
        "backup": str(backup) if backup else None,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
