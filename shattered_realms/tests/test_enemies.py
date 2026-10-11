import unittest

from srealms.entities.enemies import Flyer, Shooter, Walker
from srealms.entities.projectile import Projectile
from srealms.physics import TILE

from .helpers import DT, arena, make_world, run


def world_with(enemy_cls, tile_x, tile_y=10, rows=None, **kw):
    """Arena with one enemy of the given class dropped in (replacing the map's own spawns)."""
    world = make_world(rows)
    enemy = enemy_cls(tile_x * TILE + TILE / 2, (tile_y + 1) * TILE)
    world.enemies = [enemy]
    return world, enemy


class WalkerTests(unittest.TestCase):
    def test_turns_around_at_wall(self):
        rows = arena(edits=[(12, y, "#") for y in range(1, 11)])
        world, w = world_with(Walker, 6, rows=rows)
        world.player.box.x = 25 * TILE  # far away: no chase
        w.facing = 1
        run(world, 600)
        self.assertEqual(w.facing, -1)

    def test_never_walks_off_ledge(self):
        rows = arena()
        rows[-1] = " " * 8 + "#" * 6 + " " * 16  # a 6-tile island
        world, w = world_with(Walker, 10, rows=rows)
        world.player.box.x = 25 * TILE
        run(world, 1200)  # 10 seconds of patrolling
        self.assertTrue(w.alive)
        self.assertTrue(w.on_floor)
        self.assertGreater(w.box.centerx, 8 * TILE)
        self.assertLess(w.box.centerx, 14 * TILE)

    def test_chases_player_on_sight(self):
        world, w = world_with(Walker, 12)
        run(world, 30)
        world.player.box.x = 8 * TILE
        run(world, 60)
        self.assertEqual(w.state, "chase")
        self.assertEqual(w.facing, -1)
        self.assertLess(w.vx, -w.PATROL_SPEED)

    def test_wall_blocks_line_of_sight(self):
        rows = arena(edits=[(7, y, "#") for y in range(1, 11)])
        world, w = world_with(Walker, 12, rows=rows)
        run(world, 60)
        self.assertEqual(w.state, "patrol")


class FlyerTests(unittest.TestCase):
    def test_approaches_player(self):
        world, f = world_with(Flyer, 11, tile_y=6)
        run(world, 5)
        before = abs(f.box.centerx - world.player.box.centerx)
        run(world, 120)
        after = abs(f.box.centerx - world.player.box.centerx)
        self.assertLess(after, before)
        self.assertEqual(f.state, "hunt")

    def test_does_not_fall(self):
        world, f = world_with(Flyer, 25, tile_y=3)
        world.player.box.x = 3 * TILE
        y0 = f.box.centery
        run(world, 240)
        self.assertLess(abs(f.box.centery - y0), 60)


class ShooterTests(unittest.TestCase):
    def test_telegraphs_then_fires(self):
        world, s = world_with(Shooter, 15)
        run(world, 5)
        windup_seen = False
        for _ in range(int(3.5 / DT)):
            run(world, 1)
            windup_seen = windup_seen or s.windup_progress > 0
            if world.projectiles:
                break
        self.assertTrue(windup_seen)
        self.assertTrue(world.projectiles)
        self.assertIn("shoot", [e.kind for e in world.events])

    def test_wall_prevents_firing(self):
        rows = arena(edits=[(9, y, "#") for y in range(1, 11)])
        world, s = world_with(Shooter, 15, rows=rows)
        run(world, int(4 / DT))
        self.assertFalse(world.projectiles)


class ProjectileTests(unittest.TestCase):
    def test_hits_player_and_disappears(self):
        world = make_world()
        p = world.player
        run(world, 30)
        proj = Projectile(p.box.centerx - 40, p.box.centery, 300, 0, 10)
        world.projectiles.append(proj)
        run(world, 60)
        self.assertEqual(p.health.hp, 90)
        self.assertFalse(proj.alive)

    def test_dash_dodges_projectile(self):
        world = make_world()
        p = world.player
        run(world, 30)
        proj = Projectile(p.box.centerx - 30, p.box.centery, 300, 0, 10)
        world.projectiles.append(proj)
        run(world, 1, dash_pressed=True, move_x=1.0)
        run(world, 12, move_x=1.0)
        self.assertEqual(p.health.hp, 100)

    def test_dies_on_wall(self):
        world = make_world(arena(edits=[(10, y, "#") for y in range(1, 11)]))
        proj = Projectile(9 * TILE, 5 * TILE, 400, 0, 10)
        world.projectiles.append(proj)
        run(world, 60)
        self.assertFalse(proj.alive)
        self.assertIn("proj_hit", [e.kind for e in world.events])

    def test_reflected_projectile_kills_shooter(self):
        world, s = world_with(Shooter, 20)
        proj = Projectile(world.player.box.centerx, 5 * TILE, -400, 0, 10)
        proj.reflect()
        proj.box.x, proj.box.y = s.box.x - 40, s.box.centery
        proj.vx, proj.vy = 400, 0
        world.projectiles.append(proj)
        hp = s.health.hp
        run(world, 40)
        self.assertLess(s.health.hp, hp)
        self.assertEqual(proj.owner, "player")


class EnemyHurtTests(unittest.TestCase):
    def test_knockback_stagger_and_death(self):
        world, w = world_with(Walker, 12)
        died = w.hurt(10, w.box.centerx - 20, 200, 0.3, world)
        self.assertFalse(died)
        self.assertGreater(w.vx, 0)
        self.assertGreater(w.stagger, 0)
        self.assertTrue(w.hurt(999, w.box.centerx, 200, 0.3, world))
        self.assertFalse(w.alive)


if __name__ == "__main__":
    unittest.main()
