"""Tests for safe Herdr agent-session resolution used by Stream Deck slots."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))
sys.path.insert(0, str(ROOT / "scripts"))

import configure_herdr_sessions  # noqa: E402
import herdr_agent  # noqa: E402
import migrate_herdr_claims  # noqa: E402
import slotclaims  # noqa: E402


class HerdrAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self._home = tempfile.TemporaryDirectory()
        self._old_home = os.environ.get("COCKPIT_HOME")
        self._old_herdr = os.environ.get("HERDR_ENV")
        self._old_workspace = os.environ.get("HERDR_WORKSPACE_ID")
        self._old_tab = os.environ.get("HERDR_TAB_ID")
        self._old_pane = os.environ.get("HERDR_PANE_ID")
        os.environ["COCKPIT_HOME"] = self._home.name

    def tearDown(self) -> None:
        for name, value in {
            "COCKPIT_HOME": self._old_home,
            "HERDR_ENV": self._old_herdr,
            "HERDR_WORKSPACE_ID": self._old_workspace,
            "HERDR_TAB_ID": self._old_tab,
            "HERDR_PANE_ID": self._old_pane,
        }.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self._home.cleanup()

    @staticmethod
    def agents_payload() -> str:
        return '{"result":{"agents":[{"agent":"claude","agent_session":{"value":"claude-a"},"pane_id":"w1:p9","tab_id":"w1:t3","workspace_id":"w1"},{"agent":"codex","agent_session":{"value":"codex-a"},"pane_id":"w1:p10","tab_id":"w1:t4","workspace_id":"w1"}]}}'

    def with_fake_herdr(self):
        calls: list[list[str]] = []

        def fake_run(arguments, **_kwargs):
            calls.append(arguments)
            if arguments == ["agent", "list"]:
                return subprocess.CompletedProcess(arguments, 0, self.agents_payload(), "")
            if arguments == ["agent", "focus", "w1:p9"]:
                return subprocess.CompletedProcess(arguments, 0, "{}", "")
            return subprocess.CompletedProcess(arguments, 1, "", "unexpected")

        return calls, fake_run

    def test_focus_resolves_the_current_pane_from_agent_session(self) -> None:
        calls, fake_run = self.with_fake_herdr()
        original = herdr_agent._run
        herdr_agent._run = fake_run  # type: ignore[assignment]
        try:
            focused = herdr_agent.focus("claude-a", "claude")
        finally:
            herdr_agent._run = original  # type: ignore[assignment]
        self.assertEqual(focused["pane_id"], "w1:p9")
        self.assertEqual(calls, [["agent", "list"], ["agent", "focus", "w1:p9"]])

    def test_resolve_rejects_agent_type_mismatch(self) -> None:
        _calls, fake_run = self.with_fake_herdr()
        original = herdr_agent._run
        herdr_agent._run = fake_run  # type: ignore[assignment]
        try:
            with self.assertRaises(herdr_agent.HerdrError):
                herdr_agent.resolve("claude-a", "codex")
        finally:
            herdr_agent._run = original  # type: ignore[assignment]

    def test_herdr_context_is_captured_only_when_complete(self) -> None:
        os.environ.update({
            "HERDR_ENV": "1",
            "HERDR_WORKSPACE_ID": "w1",
            "HERDR_TAB_ID": "w1:t3",
            "HERDR_PANE_ID": "w1:p9",
        })
        self.assertEqual(slotclaims.herdr_context()["herdrPaneId"], "w1:p9")
        os.environ["HERDR_PANE_ID"] = "bad value"
        self.assertEqual(slotclaims.herdr_context(), {})

    def test_reconcile_releases_only_marked_dead_herdr_claims(self) -> None:
        now = time.time()
        data = {"slots": {
            "session.claude.slot1": {"agent": "claude", "agentSessionId": "gone", "herdrPaneId": "w1:p1", "updatedAt": now},
            "session.claude.slot2": {"agent": "claude", "agentSessionId": "ordinary", "updatedAt": now},
            "session.codex.slot1": {"agent": "codex", "agentSessionId": "gone-codex", "herdrPaneId": "w1:p2", "updatedAt": now},
        }}
        released = slotclaims.release_missing_herdr_claims(data, {"live"}, agent="claude")
        self.assertEqual(released, ["session.claude.slot1"])
        self.assertIn("session.claude.slot2", data["slots"])
        self.assertIn("session.codex.slot1", data["slots"])

    def test_configure_replaces_only_attached_agent_slot_focus(self) -> None:
        config = {"sessions": {
            "session.claude.slot1": {"agent": "claude", "commands": {}},
            "session.codex.slot1": {"agent": "codex", "commands": {}},
            "session.claude.main": {"agent": "claude", "commands": {}},
        }}
        changed = configure_herdr_sessions.configure(
            config,
            Path("/runtime"),
            Path("/bin/herdr"),
            None,
        )
        self.assertEqual(changed, ["session.claude.slot1", "session.codex.slot1"])
        self.assertIn("focus_herdr.py", config["sessions"]["session.claude.slot1"]["commands"]["focus"]["argv"][2])
        self.assertNotIn("adapter", config["sessions"]["session.claude.main"])

    def test_migration_adopts_live_and_drops_explicit_stale_claims(self) -> None:
        data = {"slots": {
            "session.claude.slot1": {"agent": "claude", "agentSessionId": "claude-a"},
            "session.claude.slot2": {"agent": "claude", "agentSessionId": "gone"},
        }}
        result = migrate_herdr_claims.migrate(
            data,
            "claude",
            [{"agent": "claude", "agent_session": {"value": "claude-a"}, "workspace_id": "w1", "tab_id": "w1:t3", "pane_id": "w1:p9"}],
            True,
        )
        self.assertEqual(result, {"adopted": ["session.claude.slot1"], "claimed": [], "dropped": ["session.claude.slot2"]})
        self.assertEqual(data["slots"]["session.claude.slot1"]["herdrPaneId"], "w1:p9")

    def test_migration_claims_unbound_live_agents(self) -> None:
        data = {"slots": {}}
        result = migrate_herdr_claims.migrate(
            data,
            "claude",
            [{"agent": "claude", "agent_session": {"value": "claude-a"}, "cwd": "/tmp/project", "workspace_id": "w1", "tab_id": "w1:t3", "pane_id": "w1:p9"}],
            False,
            True,
        )
        self.assertEqual(result["claimed"], ["session.claude.slot1"])
        self.assertEqual(data["slots"]["session.claude.slot1"]["agentSessionId"], "claude-a")
