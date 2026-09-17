#!/usr/bin/env python3
"""Open/focus a terminal attached to one validated tmux session.

This helper never accepts arbitrary terminal commands. The session name is
strictly validated before it is embedded in platform automation.
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

SESSION_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")


def available(name: str) -> bool:
    return shutil.which(name) is not None


def ensure_session(session: str) -> None:
    if not SESSION_RE.fullmatch(session):
        raise RuntimeError("Session name contains unsupported characters")
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
            check=False,
            shell=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("tmux is not installed") from exc
    if result.returncode != 0:
        raise RuntimeError(f"tmux session does not exist: {session}")


def select_terminal(requested: str) -> str:
    if requested != "auto":
        return requested
    if os.environ.get("TMUX"):
        return "tmux-client"
    system = platform.system().lower()
    if system == "darwin":
        if available("wezterm"):
            return "wezterm"
        return "terminal"
    if system == "windows":
        return "windows-terminal"
    for candidate, executable in (
        ("wezterm", "wezterm"),
        ("kitty", "kitty"),
        ("gnome-terminal", "gnome-terminal"),
        ("konsole", "konsole"),
    ):
        if available(executable):
            return candidate
    raise RuntimeError("No supported terminal was detected; configure an explicit focus command")


def command_for(terminal: str, session: str) -> list[str]:
    attach = ["tmux", "attach-session", "-t", session]
    if terminal == "tmux-client":
        return ["tmux", "switch-client", "-t", session]
    if terminal == "wezterm":
        return ["wezterm", "start", "--", *attach]
    if terminal == "kitty":
        return ["kitty", *attach]
    if terminal == "gnome-terminal":
        return ["gnome-terminal", "--", *attach]
    if terminal == "konsole":
        return ["konsole", "-e", *attach]
    if terminal == "windows-terminal":
        return ["wt.exe", "wsl.exe", *attach]
    if terminal == "terminal":
        script = (
            'tell application "Terminal"\n'
            'activate\n'
            f'do script "exec tmux attach-session -t {session}"\n'
            'end tell'
        )
        return ["osascript", "-e", script]
    if terminal == "iterm":
        script = (
            'tell application id "com.googlecode.iterm2"\n'
            'activate\n'
            'tell current window\n'
            'create tab with default profile\n'
            f'tell current session to write text "exec tmux attach-session -t {session}"\n'
            'end tell\n'
            'end tell'
        )
        return ["osascript", "-e", script]
    raise RuntimeError(f"Unsupported terminal: {terminal}")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True)
    parser.add_argument(
        "--terminal",
        default="auto",
        choices=["auto", "tmux-client", "terminal", "iterm", "wezterm", "kitty", "gnome-terminal", "konsole", "windows-terminal"],
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        if not SESSION_RE.fullmatch(args.session):
            raise RuntimeError("Session name contains unsupported characters")
        terminal = select_terminal(args.terminal)
        command = command_for(terminal, args.session)
        if args.dry_run:
            print(" ".join(command))
            return 0
        ensure_session(args.session)
        if terminal == "tmux-client":
            completed = subprocess.run(command, check=False, shell=False)
            return completed.returncode
        subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            shell=False,
        )
        return 0
    except (RuntimeError, FileNotFoundError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
