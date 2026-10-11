"""Credits and version information."""
from __future__ import annotations

from typing import Any

import pygame

from ..config import BASE_H, BASE_W, TITLE, VERSION
from ..graphics import VoidBackground
from ..state_manager import State
from ..ui import draw_text, get_theme

_LINES = (
    ("Design, code and generated art", "Built with Claude"),
    ("Engine", "Python + Pygame"),
    ("Graphics and sound", "Fully procedural, no external assets required"),
    ("Status", "Phase 2: movement, combat and enemies"),
)


class CreditsState(State):
    name = "credits"

    def enter(self, **kwargs: Any) -> None:
        self.background = VoidBackground(seed=3)

    def handle_event(self, event: pygame.event.Event) -> None:
        close = event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE)
        close = close or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)
        if close:
            self.game.audio.play("ui_back")
            self.game.states.pop()

    def update(self, dt: float) -> None:
        self.background.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        theme = get_theme(self.game.settings.high_contrast)
        self.background.draw(surface)
        draw_text(surface, "CREDITS", 72, theme.text, (BASE_W // 2, 100), "center", shadow=True)
        draw_text(surface, TITLE, 34, theme.accent, (BASE_W // 2, 170), "center")
        draw_text(surface, f"Version {VERSION}", 28, theme.dim, (BASE_W // 2, 205), "center")
        y = 290
        for heading, body in _LINES:
            draw_text(surface, heading, 28, theme.dim, (BASE_W // 2, y), "center")
            draw_text(surface, body, 36, theme.text, (BASE_W // 2, y + 34), "center", shadow=True)
            y += 100
        draw_text(surface, "Press Esc, Enter or click to return", 24, theme.dim, (BASE_W // 2, BASE_H - 24), "center")
