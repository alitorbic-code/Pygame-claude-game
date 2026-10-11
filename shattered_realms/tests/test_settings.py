import json
import tempfile
import unittest
from pathlib import Path

from srealms import config
from srealms.settings import DEFAULT_BINDINGS, Settings, load_settings, save_settings


class SettingsValidationTests(unittest.TestCase):
    def test_defaults_are_in_range(self):
        s = Settings()
        for value in (s.master_volume, s.music_volume, s.sfx_volume, s.screen_shake):
            self.assertTrue(0.0 <= value <= 1.0)
        self.assertEqual(s.bindings, DEFAULT_BINDINGS)

    def test_numbers_are_clamped_and_bad_types_fall_back(self):
        s = Settings.from_dict({"master_volume": 7, "music_volume": -3, "sfx_volume": "loud",
                                "screen_shake": float("nan")})
        self.assertEqual(s.master_volume, 1.0)
        self.assertEqual(s.music_volume, 0.0)
        self.assertEqual(s.sfx_volume, Settings().sfx_volume)
        self.assertEqual(s.screen_shake, Settings().screen_shake)

    def test_bool_is_not_accepted_as_a_number_or_index(self):
        s = Settings.from_dict({"master_volume": True, "resolution_index": True})
        self.assertEqual(s.master_volume, Settings().master_volume)
        self.assertEqual(s.resolution_index, Settings().resolution_index)

    def test_resolution_index_must_be_valid(self):
        self.assertEqual(Settings.from_dict({"resolution_index": 99}).resolution_index,
                         config.DEFAULT_RESOLUTION_INDEX)
        self.assertEqual(Settings.from_dict({"resolution_index": 0}).resolution_index, 0)

    def test_flags_require_real_booleans(self):
        s = Settings.from_dict({"fullscreen": "yes", "high_contrast": 1, "show_fps": True})
        self.assertFalse(s.fullscreen)
        self.assertFalse(s.high_contrast)
        self.assertTrue(s.show_fps)

    def test_bindings_ignore_unknown_actions_and_bad_names(self):
        s = Settings.from_dict({"bindings": {"jump": "x", "bogus": "y", "dash": 5, "attack": "   "}})
        self.assertEqual(s.bindings["jump"], "x")
        self.assertNotIn("bogus", s.bindings)
        self.assertEqual(s.bindings["dash"], DEFAULT_BINDINGS["dash"])
        self.assertEqual(s.bindings["attack"], DEFAULT_BINDINGS["attack"])

    def test_reset_to_defaults_restores_everything(self):
        s = Settings(master_volume=0.1, fullscreen=True)
        s.bindings["jump"] = "x"
        s.reset_to_defaults()
        self.assertEqual(s, Settings())


class SettingsPersistenceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.path = self.dir / "settings.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_file_gives_defaults_without_warning(self):
        s, warning = load_settings(self.path)
        self.assertEqual(s, Settings())
        self.assertIsNone(warning)

    def test_round_trip(self):
        original = Settings(master_volume=0.25, fullscreen=True, resolution_index=2, show_fps=True)
        original.bindings["jump"] = "x"
        self.assertTrue(save_settings(original, self.path))
        loaded, warning = load_settings(self.path)
        self.assertIsNone(warning)
        self.assertEqual(loaded, original)

    def test_corrupt_json_is_backed_up_not_overwritten(self):
        self.path.write_text("{ this is not json", encoding="utf-8")
        s, warning = load_settings(self.path)
        self.assertEqual(s, Settings())
        self.assertIsNotNone(warning)
        backup = self.dir / "settings.json.corrupt"
        self.assertTrue(backup.exists())
        self.assertEqual(backup.read_text(encoding="utf-8"), "{ this is not json")

    def test_non_object_json_is_rejected(self):
        self.path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        s, warning = load_settings(self.path)
        self.assertEqual(s, Settings())
        self.assertIn("unexpected format", warning)

    def test_invalid_utf8_is_handled(self):
        self.path.write_bytes(b"\xff\xfe\x00bad")
        s, warning = load_settings(self.path)
        self.assertEqual(s, Settings())
        self.assertIsNotNone(warning)

    def test_failed_save_returns_false_and_keeps_old_file(self):
        self.assertTrue(save_settings(Settings(master_volume=0.5), self.path))
        before = self.path.read_text(encoding="utf-8")
        blocker = self.dir / "blocker"
        blocker.write_text("i am a file", encoding="utf-8")
        self.assertFalse(save_settings(Settings(), blocker / "settings.json"))
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_no_temp_files_left_behind(self):
        save_settings(Settings(), self.path)
        self.assertEqual([p.name for p in self.dir.iterdir()], ["settings.json"])


if __name__ == "__main__":
    unittest.main()
