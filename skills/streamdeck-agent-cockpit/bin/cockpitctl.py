#!/usr/bin/env python3
"""CLI client for the standalone Stream Deck Agent Cockpit daemon."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def expand_local(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(value))


def load_config(path: str | Path) -> Dict[str, Any]:
    config_path = Path(expand_local(str(path)))
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Config not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON at {config_path}:{exc.lineno}:{exc.colno}: {exc.msg}") from exc
    if not isinstance(data, dict) or data.get("version") != 3:
        raise RuntimeError("Expected cockpit configuration version 3")
    return data


def read_token(path: str | Path) -> str:
    token_path = Path(expand_local(str(path)))
    try:
        token = token_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise RuntimeError(f"Token file not found; start cockpitd first: {token_path}") from exc
    if not token:
        raise RuntimeError(f"Token file is empty: {token_path}")
    return token


class Client:
    def __init__(self, base_url: str, token: Optional[str], timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = float(timeout)

    def request(self, method: str, path: str, payload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(dict(payload), ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except HTTPError as exc:
            raw = exc.read()
            try:
                data = json.loads(raw.decode("utf-8"))
                message = data.get("error", {}).get("message", str(exc))
                code = data.get("error", {}).get("code", "http_error")
            except Exception:
                message, code = str(exc), "http_error"
            raise RuntimeError(f"{code}: {message}") from exc
        except URLError as exc:
            raise RuntimeError(f"Daemon unavailable at {self.base_url}: {exc.reason}") from exc
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Daemon returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise RuntimeError("Daemon returned a non-object JSON response")
        return data


def build_client(args: argparse.Namespace, *, health_only: bool = False) -> Client:
    config = load_config(args.config)
    server = config.get("server", {})
    base_url = args.url or f"http://{server.get('host', '127.0.0.1')}:{server.get('port', 39393)}"
    token = None if health_only else read_token(args.token_file or server.get("tokenFile", "~/.agent-cockpit/token"))
    return Client(base_url, token, timeout=args.timeout)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="~/.agent-cockpit/cockpit.json")
    parser.add_argument("--url", help="Override daemon base URL")
    parser.add_argument("--token-file", help="Override token file")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--compact", action="store_true", help="Emit one-line JSON")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("health", help="Check unauthenticated daemon health")
    sub.add_parser("controls", help="List configured controls and current state")

    state = sub.add_parser("state", help="Read one control state")
    state.add_argument("control_id")

    session = sub.add_parser("session", help="Read one session state")
    session.add_argument("session_id")

    invoke = sub.add_parser("invoke", help="Invoke one configured control gesture")
    invoke.add_argument("control_id")
    invoke.add_argument("--gesture", default="tap", choices=["tap", "longPress", "dialPress", "dialLeft", "dialRight"])
    invoke.add_argument("--confirm", action="store_true")
    invoke.add_argument("--value", type=int, default=0)

    report = sub.add_parser("report", help="Report evidence-backed semantic session state")
    report.add_argument("session_id")
    report.add_argument("state", choices=["idle", "running", "needs_attention", "blocked", "succeeded", "failed"])
    report.add_argument("--label")
    report.add_argument("--detail")
    report.add_argument("--progress", type=float)
    report.add_argument("--ttl", type=int)
    report.add_argument("--source", default="reporter")

    clear = sub.add_parser("clear", help="Clear one cached semantic session report")
    clear.add_argument("session_id")

    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "health":
            data = build_client(args, health_only=True).request("GET", "/v1/health")
        elif args.command == "controls":
            data = build_client(args).request("GET", "/v1/controls")
        elif args.command == "state":
            data = build_client(args).request("GET", f"/v1/controls/{quote(args.control_id, safe='')}")
        elif args.command == "session":
            data = build_client(args).request("GET", f"/v1/sessions/{quote(args.session_id, safe='')}")
        elif args.command == "invoke":
            payload = {"gesture": args.gesture, "confirmed": args.confirm, "value": args.value}
            data = build_client(args).request(
                "POST", f"/v1/controls/{quote(args.control_id, safe='')}/invoke", payload
            )
        elif args.command == "report":
            payload: Dict[str, Any] = {"state": args.state, "source": args.source}
            for key in ("label", "detail", "progress", "ttl"):
                value = getattr(args, key)
                if value is not None:
                    payload[key] = value
            data = build_client(args).request(
                "POST", f"/v1/sessions/{quote(args.session_id, safe='')}/report", payload
            )
        elif args.command == "clear":
            data = build_client(args).request(
                "DELETE", f"/v1/sessions/{quote(args.session_id, safe='')}" + "/report"
            )
        else:
            raise RuntimeError(f"Unsupported command: {args.command}")
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.compact:
        print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
