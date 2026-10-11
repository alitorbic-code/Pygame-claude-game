import unittest

from srealms.state_manager import State, StateManager


class Recorder(State):
    transparent = False

    def __init__(self, game, name, log, transparent=False):
        super().__init__(game)
        self.name = name
        self.log = log
        self.transparent = transparent

    def enter(self, **kwargs):
        self.log.append(f"{self.name}.enter{kwargs or ''}")

    def exit(self):
        self.log.append(f"{self.name}.exit")

    def pause(self):
        self.log.append(f"{self.name}.pause")

    def resume(self):
        self.log.append(f"{self.name}.resume")

    def draw(self, surface):
        surface.append(self.name)

    def update(self, dt):
        self.log.append(f"{self.name}.update")


class StateManagerTests(unittest.TestCase):
    def setUp(self):
        self.log = []
        self.manager = StateManager(game=object())
        for name, transparent in (("a", False), ("b", False), ("overlay", True)):
            self.manager.register(
                name, lambda game, n=name, t=transparent: Recorder(game, n, self.log, t))

    def test_transitions_are_deferred_until_apply_pending(self):
        self.manager.push("a")
        self.assertTrue(self.manager.is_empty)
        self.assertTrue(self.manager.has_pending)
        self.manager.apply_pending()
        self.assertEqual(self.manager.stack_names, ["a"])
        self.assertFalse(self.manager.has_pending)

    def test_push_pauses_and_pop_resumes(self):
        self.manager.push("a")
        self.manager.push("b")
        self.manager.apply_pending()
        self.manager.pop()
        self.manager.apply_pending()
        self.assertEqual(self.log, ["a.enter", "a.pause", "b.enter", "b.exit", "a.resume"])

    def test_switch_replaces_top_without_resuming_below(self):
        self.manager.push("a")
        self.manager.push("b")
        self.manager.apply_pending()
        self.log.clear()
        self.manager.switch("overlay")
        self.manager.apply_pending()
        self.assertEqual(self.manager.stack_names, ["a", "overlay"])
        self.assertEqual(self.log, ["b.exit", "overlay.enter"])

    def test_reset_clears_whole_stack(self):
        for name in ("a", "b", "overlay"):
            self.manager.push(name)
        self.manager.apply_pending()
        self.log.clear()
        self.manager.reset("a")
        self.manager.apply_pending()
        self.assertEqual(self.manager.stack_names, ["a"])
        self.assertEqual(self.log, ["overlay.exit", "b.exit", "a.exit", "a.enter"])

    def test_unknown_state_raises_immediately(self):
        for call in (self.manager.push, self.manager.switch, self.manager.reset):
            with self.assertRaises(KeyError):
                call("nope")

    def test_pop_on_empty_stack_is_harmless(self):
        self.manager.pop()
        self.manager.apply_pending()
        self.assertTrue(self.manager.is_empty)

    def test_only_top_state_updates(self):
        self.manager.push("a")
        self.manager.push("b")
        self.manager.apply_pending()
        self.log.clear()
        self.manager.update(0.016)
        self.assertEqual(self.log, ["b.update"])

    def test_draw_starts_at_lowest_state_under_transparent_ones(self):
        for name in ("a", "b", "overlay"):
            self.manager.push(name)
        self.manager.apply_pending()
        drawn = []
        self.manager.draw(drawn)
        self.assertEqual(drawn, ["b", "overlay"])

    def test_enter_receives_kwargs(self):
        self.manager.push("a", level=3)
        self.manager.apply_pending()
        self.assertIn("a.enter{'level': 3}", self.log)

    def test_state_can_queue_its_own_pop_during_update(self):
        class SelfClosing(Recorder):
            def update(inner, dt):
                self.manager.pop()

        self.manager.register("closer", lambda game: SelfClosing(game, "closer", self.log))
        self.manager.push("a")
        self.manager.push("closer")
        self.manager.apply_pending()
        self.manager.update(0.016)
        self.assertEqual(self.manager.stack_names, ["a", "closer"])
        self.manager.apply_pending()
        self.assertEqual(self.manager.stack_names, ["a"])


if __name__ == "__main__":
    unittest.main()
