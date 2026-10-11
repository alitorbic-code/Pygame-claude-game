"""Gameplay state: fixed-timestep simulation, camera, effects, HUD, and end-of-level flow."""
from __future__ import annotations

import math
import random
from dataclasses import replace
from typing import Any

import pygame

from ..camera import Camera
from ..config import BASE_H, BASE_W, Palette
from ..entities.player import PlayerInput
from ..graphics import FloatingTexts, ParticleSystem, VoidBackground
from ..levels import build_proving_grounds
from ..render import WorldRenderer
from ..state_manager import State
from ..ui import draw_text, get_theme
from ..world import Event, World

FIXED_DT = 1.0 / 120.0
MAX_STEPS_PER_FRAME = 8
DEATH_SCREEN_DELAY = 1.3


class PlayState(State):
    name = "play"

    def enter(self, **kwargs: Any) -> None:
        self.tilemap = build_proving_grounds()
        self.world = World(self.tilemap, random.Random())
        player = self.world.player
        self.camera = Camera(BASE_W, BASE_H, self.tilemap.pixel_w, self.tilemap.pixel_h)
        self.camera.snap(player.box.centerx, player.box.centery)
        self.renderer = WorldRenderer(self.tilemap)
        self.background = VoidBackground(seed=23, top=(10, 8, 26), bottom=(34, 18, 60))
        self.particles = ParticleSystem()
        self.texts = FloatingTexts()
        self.accumulator = 0.0
        self.elapsed = 0.0
        self.hurt_flash = 0.0
        self.ended = False
        self.hint_timer = 14.0
        self._edges = {"jump": False, "dash": False, "attack": False}
        self._vignette = pygame.Surface((BASE_W, BASE_H), pygame.SRCALPHA)
        self._vignette.fill((200, 20, 40, 255))
        self.game.audio.play_music("explore")

    # -- input -------------------------------------------------------------
    def on_focus_lost(self) -> None:
        states = self.game.states
        if states.current is self and not states.has_pending and not self.ended:
            states.push("pause")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._edges["attack"] = True
            return
        if event.type != pygame.KEYDOWN:
            return
        actions = self.game.input.actions_for_key(event.key)
        if event.key == pygame.K_ESCAPE or "pause" in actions:
            self.game.audio.play("ui_back")
            self.game.states.push("pause")
            return
        if "jump" in actions or event.key == pygame.K_UP:
            self._edges["jump"] = True
        if "dash" in actions:
            self._edges["dash"] = True
        if "attack" in actions:
            self._edges["attack"] = True

    def _read_input(self) -> PlayerInput:
        keys = pygame.key.get_pressed()
        inp = self.game.input
        right = inp.is_down("move_right", keys) or keys[pygame.K_RIGHT]
        left = inp.is_down("move_left", keys) or keys[pygame.K_LEFT]
        return PlayerInput(
            move_x=float(right) - float(left),
            jump_pressed=self._edges["jump"],
            jump_held=inp.is_down("jump", keys) or keys[pygame.K_UP],
            dash_pressed=self._edges["dash"],
            attack_pressed=self._edges["attack"],
            down_held=inp.is_down("move_down", keys) or keys[pygame.K_DOWN],
        )

    # -- simulation --------------------------------------------------------
    def update(self, dt: float) -> None:
        self.elapsed += dt
        self.hint_timer = max(0.0, self.hint_timer - dt)
        self.accumulator = min(self.accumulator + dt, 0.1)
        inp = self._read_input()
        steps = 0
        while self.accumulator >= FIXED_DT and steps < MAX_STEPS_PER_FRAME:
            self.world.update(FIXED_DT, inp)
            inp = replace(inp, jump_pressed=False, dash_pressed=False, attack_pressed=False)
            self.accumulator -= FIXED_DT
            steps += 1
        if steps:
            self._edges = {"jump": False, "dash": False, "attack": False}

        for event in self.world.drain_events():
            self._handle_world_event(event)
        player = self.world.player
        self.camera.follow(player.box.centerx + player.facing * 50, player.box.centery - 30, dt)
        self.background.update(dt)
        self.renderer.update(dt, player)
        self.particles.update(dt)
        self.texts.update(dt)
        self.hurt_flash = max(0.0, self.hurt_flash - dt)
        self._check_end()

    def _check_end(self) -> None:
        if self.ended:
            return
        player = self.world.player
        if self.world.won:
            self._finish(True)
        elif not player.alive and player.dead_time > DEATH_SCREEN_DELAY:
            self._finish(False)

    def _finish(self, win: bool) -> None:
        self.ended = True
        world = self.world
        minutes, seconds = divmod(int(self.elapsed), 60)
        lines = (f"Guardians defeated: {world.kills} / {world.total_enemies}",
                 f"Damage dealt: {world.player.damage_dealt}",
                 f"Time: {minutes}:{seconds:02d}")
        self.game.states.push("result", win=win, lines=lines)

    # -- effects -----------------------------------------------------------
    def _handle_world_event(self, ev: Event) -> None:
        audio, game, particles = self.game.audio, self.game, self.particles
        kind = ev.kind
        if kind == "hit":
            crit = ev.tag == "crit"
            particles.emit(ev.x, ev.y, 18 if crit else 10, Palette.GOLD if crit else Palette.EMBER,
                           speed=(90, 320), life=(0.2, 0.5), drag=2.5)
            self.texts.add(ev.x, ev.y - 20, f"{int(ev.value)}{'!' if crit else ''}",
                           Palette.GOLD if crit else (255, 255, 255), 40 if crit else 30)
            audio.play("hit")
            game.shake(7 if crit else 3)
        elif kind == "enemy_die":
            colors = {"walker": (200, 90, 80), "flyer": (170, 110, 255), "shooter": (90, 200, 130)}
            particles.emit(ev.x, ev.y, 34, colors.get(ev.tag, Palette.EMBER), speed=(80, 380),
                           life=(0.4, 0.9), size=(3, 7), gravity=500, drag=1.5)
            audio.play("enemy_die")
            game.shake(6)
        elif kind == "player_hurt":
            particles.emit(ev.x, ev.y, 22, Palette.DANGER, speed=(100, 340), life=(0.3, 0.7), gravity=300)
            self.texts.add(ev.x, ev.y - 30, f"-{int(ev.value)}", Palette.DANGER, 36)
            self.hurt_flash = 0.35
            audio.play("hurt")
            game.shake(12)
        elif kind == "player_die":
            particles.emit(ev.x, ev.y, 70, Palette.DANGER, speed=(100, 480), life=(0.6, 1.4),
                           size=(3, 8), gravity=400, drag=1.0)
            game.shake(20)
        elif kind == "respawn":
            particles.emit(ev.x, ev.y, 24, Palette.CYAN, speed=(60, 240), life=(0.3, 0.8))
        elif kind == "jump":
            particles.emit(ev.x, ev.y, 8, (150, 140, 190), speed=(30, 120), life=(0.2, 0.5),
                           angle=-math.pi / 2, spread=2.4, gravity=200)
            audio.play("jump")
        elif kind == "double_jump":
            particles.emit(ev.x, ev.y, 16, Palette.CYAN, speed=(60, 200), life=(0.25, 0.5),
                           angle=math.pi / 2, spread=2.6)
            audio.play("jump")
        elif kind == "wall_jump":
            particles.emit(ev.x, ev.y - 20, 10, (200, 200, 230), speed=(40, 160), life=(0.2, 0.5))
            audio.play("jump")
        elif kind == "land":
            particles.emit(ev.x, ev.y, 10, (150, 140, 190), speed=(40, 160), life=(0.2, 0.5),
                           angle=-math.pi / 2, spread=math.pi, gravity=300)
        elif kind == "dash":
            particles.emit(ev.x, ev.y, 14, Palette.CYAN, speed=(40, 220), life=(0.2, 0.5), size=(3, 6))
            audio.play("dash")
        elif kind == "swing":
            audio.play("swing")
        elif kind == "shoot":
            audio.play("shoot")
        elif kind == "proj_hit":
            particles.emit(ev.x, ev.y, 8, (255, 160, 100), speed=(40, 200), life=(0.15, 0.4))
        elif kind == "parry":
            particles.emit(ev.x, ev.y, 22, Palette.CYAN, speed=(100, 360), life=(0.2, 0.5), drag=3.0)
            self.texts.add(ev.x, ev.y - 24, "DEFLECT", Palette.CYAN, 28, 0.8)
            audio.play("hit")
            game.shake(4)

    # -- drawing -----------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        theme = get_theme(self.game.settings.high_contrast)
        cam = self.camera
        self.background.draw(surface, scroll_x=cam.x * 0.25)
        self.renderer.draw(surface, self.world, cam, self.game.time, self.game.debug)
        offset = (-cam.x, -cam.y)
        self.particles.draw(surface, offset)
        self.texts.draw(surface, offset)
        if self.hurt_flash > 0:
            self._vignette.set_alpha(int(70 * self.hurt_flash / 0.35))
            surface.blit(self._vignette, (0, 0))
        self._draw_hud(surface, theme)

    def _draw_hud(self, surface: pygame.Surface, theme) -> None:
        world, p = self.world, self.world.player
        bar = pygame.Rect(24, 24, 300, 22)
        pygame.draw.rect(surface, (30, 14, 24), bar, border_radius=6)
        fraction = p.health.fraction
        color = (int(255 * (1 - fraction) + 90 * fraction), int(90 * (1 - fraction) + 220 * fraction), 110)
        if fraction > 0:
            pygame.draw.rect(surface, color, (bar.x, bar.y, int(bar.width * fraction), bar.height), border_radius=6)
        pygame.draw.rect(surface, theme.edge, bar, 2, border_radius=6)
        draw_text(surface, f"{max(0, math.ceil(p.health.hp))} / {int(p.health.max_hp)}", 22, theme.text,
                  bar.center, "center", True)
        ready = p.dash_cooldown <= 0 and p.dash_charges > 0
        pygame.draw.circle(surface, theme.accent if ready else theme.edge, (36, 66), 9, 0 if ready else 2)
        draw_text(surface, "DASH", 20, theme.dim, (52, 66), "midleft")
        if p.combo_step >= 0 and p.combo_timer > 0:
            draw_text(surface, f"COMBO x{p.combo_step + 1}", 26, Palette.GOLD, (24, 92), "topleft", True)
        remaining = len(world.enemies)
        status = "Seal broken: reach the portal!" if world.exit_open else f"Guardians left: {remaining}"
        draw_text(surface, status, 28, Palette.GOLD if world.exit_open else theme.text,
                  (BASE_W - 24, BASE_H - 24), "bottomright", True)
        minutes, seconds = divmod(int(self.elapsed), 60)
        draw_text(surface, f"{minutes}:{seconds:02d}", 26, theme.dim, (BASE_W // 2, 22), "center", True)
        if self.hint_timer > 0:
            name = self.game.input.key_name
            hint = (f"Move {name('move_left')}/{name('move_right')}   Jump {name('jump')} (x2, walls)   "
                    f"Dash {name('dash')}   Attack {name('attack')}   Drop through: {name('move_down')}+{name('jump')}")
            draw_text(surface, hint, 24, theme.text, (BASE_W // 2, BASE_H - 26), "center", True,
                      int(255 * min(1.0, self.hint_timer)))

    def debug_info(self) -> list[str]:
        w, p = self.world, self.world.player
        return [f"enemies: {len(w.enemies)}  projectiles: {len(w.projectiles)}  particles: {len(self.particles)}",
                f"player: ({p.box.x:.0f},{p.box.y:.0f}) v=({p.vx:.0f},{p.vy:.0f}) floor={p.on_floor} wall={p.wall_dir}",
                f"camera: ({self.camera.x:.0f},{self.camera.y:.0f})"]
