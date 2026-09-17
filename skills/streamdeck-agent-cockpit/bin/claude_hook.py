#!/usr/bin/env python3
"""Claude Code hook bridge: report an already-running session to cockpitd.

Reads a hook payload on stdin, claims a cockpit slot for the Claude Code
session, and reports an evidence-backed semantic state. State comes only from
hook events; terminal titles are never scraped.

Register with `install_claude_hooks.py`. Other agents need their own bridge —
the slot and focus machinery is agent-neutral, only this event mapping is not.

This script never fails loudly. A broken cockpit must not disturb the agent
session that is hosting it.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

import slotclaims  # noqa: E402
import herdr_agent  # noqa: E402

AGENT = "claude"
SLOT_COUNT = int(os.environ.get("COCKPIT_SLOT_COUNT", "4"))

# hook_event_name -> (state, detail, ttl seconds)
#
# Every event below was confirmed against the installed Claude Code build,
# either in the hook reference it ships or by its hook dispatcher symbol.
# Do not add an event on the strength of a remembered name; check first.
#
# A Stop event means the turn ended, not that the user's task succeeded, so it
# reports idle rather than a success state.
EVENT_MAP = {
    "SessionStart": ("idle", "session started", 7200),
    "UserPromptSubmit": ("running", "working", 1800),
    "PreToolUse": ("running", "running a tool", 1800),
    "PostToolUse": ("running", "working", 1800),
    "PostToolUseFailure": ("running", "handling a tool failure", 1800),
    "PermissionRequest": ("needs_attention", "approval required", 3600),
    "PermissionDenied": ("blocked", "permission denied", 3600),
    "Elicitation": ("needs_attention", "input requested", 3600),
    "ElicitationResult": ("running", "input received", 1800),
    "SubagentStart": ("running", "subagent running", 1800),
    "SubagentStop": ("running", "working", 1800),
    "TaskCreated": ("running", "task created", 1800),
    "TaskCompleted": ("running", "working", 1800),
    "PreCompact": ("running", "compacting context", 1800),
    "PostCompact": ("running", "working", 1800),
    "Stop": ("idle", "response complete", 7200),
    "StopFailure": ("failed", "turn stopped with an error", 3600),
}

# Notification hooks carry a documented `notification_type`. Match it exactly
# when present.
NOTIFICATION_TYPES = {
    "permission_prompt": ("needs_attention", "approval required", 3600),
    "idle_prompt": ("needs_attention", "waiting for input", 3600),
    "agent_needs_input": ("needs_attention", "input requested", 3600),
    "elicitation_dialog": ("needs_attention", "input requested", 3600),
    "elicitation_complete": ("running", "input received", 1800),
    "agent_completed": ("idle", "response complete", 7200),
}

# Fallback for payloads that carry only a human-readable message.
# Substring of the Notification message -> (state, detail, ttl seconds)
NOTIFICATION_MAP = (
    ("permission", ("needs_attention", "approval required", 3600)),
    ("idle", ("needs_attention", "waiting for input", 3600)),
    ("elicit", ("needs_attention", "input requested", 3600)),
    ("waiting", ("needs_attention", "waiting", 3600)),
)


def config_path() -> str:
    return str(slotclaims.cockpit_home() / "cockpit.json")


def project_label(cwd: str) -> str:
    return (os.path.basename(cwd.rstrip("/")) or cwd or AGENT)[:40]


def resolve(event: str, payload: Dict[str, Any]) -> Optional[Tuple[str, str, int]]:
    if event in EVENT_MAP:
        return EVENT_MAP[event]
    if event == "Notification":
        kind = str(payload.get("notification_type") or payload.get("notificationType") or "").lower()
        if kind in NOTIFICATION_TYPES:
            return NOTIFICATION_TYPES[kind]
        message = str(payload.get("message") or "").lower()
        for needle, result in NOTIFICATION_MAP:
            if needle in message:
                return result
        return ("needs_attention", "notification", 3600)
    return None


def post_report(slot: str, state: str, label: str, detail: str, ttl: int) -> None:
    from cockpitctl import Client, load_config, read_token  # noqa: E402

    config = load_config(config_path())
    server = config.get("server", {})
    client = Client(
        f"http://{server.get('host', '127.0.0.1')}:{int(server.get('port', 39393))}",
        read_token(server.get("tokenFile", "~/.agent-cockpit/token")),
        timeout=5.0,
    )
    client.request(
        "POST",
        f"/v1/sessions/{slot}/report",
        {
            "state": state,
            "label": label[:120],
            "detail": detail[:500],
            "ttl": ttl,
            "source": f"{AGENT}-hook",
        },
    )


def clear_report(slot: str) -> None:
    from cockpitctl import Client, load_config, read_token  # noqa: E402

    config = load_config(config_path())
    server = config.get("server", {})
    client = Client(
        f"http://{server.get('host', '127.0.0.1')}:{int(server.get('port', 39393))}",
        read_token(server.get("tokenFile", "~/.agent-cockpit/token")),
        timeout=5.0,
    )
    from urllib.parse import quote

    client.request("DELETE", f"/v1/sessions/{quote(slot, safe='')}/report")


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, OSError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0

    session_id = str(payload.get("session_id") or "")
    if not session_id:
        return 0
    event = str(payload.get("hook_event_name") or "")
    cwd = str(payload.get("cwd") or "")

    data = slotclaims.load()

    if event == "SessionEnd":
        released = slotclaims.release(data, session_id)
        if released:
            slotclaims.save(data)
            try:
                clear_report(released)
            except Exception:
                pass
        return 0

    resolved = resolve(event, payload)
    if resolved is None:
        return 0
    state, detail, ttl = resolved

    herdr = slotclaims.herdr_context()
    live_herdr_session_ids = None
    released_herdr_slots: list[str] = []
    if herdr:
        try:
            live_ids = {
                session_id
                for agent_info in herdr_agent.live_agents()
                if agent_info.get("agent") == AGENT
                for session_id in [herdr_agent.agent_session_id(agent_info)]
                if session_id
            }
            released_herdr_slots = slotclaims.release_missing_herdr_claims(
                data, live_ids, agent=AGENT
            )
            live_herdr_session_ids = live_ids
        except herdr_agent.HerdrError:
            # A status bridge must never disturb the agent if Herdr is briefly
            # unavailable; the existing claim will be retried on its next hook.
            pass

    slot = slotclaims.acquire(
        data,
        session_id,
        AGENT,
        SLOT_COUNT,
        live_herdr_session_ids=live_herdr_session_ids,
    )
    if slot is None:
        return 0  # every slot is busy; stay silent rather than evict a session

    owner = slotclaims.discover_owner()
    data.setdefault("slots", {})[slot] = {
        "agentSessionId": session_id,
        "agent": AGENT,
        "cwd": cwd,
        "project": project_label(cwd),
        "pid": owner.get("pid"),
        "tty": owner.get("tty"),
        "updatedAt": time.time(),
        **herdr,
    }
    slotclaims.save(data)

    for released_slot in released_herdr_slots:
        try:
            clear_report(released_slot)
        except Exception:
            pass

    try:
        post_report(slot, state, project_label(cwd), detail, ttl)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        raise SystemExit(0)
