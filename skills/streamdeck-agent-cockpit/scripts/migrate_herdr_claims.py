#!/usr/bin/env python3
"""Adopt active Herdr agents into existing cockpit claims.

Run this from a Herdr-managed pane after installing the Herdr adapter.  It
records Herdr ids for matching live agent-session ids.  ``--drop-unmatched``
is intentionally opt-in because it removes stale claims of the selected agent.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

import herdr_agent  # noqa: E402
import slotclaims  # noqa: E402


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=["claude", "codex"], required=True)
    parser.add_argument("--drop-unmatched", action="store_true")
    parser.add_argument("--claim-unclaimed", action="store_true", help="Claim live selected-agent sessions not yet on the deck")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def context(agent: Dict[str, Any]) -> Dict[str, str]:
    keys = {
        "herdrWorkspaceId": "workspace_id",
        "herdrTabId": "tab_id",
        "herdrPaneId": "pane_id",
    }
    values = {target: str(agent.get(source) or "") for target, source in keys.items()}
    if not all(values.values()):
        raise ValueError("live Herdr agent has incomplete location metadata")
    return values


def migrate(
    data: Dict[str, Any],
    agent_name: str,
    agents: list[Dict[str, Any]],
    drop_unmatched: bool,
    claim_unclaimed: bool = False,
) -> Dict[str, list[str]]:
    live = {
        session_id: agent
        for agent in agents
        if agent.get("agent") == agent_name
        for session_id in [herdr_agent.agent_session_id(agent)]
        if session_id
    }
    slots = data.get("slots", {})
    if not isinstance(slots, dict):
        raise ValueError("claims has no slots object")
    adopted: list[str] = []
    dropped: list[str] = []
    claimed: list[str] = []
    for slot, claim in list(slots.items()):
        if not isinstance(claim, dict) or claim.get("agent") != agent_name:
            continue
        live_agent = live.get(str(claim.get("agentSessionId") or ""))
        if live_agent:
            claim.update(context(live_agent))
            adopted.append(slot)
        elif drop_unmatched:
            slots.pop(slot, None)
            dropped.append(slot)
    if claim_unclaimed:
        claimed_session_ids = {
            str(claim.get("agentSessionId") or "")
            for claim in slots.values()
            if isinstance(claim, dict) and claim.get("agent") == agent_name
        }
        for session_id, live_agent in live.items():
            if session_id in claimed_session_ids:
                continue
            slot = slotclaims.acquire(
                data,
                session_id,
                agent_name,
                live_herdr_session_ids=set(live),
            )
            if slot is None:
                continue
            cwd = str(live_agent.get("cwd") or "")
            slots[slot] = {
                "agentSessionId": session_id,
                "agent": agent_name,
                "cwd": cwd,
                "project": os.path.basename(cwd.rstrip("/")) or agent_name,
                "pid": None,
                "tty": "",
                "updatedAt": time.time(),
                **context(live_agent),
            }
            claimed_session_ids.add(session_id)
            claimed.append(slot)
    return {"adopted": adopted, "claimed": claimed, "dropped": dropped}


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if os.environ.get("HERDR_ENV") != "1":
        print("error: run from a Herdr-managed pane (HERDR_ENV=1)", file=sys.stderr)
        return 2
    try:
        data = slotclaims.load()
        result = migrate(
            data,
            args.agent,
            herdr_agent.live_agents(),
            args.drop_unmatched,
            args.claim_unclaimed,
        )
    except (ValueError, herdr_agent.HerdrError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not args.apply:
        print(json.dumps({"ok": True, "dryRun": True, **result}, indent=2))
        return 0

    path = slotclaims.claims_path()
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = path.with_name(f"{path.name}.backup-{stamp}")
    had_claims = path.exists()
    try:
        if had_claims:
            shutil.copy2(path, backup)
        slotclaims.save(data)
    except OSError as exc:
        print(f"error: failed to write claims: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result, "backup": str(backup) if had_claims else None}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
