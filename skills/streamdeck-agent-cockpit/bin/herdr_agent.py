#!/usr/bin/env python3
"""Resolve a live Herdr agent session and focus its current pane safely.

The cockpit records an agent-session id in a local claim.  Herdr owns the
mutable pane topology, so this module resolves that id through ``herdr agent
list`` on every operation instead of trusting a previously stored pane id.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

HERDR_BIN_ENV = "AGENT_COCKPIT_HERDR_BIN"
DEFAULT_TIMEOUT_SECONDS = 12


class HerdrError(RuntimeError):
    """A local Herdr adapter failure that should make a cockpit action fail."""


def executable() -> str:
    configured = os.environ.get(HERDR_BIN_ENV, "").strip()
    if configured:
        path = Path(configured).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
        raise HerdrError(f"configured Herdr executable is unavailable: {path}")
    found = shutil.which("herdr")
    if found:
        return found
    raise HerdrError("herdr executable is unavailable")


def _run(arguments: List[str], *, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [executable(), *arguments],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise HerdrError("herdr executable is unavailable") from exc
    except subprocess.TimeoutExpired as exc:
        raise HerdrError("herdr command timed out") from exc
    except OSError as exc:
        raise HerdrError(f"herdr command could not start: {exc.__class__.__name__}") from exc


def live_agents() -> List[Dict[str, Any]]:
    result = _run(["agent", "list"])
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit {result.returncode}"
        raise HerdrError(f"herdr agent list failed: {detail[:240]}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise HerdrError("herdr agent list returned invalid JSON") from exc
    agents = ((payload.get("result") or {}).get("agents")) if isinstance(payload, Mapping) else None
    if not isinstance(agents, list):
        raise HerdrError("herdr agent list returned no agents")
    return [agent for agent in agents if isinstance(agent, dict)]


def agent_session_id(agent: Mapping[str, Any]) -> Optional[str]:
    session = agent.get("agent_session")
    value = session.get("value") if isinstance(session, Mapping) else None
    return value if isinstance(value, str) and value else None


def resolve(session_id: str, expected_agent: Optional[str] = None) -> Dict[str, Any]:
    if not session_id:
        raise HerdrError("claim has no agent session id")
    for agent in live_agents():
        if agent_session_id(agent) != session_id:
            continue
        kind = agent.get("agent")
        pane_id = agent.get("pane_id")
        if expected_agent and kind != expected_agent:
            raise HerdrError("claim agent type does not match live Herdr agent")
        if not isinstance(pane_id, str) or not pane_id:
            raise HerdrError("live Herdr agent has no pane id")
        return agent
    raise HerdrError("claimed agent session is no longer live in Herdr")


def focus(session_id: str, expected_agent: Optional[str] = None) -> Dict[str, Any]:
    agent = resolve(session_id, expected_agent)
    pane_id = str(agent["pane_id"])
    result = _run(["agent", "focus", pane_id])
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit {result.returncode}"
        raise HerdrError(f"herdr agent focus failed: {detail[:240]}")
    return agent
