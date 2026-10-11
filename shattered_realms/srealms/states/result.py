"""Victory / defeat overlay shown on top of the (frozen) gameplay screen."""
from __future__ import annotations

from typing import Any

import pygame

from ..config import BASE_H, BASE_W, Palette
from ..state_manager import State
from ..ui import Button, MenuList, draw_text, get_theme


class ResultState(State):
    name = "result"
    transparent = True

    def enter(self, win: bool = False, lines: tuple[str, ...] = (), **kwargs: Any) -> None:
        game = self.game
        self.win = win
        self.lines = list(lines)
        self.dim = pygame.Surface((BASE_W, BASE_H), pygame.SRCALPHA)
        self.dim.fill((0, 0, 0, 170))
        self.menu = MenuList(game, [
            Button("Play Again" if win else "Try Again", lambda: game.states.reset("play")),
            Button("Main Menu", lambda: game.states.reset("menu")),
        ], center_x=BASE_W // 2, top=470)
        game.audio.play("win" if win else "lose")

    def handle_event(self, event: pygame.event.Event) -> None:
        self.menu.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        theme = get_theme(self.game.settings.high_contrast)
        surface.blit(self.dim, (0, 0))
        title = "REALM CLEARED" if self.win else "YOU FELL"
        color = Palette.GOLD if self.win else theme.danger
        draw_text(surface, title, 100, color, (BASE_W // 2, 180), "center", shadow=True)
        y = 270
        for line in self.lines:
            draw_text(surface, line, 34, theme.text, (BASE_W // 2, y), "center", shadow=True)
            y += 44
        self.menu.draw(surface)
