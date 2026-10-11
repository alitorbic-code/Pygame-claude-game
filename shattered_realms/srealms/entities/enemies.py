"""Enemy types with simple, readable AI. Pure logic; rendering lives in render.py."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ..combat import Health
from ..physics import Box, approach
from .projectile import Projectile

if TYPE_CHECKING:
    from ..world import World


class Enemy:
    kind = "enemy"
    W = 28.0
    H = 28.0
    MAX_HP = 30
    ARMOR = 0
    CONTACT_DAMAGE = 10
    GRAVITY = 1900.0
    KNOCK_RESIST = 0.0  # 0 = full knockback, 1 = immovable
    FLIES = False

    def __init__(self, x: float, y: float) -> None:
        """x, y is the position of the feet (bottom center)."""
        self.box = Box(x - self.W / 2, y - self.H, self.W, self.H)
        self.vx = 0.0
        self.vy = 0.0
        self.facing = -1
        self.health = Health(self.MAX_HP)
        self.stagger = 0.0
        self.on_floor = False
        self.alive = True
        self.age = 0.0
        self.state = "idle"
        self.state_time = 0.0

    def hurt(self, amount: float, source_x: float, knockback: float, stagger: float,
             world: "World") -> bool:
        """Apply a hit; returns True if this killed the enemy."""
        if self.health.damage(amount) <= 0:
            return False
        scale = 1.0 - self.KNOCK_RESIST
        direction = 1 if self.box.centerx >= source_x else -1
        self.vx = direction * knockback * scale
        self.vy = -knockback * 0.3 * scale
        self.stagger = stagger * max(0.2, scale)
        if not self.health.alive:
            self.alive = False
        return not self.alive

    def update(self, dt: float, world: "World") -> None:
        self.age += dt
        self.health.update(dt)
        if self.stagger > 0:
            self.stagger -= dt
        else:
            self.think(dt, world)
        self.physics(dt, world)

    def think(self, dt: float, world: "World") -> None:
        """Decide what to do this step (set velocities/state). Overridden per enemy."""

    def physics(self, dt: float, world: "World") -> None:
        if not self.FLIES:
            self.vy = min(self.vy + self.GRAVITY * dt, 900.0)
        result = world.tilemap.move(self.box, self.vx * dt, self.vy * dt)
        self.on_floor = result.on_floor
        if result.on_floor and self.vy > 0:
            self.vy = 0.0
        if result.hit_ceiling and self.vy < 0:
            self.vy = 0.0
        if (result.hit_left and self.vx < 0) or (result.hit_right and self.vx > 0):
            self.vx = 0.0
        if self.stagger > 0 and self.on_floor and not self.FLIES:
            self.vx = approach(self.vx, 0.0, 1400.0 * dt)
        if self.box.top > world.tilemap.pixel_h + 200:
            self.alive = False

    def sees_player(self, world: "World", max_dist: float, max_dy: float = 9999.0) -> bool:
        player = world.player
        if not player.alive:
            return False
        dx = player.box.centerx - self.box.centerx
        dy = player.box.centery - self.box.centery
        if math.hypot(dx, dy) > max_dist or abs(dy) > max_dy:
            return False
        return world.tilemap.line_clear(self.box.centerx, self.box.centery,
                                        player.box.centerx, player.box.centery)


class Walker(Enemy):
    """Patrols platforms, turns at walls and ledges, chases on sight."""
    kind = "walker"
    W, H = 30.0, 30.0
    MAX_HP = 30
    CONTACT_DAMAGE = 12
    PATROL_SPEED = 60.0
    CHASE_SPEED = 140.0
    SIGHT = 300.0

    def think(self, dt: float, world: "World") -> None:
        player = world.player
        if self.sees_player(world, self.SIGHT, max_dy=80.0):
            self.state = "chase"
            self.facing = 1 if player.box.centerx >= self.box.centerx else -1
            speed = self.CHASE_SPEED
        else:
            self.state = "patrol"
            speed = self.PATROL_SPEED
        if self.on_floor and self._edge_ahead(world):
            if self.state == "patrol":
                self.facing = -self.facing
            else:
                speed = 0.0
        self.vx = approach(self.vx, self.facing * speed, 1600.0 * dt)

    def _edge_ahead(self, world: "World") -> bool:
        front = self.box.centerx + self.facing * (self.W / 2 + 3)
        tilemap = world.tilemap
        return (tilemap.solid_at_pixel(front, self.box.centery)
                or not tilemap.standable_at_pixel(front, self.box.bottom + 4))


class Flyer(Enemy):
    """Hovers around its post, then swoops at the player on sight."""
    kind = "flyer"
    W, H = 28.0, 24.0
    MAX_HP = 20
    CONTACT_DAMAGE = 10
    GRAVITY = 0.0
    FLIES = True
    SIGHT = 380.0
    SPEED = 125.0

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y)
        self.home = (self.box.centerx, self.box.centery)

    def think(self, dt: float, world: "World") -> None:
        player = world.player
        if self.sees_player(world, self.SIGHT):
            self.state = "hunt"
            dx = player.box.centerx - self.box.centerx
            target_x = player.box.centerx
            target_y = player.box.centery if abs(dx) < 70 else player.box.centery - 60 + math.sin(self.age * 3) * 25
            speed = self.SPEED
        else:
            self.state = "hover"
            target_x = self.home[0] + math.sin(self.age * 0.9) * 80
            target_y = self.home[1] + math.sin(self.age * 1.7) * 24
            speed = self.SPEED * 0.5
        dx, dy = target_x - self.box.centerx, target_y - self.box.centery
        dist = math.hypot(dx, dy)
        scale = min(speed, dist * 3.0) / dist if dist > 1e-6 else 0.0
        self.vx = approach(self.vx, dx * scale, 520.0 * dt)
        self.vy = approach(self.vy, dy * scale, 520.0 * dt)
        if abs(self.vx) > 5:
            self.facing = 1 if self.vx > 0 else -1


class Shooter(Enemy):
    """Stationary turret-like enemy that telegraphs, then fires at the player."""
    kind = "shooter"
    W, H = 30.0, 34.0
    MAX_HP = 25
    CONTACT_DAMAGE = 8
    RANGE = 460.0
    COOLDOWN = 2.0
    WINDUP = 0.5
    PROJECTILE_SPEED = 300.0
    PROJECTILE_DAMAGE = 10

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y)
        self.cooldown = 1.0

    @property
    def windup_progress(self) -> float:
        return min(1.0, self.state_time / self.WINDUP) if self.state == "windup" else 0.0

    def think(self, dt: float, world: "World") -> None:
        player = world.player
        self.facing = 1 if player.box.centerx >= self.box.centerx else -1
        self.vx = approach(self.vx, 0.0, 1600.0 * dt)
        if self.state == "windup":
            self.state_time += dt
            if self.state_time >= self.WINDUP:
                self._fire(world)
                self.state = "idle"
                self.cooldown = self.COOLDOWN
            return
        self.cooldown = max(0.0, self.cooldown - dt)
        if self.cooldown <= 0 and self.sees_player(world, self.RANGE):
            self.state = "windup"
            self.state_time = 0.0

    def _fire(self, world: "World") -> None:
        player = world.player
        dx = player.box.centerx - self.box.centerx
        dy = player.box.centery - self.box.centery
        dist = math.hypot(dx, dy) or 1.0
        speed = self.PROJECTILE_SPEED
        world.projectiles.append(Projectile(
            self.box.centerx + self.facing * 14, self.box.centery - 4,
            dx / dist * speed, dy / dist * speed, self.PROJECTILE_DAMAGE))
        world.emit("shoot", self.box.centerx, self.box.centery)


ENEMY_TYPES: dict[str, type[Enemy]] = {"w": Walker, "f": Flyer, "s": Shooter}
