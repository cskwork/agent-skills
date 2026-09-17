#!/usr/bin/env python3
"""Register the Codex CLI hook bridge in a user hooks.json file.

The operation is append-only and idempotent. Use --dry-run first and back up
the existing file before the first write. Codex still requires the user to
review/trust a newly installed command hook in the /hooks screen.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

HOOK_SCRIPT = Path(__file__).resolve().parent / "codex_hook.py"

EVENTS = {
    "SessionStart": True,
    "UserPromptSubmit": False,
    "Stop": False,
    "SessionEnd": True,
}

EXTENDED_EVENTS = {
    "PreToolUse": True,
    "PostToolUse": True,
    "PermissionRequest": True,
    "PreCompact": True,
    "PostCompact": True,
    "SubagentStart": False,
    "SubagentStop": False,
}


def command_string(interpreter: str) -> str:
    return f"{shlex.quote(interpreter)} {shlex.quote(str(HOOK_SCRIPT))}"


def block(command: str, with_matcher: bool) -> Dict[str, Any]:
    handler = {"type": "command", "command": command, "timeout": 15}
    entry: Dict[str, Any] = {"hooks": [handler]}
    if with_matcher:
        entry["matcher"] = "*"
    return entry


def already_present(blocks: List[Any]) -> bool:
    for entry in blocks:
        for handler in (entry or {}).get("hooks", []):
            if HOOK_SCRIPT.name in str((handler or {}).get("command", "")):
                return True
    return False


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", default="~/.codex/hooks.json")
    parser.add_argument("--interpreter", default=sys.executable)
    parser.add_argument("--extended", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    settings = Path(os.path.expanduser(args.settings))
    if settings.exists():
        try:
            data = json.loads(settings.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"invalid JSON in {settings}: {exc}", file=sys.stderr)
            return 1
        if not isinstance(data, dict):
            print(f"invalid hooks root in {settings}: expected object", file=sys.stderr)
            return 1
    else:
        data = {}

    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        print(f"invalid hooks value in {settings}: expected object", file=sys.stderr)
        return 1

    events = dict(EVENTS)
    if args.extended:
        events.update(EXTENDED_EVENTS)

    command = command_string(args.interpreter)
    added: list[str] = []
    for event, with_matcher in events.items():
        blocks = hooks.setdefault(event, [])
        if not isinstance(blocks, list):
            print(f"invalid {event} hooks in {settings}: expected array", file=sys.stderr)
            return 1
        if already_present(blocks):
            continue
        blocks.append(block(command, with_matcher))
        added.append(event)

    if not added:
        print("no change; the Codex hook bridge is already registered")
        return 0

    print(f"command: {command}")
    print("events to add: " + ", ".join(added))
    if args.dry_run:
        print("(dry run; nothing written)")
        return 0

    settings.parent.mkdir(parents=True, exist_ok=True)
    temporary = settings.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(settings)
    print(f"installed: {settings}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
