"""Projectiles fired by enemies (and reflected back by the player's swings)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..physics import Box

if TYPE_CHECKING:
    from ..world import World


class Projectile:
    SIZE = 12.0

    def __init__(self, x: float, y: float, vx: float, vy: float, damage: int,
                 owner: str = "enemy", life: float = 4.0) -> None:
        self.box = Box(x - self.SIZE / 2, y - self.SIZE / 2, self.SIZE, self.SIZE)
        self.vx, self.vy = vx, vy
        self.damage = damage
        self.owner = owner
        self.life = life
        self.alive = True

    @property
    def x(self) -> float:
        return self.box.centerx

    @property
    def y(self) -> float:
        return self.box.centery

    def reflect(self) -> None:
        """Turn the projectile around, faster and stronger, owned by the player."""
        self.vx, self.vy = -self.vx * 1.3, -self.vy * 1.3
        self.owner = "player"
        self.damage = int(self.damage * 2)
        self.life = 3.0

    def update(self, dt: float, world: "World") -> None:
        self.life -= dt
        if self.life <= 0:
            self.alive = False
            return
        self.box.x += self.vx * dt
        self.box.y += self.vy * dt
        if world.tilemap.solid_overlap(self.box):
            self.alive = False
            world.emit("proj_hit", self.x, self.y)
        elif self.owner == "enemy":
            player = world.player
            if player.alive and self.box.overlaps(player.box):
                if player.hurt(self.damage, self.x, world):
                    self.alive = False
        else:
            for enemy in world.enemies:
                if enemy.alive and self.box.overlaps(enemy.box):
                    world.damage_enemy(enemy, self.damage, self.x, knockback=220, stagger=0.3)
                    self.alive = False
                    break
