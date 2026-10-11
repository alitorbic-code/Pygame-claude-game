"""Player controller: pure game logic driven by a PlayerInput every fixed step."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from ..combat import Health
from ..physics import ONEWAY, SOLID, TILE, Box, approach, sign

if TYPE_CHECKING:
    from ..world import World


@dataclass
class PlayerInput:
    move_x: float = 0.0
    jump_pressed: bool = False  # edge: went down this step
    jump_held: bool = False
    dash_pressed: bool = False
    attack_pressed: bool = False
    down_held: bool = False


@dataclass(frozen=True)
class AttackSpec:
    damage: int
    reach: float
    height: float
    windup: float
    active: float
    recover: float
    knockback: float
    lunge: float
    stagger: float

    @property
    def total(self) -> float:
        return self.windup + self.active + self.recover


ATTACKS = (
    AttackSpec(damage=12, reach=46, height=38, windup=0.05, active=0.09, recover=0.10, knockback=200, lunge=170, stagger=0.25),
    AttackSpec(damage=14, reach=50, height=42, windup=0.05, active=0.09, recover=0.10, knockback=230, lunge=190, stagger=0.28),
    AttackSpec(damage=24, reach=72, height=54, windup=0.09, active=0.12, recover=0.22, knockback=420, lunge=340, stagger=0.45),
)


class Player:
    W = 22.0
    H = 40.0
    RUN_SPEED = 270.0
    GROUND_ACCEL = 3200.0
    AIR_ACCEL = 1800.0
    GROUND_FRICTION = 3000.0
    AIR_FRICTION = 500.0
    ATTACK_ACCEL = 900.0
    ATTACK_MOVE_MULT = 0.35
    GRAVITY = 1900.0
    JUMP_CUT = 2.4
    FALL_MULT = 1.25
    MAX_FALL = 900.0
    JUMP_VEL = 640.0
    DOUBLE_JUMP_VEL = 560.0
    AIR_JUMPS = 1
    COYOTE = 0.10
    JUMP_BUFFER = 0.12
    ATTACK_BUFFER = 0.18
    WALL_SLIDE_SPEED = 110.0
    WALL_JUMP_VX = 320.0
    WALL_JUMP_VY = 600.0
    WALL_LOCK = 0.18
    DASH_SPEED = 760.0
    DASH_TIME = 0.15
    DASH_COOLDOWN = 0.55
    COMBO_WINDOW = 0.35
    HURT_STUN = 0.22
    KNOCK_X = 260.0
    KNOCK_Y = 300.0
    HAZARD_DAMAGE = 15
    VOID_DAMAGE = 25
    LAND_EVENT_SPEED = 450.0

    def __init__(self, x: float, y: float) -> None:
        """x, y is the position of the feet (bottom center)."""
        self.box = Box(x - self.W / 2, y - self.H, self.W, self.H)
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.health = Health(100, invuln_time=1.0)
        self.crit_chance = 0.10
        self.crit_mult = 2.0
        self.on_floor = False
        self.wall_dir = 0  # -1 wall on the left, 1 on the right, 0 none
        self.wall_sliding = False
        self.coyote = self.jump_buffer = self.attack_buffer = 0.0
        self.dash_timer = self.dash_cooldown = self.wall_lock = self.hurt_stun = 0.0
        self.drop_timer = self.combo_timer = self.safe_timer = 0.0
        self.dash_dir = 1
        self.dash_charges = 1
        self.air_jumps = self.AIR_JUMPS
        self.attacking = False
        self.attack_time = 0.0
        self.combo_step = -1
        self.hit_ids: set[int] = set()
        self.last_safe = (x, y)
        self.dead_time = 0.0
        self.damage_dealt = 0
        self.kills = 0
        self._death_reported = False

    # -- state helpers -----------------------------------------------------
    @property
    def alive(self) -> bool:
        return self.health.alive

    @property
    def invulnerable(self) -> bool:
        return self.dash_timer > 0 or self.health.invuln > 0

    @property
    def current_attack(self) -> Optional[AttackSpec]:
        return ATTACKS[self.combo_step] if self.attacking and self.combo_step >= 0 else None

    def attack_hitbox(self) -> Optional[Box]:
        """The damaging area, present only during the active frames of a swing."""
        spec = self.current_attack
        if spec is None or not (spec.windup <= self.attack_time < spec.windup + spec.active):
            return None
        width = spec.reach + self.W / 2
        x = self.box.centerx if self.facing > 0 else self.box.centerx - width
        return Box(x, self.box.centery - spec.height / 2, width, spec.height)

    # -- per-step update ---------------------------------------------------
    def update(self, dt: float, inp: PlayerInput, world: "World") -> None:
        self.health.update(dt)
        if not self.alive:
            self._update_dead(dt, world)
            return
        self._tick_timers(dt, inp)
        self._try_dash(inp, world)
        if self.dash_timer > 0:
            self._dash_step(dt, world)
        else:
            self._try_start_attack(inp, world)
            self._vertical(dt, inp, world)
            self._horizontal(dt, inp)
            self._move(dt, world)
        self._after_move(dt, world)

    def _update_dead(self, dt: float, world: "World") -> None:
        self.dead_time += dt
        self.vx *= max(0.0, 1.0 - 4.0 * dt)
        if self.box.top < world.tilemap.pixel_h + 400:
            self.vy = min(self.vy + self.GRAVITY * dt, self.MAX_FALL)
            result = world.tilemap.move(self.box, self.vx * dt, self.vy * dt)
            if result.on_floor:
                self.vy = 0.0

    def _tick_timers(self, dt: float, inp: PlayerInput) -> None:
        for name in ("coyote", "jump_buffer", "attack_buffer", "dash_cooldown", "wall_lock",
                     "hurt_stun", "drop_timer", "combo_timer", "safe_timer"):
            setattr(self, name, max(0.0, getattr(self, name) - dt))
        if inp.jump_pressed:
            self.jump_buffer = self.JUMP_BUFFER
        if inp.attack_pressed:
            self.attack_buffer = self.ATTACK_BUFFER
        if self.attacking:
            self.attack_time += dt
            spec = ATTACKS[self.combo_step]
            if self.attack_time >= spec.total:
                self.attacking = False
        if self.combo_timer <= 0 and not self.attacking:
            self.combo_step = -1

    # -- dash --------------------------------------------------------------
    def _try_dash(self, inp: PlayerInput, world: "World") -> None:
        if not (inp.dash_pressed and self.dash_cooldown <= 0 and self.dash_charges > 0
                and self.hurt_stun <= 0 and self.dash_timer <= 0):
            return
        direction = sign(inp.move_x) or self.facing
        self.dash_dir = self.facing = direction
        self.dash_timer = self.DASH_TIME
        self.dash_cooldown = self.DASH_COOLDOWN
        self.dash_charges -= 1
        self.attacking = False
        self.vy = 0.0
        world.emit("dash", self.box.centerx, self.box.centery, tag=str(direction))

    def _dash_step(self, dt: float, world: "World") -> None:
        self.vx = self.dash_dir * self.DASH_SPEED
        self.vy = 0.0
        self._move(dt, world)
        self.dash_timer -= dt
        if self.dash_timer <= 0:
            self.dash_timer = 0.0
            self.vx = self.dash_dir * self.RUN_SPEED * 0.8

    # -- attack ------------------------------------------------------------
    def _try_start_attack(self, inp: PlayerInput, world: "World") -> None:
        if self.attack_buffer <= 0 or self.hurt_stun > 0:
            return
        if self.attacking:
            spec = ATTACKS[self.combo_step]
            if self.attack_time < spec.windup + spec.active:
                return  # cannot cancel a swing before its recovery phase
        if inp.move_x:
            self.facing = sign(inp.move_x)
        self.combo_step = (self.combo_step + 1) % len(ATTACKS)
        spec = ATTACKS[self.combo_step]
        self.attacking = True
        self.attack_time = 0.0
        self.hit_ids = set()
        self.attack_buffer = 0.0
        self.combo_timer = spec.total + self.COMBO_WINDOW
        self.vx = self.facing * spec.lunge
        world.emit("swing", self.box.centerx, self.box.centery, value=self.combo_step, tag=str(self.facing))

    # -- movement ----------------------------------------------------------
    def _wall_blocked(self, world: "World", side: int) -> bool:
        probe = Box(self.box.x + side, self.box.y + 4, self.box.w, self.box.h - 8)
        return world.tilemap.solid_overlap(probe)

    def _on_oneway(self, world: "World") -> bool:
        row = math.floor((self.box.bottom + 1) / TILE)
        columns = {math.floor((self.box.left + 2) / TILE), math.floor((self.box.right - 2) / TILE)}
        tiles = [world.tilemap.tile_at(col, row) for col in columns]
        return ONEWAY in tiles and SOLID not in tiles

    def _vertical(self, dt: float, inp: PlayerInput, world: "World") -> None:
        self.wall_dir = 0
        if not self.on_floor:
            if self._wall_blocked(world, -1):
                self.wall_dir = -1
            elif self._wall_blocked(world, 1):
                self.wall_dir = 1
        if self.on_floor:
            self.coyote = self.COYOTE
            self.air_jumps = self.AIR_JUMPS
            self.dash_charges = 1
        elif self.wall_dir:
            self.air_jumps = self.AIR_JUMPS
            self.dash_charges = 1

        if self.on_floor and inp.down_held and inp.jump_pressed and self._on_oneway(world):
            self.drop_timer = 0.2
            self.jump_buffer = self.coyote = 0.0
            self.on_floor = False
        elif self.jump_buffer > 0 and self.hurt_stun <= 0:
            self._try_jump(world)

        self.wall_sliding = (not self.on_floor and self.wall_dir != 0 and self.vy > 0
                             and inp.move_x * self.wall_dir > 0)
        gravity = self.GRAVITY
        if self.vy < 0 and not inp.jump_held:
            gravity *= self.JUMP_CUT
        elif self.vy > 0:
            gravity *= self.FALL_MULT
        self.vy = min(self.vy + gravity * dt, self.MAX_FALL)
        if self.wall_sliding:
            self.vy = min(self.vy, self.WALL_SLIDE_SPEED)

    def _try_jump(self, world: "World") -> None:
        x, feet = self.box.centerx, self.box.bottom
        if self.coyote > 0:
            self.vy = -self.JUMP_VEL
            self.coyote = self.jump_buffer = 0.0
            self.on_floor = False
            world.emit("jump", x, feet)
        elif self.wall_dir:
            self.vy = -self.WALL_JUMP_VY
            self.vx = -self.wall_dir * self.WALL_JUMP_VX
            self.facing = -self.wall_dir
            self.wall_lock = self.WALL_LOCK
            self.jump_buffer = 0.0
            world.emit("wall_jump", x, feet, tag=str(-self.wall_dir))
        elif self.air_jumps > 0:
            self.air_jumps -= 1
            self.vy = -self.DOUBLE_JUMP_VEL
            self.jump_buffer = 0.0
            world.emit("double_jump", x, feet)

    def _horizontal(self, dt: float, inp: PlayerInput) -> None:
        if self.wall_lock > 0:
            return
        move_x = inp.move_x if self.hurt_stun <= 0 else 0.0
        speed = self.RUN_SPEED * (self.ATTACK_MOVE_MULT if self.attacking and self.on_floor else 1.0)
        if self.attacking:
            accel = friction = self.ATTACK_ACCEL
        else:
            accel = self.GROUND_ACCEL if self.on_floor else self.AIR_ACCEL
            friction = self.GROUND_FRICTION if self.on_floor else self.AIR_FRICTION
        if move_x:
            self.vx = approach(self.vx, move_x * speed, accel * dt)
            if not self.attacking:
                self.facing = sign(move_x)
        else:
            self.vx = approach(self.vx, 0.0, friction * dt)

    def _move(self, dt: float, world: "World") -> None:
        result = world.tilemap.move(self.box, self.vx * dt, self.vy * dt, drop_through=self.drop_timer > 0)
        self.on_floor = result.on_floor
        if result.hit_ceiling and self.vy < 0:
            self.vy = 0.0
        if result.on_floor and self.vy > 0:
            if self.vy > self.LAND_EVENT_SPEED:
                world.emit("land", self.box.centerx, self.box.bottom)
            self.vy = 0.0
        if (result.hit_left and self.vx < 0) or (result.hit_right and self.vx > 0):
            self.vx = 0.0
        if result.hazard and not self.invulnerable:
            self._punish_and_respawn(world, self.HAZARD_DAMAGE, force=False)
        elif self.box.top > world.tilemap.pixel_h + 96:
            self._punish_and_respawn(world, self.VOID_DAMAGE, force=True)

    def _after_move(self, dt: float, world: "World") -> None:
        if self.alive and self.on_floor and self.safe_timer <= 0 and self.hurt_stun <= 0:
            self.last_safe = (self.box.centerx, self.box.bottom)
            self.safe_timer = 0.25

    # -- damage ------------------------------------------------------------
    def hurt(self, amount: float, source_x: float, world: "World") -> bool:
        """Take a hit from a source at source_x; returns True if damage landed."""
        if not self.alive or self.invulnerable:
            return False
        dealt = self.health.damage(amount)
        if dealt <= 0:
            return False
        direction = 1 if self.box.centerx >= source_x else -1
        self.vx = direction * self.KNOCK_X
        self.vy = -self.KNOCK_Y
        self.hurt_stun = self.HURT_STUN
        self.attacking = False
        self.dash_timer = 0.0
        world.emit("player_hurt", self.box.centerx, self.box.centery, dealt)
        self._report_death(world)
        return True

    def _punish_and_respawn(self, world: "World", damage: float, force: bool) -> None:
        if not self.alive:
            return
        dealt = self.health.damage(damage, ignore_invuln=force)
        world.emit("player_hurt", self.box.centerx, self.box.centery, dealt)
        if self._report_death(world):
            return
        self.box.x = self.last_safe[0] - self.W / 2
        self.box.y = self.last_safe[1] - self.H
        self.vx = self.vy = 0.0
        self.dash_timer = 0.0
        self.attacking = False
        self.hurt_stun = 0.3
        world.emit("respawn", self.box.centerx, self.box.centery)

    def _report_death(self, world: "World") -> bool:
        if self.health.alive:
            return False
        if not self._death_reported:
            self._death_reported = True
            world.emit("player_die", self.box.centerx, self.box.centery)
        return True
