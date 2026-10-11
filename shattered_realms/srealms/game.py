"""Application core: window, main loop, global hotkeys, toasts, and debug overlay."""
from __future__ import annotations

import math
import random

import pygame

from . import config
from .audio import AudioManager
from .input_map import InputMap
from .settings import load_settings, save_settings
from .state_manager import StateManager
from .states import register_all
from .ui import draw_text, get_theme


class Game:
    def __init__(self, debug: bool = False) -> None:
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption(config.TITLE)
        self.settings, load_warning = load_settings()
        self.debug = debug
        self.running = True
        self.clock = pygame.time.Clock()
        self.time = 0.0
        self.fps = 0.0
        self.frame_ms = 0.0
        self.shake_amount = 0.0
        self._toasts: list[list] = []  # [text, seconds_left]
        self._view = (0, 0, 1.0)  # canvas offset x, y and scale inside the window
        self._create_window()
        self.canvas = pygame.Surface((config.BASE_W, config.BASE_H))
        self.audio = AudioManager(self.settings, config.ASSET_DIR)
        self.input = InputMap(self.settings.bindings)
        self.states = StateManager(self)
        register_all(self.states)
        if load_warning:
            self.notify(load_warning)

    # -- window ------------------------------------------------------------
    def _create_window(self) -> None:
        width, height = config.RESOLUTIONS[self.settings.resolution_index]
        try:
            if self.settings.fullscreen:
                surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            else:
                surface = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        except pygame.error:
            self.settings.fullscreen = False
            surface = pygame.display.set_mode((width, height))
        self._view = self._compute_view(surface.get_size())

    def apply_display_settings(self) -> None:
        self._create_window()

    def toggle_fullscreen(self) -> None:
        self.settings.fullscreen = not self.settings.fullscreen
        self.apply_display_settings()
        save_settings(self.settings)

    @staticmethod
    def _compute_view(size: tuple[int, int]) -> tuple[int, int, float]:
        win_w, win_h = size
        scale = min(win_w / config.BASE_W, win_h / config.BASE_H)
        view_w, view_h = int(config.BASE_W * scale), int(config.BASE_H * scale)
        return ((win_w - view_w) // 2, (win_h - view_h) // 2, max(scale, 1e-6))

    def to_canvas(self, pos: tuple[int, int]) -> tuple[int, int]:
        ox, oy, scale = self._view
        return (int((pos[0] - ox) / scale), int((pos[1] - oy) / scale))

    # -- feedback ----------------------------------------------------------
    def shake(self, amount: float) -> None:
        self.shake_amount = max(self.shake_amount, amount)

    def notify(self, text: str) -> None:
        self._toasts.append([text, config.TOAST_SECONDS])
        del self._toasts[:-config.MAX_TOASTS]

    # -- main loop ---------------------------------------------------------
    def run(self) -> None:
        self.states.push("menu")
        while self.running and self.frame():
            pass
        self.shutdown()

    def frame(self, elapsed: float | None = None) -> bool:
        """Run one frame. Returns False when the game should exit. Tests pass a fixed elapsed."""
        if elapsed is None:
            elapsed = self.clock.tick(config.FPS_TARGET) / 1000.0
        dt = min(elapsed, config.MAX_FRAME_DT)
        self.frame_ms = elapsed * 1000.0
        self.fps = self.clock.get_fps()
        self.time += dt
        for event in pygame.event.get():
            self._dispatch(event)
        self.states.apply_pending()
        if self.states.is_empty:
            return False
        self.states.update(dt)
        self._update_overlays(dt)
        self.canvas.fill((0, 0, 0))
        self.states.draw(self.canvas)
        self._draw_overlays()
        self._present()
        pygame.display.flip()
        return True

    def _dispatch(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == getattr(pygame, "WINDOWFOCUSLOST", -1):
            self.states.on_focus_lost()
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F3:
                self.debug = not self.debug
                return
            if event.key == pygame.K_F11 or (event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT):
                self.toggle_fullscreen()
                return
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            event = pygame.event.Event(event.type, {**event.dict, "pos": self.to_canvas(event.pos)})
        self.states.handle_event(event)

    def _update_overlays(self, dt: float) -> None:
        self.shake_amount *= math.exp(-10.0 * dt)
        if self.shake_amount < 0.3:
            self.shake_amount = 0.0
        for toast in self._toasts:
            toast[1] -= dt
        self._toasts = [t for t in self._toasts if t[1] > 0]

    def _draw_overlays(self) -> None:
        theme = get_theme(self.settings.high_contrast)
        y = 14
        for text, left in self._toasts:
            alpha = int(255 * min(1.0, left / 0.5))
            draw_text(self.canvas, text, 28, theme.accent, (config.BASE_W - 16, y), "topright", True, alpha)
            y += 30
        if self.debug:
            lines = [
                f"FPS {self.fps:5.1f}  frame {self.frame_ms:5.1f} ms",
                f"states: {' > '.join(self.states.stack_names)}",
                f"audio: {'on' if self.audio.available else 'unavailable'}  sounds: {len(self.audio.sounds)}",
            ]
            current = self.states.current
            if current is not None:
                lines.extend(current.debug_info())
            panel = pygame.Surface((420, 12 + 22 * len(lines)), pygame.SRCALPHA)
            panel.fill((0, 0, 0, 150))
            self.canvas.blit(panel, (8, 8))
            for i, line in enumerate(lines):
                draw_text(self.canvas, line, 22, (120, 255, 160), (16, 14 + 22 * i))
        elif self.settings.show_fps:
            draw_text(self.canvas, f"{self.fps:.0f} FPS", 24, theme.dim, (10, 8), "topleft", True)

    def _present(self) -> None:
        window = pygame.display.get_surface()
        self._view = self._compute_view(window.get_size())
        ox, oy, scale = self._view
        window.fill((0, 0, 0))
        shake_x = shake_y = 0
        if self.shake_amount > 0:
            magnitude = self.shake_amount * self.settings.screen_shake
            shake_x = int(random.uniform(-magnitude, magnitude))
            shake_y = int(random.uniform(-magnitude, magnitude))
        if abs(scale - 1.0) < 1e-6:
            window.blit(self.canvas, (ox + shake_x, oy + shake_y))
        else:
            size = (int(config.BASE_W * scale), int(config.BASE_H * scale))
            window.blit(pygame.transform.scale(self.canvas, size), (ox + shake_x, oy + shake_y))

    def shutdown(self) -> None:
        save_settings(self.settings)
        self.audio.shutdown()
        pygame.quit()
