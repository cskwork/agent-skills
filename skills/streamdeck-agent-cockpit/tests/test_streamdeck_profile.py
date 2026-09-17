from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import streamdeck_profile  # noqa: E402


class StreamDeckProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.profile = base / "Default Profile.sdProfile"
        self.profiles = self.profile / "Profiles"
        self.page_id = "f5297c44-13e2-45ab-9b2e-6c0cb68be6d0"
        self.other_page_id = "11bdd8aa-0000-0000-0000-000000000000"
        self.page = self.profiles / self.page_id / "manifest.json"
        self.other_page = self.profiles / self.other_page_id / "manifest.json"
        self.page.parent.mkdir(parents=True)
        self.other_page.parent.mkdir(parents=True)
        (self.profile / "manifest.json").write_text(
            json.dumps({"Name": "Default Profile"}), encoding="utf-8"
        )
        self.page.write_text(
            json.dumps({"Controllers": [{"Type": "Keypad", "Actions": None}]}),
            encoding="utf-8",
        )
        self.other_page.write_text(
            json.dumps({"Controllers": [{"Type": "Keypad", "Actions": {"0,0": {"sentinel": True}}}]}),
            encoding="utf-8",
        )
        self.claude_launcher = base / "claude.command"
        self.codex_launcher = base / "codex.command"
        self.claude_launcher.write_text("claude", encoding="utf-8")
        self.codex_launcher.write_text("codex", encoding="utf-8")
        self.backups = base / "backups"

    def run_helper(
        self,
        *controls: str,
        replace: bool = False,
        plugin_controls: tuple[str, ...] = (),
    ) -> int:
        argv = [
            "--profile-root",
            str(self.profile),
            "--page-id",
            self.page_id,
            "--backup-dir",
            str(self.backups),
        ]
        for control in controls:
            argv.extend(["--control", control])
        for control in plugin_controls:
            argv.extend(["--plugin-control", control])
        if replace:
            argv.append("--replace")
        with contextlib.redirect_stdout(io.StringIO()):
            return streamdeck_profile.main(argv)

    def test_adds_only_requested_actions_and_creates_backup(self) -> None:
        root_before = (self.profile / "manifest.json").read_bytes()
        other_before = self.other_page.read_bytes()

        result = self.run_helper(
            f"0,0={self.claude_launcher}|Claude Code",
            f"1,0={self.codex_launcher}|Codex",
        )

        self.assertEqual(result, 0)
        updated = json.loads(self.page.read_text(encoding="utf-8"))
        actions = updated["Controllers"][0]["Actions"]
        self.assertEqual(actions["0,0"]["Name"], "Open")
        self.assertEqual(actions["0,0"]["States"][0]["Title"], "Claude Code")
        self.assertEqual(actions["1,0"]["States"][0]["Title"], "Codex")
        self.assertEqual(
            actions["0,0"]["Settings"]["path"],
            json.dumps(str(self.claude_launcher.resolve())),
        )
        self.assertEqual((self.profile / "manifest.json").read_bytes(), root_before)
        self.assertEqual(self.other_page.read_bytes(), other_before)

        backup_paths = list(self.backups.iterdir())
        self.assertEqual(len(backup_paths), 1)
        backup_page = backup_paths[0] / "Profiles" / self.page_id / "manifest.json"
        self.assertEqual(json.loads(backup_page.read_text(encoding="utf-8"))["Controllers"][0]["Actions"], None)

    def test_refuses_occupied_and_duplicate_keys_without_new_backup(self) -> None:
        self.assertEqual(
            self.run_helper(f"0,0={self.claude_launcher}|Claude Code"), 0
        )
        backup_count = len(list(self.backups.iterdir()))

        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            occupied = self.run_helper(f"0,0={self.claude_launcher}|Claude Code")
        self.assertEqual(occupied, 1)
        self.assertIn("already occupied", error.getvalue())
        self.assertEqual(len(list(self.backups.iterdir())), backup_count)

        replaced = self.run_helper(
            f"0,0={self.claude_launcher}|Claude iTerm",
            replace=True,
        )
        self.assertEqual(replaced, 0)
        updated = json.loads(self.page.read_text(encoding="utf-8"))
        self.assertEqual(updated["Controllers"][0]["Actions"]["0,0"]["States"][0]["Title"], "Claude iTerm")
        self.assertEqual(len(list(self.backups.iterdir())), backup_count + 1)

        duplicate_error = io.StringIO()
        with contextlib.redirect_stderr(duplicate_error):
            duplicate = self.run_helper(
                f"1,0={self.claude_launcher}|Claude Code",
                f"1,0={self.codex_launcher}|Codex",
            )
        self.assertEqual(duplicate, 1)
        self.assertIn("duplicate page key", duplicate_error.getvalue())
        self.assertEqual(len(list(self.backups.iterdir())), backup_count + 1)

    def test_rejects_non_uuid_page_id_before_reading_outside_profile(self) -> None:
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            result = streamdeck_profile.main(
                [
                    "--profile-root",
                    str(self.profile),
                    "--page-id",
                    "../../manifest.json",
                    "--control",
                    f"0,0={self.claude_launcher}|Claude Code",
                ]
            )
        self.assertEqual(result, 2)
        self.assertIn("not a UUID", error.getvalue())

    def test_replaces_open_actions_with_owned_plugin_controls(self) -> None:
        self.assertEqual(
            self.run_helper(f"0,0={self.claude_launcher}|Claude Code"), 0
        )
        root_before = (self.profile / "manifest.json").read_bytes()
        other_before = self.other_page.read_bytes()

        result = self.run_helper(
            replace=True,
            plugin_controls=(
                "0,0=session.claude.iterm|Claude 1",
                "1,0=session.codex.iterm|Codex 1",
            ),
        )

        self.assertEqual(result, 0)
        actions = json.loads(self.page.read_text(encoding="utf-8"))["Controllers"][0]["Actions"]
        self.assertEqual(actions["0,0"]["UUID"], streamdeck_profile.COCKPIT_ACTION_UUID)
        self.assertEqual(actions["0,0"]["Settings"]["controlId"], "session.claude.iterm")
        self.assertFalse(actions["0,0"]["States"][0]["ShowTitle"])
        self.assertEqual(actions["1,0"]["Settings"]["controlId"], "session.codex.iterm")
        self.assertEqual((self.profile / "manifest.json").read_bytes(), root_before)
        self.assertEqual(self.other_page.read_bytes(), other_before)


if __name__ == "__main__":
    unittest.main()
