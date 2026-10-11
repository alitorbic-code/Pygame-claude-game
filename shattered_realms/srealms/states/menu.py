"""Animated main menu."""
from __future__ import annotations

import math
import random
from typing import Any

import pygame

from ..config import BASE_H, BASE_W, VERSION, Palette
from ..graphics import ParticleSystem, VoidBackground
from ..state_manager import State
from ..ui import Button, MenuList, draw_text, get_theme


class MenuState(State):
    name = "menu"

    def enter(self, **kwargs: Any) -> None:
        game = self.game
        self.time = 0.0
        self.background = VoidBackground(seed=7)
        self.particles = ParticleSystem()
        game.audio.play_music("menu")
        self.menu = MenuList(game, [
            Button("New Game", lambda: game.states.switch("play")),
            Button("Continue", lambda: None, enabled=False),  # unlocked when the save system lands
            Button("Settings", lambda: game.states.push("settings")),
            Button("Credits", lambda: game.states.push("credits")),
            Button("Quit", self._quit),
        ], center_x=BASE_W // 2, top=320)

    def _quit(self) -> None:
        self.game.running = False

    def handle_event(self, event: pygame.event.Event) -> None:
        self.menu.handle_event(event)

    def update(self, dt: float) -> None:
        self.time += dt
        self.background.update(dt)
        if random.random() < dt * 24:
            color = random.choice((Palette.VOID_PURPLE, Palette.CYAN, Palette.GOLD))
            self.particles.emit(random.uniform(0, BASE_W), BASE_H + 10, 1, color, speed=(25, 70),
                                life=(3.0, 6.0), size=(2, 4), angle=-math.pi / 2, spread=0.6)
        self.particles.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        theme = get_theme(self.game.settings.high_contrast)
        self.background.draw(surface)
        self.particles.draw(surface)
        pulse = 0.5 + 0.5 * math.sin(self.time * 1.6)
        for offset in (-3, 3):
            draw_text(surface, "SHATTERED REALMS", 124, Palette.VOID_PURPLE, (BASE_W // 2 + offset, 130 + offset),
                      "center", alpha=int(70 + 80 * pulse))
        draw_text(surface, "SHATTERED REALMS", 124, theme.text, (BASE_W // 2, 130), "center", shadow=True)
        draw_text(surface, "ECHOES OF THE VOID", 50, theme.accent, (BASE_W // 2, 218), "center", shadow=True)
        self.menu.draw(surface)
        draw_text(surface, "Continue unlocks once the save system is added", 22, theme.dim,
                  (BASE_W // 2, 610), "center")
        draw_text(surface, f"v{VERSION}", 24, theme.dim, (14, BASE_H - 12), "bottomleft")
        draw_text(surface, "Arrows/WASD + Enter, or mouse   |   F11 fullscreen   |   F3 debug", 22, theme.dim,
                  (BASE_W - 14, BASE_H - 12), "bottomright")
