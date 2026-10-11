"""Settings screen: audio, display, accessibility, and reset."""
from __future__ import annotations

from typing import Any

import pygame

from .. import config
from ..graphics import VoidBackground
from ..settings import save_settings
from ..state_manager import State
from ..ui import Button, Choice, MenuList, Slider, Toggle, draw_text, get_theme


class SettingsState(State):
    name = "settings"

    def enter(self, **kwargs: Any) -> None:
        game = self.game
        self.background = VoidBackground(seed=11)
        resolutions = [f"{w} x {h}" for w, h in config.RESOLUTIONS]
        self.menu = MenuList(game, [
            Slider("Master Volume", lambda: game.settings.master_volume, lambda v: self._set_volume("master_volume", v)),
            Slider("Music Volume", lambda: game.settings.music_volume, lambda v: self._set_volume("music_volume", v)),
            Slider("Effects Volume", lambda: game.settings.sfx_volume, lambda v: self._set_volume("sfx_volume", v)),
            Slider("Screen Shake", lambda: game.settings.screen_shake, lambda v: setattr(game.settings, "screen_shake", v)),
            Toggle("Fullscreen", lambda: game.settings.fullscreen, self._set_fullscreen),
            Choice("Window Size", resolutions, lambda: game.settings.resolution_index, self._set_resolution),
            Toggle("Show FPS", lambda: game.settings.show_fps, lambda v: setattr(game.settings, "show_fps", v)),
            Toggle("High Contrast UI", lambda: game.settings.high_contrast, lambda v: setattr(game.settings, "high_contrast", v)),
            Button("Reset to Defaults", self._reset),
            Button("Back", self._close),
        ], center_x=config.BASE_W // 2, top=110, width=640, row_height=46, spacing=8)

    def _set_volume(self, name: str, value: float) -> None:
        setattr(self.game.settings, name, value)
        self.game.audio.apply_volumes()

    def _set_fullscreen(self, value: bool) -> None:
        self.game.settings.fullscreen = value
        self.game.apply_display_settings()

    def _set_resolution(self, index: int) -> None:
        self.game.settings.resolution_index = index
        if not self.game.settings.fullscreen:
            self.game.apply_display_settings()

    def _reset(self) -> None:
        game = self.game
        game.settings.reset_to_defaults()
        game.input.rebuild(game.settings.bindings)
        game.audio.apply_volumes()
        game.apply_display_settings()
        game.notify("Settings reset to defaults")

    def _close(self) -> None:
        if not save_settings(self.game.settings):
            self.game.notify("Could not save settings to disk")
        self.game.audio.play("ui_back")
        self.game.states.pop()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._close()
            return
        self.menu.handle_event(event)

    def update(self, dt: float) -> None:
        self.background.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        theme = get_theme(self.game.settings.high_contrast)
        self.background.draw(surface)
        draw_text(surface, "SETTINGS", 64, theme.text, (config.BASE_W // 2, 58), "center", shadow=True)
        self.menu.draw(surface)
        draw_text(surface, "Left/Right adjusts   |   Esc to go back", 22, theme.dim,
                  (config.BASE_W // 2, config.BASE_H - 18), "center")
