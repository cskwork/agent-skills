#!/usr/bin/env python3
"""Coarse probe for a slot holding an already-running agent session.

Exit 0 (`present`) only when the slot is claimed and the owning terminal pane
is still alive. Anything else exits 1 (`offline`). This is existence evidence
only: it says nothing about whether the agent is working, waiting, or blocked.
Semantic state must arrive from a hook report.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import slotclaims  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slot", required=True, help="Session id declared in cockpit.json")
    args = parser.parse_args()

    claim = slotclaims.load().get("slots", {}).get(args.slot)
    return 0 if slotclaims.claim_is_live(claim) else 1


if __name__ == "__main__":
    raise SystemExit(main())
