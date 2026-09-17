#!/usr/bin/env python3
"""Generate static Stream Deck launchers for configured tap controls."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_cockpit  # noqa: E402
from typing import Any, Dict, Optional, Sequence


def load_config(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Config not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON at {path}:{exc.lineno}:{exc.colno}: {exc.msg}") from exc
    if not isinstance(data, dict) or data.get("version") != 3:
        raise RuntimeError("Expected cockpit configuration version 3")
    return data


def safe_name(control_id: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", control_id).strip(".-")
    return name or "control"


def resolve_ctl(explicit: Optional[str]) -> Path:
    if explicit:
        return Path(os.path.expandvars(os.path.expanduser(explicit))).resolve()
    here = Path(__file__).resolve()
    candidates = [here.parent / "cockpitctl.py", here.parents[1] / "bin/cockpitctl.py"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def posix_launcher(python: str, ctl: Path, config: Path, control_id: str) -> str:
    argv = [python, str(ctl), "--config", str(config), "invoke", control_id, "--gesture", "tap"]
    return "#!/bin/sh\nexec " + " ".join(shlex.quote(part) for part in argv) + "\n"


def cmd_quote(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def windows_launcher(python: str, ctl: Path, config: Path, control_id: str) -> str:
    argv = [python, str(ctl), "--config", str(config), "invoke", control_id, "--gesture", "tap"]
    return "@echo off\r\n" + " ".join(cmd_quote(part) for part in argv) + "\r\nexit /b %ERRORLEVEL%\r\n"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="~/.agent-cockpit/cockpit.json")
    parser.add_argument("--output", default="~/.agent-cockpit/launchers")
    parser.add_argument("--cockpitctl")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--platform", choices=["auto", "posix", "windows", "all"], default="auto")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    config_path = Path(os.path.expandvars(os.path.expanduser(args.config))).resolve()
    output = Path(os.path.expandvars(os.path.expanduser(args.output))).resolve()
    ctl = resolve_ctl(args.cockpitctl)
    try:
        config = load_config(config_path)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    findings = validate_cockpit.validate(config)
    if findings.errors:
        print("error: refusing to generate launchers from invalid configuration", file=sys.stderr)
        for item in findings.errors:
            print(f"  {item}", file=sys.stderr)
        return 2
    if not ctl.exists():
        print(f"error: cockpitctl.py not found: {ctl}", file=sys.stderr)
        return 2

    selected = args.platform
    if selected == "auto":
        selected = "windows" if platform.system().lower() == "windows" else "posix"
    platforms = ["posix", "windows"] if selected == "all" else [selected]

    generated: list[Dict[str, Any]] = []
    skipped: list[Dict[str, str]] = []
    for control_id, control in sorted((config.get("controls") or {}).items()):
        tap = (control.get("gestures") or {}).get("tap") if isinstance(control, dict) else None
        if not isinstance(tap, dict):
            skipped.append({"controlId": control_id, "reason": "no tap gesture"})
            continue
        if tap.get("confirmation", "none") != "none":
            skipped.append({"controlId": control_id, "reason": "tap requires confirmation; static launcher omitted"})
            continue
        name = safe_name(control_id)
        for target_platform in platforms:
            if target_platform == "posix":
                destination = output / f"{name}.command"
                content = posix_launcher(args.python, ctl, config_path, control_id)
            else:
                destination = output / f"{name}.cmd"
                content = windows_launcher(args.python, ctl, config_path, control_id)
            if destination.exists() and not args.force:
                skipped.append({"controlId": control_id, "reason": f"exists: {destination.name}"})
                continue
            generated.append({"controlId": control_id, "path": str(destination), "platform": target_platform})
            if not args.dry_run:
                output.mkdir(parents=True, exist_ok=True)
                destination.write_text(content, encoding="utf-8", newline="")
                if target_platform == "posix":
                    destination.chmod(0o755)

    manifest = {"version": 1, "config": str(config_path), "generated": generated, "skipped": skipped}
    if not args.dry_run:
        output.mkdir(parents=True, exist_ok=True)
        (output / "launchers.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
