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

import install_streamdeck_plugin  # noqa: E402


class InstallStreamDeckPluginTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = root / install_streamdeck_plugin.PLUGIN_DIRNAME
        (self.source / "bin").mkdir(parents=True)
        (self.source / "bin" / "plugin.js").write_text("export {};\n", encoding="utf-8")
        (self.source / "manifest.json").write_text(
            json.dumps(
                {
                    "UUID": install_streamdeck_plugin.PLUGIN_UUID,
                    "Actions": [{"UUID": install_streamdeck_plugin.ACTION_UUID}],
                }
            ),
            encoding="utf-8",
        )
        self.destination = root / "Plugins" / install_streamdeck_plugin.PLUGIN_DIRNAME

    def run_installer(self, *, force: bool = False) -> tuple[int, str]:
        argv = ["--source", str(self.source), "--destination", str(self.destination)]
        if force:
            argv.append("--force")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = install_streamdeck_plugin.main(argv)
        return result, output.getvalue()

    def test_installs_built_owned_plugin(self) -> None:
        result, output = self.run_installer()

        self.assertEqual(result, 0)
        self.assertTrue((self.destination / "bin" / "plugin.js").is_file())
        self.assertEqual(json.loads(output)["backup"], None)

    def test_force_install_preserves_previous_owned_plugin(self) -> None:
        self.assertEqual(self.run_installer()[0], 0)

        result, output = self.run_installer(force=True)

        self.assertEqual(result, 0)
        backup = Path(json.loads(output)["backup"])
        self.assertTrue((backup / "manifest.json").is_file())
        self.assertTrue((self.destination / "bin" / "plugin.js").is_file())


if __name__ == "__main__":
    unittest.main()
