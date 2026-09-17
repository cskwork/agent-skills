#!/usr/bin/env python3
"""Focus the terminal pane that owns a claimed slot.

On macOS this matches the tty recorded when the slot was claimed, because agent
session ids are invisible to the terminal emulator. iTerm2 and Apple Terminal
both expose a documented `tty` property through AppleScript.

Windows Terminal exposes no tty, so it is addressed by exact tab title instead:
pass `--tab-title` and the bundled UI Automation script selects that tab. Since
the title is supplied rather than discovered, that path does not consult slot
bookkeeping and works whether or not a claim exists.

Exits non-zero when the slot is unclaimed or the pane is gone, so a key reports
an honest failure instead of a false success.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import slotclaims  # noqa: E402

ITERM2_BUNDLE_ID = "com.googlecode.iterm2"

ITERM2 = f'''
on run argv
  set wantedTty to item 1 of argv
  tell application id "{ITERM2_BUNDLE_ID}"
    repeat with w in windows
      repeat with t in tabs of w
        repeat with s in sessions of t
          if (tty of s) is wantedTty then
            select w
            select t
            select s
            activate
            return "ok"
          end if
        end repeat
      end repeat
    end repeat
  end tell
  return "not_found"
end run
'''

APPLE_TERMINAL = '''
on run argv
  set wantedTty to item 1 of argv
  tell application "Terminal"
    repeat with w in windows
      repeat with t in tabs of w
        if (tty of t) is wantedTty then
          set selected tab of w to t
          set index of w to 1
          activate
          return "ok"
        end if
      end repeat
    end repeat
  end tell
  return "not_found"
end run
'''

APPS = (("iTerm2", ITERM2), ("Terminal", APPLE_TERMINAL))

WINDOWS_TERMINAL_SCRIPT = Path(__file__).resolve().parent / "windows_terminal_uia.ps1"


def focus_windows_terminal(tab_title: str) -> Optional[str]:
    """Select a Windows Terminal tab by exact title. Returns a problem or None.

    Windows Terminal has no scriptable tty, so the tab title is the only stable
    handle an external process can address. The script matches case-sensitively
    and exits non-zero when nothing matches, so a wrong title fails loudly.
    """
    if not WINDOWS_TERMINAL_SCRIPT.exists():
        return f"missing helper script: {WINDOWS_TERMINAL_SCRIPT}"
    executable = "powershell.exe" if os.name == "nt" else "pwsh"
    try:
        result = subprocess.run(
            [executable, "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(WINDOWS_TERMINAL_SCRIPT), "-TabTitle", tab_title],
            capture_output=True, text=True, timeout=20,
        )
    except FileNotFoundError:
        return f"{executable} not found"
    except (OSError, subprocess.SubprocessError) as exc:
        return f"{executable} failed: {exc}"
    if result.returncode != 0:
        return result.stderr.strip() or f"exit {result.returncode}"
    return None if result.stdout.strip() == "focused" else "not_found"


def is_running(app: str) -> bool:
    target = (
        f'application id "{ITERM2_BUNDLE_ID}" is running'
        if app == "iTerm2"
        else f'application "{app}" is running'
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", target],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.stdout.strip() == "true"


def try_focus(script: str, tty: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["osascript", "-", tty],
            input=script, capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"osascript failed: {exc}"
    if result.returncode != 0:
        return result.stderr.strip() or "osascript returned an error"
    return None if result.stdout.strip() == "ok" else "not_found"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slot", help="Session id declared in cockpit.json")
    parser.add_argument("--app", choices=[name for name, _ in APPS],
                        help="Restrict to one terminal application (macOS)")
    parser.add_argument("--tab-title",
                        help="Exact Windows Terminal tab title to select instead of a tty")
    args = parser.parse_args()

    if args.tab_title:
        problem = focus_windows_terminal(args.tab_title)
        if problem is None:
            return 0
        print(f"Windows Terminal: {problem}", file=sys.stderr)
        return 1

    if not args.slot:
        print("either --slot or --tab-title is required", file=sys.stderr)
        return 1

    claim = slotclaims.load().get("slots", {}).get(args.slot)
    if not slotclaims.claim_is_live(claim):
        print(f"slot not claimed: {args.slot}", file=sys.stderr)
        return 1
    tty = str((claim or {}).get("tty") or "")
    if not tty:
        print(f"no terminal recorded for {args.slot}", file=sys.stderr)
        return 1

    candidates = [(n, s) for n, s in APPS if args.app in (None, n)]
    problems = []
    for name, script in candidates:
        if not is_running(name):
            continue
        problem = try_focus(script, tty)
        if problem is None:
            return 0
        problems.append(f"{name}: {problem}")

    print(f"no terminal session with tty {tty}" if not problems else "; ".join(problems),
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
