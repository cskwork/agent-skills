#!/usr/bin/env python3
"""Slot bookkeeping for agent sessions that already exist.

The daemon only accepts reports for sessions declared in `cockpit.json`, so a
session the user started by hand — a Claude Code tab in iTerm2, say — cannot
register itself. This module maps a volatile agent session id onto one of a
fixed set of predeclared slots and records enough evidence to focus the owning
terminal later.

Set `COCKPIT_HOME` to relocate the runtime directory; it defaults to
`~/.agent-cockpit`.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

STALE_AFTER_SECONDS = 6 * 3600
DEFAULT_SLOT_COUNT = 4
HERDR_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")


def cockpit_home() -> Path:
    return Path(os.path.expanduser(os.environ.get("COCKPIT_HOME", "~/.agent-cockpit")))


def claims_path() -> Path:
    return cockpit_home() / "claims.json"


def slot_ids(agent: str = "claude", count: int = DEFAULT_SLOT_COUNT) -> List[str]:
    return [f"session.{agent}.slot{n}" for n in range(1, count + 1)]


def load() -> Dict[str, Any]:
    try:
        data = json.loads(claims_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"slots": {}}
    if not isinstance(data, dict) or not isinstance(data.get("slots"), dict):
        return {"slots": {}}
    return data


def save(data: Dict[str, Any]) -> None:
    path = claims_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def herdr_context() -> Dict[str, str]:
    """Return the caller's Herdr identifiers only when they are trustworthy.

    Hooks inherit these variables from a Herdr-managed agent pane.  They are
    evidence for the claim, not a focus target: the focus adapter re-resolves
    the agent session through Herdr on every button press so pane moves remain
    safe.
    """
    if os.environ.get("HERDR_ENV") != "1":
        return {}
    values = {
        "herdrWorkspaceId": os.environ.get("HERDR_WORKSPACE_ID", "").strip(),
        "herdrTabId": os.environ.get("HERDR_TAB_ID", "").strip(),
        "herdrPaneId": os.environ.get("HERDR_PANE_ID", "").strip(),
    }
    if not all(HERDR_ID_RE.fullmatch(value) for value in values.values()):
        return {}
    return values


def release_missing_herdr_claims(
    data: Dict[str, Any],
    live_session_ids: set[str],
    *,
    agent: Optional[str] = None,
) -> List[str]:
    """Release only explicitly Herdr-backed claims no longer reported live.

    Legacy tty claims are intentionally left alone.  This prevents a Herdr
    hook from deleting a separate, ordinary iTerm session that happens to use
    the same agent type.
    """
    released: List[str] = []
    slots = data.get("slots", {})
    if not isinstance(slots, dict):
        return released
    for slot, claim in list(slots.items()):
        if not isinstance(claim, dict) or not claim.get("herdrPaneId"):
            continue
        if agent and claim.get("agent") != agent:
            continue
        if str(claim.get("agentSessionId") or "") not in live_session_ids:
            slots.pop(slot, None)
            released.append(slot)
    return released


def _pid_alive_windows(pid: int) -> bool:
    """Ask the Win32 API directly; Windows has no signal-0 equivalent.

    `OpenProcess` failing with ERROR_ACCESS_DENIED (5) still proves the process
    exists, so that case reports alive. A missing process reports
    ERROR_INVALID_PARAMETER (87) instead.
    """
    try:
        import ctypes
        from ctypes import wintypes

        query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel32.OpenProcess(query_limited_information, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5  # type: ignore[attr-defined]
        try:
            code = wintypes.DWORD()
            got = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return bool(got) and code.value == still_active
        finally:
            kernel32.CloseHandle(handle)
    except (ImportError, OSError, AttributeError):
        return False


def pid_alive(pid: Optional[int]) -> bool:
    if not pid:
        return False
    try:
        value = int(pid)
    except (TypeError, ValueError):
        return False
    if value <= 0:
        return False
    if os.name == "nt":
        return _pid_alive_windows(value)
    try:
        os.kill(value, 0)
    except (OSError, ValueError):
        return False
    return True


def claim_is_live(claim: Any) -> bool:
    if not isinstance(claim, dict):
        return False
    if time.time() - float(claim.get("updatedAt", 0)) > STALE_AFTER_SECONDS:
        return False
    return pid_alive(claim.get("pid"))


def _ps(pid: int) -> Optional[Tuple[int, str, str]]:
    """Return (ppid, comm, tty) for pid, or None when it is gone.

    POSIX only. Attaching to a running session depends on `ps` ancestry and a
    tty, neither of which Windows provides in this form, so callers get None
    rather than a subprocess that may block.
    """
    if os.name != "posix":
        return None
    try:
        result = subprocess.run(
            ["ps", "-o", "ppid=,comm=,tty=", "-p", str(pid)],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    line = result.stdout.strip()
    if result.returncode != 0 or not line:
        return None
    parts = line.split(None, 2)
    if len(parts) < 2:
        return None
    ppid = int(parts[0]) if parts[0].isdigit() else 0
    tty = parts[2].strip() if len(parts) > 2 else ""
    return ppid, parts[1], tty


def discover_owner() -> Dict[str, Any]:
    """Walk our own ancestry to find the owning terminal pane.

    POSIX only; on other platforms this returns just the current pid and no
    tty, which leaves `focus_terminal.py` reporting an honest failure.

    A hook runs as a descendant of the agent process, so the chain is reliable.
    Liveness is anchored on the `login` ancestor rather than the agent process:
    an agent CLI is often a launcher that execs `node`, so matching on the
    command name is not dependable, whereas `login` exits exactly when the
    terminal pane closes. The tty comes from the same ancestor because shell
    wrappers can allocate an inner pty that the terminal emulator never sees.
    """
    owner: Dict[str, Any] = {}
    pid = os.getpid()
    fallback_pid, fallback_tty = pid, ""
    for _ in range(24):
        info = _ps(pid)
        if not info:
            break
        ppid, comm, tty = info
        if tty and tty != "??":
            fallback_pid, fallback_tty = pid, tty
        if os.path.basename(comm) == "login" and "pid" not in owner:
            owner["pid"] = pid
            owner["tty"] = tty
        if ppid <= 1:
            break
        pid = ppid
    if "pid" not in owner:
        owner["pid"] = fallback_pid
        owner["tty"] = fallback_tty
    tty = str(owner.get("tty") or "")
    if tty and not tty.startswith("/dev/"):
        owner["tty"] = "/dev/" + tty
    return owner


def find_slot(data: Dict[str, Any], agent_session_id: str) -> Optional[str]:
    for slot, claim in data.get("slots", {}).items():
        if isinstance(claim, dict) and claim.get("agentSessionId") == agent_session_id:
            return slot
    return None


def acquire(
    data: Dict[str, Any],
    agent_session_id: str,
    agent: str = "claude",
    count: int = DEFAULT_SLOT_COUNT,
    live_herdr_session_ids: Optional[set[str]] = None,
) -> Optional[str]:
    """Return the slot for this session, claiming a free one when needed.

    Returns None when every slot is held by a live session. Callers must not
    evict an existing claim: a key that silently switches to another session is
    worse than a session that is simply not shown.
    """
    existing = find_slot(data, agent_session_id)
    if existing:
        return existing
    slots = data.setdefault("slots", {})
    for slot in slot_ids(agent, count):
        claim = slots.get(slot)
        if (
            live_herdr_session_ids is not None
            and isinstance(claim, dict)
            and claim.get("herdrPaneId")
            and str(claim.get("agentSessionId") or "") in live_herdr_session_ids
        ):
            continue
        if not claim_is_live(claim):
            return slot
    return None


def release(data: Dict[str, Any], agent_session_id: str) -> Optional[str]:
    slot = find_slot(data, agent_session_id)
    if slot:
        data.get("slots", {}).pop(slot, None)
    return slot
