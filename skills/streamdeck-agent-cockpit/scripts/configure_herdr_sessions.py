#!/usr/bin/env python3
"""Convert declared attached-agent slots from terminal tty to Herdr focus.

Only ``session.claude.slotN`` and ``session.codex.slotN`` are changed.  The
script preserves every other session/control, makes a timestamped backup, and
requires ``--apply`` before it writes the user configuration.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence


SLOT_RE = re.compile(r"^session\.(claude|codex)\.slot[1-9][0-9]*$")


def expand(value: str | Path) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(value)))).resolve()


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="~/.agent-cockpit/cockpit.json")
    parser.add_argument("--runtime-dir", default="~/.agent-cockpit")
    parser.add_argument("--herdr-bin", default=shutil.which("herdr") or "herdr")
    parser.add_argument("--session", action="append", help="One attached slot to update; repeatable")
    parser.add_argument("--apply", action="store_true", help="Write the modified config after backing it up")
    return parser.parse_args(argv)


def load_config(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid config {path}: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("sessions"), dict):
        raise ValueError("config has no sessions object")
    return value


def configure(config: Dict[str, Any], runtime_dir: Path, herdr_bin: Path, selected: Optional[set[str]]) -> list[str]:
    sessions = config["sessions"]
    changed: list[str] = []
    for session_id, session in sessions.items():
        if selected is not None and session_id not in selected:
            continue
        if not SLOT_RE.fullmatch(session_id):
            continue
        if not isinstance(session, dict):
            raise ValueError(f"session is not an object: {session_id}")
        agent = SLOT_RE.fullmatch(session_id).group(1)  # type: ignore[union-attr]
        if session.get("agent") != agent:
            raise ValueError(f"session agent does not match id: {session_id}")
        commands = session.setdefault("commands", {})
        if not isinstance(commands, dict):
            raise ValueError(f"session commands is not an object: {session_id}")
        env = {"AGENT_COCKPIT_HERDR_BIN": str(herdr_bin)}
        session["adapter"] = {
            "type": "command",
            "probe": {
                "argv": ["/usr/bin/env", "python3", str(runtime_dir / "bin" / "herdr_claim_probe.py"), "--slot", session_id],
                "env": env,
                "timeoutSeconds": 12,
            },
        }
        commands["focus"] = {
            "argv": ["/usr/bin/env", "python3", str(runtime_dir / "bin" / "focus_herdr.py"), "--slot", session_id],
            "env": env,
            "timeoutSeconds": 12,
        }
        changed.append(session_id)
    if selected is not None:
        missing = selected.difference(changed)
        if missing:
            raise ValueError(f"not attached Claude/Codex slots: {', '.join(sorted(missing))}")
    if not changed:
        raise ValueError("no attached Claude/Codex slots found")
    return changed


def atomic_write(path: Path, value: Dict[str, Any]) -> None:
    mode = path.stat().st_mode & 0o777
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, mode or 0o600)
    temporary.replace(path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    config_path = expand(args.config)
    runtime_dir = expand(args.runtime_dir)
    herdr_bin = expand(args.herdr_bin)
    if not herdr_bin.is_file() or not os.access(herdr_bin, os.X_OK):
        print(f"error: Herdr executable is unavailable: {herdr_bin}", file=sys.stderr)
        return 2
    try:
        config = load_config(config_path)
        selected = set(args.session) if args.session else None
        changed = configure(config, runtime_dir, herdr_bin, selected)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not args.apply:
        print(json.dumps({"ok": True, "dryRun": True, "sessions": changed}, indent=2))
        return 0

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = config_path.with_name(f"{config_path.name}.backup-{stamp}")
    try:
        shutil.copy2(config_path, backup)
        atomic_write(config_path, config)
    except OSError as exc:
        print(f"error: failed to write config: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "sessions": changed, "backup": str(backup)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
