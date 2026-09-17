#!/usr/bin/env python3
"""Hook-friendly wrapper for reporting semantic Agent Cockpit state."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cockpitctl import main as cockpitctl_main  # noqa: E402


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="~/.agent-cockpit/cockpit.json")
    parser.add_argument("--url")
    parser.add_argument("--token-file")
    parser.add_argument("--session", required=True)
    parser.add_argument("--state", required=True, choices=["idle", "running", "needs_attention", "blocked", "succeeded", "failed"])
    parser.add_argument("--label")
    parser.add_argument("--detail")
    parser.add_argument("--progress", type=float)
    parser.add_argument("--ttl", type=int)
    parser.add_argument("--source", default="reporter")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    forwarded = ["--config", args.config]
    if args.url:
        forwarded += ["--url", args.url]
    if args.token_file:
        forwarded += ["--token-file", args.token_file]
    forwarded += ["report", args.session, args.state, "--source", args.source]
    for option in ("label", "detail", "progress", "ttl"):
        value = getattr(args, option)
        if value is not None:
            forwarded += ["--" + option.replace("_", "-"), str(value)]
    return cockpitctl_main(forwarded)


if __name__ == "__main__":
    raise SystemExit(main())
