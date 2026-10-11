import unittest

from srealms.entities.enemies import Walker
from srealms.entities.projectile import Projectile
from srealms.levels import build_proving_grounds
from srealms.physics import ONEWAY, SOLID, TILE, TileMap
from srealms.world import World

from .helpers import DT, arena, make_world, run


def place_walker(world, tile_x, tile_y=10):
    walker = Walker(tile_x * TILE + TILE / 2, (tile_y + 1) * TILE)
    world.enemies = [walker]
    return walker


class CombatFlowTests(unittest.TestCase):
    def setUp(self):
        self.world = make_world()
        run(self.world, 30)
        self.p = self.world.player

    def test_swing_damages_enemy_once(self):
        w = place_walker(self.world, 4)
        w.box.x = self.p.box.right + 30
        w.facing = -1
        hp = w.health.hp
        run(self.world, 1, attack_pressed=True)
        run(self.world, 40)
        self.assertLess(w.health.hp, hp)
        hp_after = w.health.hp
        run(self.world, 40)
        self.assertEqual(w.health.hp, hp_after)  # same swing cannot hit twice

    def test_hit_emits_event_and_triggers_hitstop(self):
        w = place_walker(self.world, 4)
        w.box.x = self.p.box.right + 30
        run(self.world, 1, attack_pressed=True)
        run(self.world, 20)
        kinds = [e.kind for e in self.world.drain_events()]
        self.assertIn("hit", kinds)

    def test_hitstop_freezes_simulation(self):
        w = place_walker(self.world, 20)
        self.world.hitstop = 0.05
        t = self.world.time
        run(self.world, 3)
        self.assertEqual(self.world.time, t)
        run(self.world, 10)
        self.assertGreater(self.world.time, t)

    def test_killing_enemies_counts_and_removes_them(self):
        w = place_walker(self.world, 4)
        w.box.x = self.p.box.right + 30
        w.health.hp = 1
        run(self.world, 1, attack_pressed=True)
        run(self.world, 40)
        self.assertEqual(self.world.kills, 1)
        self.assertEqual(self.world.enemies, [])
        self.assertIn("enemy_die", [e.kind for e in self.world.drain_events()])

    def test_contact_damage_hurts_player(self):
        w = place_walker(self.world, 4)
        w.box.x = self.p.box.x
        run(self.world, 2)
        self.assertLess(self.p.health.hp, 100)

    def test_swing_reflects_enemy_projectile(self):
        proj = Projectile(self.p.box.right + 30, self.p.box.centery, -50, 0, 10)
        self.world.projectiles.append(proj)
        run(self.world, 1, attack_pressed=True)
        run(self.world, 20)
        self.assertEqual(proj.owner, "player")
        self.assertIn("parry", [e.kind for e in self.world.drain_events()])


class ExitTests(unittest.TestCase):
    def test_exit_requires_all_enemies_dead(self):
        rows = arena(edits=[(10, 10, "X")])
        world = make_world(rows)
        walker = place_walker(world, 25)
        self.assertFalse(world.exit_open)
        world.player.box.x = 10 * TILE
        run(world, 5)
        self.assertFalse(world.won)
        world.enemies = []
        run(world, 5)
        self.assertTrue(world.won)

    def test_level_without_player_is_rejected(self):
        with self.assertRaises(ValueError):
            World(TileMap(["   ", "###"]))


class LevelTests(unittest.TestCase):
    def setUp(self):
        self.tm = build_proving_grounds()
        self.world = World(self.tm)

    def test_expected_population(self):
        self.assertEqual(len(self.world.enemies), 9)
        self.assertIsNotNone(self.world.exit_box)
        kinds = sorted(e.kind for e in self.world.enemies)
        self.assertEqual(kinds, ["flyer"] * 3 + ["shooter"] * 3 + ["walker"] * 3)

    def test_ground_units_spawn_standing_on_something(self):
        for e in self.world.enemies:
            if e.FLIES:
                continue
            below = self.tm.tile_at_pixel(e.box.centerx, e.box.bottom + 2)
            self.assertIn(below, (SOLID, ONEWAY), f"{e.kind} at {e.box.centerx}")

    def test_nothing_spawns_inside_solid_tiles(self):
        entities = [self.world.player, *self.world.enemies]
        for e in entities:
            self.assertFalse(self.tm.solid_overlap(e.box), type(e).__name__)

    def test_player_settles_and_survives_idle_start(self):
        run(self.world, 600)
        self.assertTrue(self.world.player.on_floor)
        self.assertTrue(self.world.player.alive)

    def test_level_is_a_full_rectangle_with_walls(self):
        self.assertEqual((self.tm.width, self.tm.height), (80, 30))
        self.assertTrue(all(self.tm.tile_at(0, y) == SOLID for y in range(30)))


class DeterminismTests(unittest.TestCase):
    def test_same_seed_same_outcome(self):
        def play():
            w = make_world(seed=5)
            for i in range(200):
                run(w, 1, attack_pressed=(i % 40 == 0), move_x=1.0)
            return round(w.player.box.x, 6), w.player.combo_step

        self.assertEqual(play(), play())


if __name__ == "__main__":
    unittest.main()
