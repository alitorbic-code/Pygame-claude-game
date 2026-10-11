"""Simulation container: owns the player, enemies, projectiles and resolves their interactions.

World has no pygame dependency. It reports what happened through ``events``, which the
play state turns into particles, sounds, and screen shake.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from .combat import roll_damage
from .entities.enemies import ENEMY_TYPES, Enemy
from .entities.player import Player, PlayerInput
from .entities.projectile import Projectile
from .physics import TILE, Box, TileMap

MAX_QUEUED_EVENTS = 512


@dataclass
class Event:
    kind: str
    x: float = 0.0
    y: float = 0.0
    value: float = 0.0
    tag: str = ""


class World:
    def __init__(self, tilemap: TileMap, rng: Optional[random.Random] = None) -> None:
        self.tilemap = tilemap
        self.rng = rng or random.Random()
        self.enemies: list[Enemy] = []
        self.projectiles: list[Projectile] = []
        self.events: list[Event] = []
        self.time = 0.0
        self.hitstop = 0.0
        self.kills = 0
        self.total_enemies = 0
        self.exit_box: Optional[Box] = None
        self.won = False
        self.player: Optional[Player] = None
        self._spawn_from_map()
        if self.player is None:
            raise ValueError("Level has no player spawn ('P')")

    def _spawn_from_map(self) -> None:
        for char, tx, ty in self.tilemap.spawns:
            center_x = tx * TILE + TILE / 2
            feet_y = (ty + 1) * TILE
            if char == "P":
                self.player = Player(center_x, feet_y)
            elif char == "X":
                self.exit_box = Box(tx * TILE - 16, feet_y - 96, TILE + 32, 96)
            elif char in ENEMY_TYPES:
                cls = ENEMY_TYPES[char]
                if cls.FLIES:  # flyers spawn centered on their tile
                    feet_y = (ty + 0.5) * TILE + cls.H / 2
                self.enemies.append(cls(center_x, feet_y))
        self.total_enemies = len(self.enemies)

    # -- events ------------------------------------------------------------
    def emit(self, kind: str, x: float = 0.0, y: float = 0.0, value: float = 0.0, tag: str = "") -> None:
        if len(self.events) < MAX_QUEUED_EVENTS:
            self.events.append(Event(kind, x, y, value, tag))

    def drain_events(self) -> list[Event]:
        events, self.events = self.events, []
        return events

    @property
    def exit_open(self) -> bool:
        return not self.enemies

    # -- simulation --------------------------------------------------------
    def update(self, dt: float, inp: PlayerInput) -> None:
        if self.hitstop > 0:  # brief freeze that makes hits feel heavy
            self.hitstop = max(0.0, self.hitstop - dt)
            return
        self.time += dt
        self.player.update(dt, inp, self)
        self._resolve_player_attack()
        for enemy in self.enemies:
            enemy.update(dt, self)
        self._resolve_contacts()
        for projectile in self.projectiles:
            projectile.update(dt, self)
        self.enemies = [e for e in self.enemies if e.alive]
        self.projectiles = [p for p in self.projectiles if p.alive]
        if (self.exit_box and self.exit_open and self.player.alive
                and self.player.box.overlaps(self.exit_box)):
            self.won = True

    def damage_enemy(self, enemy: Enemy, amount: float, source_x: float, knockback: float,
                     stagger: float, crit: bool = False, hitstop: float = 0.045) -> bool:
        died = enemy.hurt(amount, source_x, knockback, stagger, self)
        self.player.damage_dealt += int(amount)
        self.hitstop = max(self.hitstop, 0.08 if died else hitstop)
        self.emit("hit", enemy.box.centerx, enemy.box.centery, amount, "crit" if crit else "")
        if died:
            self.kills += 1
            self.player.kills += 1
            self.emit("enemy_die", enemy.box.centerx, enemy.box.centery, enemy.MAX_HP, enemy.kind)
        return died

    def _resolve_player_attack(self) -> None:
        hitbox = self.player.attack_hitbox()
        if hitbox is None:
            return
        spec = self.player.current_attack
        for enemy in self.enemies:
            if not enemy.alive or id(enemy) in self.player.hit_ids or not hitbox.overlaps(enemy.box):
                continue
            self.player.hit_ids.add(id(enemy))
            amount, crit = roll_damage(spec.damage, self.player.crit_chance, self.player.crit_mult,
                                       enemy.ARMOR, self.rng)
            heavy = self.player.combo_step == 2
            self.damage_enemy(enemy, amount, self.player.box.centerx, spec.knockback, spec.stagger,
                              crit, hitstop=0.07 if heavy else 0.045)
        for projectile in self.projectiles:
            if projectile.alive and projectile.owner == "enemy" and hitbox.overlaps(projectile.box):
                projectile.reflect()
                self.hitstop = max(self.hitstop, 0.06)
                self.emit("parry", projectile.x, projectile.y)

    def _resolve_contacts(self) -> None:
        if not self.player.alive:
            return
        for enemy in self.enemies:
            if (enemy.alive and enemy.CONTACT_DAMAGE and enemy.stagger <= 0
                    and enemy.box.overlaps(self.player.box)):
                self.player.hurt(enemy.CONTACT_DAMAGE, enemy.box.centerx, self)
