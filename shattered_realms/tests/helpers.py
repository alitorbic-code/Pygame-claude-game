"""Shared builders for gameplay tests."""
import random

from srealms.entities.player import PlayerInput
from srealms.physics import TILE, TileMap
from srealms.world import World

DT = 1 / 120


def arena(width=30, height=12, edits=None):
    """Empty room with a solid floor on the bottom row; the player 'P' stands at tile (3, height-2)."""
    rows = [[" "] * width for _ in range(height)]
    rows[-1] = ["#"] * width
    rows[height - 2][3] = "P"
    for x, y, ch in edits or ():
        rows[y][x] = ch
    return ["".join(r) for r in rows]


def make_world(rows=None, seed=1):
    return World(TileMap(rows or arena()), rng=random.Random(seed))


def run(world, steps, **inp):
    """Advance the world; edge flags (…_pressed) apply to the first step only."""
    edges = {k: v for k, v in inp.items() if k.endswith("_pressed")}
    held = {k: v for k, v in inp.items() if not k.endswith("_pressed")}
    for i in range(steps):
        world.update(DT, PlayerInput(**held, **(edges if i == 0 else {})))


def floor_y(rows):
    return (len(rows) - 1) * TILE
