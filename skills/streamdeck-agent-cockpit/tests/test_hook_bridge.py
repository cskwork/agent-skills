"""Tests for the Claude Code event mapping and the Windows Terminal focus path."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

import claude_hook  # noqa: E402
import codex_hook  # noqa: E402
import focus_terminal  # noqa: E402
import install_claude_hooks  # noqa: E402
import install_codex_hooks  # noqa: E402


class EventMappingTest(unittest.TestCase):
    def test_stop_is_idle_not_a_success_state(self) -> None:
        state, _, _ = claude_hook.EVENT_MAP["Stop"]
        self.assertEqual(state, "idle")

    def test_permission_events_split_attention_from_blocked(self) -> None:
        self.assertEqual(claude_hook.EVENT_MAP["PermissionRequest"][0], "needs_attention")
        self.assertEqual(claude_hook.EVENT_MAP["PermissionDenied"][0], "blocked")

    def test_stop_failure_is_the_only_failed_event(self) -> None:
        failed = [name for name, (state, _, _) in claude_hook.EVENT_MAP.items() if state == "failed"]
        self.assertEqual(failed, ["StopFailure"])

    def test_every_state_is_part_of_the_published_vocabulary(self) -> None:
        allowed = {"idle", "running", "needs_attention", "blocked", "succeeded", "failed"}
        for name, (state, _, ttl) in claude_hook.EVENT_MAP.items():
            self.assertIn(state, allowed, name)
            self.assertGreater(ttl, 0, name)

    def test_notification_type_wins_over_the_message_fallback(self) -> None:
        payload = {"notification_type": "permission_prompt", "message": "all quiet"}
        self.assertEqual(claude_hook.resolve("Notification", payload)[0], "needs_attention")

    def test_notification_falls_back_to_the_message(self) -> None:
        payload = {"message": "Claude needs your permission to run Bash"}
        self.assertEqual(claude_hook.resolve("Notification", payload)[0], "needs_attention")

    def test_completion_notification_is_idle(self) -> None:
        self.assertEqual(claude_hook.resolve("Notification", {"notification_type": "agent_completed"})[0], "idle")

    def test_unknown_event_is_ignored(self) -> None:
        self.assertIsNone(claude_hook.resolve("SomethingElse", {}))

    def test_registered_events_are_all_mapped(self) -> None:
        registered = set(install_claude_hooks.EVENTS) | set(install_claude_hooks.EXTENDED_EVENTS)
        handled = set(claude_hook.EVENT_MAP) | {"Notification", "SessionEnd"}
        self.assertEqual(registered - handled, set())

    def test_extended_events_are_opt_in(self) -> None:
        self.assertEqual(set(install_claude_hooks.EVENTS) & set(install_claude_hooks.EXTENDED_EVENTS), set())

    def test_codex_bridge_uses_the_codex_namespace(self) -> None:
        self.assertEqual(codex_hook.bridge.AGENT, "claude")
        self.assertIn("codex_hook.py", install_codex_hooks.command_string("python3"))

    def test_codex_registration_covers_session_lifecycle(self) -> None:
        self.assertEqual(
            set(install_codex_hooks.EVENTS),
            {"SessionStart", "UserPromptSubmit", "Stop", "SessionEnd"},
        )


class AppleScriptTest(unittest.TestCase):
    """An unbalanced block compiles to nothing and fails only at focus time.

    The iTerm2 script shipped from 3.1.0 to 3.2.0 closed its innermost `repeat`
    with `end tell`, so every focus attempt died with a syntax error that only
    surfaced on a real key press. Structure is checked here instead.
    """

    def keywords(self, script: str) -> dict:
        counts = {"tell": 0, "end tell": 0, "repeat": 0, "end repeat": 0, "if": 0, "end if": 0}
        for line in script.splitlines():
            stripped = line.strip()
            if stripped.startswith("end "):
                key = " ".join(stripped.split()[:2])
                if key in counts:
                    counts[key] += 1
            else:
                head = stripped.split(" ")[0]
                if head in ("tell", "repeat", "if"):
                    counts[head] += 1
        return counts

    def test_every_block_is_closed_by_its_own_keyword(self) -> None:
        for name, script in focus_terminal.APPS:
            counts = self.keywords(script)
            for opener in ("tell", "repeat", "if"):
                self.assertEqual(
                    counts[opener], counts[f"end {opener}"],
                    f"{name}: {counts[opener]} `{opener}` vs {counts[f'end {opener}']} `end {opener}`",
                )

    def test_iterm_script_uses_bundle_identity(self) -> None:
        self.assertIn(focus_terminal.ITERM2_BUNDLE_ID, focus_terminal.ITERM2)

    def test_iterm_running_check_uses_bundle_identity(self) -> None:
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            return type("R", (), {"stdout": "true\n"})()

        original = focus_terminal.subprocess.run
        focus_terminal.subprocess.run = fake_run  # type: ignore[assignment]
        try:
            self.assertTrue(focus_terminal.is_running("iTerm2"))
        finally:
            focus_terminal.subprocess.run = original  # type: ignore[assignment]
        self.assertIn(focus_terminal.ITERM2_BUNDLE_ID, captured["argv"][-1])

    @unittest.skipUnless(sys.platform == "darwin", "osacompile is macOS only")
    def test_scripts_compile(self) -> None:
        for name, script in focus_terminal.APPS:
            result = subprocess.run(
                ["osacompile", "-o", "/dev/null", "-"],
                input=script, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, f"{name}: {result.stderr.strip()}")


class WindowsTerminalFocusTest(unittest.TestCase):
    def test_helper_script_ships_with_the_runtime(self) -> None:
        self.assertTrue(focus_terminal.WINDOWS_TERMINAL_SCRIPT.exists())

    def test_focus_reports_a_problem_when_no_tab_matches(self) -> None:
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            return type("R", (), {"returncode": 3, "stdout": "", "stderr": "no tab"})()

        original = focus_terminal.subprocess.run
        focus_terminal.subprocess.run = fake_run  # type: ignore[assignment]
        try:
            problem = focus_terminal.focus_windows_terminal("Claude · Main")
        finally:
            focus_terminal.subprocess.run = original  # type: ignore[assignment]
        self.assertEqual(problem, "no tab")
        self.assertIn("-TabTitle", captured["argv"])
        self.assertEqual(captured["argv"][-1], "Claude · Main")

    def test_focus_succeeds_only_on_the_focused_marker(self) -> None:
        def fake_run(argv, **kwargs):
            return type("R", (), {"returncode": 0, "stdout": "focused\n", "stderr": ""})()

        original = focus_terminal.subprocess.run
        focus_terminal.subprocess.run = fake_run  # type: ignore[assignment]
        try:
            self.assertIsNone(focus_terminal.focus_windows_terminal("Claude · Main"))
        finally:
            focus_terminal.subprocess.run = original  # type: ignore[assignment]

    def test_missing_powershell_is_an_honest_failure(self) -> None:
        def fake_run(argv, **kwargs):
            raise FileNotFoundError(argv[0])

        original = focus_terminal.subprocess.run
        focus_terminal.subprocess.run = fake_run  # type: ignore[assignment]
        try:
            problem = focus_terminal.focus_windows_terminal("Claude · Main")
        finally:
            focus_terminal.subprocess.run = original  # type: ignore[assignment]
        self.assertIn("not found", str(problem))


if __name__ == "__main__":
    unittest.main()
