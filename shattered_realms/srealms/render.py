"""World rendering with procedural art: pre-baked tile layer plus per-frame entities."""
from __future__ import annotations

import math
import pygame

from . import config
from .camera import Camera
from .config import Palette
from .entities.enemies import Enemy, Flyer, Shooter, Walker
from .entities.player import Player
from .physics import EMPTY, HAZARD, ONEWAY, SOLID, TILE, TileMap
from .world import World

WHITE = (255, 255, 255)


class TileRenderer:
    """Renders the whole tile map once; each frame only blits the visible window."""

    FILL = (34, 30, 62)
    INNER = (46, 41, 82)
    EDGE = (130, 96, 255)
    PLANK = (90, 200, 255)
    SPIKE = (255, 90, 110)

    def __init__(self, tilemap: TileMap) -> None:
        self.surface = pygame.Surface((tilemap.pixel_w, tilemap.pixel_h), pygame.SRCALPHA)
        for ty in range(tilemap.height):
            for tx in range(tilemap.width):
                tile = tilemap.tiles[ty][tx]
                if tile == EMPTY:
                    continue
                rect = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
                if tile == SOLID:
                    self._draw_solid(tilemap, tx, ty, rect)
                elif tile == ONEWAY:
                    pygame.draw.rect(self.surface, self.PLANK, (rect.x, rect.y, TILE, 7), border_radius=3)
                    pygame.draw.rect(self.surface, self.FILL, (rect.x + 2, rect.y + 7, TILE - 4, 5))
                elif tile == HAZARD:
                    for i in range(2):
                        bx = rect.x + i * 16
                        pygame.draw.polygon(self.surface, self.SPIKE,
                                            [(bx + 1, rect.bottom), (bx + 8, rect.bottom - 18), (bx + 15, rect.bottom)])

    def _draw_solid(self, tilemap: TileMap, tx: int, ty: int, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.surface, self.FILL, rect)
        pygame.draw.rect(self.surface, self.INNER, rect.inflate(-6, -6), border_radius=4)
        if tilemap.tile_at(tx, ty - 1) != SOLID:
            pygame.draw.line(self.surface, self.EDGE, rect.topleft, (rect.right - 1, rect.top), 3)
        if tilemap.tile_at(tx - 1, ty) != SOLID:
            pygame.draw.line(self.surface, self.EDGE, rect.topleft, (rect.left, rect.bottom - 1), 2)
        if tilemap.tile_at(tx + 1, ty) != SOLID:
            pygame.draw.line(self.surface, self.EDGE, (rect.right - 1, rect.top), (rect.right - 1, rect.bottom - 1), 2)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        view = pygame.Rect(int(camera.x), int(camera.y), config.BASE_W, config.BASE_H)
        area = view.clip(self.surface.get_rect())
        if area.width > 0 and area.height > 0:
            surface.blit(self.surface, (area.x - view.x, area.y - view.y), area)


class WorldRenderer:
    def __init__(self, tilemap: TileMap) -> None:
        self.tiles = TileRenderer(tilemap)
        self.trail: list[list] = []  # dash afterimages: [x, y, w, h, life]

    def update(self, dt: float, player: Player) -> None:
        if player.dash_timer > 0:
            self.trail.append([player.box.x, player.box.y, player.box.w, player.box.h, 0.22])
        for item in self.trail:
            item[4] -= dt
        self.trail = [item for item in self.trail if item[4] > 0]

    def draw(self, surface: pygame.Surface, world: World, camera: Camera, time: float,
             debug: bool = False) -> None:
        self.tiles.draw(surface, camera)
        self._draw_exit(surface, world, camera, time)
        for item in self.trail:
            fade = item[4] / 0.22
            color = (int(60 * fade), int(150 * fade), int(210 * fade))
            pygame.draw.rect(surface, color, (item[0] - camera.x, item[1] - camera.y, item[2], item[3]), border_radius=6)
        for enemy in world.enemies:
            if camera.is_visible(enemy.box.x, enemy.box.y, enemy.box.w, enemy.box.h):
                self._draw_enemy(surface, enemy, camera, time)
        for proj in world.projectiles:
            self._draw_projectile(surface, proj, camera, time)
        self._draw_player(surface, world.player, camera, time)
        if debug:
            self._draw_debug(surface, world, camera)

    # -- entities ----------------------------------------------------------
    def _draw_exit(self, surface: pygame.Surface, world: World, camera: Camera, time: float) -> None:
        box = world.exit_box
        if box is None:
            return
        x, y = box.x - camera.x, box.y - camera.y
        rect = pygame.Rect(int(x), int(y), int(box.w), int(box.h))
        if world.exit_open:
            pulse = 0.6 + 0.4 * math.sin(time * 4)
            for grow, bright in ((10, 0.25), (4, 0.5), (0, 1.0)):
                color = tuple(int(c * bright * pulse) for c in Palette.GOLD)
                pygame.draw.ellipse(surface, color, rect.inflate(grow * 2, grow * 2), 0 if grow == 0 else 3)
        else:
            pygame.draw.ellipse(surface, (70, 60, 100), rect, 3)
            pygame.draw.line(surface, (70, 60, 100), rect.midleft, rect.midright, 2)

    def _draw_player(self, surface: pygame.Surface, p: Player, camera: Camera, time: float) -> None:
        x, y = p.box.x - camera.x, p.box.y - camera.y
        if p.alive and p.health.invuln > 0 and p.dash_timer <= 0 and int(time * 18) % 2 == 0:
            return  # i-frame flicker
        cx, f = x + p.W / 2, p.facing
        body = (150, 150, 170) if not p.alive else (WHITE if p.health.flash > 0 else (70, 190, 255))
        dark = (30, 90, 150)
        sway = max(-14.0, min(14.0, -p.vx * 0.04))
        pygame.draw.polygon(surface, dark, [(cx - f * 7, y + 14), (cx - f * 7, y + 28),
                                            (cx - f * 20 + sway, y + 36 + math.sin(time * 9) * 2)])
        pygame.draw.rect(surface, body, (x, y + 12, p.W, p.H - 12), border_radius=6)
        pygame.draw.circle(surface, body, (int(cx), int(y + 10)), 10)
        pygame.draw.rect(surface, WHITE if p.alive else (60, 60, 70), (cx + (1 if f > 0 else -8), y + 7, 7, 4))
        if p.wall_sliding:
            pygame.draw.line(surface, WHITE, (cx + p.wall_dir * 13, y + 6), (cx + p.wall_dir * 13, y + 30), 2)
        spec = p.current_attack
        if spec and p.attack_time >= spec.windup * 0.5:
            self._draw_slash(surface, p, spec, cx, y + p.H / 2)

    def _draw_slash(self, surface: pygame.Surface, p: Player, spec, cx: float, cy: float) -> None:
        progress = max(0.0, min(1.0, (p.attack_time - spec.windup) / (spec.active + 0.08)))
        fade = 1.0 - progress
        if fade <= 0:
            return
        outer = spec.reach + p.W / 2
        inner = outer * 0.62
        span = math.radians(55 + 10 * p.combo_step)
        center = 0.0 if p.facing > 0 else math.pi
        outer_pts, inner_pts = [], []
        for i in range(9):
            a = center - span + 2 * span * i / 8
            outer_pts.append((cx + math.cos(a) * outer, cy + math.sin(a) * outer))
            inner_pts.append((cx + math.cos(a) * inner, cy + math.sin(a) * inner))
        base = Palette.GOLD if p.combo_step == 2 else (190, 235, 255)
        pygame.draw.polygon(surface, tuple(int(c * fade) for c in base), outer_pts + inner_pts[::-1])

    def _draw_enemy(self, surface: pygame.Surface, e: Enemy, camera: Camera, time: float) -> None:
        x, y = e.box.x - camera.x, e.box.y - camera.y
        flash = e.health.flash > 0
        cx, cy, f = x + e.W / 2, y + e.H / 2, e.facing
        if isinstance(e, Walker):
            body = WHITE if flash else (200, 90, 80)
            bob = abs(math.sin(e.age * 8)) * 2 if e.on_floor and abs(e.vx) > 5 else 0
            pygame.draw.rect(surface, body, (x, y + 4 - bob, e.W, e.H - 4), border_radius=8)
            pygame.draw.rect(surface, (90, 30, 40), (x + 2, y + e.H - 8, e.W - 4, 6), border_radius=3)
            pygame.draw.circle(surface, WHITE, (int(cx + f * 6), int(y + 12 - bob)), 4)
            pygame.draw.circle(surface, (20, 10, 20), (int(cx + f * 7), int(y + 12 - bob)), 2)
            if e.state == "chase":
                pygame.draw.line(surface, (255, 220, 120), (cx - 8, y - 6), (cx + 8, y - 6), 3)
        elif isinstance(e, Flyer):
            body = WHITE if flash else (170, 110, 255)
            flap = math.sin(e.age * 18) * 8
            pygame.draw.polygon(surface, (110, 70, 190), [(cx, cy), (cx - 22, cy - 6 - flap), (cx - 10, cy + 4)])
            pygame.draw.polygon(surface, (110, 70, 190), [(cx, cy), (cx + 22, cy - 6 - flap), (cx + 10, cy + 4)])
            pygame.draw.polygon(surface, body, [(cx, cy - 12), (cx + 13, cy), (cx, cy + 12), (cx - 13, cy)])
            pygame.draw.circle(surface, (255, 80, 120) if e.state == "hunt" else WHITE, (int(cx + f * 3), int(cy)), 3)
        elif isinstance(e, Shooter):
            body = WHITE if flash else (90, 200, 130)
            pygame.draw.rect(surface, (40, 90, 70), (x - 2, y + e.H - 10, e.W + 4, 10), border_radius=3)
            pygame.draw.rect(surface, body, (x + 2, y + 4, e.W - 4, e.H - 12), border_radius=8)
            pygame.draw.rect(surface, (30, 60, 50), (cx if f > 0 else cx - 15, cy - 6, 15, 8))
            charge = e.windup_progress
            if charge > 0:
                color = (255, int(220 - 140 * charge), 80)
                pygame.draw.circle(surface, color, (int(cx + f * 16), int(cy - 2)), int(3 + 8 * charge))
        if e.health.hp < e.health.max_hp:
            pygame.draw.rect(surface, (50, 20, 30), (x, y - 12, e.W, 5))
            pygame.draw.rect(surface, (255, 90, 110), (x, y - 12, e.W * e.health.fraction, 5))

    def _draw_projectile(self, surface: pygame.Surface, proj, camera: Camera, time: float) -> None:
        cx, cy = int(proj.x - camera.x), int(proj.y - camera.y)
        color = Palette.CYAN if proj.owner == "player" else (255, 130, 90)
        pygame.draw.circle(surface, tuple(c // 3 for c in color), (cx, cy), 10)
        pygame.draw.circle(surface, color, (cx, cy), 6 + int(math.sin(time * 20)))
        pygame.draw.circle(surface, WHITE, (cx, cy), 3)

    def _draw_debug(self, surface: pygame.Surface, world: World, camera: Camera) -> None:
        def outline(box, color):
            pygame.draw.rect(surface, color, (box.x - camera.x, box.y - camera.y, box.w, box.h), 1)

        outline(world.player.box, (120, 255, 160))
        hitbox = world.player.attack_hitbox()
        if hitbox:
            outline(hitbox, (255, 80, 80))
        for enemy in world.enemies:
            outline(enemy.box, (255, 200, 80))
        for proj in world.projectiles:
            outline(proj.box, (255, 120, 255))
