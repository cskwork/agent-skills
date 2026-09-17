"""Tests for slot bookkeeping used by attached agent sessions."""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

import slotclaims  # noqa: E402


class SlotClaimsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._previous = os.environ.get("COCKPIT_HOME")
        os.environ["COCKPIT_HOME"] = self._tmp.name

    def tearDown(self) -> None:
        if self._previous is None:
            os.environ.pop("COCKPIT_HOME", None)
        else:
            os.environ["COCKPIT_HOME"] = self._previous
        self._tmp.cleanup()

    def live_claim(self, session_id: str) -> dict:
        return {"agentSessionId": session_id, "pid": os.getpid(), "updatedAt": time.time()}

    def test_missing_file_yields_empty_slots(self) -> None:
        self.assertEqual(slotclaims.load(), {"slots": {}})

    def test_round_trip_preserves_claims(self) -> None:
        slotclaims.save({"slots": {"session.claude.slot1": self.live_claim("a")}})
        self.assertIn("session.claude.slot1", slotclaims.load()["slots"])

    @unittest.skipUnless(os.name == "posix", "POSIX file modes only")
    def test_claims_file_is_private(self) -> None:
        slotclaims.save({"slots": {"session.claude.slot1": self.live_claim("a")}})
        self.assertEqual(slotclaims.claims_path().stat().st_mode & 0o777, 0o600)

    def test_same_session_keeps_its_slot(self) -> None:
        data = {"slots": {"session.claude.slot1": self.live_claim("a")}}
        self.assertEqual(slotclaims.acquire(data, "a"), "session.claude.slot1")

    def test_new_session_takes_the_next_free_slot(self) -> None:
        data = {"slots": {"session.claude.slot1": self.live_claim("a")}}
        self.assertEqual(slotclaims.acquire(data, "b"), "session.claude.slot2")

    def test_dead_claim_is_reusable(self) -> None:
        dead = {"agentSessionId": "a", "pid": 2 ** 31 - 1, "updatedAt": time.time()}
        data = {"slots": {"session.claude.slot1": dead}}
        self.assertEqual(slotclaims.acquire(data, "b"), "session.claude.slot1")

    def test_stale_claim_is_reusable(self) -> None:
        stale = {"agentSessionId": "a", "pid": os.getpid(), "updatedAt": 0}
        data = {"slots": {"session.claude.slot1": stale}}
        self.assertFalse(slotclaims.claim_is_live(stale))
        self.assertEqual(slotclaims.acquire(data, "b"), "session.claude.slot1")

    def test_full_slots_never_evict_a_live_session(self) -> None:
        data = {"slots": {slot: self.live_claim(slot) for slot in slotclaims.slot_ids()}}
        self.assertIsNone(slotclaims.acquire(data, "newcomer"))
        self.assertEqual(len(data["slots"]), slotclaims.DEFAULT_SLOT_COUNT)

    def test_live_herdr_claim_is_not_reused_without_a_process_owner(self) -> None:
        data = {"slots": {
            "session.claude.slot1": {
                "agentSessionId": "herdr-a",
                "agent": "claude",
                "herdrPaneId": "w1:p1",
                "pid": None,
                "updatedAt": time.time(),
            }
        }}
        self.assertEqual(
            slotclaims.acquire(data, "herdr-b", live_herdr_session_ids={"herdr-a", "herdr-b"}),
            "session.claude.slot2",
        )

    def test_release_frees_the_slot(self) -> None:
        data = {"slots": {"session.claude.slot1": self.live_claim("a")}}
        self.assertEqual(slotclaims.release(data, "a"), "session.claude.slot1")
        self.assertEqual(data["slots"], {})
        self.assertIsNone(slotclaims.release(data, "a"))

    @unittest.skipUnless(os.name == "posix", "ancestry and tty discovery is POSIX only")
    def test_owner_discovery_reports_a_live_pid(self) -> None:
        owner = slotclaims.discover_owner()
        self.assertTrue(slotclaims.pid_alive(owner.get("pid")))
        tty = owner.get("tty") or ""
        self.assertTrue(tty == "" or tty.startswith("/dev/"))

    def test_owner_discovery_degrades_without_ps(self) -> None:
        original = slotclaims._ps
        slotclaims._ps = lambda pid: None  # type: ignore[assignment]
        try:
            owner = slotclaims.discover_owner()
        finally:
            slotclaims._ps = original  # type: ignore[assignment]
        self.assertEqual(owner.get("pid"), os.getpid())
        self.assertEqual(owner.get("tty"), "")

    def test_pid_alive_rejects_nonsense_without_platform_calls(self) -> None:
        for value in (None, 0, -1, "", "abc", 1.5):
            self.assertFalse(slotclaims.pid_alive(value))  # type: ignore[arg-type]

    def test_pid_alive_uses_the_win32_path_on_windows(self) -> None:
        seen = []
        original_name, original_win32 = os.name, slotclaims._pid_alive_windows
        slotclaims._pid_alive_windows = lambda pid: seen.append(pid) or True  # type: ignore[assignment]
        os.name = "nt"  # type: ignore[misc]
        try:
            self.assertTrue(slotclaims.pid_alive(4321))
        finally:
            os.name = original_name  # type: ignore[misc]
            slotclaims._pid_alive_windows = original_win32  # type: ignore[assignment]
        self.assertEqual(seen, [4321])


if __name__ == "__main__":
    unittest.main()
