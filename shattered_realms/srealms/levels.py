"""Hand-built levels, assembled with a tiny builder so rows are always the right length."""
from __future__ import annotations

from .physics import TileMap


class LevelBuilder:
    def __init__(self, width: int, height: int) -> None:
        self.width, self.height = width, height
        self.grid = [[" "] * width for _ in range(height)]

    def put(self, x: int, y: int, char: str) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = char

    def rect(self, x: int, y: int, w: int, h: int, char: str = "#") -> None:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.put(xx, yy, char)

    def hline(self, x: int, y: int, length: int, char: str) -> None:
        self.rect(x, y, length, 1, char)

    def rows(self) -> list[str]:
        return ["".join(row) for row in self.grid]


def build_proving_grounds() -> TileMap:
    """The Phase 2 test level: platforming, a wall shaft, spikes, and nine guardians."""
    b = LevelBuilder(80, 30)
    b.rect(0, 0, 80, 1)            # ceiling
    b.rect(0, 0, 1, 30)            # left wall
    b.rect(79, 0, 1, 30)           # right wall
    b.rect(0, 27, 80, 3)           # ground
    b.rect(26, 27, 4, 3, " ")      # pit

    b.hline(8, 24, 5, "=")         # staircase of one-way platforms
    b.hline(14, 21, 5, "=")
    b.hline(20, 18, 5, "=")
    b.hline(44, 26, 3, "^")        # spike patch
    b.rect(50, 24, 7, 3)           # raised block

    b.rect(60, 12, 1, 13)          # wall shaft: two walls with a crawl-space underneath
    b.rect(65, 12, 1, 13)
    b.hline(66, 12, 8, "=")        # reward ledge above the right wall

    b.hline(72, 24, 4, "=")        # alternate route up to the ledge
    b.hline(76, 21, 3, "=")
    b.hline(72, 18, 4, "=")
    b.hline(68, 15, 4, "=")

    for char, x, y in (
        ("P", 3, 26),
        ("w", 15, 26), ("w", 38, 26), ("w", 68, 26),
        ("f", 21, 15), ("f", 47, 18), ("f", 68, 9),
        ("s", 22, 17), ("s", 54, 23), ("s", 70, 11),
        ("X", 77, 26),
    ):
        b.put(x, y, char)
    return TileMap(b.rows())
