#!/usr/bin/env python3
"""Codex CLI hook bridge for an already-running iTerm2 agent session.

Codex and Claude Code expose the same session lifecycle fields to command
hooks. Reuse the tested slot/tty/reporting bridge while selecting the Codex
slot namespace, so one agent cannot occupy the other agent's key.
"""

from __future__ import annotations

import os
import sys

import claude_hook as bridge


def main() -> int:
    bridge.AGENT = "codex"
    bridge.SLOT_COUNT = int(
        os.environ.get("COCKPIT_CODEX_SLOT_COUNT", os.environ.get("COCKPIT_SLOT_COUNT", "4"))
    )
    return bridge.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        raise SystemExit(0)
