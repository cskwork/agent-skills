#!/usr/bin/env python3
"""Privacy-conscious local capability probe for Agent Cockpit."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

COMMANDS = ["tmux", "node", "npm", "streamdeck", "claude", "codex", "pi", "jcode", "wezterm", "osascript", "wt.exe"]


def command_info(name: str, include_version: bool) -> Dict[str, Any]:
    path = shutil.which(name)
    result: Dict[str, Any] = {"available": bool(path)}
    if path:
        result["path"] = path
    if path and include_version:
        for args in ([path, "--version"], [path, "-v"]):
            try:
                completed = subprocess.run(
                    args,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=3,
                    check=False,
                    shell=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            line = (completed.stdout or "").strip().splitlines()
            if line:
                result["version"] = line[0][:200]
                break
    return result


def streamdeck_candidates() -> list[str]:
    home = Path.home()
    system = platform.system().lower()
    candidates: list[Path] = []
    if system == "darwin":
        candidates += [
            Path("/Applications/Elgato Stream Deck.app"),
            Path("/Applications/Stream Deck.app"),
            home / "Applications/Elgato Stream Deck.app",
            home / "Applications/Stream Deck.app",
        ]
    elif system == "windows":
        for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
            base = os.environ.get(env_name)
            if base:
                candidates += [Path(base) / "Elgato/StreamDeck/StreamDeck.exe"]
    return [str(path) for path in candidates if path.exists()]


def plugin_directories() -> list[str]:
    home = Path.home()
    system = platform.system().lower()
    candidates: list[Path] = []
    if system == "darwin":
        candidates.append(home / "Library/Application Support/com.elgato.StreamDeck/Plugins")
    elif system == "windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(Path(appdata) / "Elgato/StreamDeck/Plugins")
    return [str(path) for path in candidates if path.exists()]


def collect(include_versions: bool = False) -> Dict[str, Any]:
    return {
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
        },
        "streamDeckApplications": streamdeck_candidates(),
        "streamDeckPluginDirectories": plugin_directories(),
        "commands": {name: command_info(name, include_versions) for name in COMMANDS},
        "notes": [
            "No network request was made.",
            "No terminal output, agent history, environment-variable values, or credentials were read.",
            "Command paths indicate availability only; verify agent flags with the installed --help output before configuring them.",
        ],
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--versions", action="store_true", help="Run bounded local --version probes")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    data = collect(args.versions)
    if args.json_output:
        print(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(f"OS: {data['os']['system']} {data['os']['release']} ({data['os']['machine']})")
        print(f"Python: {data['python']['version']}")
        print("Stream Deck app: " + (", ".join(data["streamDeckApplications"]) or "not detected"))
        for name, info in data["commands"].items():
            suffix = f" — {info.get('version')}" if info.get("version") else ""
            print(f"{name}: {'yes' if info['available'] else 'no'}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
