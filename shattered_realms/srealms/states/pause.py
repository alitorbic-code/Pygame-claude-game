"""Pause overlay drawn on top of the gameplay state."""
from __future__ import annotations

from typing import Any

import pygame

from ..config import BASE_H, BASE_W
from ..state_manager import State
from ..ui import Button, MenuList, draw_text, get_theme


class PauseState(State):
    name = "pause"
    transparent = True

    def enter(self, **kwargs: Any) -> None:
        game = self.game
        self.dim = pygame.Surface((BASE_W, BASE_H), pygame.SRCALPHA)
        self.dim.fill((0, 0, 0, 160))
        self.menu = MenuList(game, [
            Button("Resume", self._resume),
            Button("Settings", lambda: game.states.push("settings")),
            Button("Quit to Main Menu", lambda: game.states.reset("menu")),
        ], center_x=BASE_W // 2, top=300)

    def _resume(self) -> None:
        self.game.audio.play("ui_back")
        self.game.states.pop()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or "pause" in self.game.input.actions_for_key(event.key):
                self._resume()
                return
        self.menu.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        theme = get_theme(self.game.settings.high_contrast)
        surface.blit(self.dim, (0, 0))
        draw_text(surface, "PAUSED", 90, theme.text, (BASE_W // 2, 200), "center", shadow=True)
        self.menu.draw(surface)
