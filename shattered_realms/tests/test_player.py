import unittest

from srealms.entities.player import ATTACKS, Player, PlayerInput
from srealms.physics import TILE

from .helpers import DT, arena, floor_y, make_world, run


def settled(rows=None):
    world = make_world(rows)
    run(world, 30)
    return world, world.player


class GroundTests(unittest.TestCase):
    def test_settles_on_floor(self):
        world, p = settled()
        self.assertTrue(p.on_floor)
        self.assertAlmostEqual(p.box.bottom, floor_y(arena()), places=2)

    def test_run_speed_and_facing(self):
        world, p = settled()
        run(world, 120, move_x=1.0)
        self.assertGreater(p.vx, p.RUN_SPEED * 0.9)
        self.assertEqual(p.facing, 1)
        run(world, 20, move_x=-1.0)
        self.assertEqual(p.facing, -1)

    def test_friction_stops_player(self):
        world, p = settled()
        run(world, 60, move_x=1.0)
        run(world, 60)
        self.assertAlmostEqual(p.vx, 0.0, places=3)


class JumpTests(unittest.TestCase):
    def apex(self, release_after=None):
        world, p = settled()
        start = p.box.bottom
        top = start
        for i in range(160):
            held = release_after is None or i < release_after
            world.update(DT, PlayerInput(jump_pressed=(i == 0), jump_held=held))
            top = min(top, p.box.bottom)
        return start - top

    def test_full_jump_height(self):
        self.assertTrue(95 <= self.apex() <= 115, self.apex())

    def test_releasing_jump_cuts_height(self):
        self.assertLess(self.apex(release_after=8), self.apex() * 0.75)

    def test_double_jump_once_only(self):
        world, p = settled()
        run(world, 1, jump_pressed=True, jump_held=True)
        run(world, 20, jump_held=True)
        run(world, 1, jump_pressed=True, jump_held=True)
        self.assertLess(p.vy, -400)
        self.assertEqual(p.air_jumps, 0)
        run(world, 5, jump_held=True)
        vy_before = p.vy
        run(world, 1, jump_pressed=True, jump_held=True)
        self.assertGreater(p.vy, vy_before)  # third jump does nothing

    def test_coyote_time_allows_late_jump(self):
        world, p = settled()
        p.on_floor = True
        run(world, 1)  # refresh coyote
        p.box.y -= 1.0  # step off the ground
        p.on_floor = False
        p.air_jumps = 0
        run(world, 1, jump_pressed=True, jump_held=True)
        self.assertLess(p.vy, -400)  # a real jump, not a (disabled) air jump


class WallTests(unittest.TestCase):
    def shaft(self):
        edits = [(10, y, "#") for y in range(1, 11)]  # wall at x=10, right of the player
        rows = arena(edits=edits)
        world = make_world(rows)
        p = world.player
        p.box.x = 10 * TILE - p.W - 0.5
        p.box.y = 4 * TILE
        p.vy = 0.0
        return world, p

    def test_wall_slide_caps_fall_speed(self):
        world, p = self.shaft()
        run(world, 60, move_x=1.0)
        self.assertTrue(p.wall_sliding)
        self.assertLessEqual(p.vy, p.WALL_SLIDE_SPEED + 1e-6)

    def test_wall_jump_pushes_away(self):
        world, p = self.shaft()
        run(world, 30, move_x=1.0)
        run(world, 1, move_x=1.0, jump_pressed=True, jump_held=True)
        self.assertLess(p.vx, 0)
        self.assertLess(p.vy, -300)
        self.assertEqual(p.facing, -1)
        kinds = [e.kind for e in world.drain_events()]
        self.assertIn("wall_jump", kinds)


class DashTests(unittest.TestCase):
    def test_dash_distance_and_invulnerability(self):
        world, p = settled()
        x0 = p.box.x
        run(world, 1, dash_pressed=True, move_x=1.0)
        self.assertTrue(p.invulnerable)
        run(world, int(p.DASH_TIME / DT) + 2, move_x=0.0)
        self.assertFalse(p.dash_timer > 0)
        self.assertGreater(p.box.x - x0, p.DASH_SPEED * p.DASH_TIME * 0.8)

    def test_dash_cooldown_and_single_air_dash(self):
        world, p = settled()
        run(world, 1, dash_pressed=True)
        run(world, 40)
        self.assertGreater(p.dash_cooldown, 0)
        run(world, 1, dash_pressed=True)
        self.assertEqual(p.dash_timer, 0)  # blocked by cooldown

    def test_dash_blocks_damage(self):
        world, p = settled()
        run(world, 1, dash_pressed=True)
        self.assertFalse(p.hurt(10, 0, world))
        self.assertEqual(p.health.hp, 100)


class AttackTests(unittest.TestCase):
    def test_three_hit_combo_cycles(self):
        world, p = settled()
        seen = []
        for _ in range(4):
            run(world, 1, attack_pressed=True)
            seen.append(p.combo_step)
            run(world, int(ATTACKS[p.combo_step].total / DT) + 2)
        self.assertEqual(seen, [0, 1, 2, 0])

    def test_hitbox_only_during_active_frames(self):
        world, p = settled()
        run(world, 1, attack_pressed=True)
        self.assertIsNone(p.attack_hitbox())  # windup
        spec = ATTACKS[0]
        run(world, int((spec.windup + 0.01) / DT))
        self.assertIsNotNone(p.attack_hitbox())
        run(world, int((spec.active + 0.02) / DT))
        self.assertIsNone(p.attack_hitbox())  # recovery

    def test_hitbox_extends_in_facing_direction(self):
        world, p = settled()
        p.facing = 1
        run(world, 1, attack_pressed=True, move_x=1.0)
        run(world, int(0.07 / DT), move_x=1.0)
        hb = p.attack_hitbox()
        self.assertGreater(hb.right, p.box.right)
        self.assertGreaterEqual(hb.left, p.box.left)

    def test_combo_resets_after_window(self):
        world, p = settled()
        run(world, 1, attack_pressed=True)
        run(world, int((ATTACKS[0].total + p.COMBO_WINDOW + 0.1) / DT))
        run(world, 1, attack_pressed=True)
        self.assertEqual(p.combo_step, 0)


class DamageTests(unittest.TestCase):
    def test_hurt_knockback_and_iframes(self):
        world, p = settled()
        self.assertTrue(p.hurt(20, source_x=p.box.centerx - 50, world=world))
        self.assertEqual(p.health.hp, 80)
        self.assertGreater(p.vx, 0)  # knocked away from the source
        self.assertFalse(p.hurt(20, p.box.centerx - 50, world))
        self.assertEqual(p.health.hp, 80)

    def test_death_reported_once(self):
        world, p = settled()
        p.hurt(500, 0, world)
        self.assertFalse(p.alive)
        run(world, 30)
        kinds = [e.kind for e in world.drain_events()]
        self.assertEqual(kinds.count("player_die"), 1)

    def test_spikes_damage_and_respawn_at_safe_spot(self):
        edits = [(8, 9, "^"), (9, 9, "^")]
        world = make_world(arena(edits=edits))
        p = world.player
        run(world, 60)
        safe = p.last_safe
        p.box.x = 8 * TILE + 4
        p.box.y = 10 * TILE - p.H - 2
        run(world, 5)
        self.assertEqual(p.health.hp, 100 - p.HAZARD_DAMAGE)
        self.assertAlmostEqual(p.box.centerx, safe[0], delta=2)

    def test_void_fall_respawns_with_damage(self):
        rows = arena()
        rows[-1] = rows[-1][:10] + " " * 6 + rows[-1][16:]
        world = make_world(rows)
        p = world.player
        run(world, 60)
        p.box.x = 12 * TILE
        p.box.y = 6 * TILE
        run(world, 300)
        self.assertEqual(p.health.hp, 100 - p.VOID_DAMAGE)
        self.assertTrue(p.alive)
        self.assertTrue(p.box.bottom < floor_y(rows) + 1)


if __name__ == "__main__":
    unittest.main()
