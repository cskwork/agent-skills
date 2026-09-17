#!/usr/bin/env python3
"""Focus the current Herdr pane holding a claimed agent session."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import herdr_agent  # noqa: E402
import slotclaims  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slot", required=True, help="Session id declared in cockpit.json")
    args = parser.parse_args()
    claim = slotclaims.load().get("slots", {}).get(args.slot)
    if not isinstance(claim, dict):
        print(f"slot not claimed: {args.slot}", file=sys.stderr)
        return 1
    try:
        agent = herdr_agent.focus(
            str(claim.get("agentSessionId") or ""),
            str(claim.get("agent") or "") or None,
        )
    except herdr_agent.HerdrError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(str(agent.get("pane_id") or ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
