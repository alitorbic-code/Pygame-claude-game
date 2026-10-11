import random
import unittest

from srealms.camera import Camera
from srealms.combat import Health, mitigate, roll_damage


class FixedRng(random.Random):
    def __init__(self, value):
        super().__init__()
        self.value = value

    def random(self):
        return self.value


class HealthTests(unittest.TestCase):
    def test_damage_and_death(self):
        h = Health(50)
        self.assertEqual(h.damage(20), 20)
        self.assertEqual(h.hp, 30)
        self.assertEqual(h.damage(999), 30)  # capped at remaining hp
        self.assertFalse(h.alive)

    def test_invulnerability_window(self):
        h = Health(100, invuln_time=1.0)
        self.assertEqual(h.damage(10), 10)
        self.assertEqual(h.damage(10), 0)
        self.assertEqual(h.damage(10, ignore_invuln=True), 10)
        h.update(1.1)
        self.assertEqual(h.damage(10), 10)

    def test_nonpositive_damage_ignored(self):
        h = Health(10)
        self.assertEqual(h.damage(0), 0)
        self.assertEqual(h.damage(-5), 0)
        self.assertEqual(h.hp, 10)

    def test_heal_clamps_and_requires_life(self):
        h = Health(100)
        h.damage(30)
        self.assertEqual(h.heal(50), 30)
        self.assertEqual(h.hp, 100)
        h.damage(100)
        self.assertEqual(h.heal(10), 0)

    def test_fraction(self):
        h = Health(80)
        h.damage(20)
        self.assertAlmostEqual(h.fraction, 0.75)


class DamageRollTests(unittest.TestCase):
    def test_crit_multiplies_damage(self):
        self.assertEqual(roll_damage(10, 0.5, 2.0, 0, FixedRng(0.1)), (20, True))
        self.assertEqual(roll_damage(10, 0.5, 2.0, 0, FixedRng(0.9)), (10, False))

    def test_armor_reduces_with_diminishing_returns(self):
        self.assertAlmostEqual(mitigate(100, 100), 50)
        self.assertEqual(roll_damage(10, 0, 2.0, 100, FixedRng(0.5))[0], 5)

    def test_minimum_damage_is_one(self):
        self.assertEqual(roll_damage(1, 0, 2.0, 10000, FixedRng(0.5))[0], 1)


class CameraTests(unittest.TestCase):
    def test_snap_clamps_to_world(self):
        cam = Camera(100, 100, 1000, 1000)
        cam.snap(0, 0)
        self.assertEqual((cam.x, cam.y), (0, 0))
        cam.snap(5000, 5000)
        self.assertEqual((cam.x, cam.y), (900, 900))

    def test_small_world_is_centered(self):
        cam = Camera(100, 100, 60, 60)
        cam.snap(30, 30)
        self.assertEqual((cam.x, cam.y), (-20, -20))

    def test_follow_converges_and_is_framerate_independent(self):
        a, b = Camera(100, 100, 2000, 2000), Camera(100, 100, 2000, 2000)
        for _ in range(60):
            a.follow(1000, 1000, 1 / 60)
        for _ in range(120):
            b.follow(1000, 1000, 1 / 120)
        self.assertAlmostEqual(a.x, b.x, places=3)
        self.assertGreater(a.x, 900)

    def test_visibility_culling(self):
        cam = Camera(100, 100, 1000, 1000)
        cam.snap(50, 50)
        self.assertTrue(cam.is_visible(10, 10, 20, 20))
        self.assertFalse(cam.is_visible(800, 800, 20, 20))


if __name__ == "__main__":
    unittest.main()
