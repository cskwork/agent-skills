from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

import cockpitd  # noqa: E402


class RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.command_marker = base / "command.txt"
        self.interrupt_marker = base / "interrupt.txt"
        self.config = {
            "version": 3,
            "server": {
                "host": "127.0.0.1",
                "port": 39393,
                "tokenFile": str(base / "token"),
                "stateFile": str(base / "state.json"),
                "commandTimeoutSeconds": 5,
            },
            "sessions": {
                "session.test.main": {
                    "label": "Test",
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
                                f"from pathlib import Path; Path({str(self.interrupt_marker)!r}).write_text('ok')",
                            ]
                        },
                    },
                    "progress": {"source": "reporter", "staleAfterSeconds": 30},
                }
            },
            "commands": {
                "workflow.test": {
                    "argv": [
                        sys.executable,
                        "-c",
                        f"from pathlib import Path; Path({str(self.command_marker)!r}).write_text('ok')",
                    ]
                }
            },
            "controls": {
                "workflow.test": {
                    "kind": "command",
                    "title": "Test",
                    "gestures": {"tap": {"operation": "run", "command": "workflow.test"}},
                },
                "session.test.main": {
                    "kind": "session",
                    "session": "session.test.main",
                    "title": "Session",
                    "gestures": {
                        "tap": {"operation": "focus_or_launch"},
                        "longPress": {"operation": "interrupt", "confirmation": "hold"},
                    },
                },
            },
            "appearance": {
                "states": {
                    "running": {"titleSuffix": "RUN"},
                    "offline": {"titleSuffix": "OFF"},
                }
            },
        }
        self.runtime = cockpitd.CockpitRuntime(self.config)

    def test_named_command_executes_without_raw_request_command(self) -> None:
        result = self.runtime.invoke("workflow.test", "tap")
        self.assertTrue(result["ok"])
        self.assertEqual(self.command_marker.read_text(), "ok")

    def test_confirmation_is_required_for_interrupt(self) -> None:
        with self.assertRaises(cockpitd.CockpitError) as caught:
            self.runtime.invoke("session.test.main", "longPress")
        self.assertEqual(caught.exception.code, "confirmation_required")
        self.runtime.invoke("session.test.main", "longPress", confirmed=True)
        self.assertEqual(self.interrupt_marker.read_text(), "ok")

    def test_reported_state_expires_to_coarse(self) -> None:
        self.runtime.report("session.test.main", {"state": "running", "ttl": 5, "progress": 25})
        fresh = self.runtime.session_state("session.test.main")
        self.assertTrue(fresh["semantic"])
        self.assertEqual(fresh["state"], "running")
        self.assertEqual(fresh["progress"], 25.0)
        self.runtime.store.data["sessions"]["session.test.main"]["expiresAt"] = time.time() - 1
        stale = self.runtime.session_state("session.test.main")
        self.assertFalse(stale["semantic"])
        self.assertEqual(stale["state"], "offline")
        self.assertTrue(stale["lastReportStale"])

    def test_clear_report_removes_cached_semantic_state(self) -> None:
        self.runtime.report("session.test.main", {"state": "running", "ttl": 5})
        self.assertTrue(self.runtime.clear_report("session.test.main")["cleared"])
        state = self.runtime.session_state("session.test.main")
        self.assertFalse(state["semantic"])

    def test_control_state_publishes_configured_short_status(self) -> None:
        self.runtime.report("session.test.main", {"state": "running", "ttl": 5})
        fresh = self.runtime.control_state("session.test.main")
        self.assertEqual(fresh["display"], {"titleSuffix": "RUN"})
        self.runtime.store.data["sessions"]["session.test.main"]["expiresAt"] = time.time() - 1
        stale = self.runtime.control_state("session.test.main")
        self.assertEqual(stale["display"], {"titleSuffix": "OFF"})

    def test_shell_command_string_is_rejected_by_runtime(self) -> None:
        runner = cockpitd.CommandRunner()
        with self.assertRaises(cockpitd.CockpitError) as caught:
            runner.run({"argv": ["bash", "-c", "echo unsafe"]})
        self.assertEqual(caught.exception.code, "shell_command_rejected")

    def test_destructive_named_workflow_requires_confirmation_defense_in_depth(self) -> None:
        marker = Path(self.temp.name) / "deploy.txt"
        self.runtime.commands["workflow.deploy.production"] = {
            "argv": [
                sys.executable,
                "-c",
                f"from pathlib import Path; Path({str(marker)!r}).write_text('ok')",
            ]
        }
        self.runtime.controls["workflow.deploy.production"] = {
            "kind": "command",
            "title": "Deploy",
            "gestures": {
                "tap": {
                    "operation": "run",
                    "command": "workflow.deploy.production",
                    "confirmation": "none",
                }
            },
        }
        with self.assertRaises(cockpitd.CockpitError) as caught:
            self.runtime.invoke("workflow.deploy.production", "tap")
        self.assertEqual(caught.exception.code, "confirmation_required")
        self.runtime.invoke("workflow.deploy.production", "tap", confirmed=True)
        self.assertEqual(marker.read_text(), "ok")

    def test_http_auth_and_unknown_control(self) -> None:
        token = "test-token-with-sufficient-length-123456"
        server = cockpitd.create_server(self.runtime, "127.0.0.1", 0, token)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_address[1]}"

        with urlopen(base + "/v1/health", timeout=3) as response:
            self.assertEqual(response.status, 200)

        with self.assertRaises(HTTPError) as unauthorized:
            urlopen(base + "/v1/controls", timeout=3)
        self.assertEqual(unauthorized.exception.code, 401)

        request = Request(base + "/v1/controls/missing", headers={"Authorization": f"Bearer {token}"})
        with self.assertRaises(HTTPError) as missing:
            urlopen(request, timeout=3)
        self.assertEqual(missing.exception.code, 404)

        self.runtime.report("session.test.main", {"state": "running", "ttl": 5})
        clear = Request(
            base + "/v1/sessions/session.test.main/report",
            headers={"Authorization": f"Bearer {token}"},
            method="DELETE",
        )
        with urlopen(clear, timeout=3) as response:
            self.assertEqual(response.status, 200)
        self.assertFalse(self.runtime.session_state("session.test.main")["semantic"])


if __name__ == "__main__":
    unittest.main()
