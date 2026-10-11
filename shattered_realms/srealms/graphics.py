"""Procedural graphics: gradient/parallax void background, vignette, particle system."""
from __future__ import annotations

import math
import random
from typing import Sequence

import pygame

from . import config
from .config import Palette
from .ui import draw_text

Color = tuple[int, int, int]


def vertical_gradient(size: tuple[int, int], top: Color, bottom: Color) -> pygame.Surface:
    width, height = size
    surface = pygame.Surface(size)
    for y in range(height):
        f = y / max(1, height - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * f) for i in range(3))
        pygame.draw.line(surface, color, (0, y), (width, y))
    return surface


def make_vignette(size: tuple[int, int], strength: int = 150, steps: int = 48) -> pygame.Surface:
    width, height = size
    surface = pygame.Surface(size, pygame.SRCALPHA)
    for i in range(steps):
        alpha = int(strength * (1.0 - i / steps) ** 2)
        rect = pygame.Rect(i * 4, i * 3, width - i * 8, height - i * 6)
        pygame.draw.rect(surface, (0, 0, 0, alpha), rect, width=4)
    return surface


class VoidBackground:
    """Gradient sky with drifting twinkling stars and slowly rotating crystal shards."""

    STAR_COUNT = 150
    SHARD_COUNT = 12

    def __init__(
        self,
        size: tuple[int, int] = (config.BASE_W, config.BASE_H),
        seed: int = 0,
        top: Color = Palette.BG_TOP,
        bottom: Color = Palette.BG_BOTTOM,
        accent: Color = Palette.VOID_PURPLE,
    ) -> None:
        self.size = size
        self.accent = accent
        self.time = 0.0
        rng = random.Random(seed)
        width, height = size
        self.gradient = vertical_gradient(size, top, bottom)
        self.vignette = make_vignette(size)
        self.stars = [
            [rng.uniform(0, width), rng.uniform(0, height), rng.uniform(0.15, 1.0), rng.uniform(0, math.tau)]
            for _ in range(self.STAR_COUNT)
        ]
        self.shards = [
            {
                "x": rng.uniform(0, width),
                "y": rng.uniform(40, height - 40),
                "r": rng.uniform(18, 90),
                "angle": rng.uniform(0, math.tau),
                "spin": rng.uniform(-0.4, 0.4),
                "speed": rng.uniform(6, 24),
                "sides": rng.randint(3, 6),
                "depth": rng.uniform(0.3, 1.0),
            }
            for _ in range(self.SHARD_COUNT)
        ]

    def update(self, dt: float) -> None:
        self.time += dt
        width = self.size[0]
        for star in self.stars:
            star[0] = (star[0] - 12.0 * star[2] * dt) % width
        for shard in self.shards:
            shard["x"] -= shard["speed"] * dt
            shard["angle"] += shard["spin"] * dt
            if shard["x"] < -shard["r"]:
                shard["x"] = width + shard["r"]

    def draw(self, surface: pygame.Surface, scroll_x: float = 0.0) -> None:
        width = self.size[0]
        surface.blit(self.gradient, (0, 0))
        for x, y, depth, phase in self.stars:
            twinkle = 0.6 + 0.4 * math.sin(self.time * 1.5 + phase)
            v = min(255, int(200 * depth * twinkle) + 30)
            px = int((x - scroll_x * depth) % width)
            size = 2 if depth > 0.7 else 1
            surface.fill((v, v, min(255, v + 40)), (px, int(y), size, size))
        for shard in self.shards:
            color = tuple(int(c * shard["depth"] * 0.65) for c in self.accent)
            points = []
            for k in range(shard["sides"]):
                a = shard["angle"] + math.tau * k / shard["sides"]
                points.append((shard["x"] - scroll_x * shard["depth"] * 0.3 + math.cos(a) * shard["r"],
                               shard["y"] + math.sin(a) * shard["r"]))
            pygame.draw.polygon(surface, color, points, 2)
        surface.blit(self.vignette, (0, 0))


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "color", "gravity", "drag")

    def __init__(self, x: float, y: float, vx: float, vy: float, life: float, size: float,
                 color: Color, gravity: float, drag: float) -> None:
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.size, self.color, self.gravity, self.drag = size, color, gravity, drag


class ParticleSystem:
    """Capped particle pool; fades particles toward black, which suits the dark palette."""

    def __init__(self, limit: int = config.MAX_PARTICLES) -> None:
        self.limit = limit
        self._items: list[Particle] = []

    def __len__(self) -> int:
        return len(self._items)

    def emit(self, x: float, y: float, count: int, color: Color,
             speed: Sequence[float] = (40.0, 160.0), life: Sequence[float] = (0.4, 1.0),
             size: Sequence[float] = (2.0, 5.0), angle: float = 0.0, spread: float = math.tau,
             gravity: float = 0.0, drag: float = 0.0) -> None:
        room = max(0, self.limit - len(self._items))
        for _ in range(min(count, room)):
            a = angle + random.uniform(-spread / 2, spread / 2)
            v = random.uniform(*speed)
            lifetime = random.uniform(*life)
            self._items.append(Particle(x, y, math.cos(a) * v, math.sin(a) * v, lifetime,
                                        random.uniform(*size), color, gravity, drag))

    def update(self, dt: float) -> None:
        alive = []
        for p in self._items:
            p.life -= dt
            if p.life <= 0:
                continue
            if p.drag:
                damp = max(0.0, 1.0 - p.drag * dt)
                p.vx *= damp
                p.vy *= damp
            p.vy += p.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            alive.append(p)
        self._items = alive

    def draw(self, surface: pygame.Surface, offset: tuple[float, float] = (0.0, 0.0)) -> None:
        ox, oy = offset
        for p in self._items:
            ratio = p.life / p.max_life
            color = (int(p.color[0] * ratio), int(p.color[1] * ratio), int(p.color[2] * ratio))
            pygame.draw.circle(surface, color, (int(p.x + ox), int(p.y + oy)),
                               max(1, int(p.size * (0.4 + 0.6 * ratio))))


class FloatingTexts:
    """Rising, fading combat text (damage numbers, callouts) in world coordinates."""

    def __init__(self, limit: int = 60) -> None:
        self.limit = limit
        self._items: list[list] = []  # [x, y, text, color, life, max_life, size]

    def __len__(self) -> int:
        return len(self._items)

    def add(self, x: float, y: float, text: str, color: Color, size: int = 30, life: float = 0.9) -> None:
        if len(self._items) >= self.limit:
            del self._items[0]
        self._items.append([x + random.uniform(-8, 8), y, text, color, life, life, size])

    def update(self, dt: float) -> None:
        for item in self._items:
            item[1] -= 55.0 * dt
            item[4] -= dt
        self._items = [item for item in self._items if item[4] > 0]

    def draw(self, surface: pygame.Surface, offset: tuple[float, float]) -> None:
        for x, y, text, color, life, max_life, size in self._items:
            alpha = int(255 * min(1.0, life / (max_life * 0.4)))
            draw_text(surface, text, size, color, (x + offset[0], y + offset[1]), "center", True, alpha)
