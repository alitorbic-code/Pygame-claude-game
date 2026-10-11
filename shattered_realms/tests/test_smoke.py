"""End-to-end smoke test: menu -> gameplay -> death -> result screen -> menu.

Uses real pygame with dummy video/audio drivers when it is installed, otherwise a stand-in.
"""
import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["SHATTERED_REALMS_HOME"] = tempfile.mkdtemp(prefix="sr_smoke_")

try:
    import pygame
    USING_REAL_PYGAME = True
except ImportError:
    from tests import fake_pygame
    pygame = fake_pygame.install()
    USING_REAL_PYGAME = False

from srealms.game import Game  # noqa: E402

DT = 1 / 60


def key(game, key_code, down=True):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=key_code, mod=0))


class SmokeTest(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.states.push("menu")
        self.frames(3)

    def tearDown(self):
        self.game.shutdown()

    def frames(self, n):
        for _ in range(n):
            self.assertTrue(self.game.frame(DT))

    def start_play(self):
        key(self.game, pygame.K_RETURN)  # "New Game" is focused first
        self.frames(3)
        self.assertEqual(self.game.states.stack_names, ["play"])
        return self.game.states.current

    def test_menu_navigation_to_settings_and_back(self):
        key(self.game, pygame.K_DOWN)  # skips the disabled "Continue" button, landing on Settings
        self.frames(2)
        key(self.game, pygame.K_RETURN)
        self.frames(3)
        self.assertEqual(self.game.states.stack_names, ["menu", "settings"])
        key(self.game, pygame.K_ESCAPE)
        self.frames(3)
        self.assertEqual(self.game.states.stack_names, ["menu"])

    def test_play_pause_resume(self):
        self.start_play()
        key(self.game, pygame.K_ESCAPE)
        self.frames(3)
        self.assertEqual(self.game.states.stack_names, ["play", "pause"])
        key(self.game, pygame.K_ESCAPE)
        self.frames(3)
        self.assertEqual(self.game.states.stack_names, ["play"])

    def test_gameplay_frames_with_inputs(self):
        play = self.start_play()
        for code in (pygame.K_SPACE, pygame.K_j, pygame.K_UP):
            key(self.game, code)
            self.frames(30)
        self.game.debug = True
        self.frames(120)
        self.assertTrue(play.world.player.alive)
        self.assertGreater(play.world.time, 1.0)

    def test_death_leads_to_result_screen_then_menu(self):
        play = self.start_play()
        play.world.player.hurt(10_000, 0, play.world)
        self.frames(int(2.0 / DT))
        self.assertEqual(self.game.states.stack_names, ["play", "result"])
        key(self.game, pygame.K_DOWN)
        self.frames(2)
        key(self.game, pygame.K_RETURN)  # "Main Menu"
        self.frames(3)
        self.assertEqual(self.game.states.stack_names, ["menu"])

    def test_try_again_starts_a_fresh_run(self):
        play = self.start_play()
        play.world.player.hurt(10_000, 0, play.world)
        self.frames(int(2.0 / DT))
        key(self.game, pygame.K_RETURN)  # "Try Again"
        self.frames(3)
        self.assertEqual(self.game.states.stack_names, ["play"])
        self.assertIsNot(self.game.states.current, play)
        self.assertTrue(self.game.states.current.world.player.alive)

    def test_victory_reaches_result_screen(self):
        play = self.start_play()
        play.world.enemies = []
        player = play.world.player
        player.box.x, player.box.y = play.world.exit_box.x + 10, play.world.exit_box.y + 10
        self.frames(10)
        self.assertEqual(self.game.states.stack_names, ["play", "result"])
        self.assertTrue(self.game.states.current.win)


if __name__ == "__main__":
    unittest.main()
