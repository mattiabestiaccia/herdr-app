import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import prototype


class PrototypeIsolation(unittest.TestCase):
    def test_default_socket_path_fits_macos(self):
        env = prototype.environment()
        socket = str(Path(env["HERDR_APP_HOME"]) / "herdr-app.sock")
        self.assertLess(len(os.fsencode(socket)), 104)

    def test_inherited_core_addresses_are_replaced(self):
        with patch.dict(os.environ, {"HC_SOCKET": "daily.sock", "HC_SESSION": "daily",
                                     "HC_TERMINAL_ID": "t1", "HERDR_APP_HOME": "/daily",
                                     "HERDR_APP_SOCKET": "daily-app.sock", "HC_SCOPE": "daily"}):
            env = prototype.environment(Path("/tmp/prototype-isolation-test"))
        for key in ("HC_SOCKET", "HC_TERMINAL_ID", "HERDR_APP_SOCKET", "HC_SCOPE"):
            self.assertNotIn(key, env)
        self.assertTrue(env["HC_SESSION"].startswith("test-glass-"))
        self.assertEqual(env["HERDR_APP_ID"], "herdr-transparency-prototype")
        self.assertEqual(env["HERDR_APP_HOME"], "/tmp/prototype-isolation-test/home")
        other = prototype.environment(Path("/tmp/prototype-isolation-test-other"))
        self.assertNotEqual(env["HC_SESSION"], other["HC_SESSION"])
        self.assertNotEqual(env["XDG_STATE_HOME"], other["XDG_STATE_HOME"])

    def test_presets_persist_and_invalid_values_preserve_file(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            env = prototype.environment(state)
            try:
                prototype.set_background("blurred", 0.65, state)
                path = state / "home/layouts/herdr-transparent.json"
                value = json.loads(path.read_text())
                self.assertEqual(value["workspace_opacity"], 0.65)
                self.assertEqual(value["background_mode"], "blurred")
                before = path.read_bytes()
                prototype.prepare(state)
                self.assertEqual(path.read_bytes(), before)
                for mode, alpha in [("glass", 0.85), ("blurred", -0.1), ("transparent", 1.1),
                                    ("transparent", math.nan), ("opaque", math.inf)]:
                    with self.assertRaises(ValueError):
                        prototype.set_background(mode, alpha, state)
                    self.assertEqual(path.read_bytes(), before)
                settings = json.loads((state / "home/settings.json").read_text())
                self.assertFalse(settings["telemetry"])
            finally:
                shutil.rmtree(env["XDG_RUNTIME_DIR"], ignore_errors=True)

    def test_fullscreen_image_is_set_checked_and_cleared(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            env = prototype.environment(state)
            try:
                picture = state / "wall.png"
                picture.write_bytes(b"png")
                prototype.set_fullscreen_image(str(picture), state)
                path = state / "home/layouts/herdr-transparent.json"
                self.assertEqual(json.loads(path.read_text())["fullscreen_image"], str(picture.resolve()))
                before = path.read_bytes()
                with self.assertRaises(ValueError):
                    prototype.set_fullscreen_image(str(state / "missing.png"), state)
                self.assertEqual(path.read_bytes(), before)
                prototype.set_fullscreen_image(None, state)
                self.assertNotIn("fullscreen_image", json.loads(path.read_text()))
            finally:
                shutil.rmtree(env["XDG_RUNTIME_DIR"], ignore_errors=True)

    def test_real_home_is_edited_in_place_without_prototype_state(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder) / "herdr-app"
            prototype.set_background("blurred", 0.4, home=home)
            path = home / "layouts/herdr-transparent.json"
            value = json.loads(path.read_text())
            self.assertEqual((value["background_mode"], value["workspace_opacity"]), ("blurred", 0.4))
            self.assertEqual(sorted(p.name for p in home.iterdir()), ["layouts"])


if __name__ == "__main__":
    unittest.main()
