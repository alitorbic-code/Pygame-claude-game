"""Pure-Python AABB physics and tile map (no pygame dependency, fully unit-testable)."""
from __future__ import annotations

import math
from dataclasses import dataclass

TILE = 32
EMPTY, SOLID, ONEWAY, HAZARD = 0, 1, 2, 3
_TILE_CHARS = {"#": SOLID, "=": ONEWAY, "^": HAZARD}
SPAWN_CHARS = frozenset("PwfsX")
MAX_STEP = 12.0  # largest distance moved per collision sub-step (prevents tunneling)
EPS = 1e-4


def approach(value: float, target: float, delta: float) -> float:
    """Move value toward target by at most delta."""
    if value < target:
        return min(value + delta, target)
    return max(value - delta, target)


def sign(value: float) -> int:
    return 1 if value > 0 else (-1 if value < 0 else 0)


def _span(low: float, high: float) -> range:
    return range(math.floor(low / TILE), math.floor((high - EPS) / TILE) + 1)


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def centerx(self) -> float:
        return self.x + self.w / 2

    @property
    def centery(self) -> float:
        return self.y + self.h / 2

    def overlaps(self, other: "Box") -> bool:
        return (self.x < other.right and self.right > other.x
                and self.y < other.bottom and self.bottom > other.y)

    def copy(self) -> "Box":
        return Box(self.x, self.y, self.w, self.h)


@dataclass
class Collision:
    on_floor: bool = False
    hit_ceiling: bool = False
    hit_left: bool = False
    hit_right: bool = False
    hazard: bool = False


class TileMap:
    """Grid of tiles parsed from text rows.

    '#' solid, '=' one-way platform, '^' spikes, ' ' or '.' empty. The characters
    in SPAWN_CHARS mark entity spawns and leave an empty tile behind.
    """

    def __init__(self, rows: list[str]) -> None:
        if not rows or not rows[0]:
            raise ValueError("Tile map needs at least one non-empty row")
        width = len(rows[0])
        if any(len(row) != width for row in rows):
            raise ValueError("Tile map rows must all be the same length")
        self.width = width
        self.height = len(rows)
        self.tiles = [[EMPTY] * width for _ in rows]
        self.spawns: list[tuple[str, int, int]] = []
        for ty, row in enumerate(rows):
            for tx, char in enumerate(row):
                if char in _TILE_CHARS:
                    self.tiles[ty][tx] = _TILE_CHARS[char]
                elif char in SPAWN_CHARS:
                    self.spawns.append((char, tx, ty))
                elif char not in " .":
                    raise ValueError(f"Unknown tile character {char!r} at ({tx}, {ty})")

    @property
    def pixel_w(self) -> int:
        return self.width * TILE

    @property
    def pixel_h(self) -> int:
        return self.height * TILE

    def tile_at(self, tx: int, ty: int) -> int:
        """Side walls and the ceiling are solid; below the map is open void."""
        if tx < 0 or tx >= self.width or ty < 0:
            return SOLID
        if ty >= self.height:
            return EMPTY
        return self.tiles[ty][tx]

    def tile_at_pixel(self, px: float, py: float) -> int:
        return self.tile_at(math.floor(px / TILE), math.floor(py / TILE))

    def solid_at_pixel(self, px: float, py: float) -> bool:
        return self.tile_at_pixel(px, py) == SOLID

    def standable_at_pixel(self, px: float, py: float) -> bool:
        return self.tile_at_pixel(px, py) in (SOLID, ONEWAY)

    def solid_overlap(self, box: Box) -> bool:
        for ty in _span(box.top, box.bottom):
            for tx in _span(box.left, box.right):
                if self.tile_at(tx, ty) == SOLID:
                    return True
        return False

    def hazard_overlap(self, box: Box) -> bool:
        for ty in _span(box.top, box.bottom):
            for tx in _span(box.left, box.right):
                if self.tile_at(tx, ty) == HAZARD:
                    spikes = Box(tx * TILE + 4, ty * TILE + 14, TILE - 8, TILE - 14)
                    if box.overlaps(spikes):
                        return True
        return False

    def line_clear(self, x0: float, y0: float, x1: float, y1: float, step: float = 8.0) -> bool:
        """True if no solid tile lies on the straight line between two pixel points."""
        steps = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / step))
        for i in range(steps + 1):
            t = i / steps
            if self.solid_at_pixel(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t):
                return False
        return True

    def move(self, box: Box, dx: float, dy: float, drop_through: bool = False) -> Collision:
        """Move a box, resolving collisions axis by axis in small sub-steps."""
        result = Collision()
        steps = max(1, math.ceil(max(abs(dx), abs(dy)) / MAX_STEP))
        step_x, step_y = dx / steps, dy / steps
        for _ in range(steps):
            if step_x:
                self._move_x(box, step_x, result)
            if step_y:
                self._move_y(box, step_y, result, drop_through)
        result.hazard = self.hazard_overlap(box)
        return result

    def _move_x(self, box: Box, step: float, result: Collision) -> None:
        box.x += step
        for ty in _span(box.top, box.bottom):
            for tx in _span(box.left, box.right):
                if self.tile_at(tx, ty) == SOLID:
                    if step > 0:
                        box.x = tx * TILE - box.w
                        result.hit_right = True
                    else:
                        box.x = (tx + 1) * TILE
                        result.hit_left = True
                    return

    def _move_y(self, box: Box, step: float, result: Collision, drop_through: bool) -> None:
        previous_bottom = box.bottom
        box.y += step
        for tx in _span(box.left, box.right):
            for ty in _span(box.top, box.bottom):
                tile = self.tile_at(tx, ty)
                if tile == SOLID:
                    if step > 0:
                        box.y = ty * TILE - box.h
                        result.on_floor = True
                    else:
                        box.y = (ty + 1) * TILE
                        result.hit_ceiling = True
                    return
                if (tile == ONEWAY and step > 0 and not drop_through
                        and previous_bottom <= ty * TILE + 1e-3):
                    box.y = ty * TILE - box.h
                    result.on_floor = True
                    return
