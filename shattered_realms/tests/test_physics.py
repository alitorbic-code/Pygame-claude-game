import unittest

from srealms.physics import EMPTY, HAZARD, ONEWAY, SOLID, TILE, Box, TileMap, approach, sign


def tilemap(*rows):
    return TileMap(list(rows))


class TileMapParsingTests(unittest.TestCase):
    def test_ragged_rows_rejected(self):
        with self.assertRaises(ValueError):
            tilemap("###", "##")

    def test_unknown_character_rejected(self):
        with self.assertRaises(ValueError):
            tilemap("#?#")

    def test_spawns_recorded_and_left_empty(self):
        tm = tilemap(" P ", "###")
        self.assertEqual(tm.spawns, [("P", 1, 0)])
        self.assertEqual(tm.tile_at(1, 0), EMPTY)

    def test_out_of_bounds_rules(self):
        tm = tilemap("   ", "###")
        self.assertEqual(tm.tile_at(-1, 0), SOLID)
        self.assertEqual(tm.tile_at(3, 0), SOLID)
        self.assertEqual(tm.tile_at(0, -1), SOLID)
        self.assertEqual(tm.tile_at(0, 2), EMPTY)  # void below the map

    def test_tile_kinds(self):
        tm = tilemap("#=^")
        self.assertEqual([tm.tile_at(i, 0) for i in range(3)], [SOLID, ONEWAY, HAZARD])


class MovementTests(unittest.TestCase):
    def setUp(self):
        self.tm = tilemap(*(["          "] * 3 + ["##########"]))  # floor top at y = 96

    def test_lands_flush_on_floor(self):
        box = Box(100, 0, 20, 40)
        result = self.tm.move(box, 0, 200)
        self.assertTrue(result.on_floor)
        self.assertAlmostEqual(box.bottom, 3 * TILE)

    def test_stops_flush_against_wall(self):
        tm = tilemap("      #   ", "##########")
        box = Box(100, 0, 20, 20)
        result = tm.move(box, 300, 0)
        self.assertTrue(result.hit_right)
        self.assertAlmostEqual(box.right, 6 * TILE)

    def test_ceiling_blocks_upward_movement(self):
        tm = tilemap("##########", "          ", "          ", "##########")
        box = Box(100, 60, 20, 30)
        result = tm.move(box, 0, -200)
        self.assertTrue(result.hit_ceiling)
        self.assertAlmostEqual(box.top, TILE)

    def test_no_tunneling_at_high_speed(self):
        box = Box(100, 0, 20, 40)
        result = self.tm.move(box, 0, 2000)
        self.assertTrue(result.on_floor)
        self.assertLessEqual(box.bottom, 3 * TILE + 1e-6)

    def test_world_edges_contain_boxes(self):
        box = Box(5, 10, 20, 20)
        self.tm.move(box, -500, 0)
        self.assertGreaterEqual(box.left, 0)

    def test_oneway_allows_passing_up_and_landing_from_above(self):
        tm = tilemap("          ", "          ", "   ====   ", "          ", "          ", "##########")
        box = Box(3 * TILE + 4, 4 * TILE, 20, 30)
        up = tm.move(box, 0, -100)
        self.assertFalse(up.hit_ceiling)
        self.assertLess(box.bottom, 2 * TILE + 40)
        box = Box(3 * TILE + 4, 0, 20, 30)
        down = tm.move(box, 0, 100)
        self.assertTrue(down.on_floor)
        self.assertAlmostEqual(box.bottom, 2 * TILE)

    def test_oneway_drop_through(self):
        tm = tilemap("          ", "   ====   ", "          ", "          ", "##########")
        box = Box(3 * TILE + 4, TILE - 30, 20, 30)  # standing on the platform
        result = tm.move(box, 0, 40, drop_through=True)
        self.assertFalse(result.on_floor)
        self.assertGreater(box.bottom, TILE + 10)

    def test_hazard_detected_only_on_spike_area(self):
        tm = tilemap("   ", " ^ ", "###")
        low = Box(TILE + 6, TILE + 10, 18, 22)
        self.assertTrue(tm.hazard_overlap(low))
        high = Box(TILE + 6, 0, 18, 24)  # above the spikes' tips
        self.assertFalse(tm.hazard_overlap(high))

    def test_line_clear(self):
        tm = tilemap("   #   ", "#######")
        self.assertFalse(tm.line_clear(10, 10, 6 * TILE, 10))
        self.assertTrue(tm.line_clear(10, 10, 2 * TILE, 10))


class HelperTests(unittest.TestCase):
    def test_approach_and_sign(self):
        self.assertEqual(approach(0, 10, 3), 3)
        self.assertEqual(approach(9, 10, 3), 10)
        self.assertEqual(approach(5, -10, 3), 2)
        self.assertEqual((sign(-4), sign(0), sign(2.5)), (-1, 0, 1))


if __name__ == "__main__":
    unittest.main()
