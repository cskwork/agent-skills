from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_cockpit  # noqa: E402


class ValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.example = json.loads((ROOT / "assets/cockpit.example.json").read_text(encoding="utf-8"))

    def test_example_is_valid(self) -> None:
        findings = validate_cockpit.validate(self.example)
        self.assertEqual(findings.errors, [])

    def test_rejects_streamdeck_mcp_dependency(self) -> None:
        data = copy.deepcopy(self.example)
        data["commands"]["workflow.bad"] = {"argv": ["streamdeck-mcp", "run"]}
        findings = validate_cockpit.validate(data)
        self.assertTrue(any("standalone" in item for item in findings.errors))

    def test_rejects_physical_coordinates(self) -> None:
        data = copy.deepcopy(self.example)
        data["controls"]["session.claude.main"]["row"] = 1
        findings = validate_cockpit.validate(data)
        self.assertTrue(any("physical key coordinates" in item for item in findings.errors))

    def test_rejects_unconfirmed_interrupt(self) -> None:
        data = copy.deepcopy(self.example)
        data["controls"]["session.claude.main"]["gestures"]["longPress"] = {"operation": "interrupt"}
        findings = validate_cockpit.validate(data)
        self.assertTrue(any("destructive operation requires" in item for item in findings.errors))

    def test_rejects_shell_string(self) -> None:
        data = copy.deepcopy(self.example)
        data["commands"]["workflow.bad"] = {"argv": ["bash", "-c", "echo unsafe"]}
        findings = validate_cockpit.validate(data)
        self.assertTrue(any("shell command strings" in item for item in findings.errors))


if __name__ == "__main__":
    unittest.main()
