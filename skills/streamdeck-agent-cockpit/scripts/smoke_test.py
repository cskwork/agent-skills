#!/usr/bin/env python3
"""End-to-end localhost smoke test for the standalone Agent Cockpit runtime."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

import cockpitd  # noqa: E402


def request(base: str, path: str, token: str | None = None, payload: dict | None = None) -> tuple[int, dict]:
    headers = {"Accept": "application/json"}
    data = None
    method = "GET"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        method = "POST"
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    req = Request(base + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=4) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        base_path = Path(tmp)
        marker = base_path / "invoked.txt"
        interrupt = base_path / "interrupt.txt"
        config = {
            "version": 3,
            "server": {
                "host": "127.0.0.1",
                "port": 0,
                "tokenFile": str(base_path / "token"),
                "stateFile": str(base_path / "state.json"),
                "commandTimeoutSeconds": 5,
            },
            "sessions": {
                "session.smoke.main": {
                    "label": "Smoke",
                    "agent": "test",
                    "adapter": {
                        "type": "command",
                        "probe": {"argv": [sys.executable, "-c", "import sys; sys.exit(1)"]},
                    },
                    "commands": {
                        "launch": {"argv": [sys.executable, "-c", "pass"]},
                        "focus": {"argv": [sys.executable, "-c", "pass"]},
                        "interrupt": {
                            "argv": [
                                sys.executable,
                                "-c",
                                f"from pathlib import Path; Path({str(interrupt)!r}).write_text('ok')",
                            ]
                        },
                    },
                    "progress": {"source": "reporter", "staleAfterSeconds": 30},
                }
            },
            "commands": {
                "workflow.smoke": {
                    "argv": [
                        sys.executable,
                        "-c",
                        f"from pathlib import Path; Path({str(marker)!r}).write_text('ok')",
                    ]
                }
            },
            "controls": {
                "workflow.smoke": {
                    "kind": "command",
                    "title": "Smoke",
                    "gestures": {"tap": {"operation": "run", "command": "workflow.smoke"}},
                },
                "session.smoke.main": {
                    "kind": "session",
                    "session": "session.smoke.main",
                    "title": "Smoke Session",
                    "gestures": {
                        "tap": {"operation": "focus_or_launch"},
                        "longPress": {"operation": "interrupt", "confirmation": "hold"},
                    },
                },
            },
        }
        token = "smoke-token-with-sufficient-length-123456"
        runtime = cockpitd.CockpitRuntime(config)
        server = cockpitd.create_server(runtime, "127.0.0.1", 0, token)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            status, body = request(url, "/v1/health")
            check(status == 200 and body.get("ok") is True, "health endpoint works without exposing control access")

            status, body = request(url, "/v1/controls")
            check(status == 401 and body.get("error", {}).get("code") == "unauthorized", "protected endpoints require token")

            status, body = request(url, "/v1/controls", token)
            check(status == 200 and len(body.get("controls", [])) == 2, "authenticated control listing works")

            control_path = quote("workflow.smoke", safe="")
            status, body = request(url, f"/v1/controls/{control_path}/invoke", token, {"gesture": "tap"})
            check(status == 200 and marker.read_text() == "ok", "named command invokes with shell-free configured argv")

            session_path = quote("session.smoke.main", safe="")
            status, body = request(url, f"/v1/controls/{session_path}/invoke", token, {"gesture": "longPress"})
            check(status == 409 and body.get("error", {}).get("code") == "confirmation_required", "destructive gesture rejects missing confirmation")

            status, body = request(url, f"/v1/controls/{session_path}/invoke", token, {"gesture": "longPress", "confirmed": True})
            check(status == 200 and interrupt.read_text() == "ok", "confirmed interrupt reaches only configured command")

            status, body = request(
                url,
                f"/v1/sessions/{session_path}/report",
                token,
                {"state": "running", "label": "Smoke work", "progress": 40, "ttl": 5},
            )
            check(status == 200, "semantic state report is accepted")

            status, body = request(url, f"/v1/sessions/{session_path}", token)
            state = body.get("session", {})
            check(status == 200 and state.get("semantic") is True and state.get("progress") == 40.0, "fresh report is returned with reported evidence")

            runtime.store.data["sessions"]["session.smoke.main"]["expiresAt"] = time.time() - 1
            status, body = request(url, f"/v1/sessions/{session_path}", token)
            state = body.get("session", {})
            check(status == 200 and state.get("semantic") is False and state.get("state") == "offline", "stale report falls back to coarse probe state")

            status, body = request(url, "/v1/controls/not-configured/invoke", token, {"gesture": "tap", "argv": ["echo", "unsafe"]})
            check(status == 404 and not (base_path / "unsafe").exists(), "unknown control and request-supplied argv cannot execute")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"SMOKE TEST FAILED: {exc}", file=sys.stderr)
        raise
