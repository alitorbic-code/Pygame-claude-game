"""UI toolkit: cached text, themes, widgets, and keyboard/mouse menu navigation."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence

import pygame

from .config import Palette

_font_cache: dict[int, pygame.font.Font] = {}
_text_cache: dict[tuple, pygame.Surface] = {}


@dataclass(frozen=True)
class Theme:
    text: tuple[int, int, int]
    dim: tuple[int, int, int]
    accent: tuple[int, int, int]
    panel: tuple[int, int, int]
    edge: tuple[int, int, int]
    danger: tuple[int, int, int]


NORMAL_THEME = Theme(Palette.TEXT, Palette.TEXT_DIM, Palette.CYAN, Palette.PANEL, Palette.PANEL_EDGE, Palette.DANGER)
HIGH_CONTRAST_THEME = Theme((255, 255, 255), (200, 200, 200), (255, 255, 0), (0, 0, 0), (255, 255, 255), (255, 80, 80))


def get_theme(high_contrast: bool) -> Theme:
    return HIGH_CONTRAST_THEME if high_contrast else NORMAL_THEME


def get_font(size: int) -> pygame.font.Font:
    font = _font_cache.get(size)
    if font is None:
        font = pygame.font.Font(None, size)
        _font_cache[size] = font
    return font


def render_text_surface(text: str, size: int, color: tuple[int, int, int]) -> pygame.Surface:
    key = (text, size, color)
    surface = _text_cache.get(key)
    if surface is None:
        if len(_text_cache) > 400:
            _text_cache.clear()
        surface = get_font(size).render(text, True, color)
        _text_cache[key] = surface
    return surface


def draw_text(surface: pygame.Surface, text: str, size: int, color: tuple[int, int, int],
              pos: tuple[float, float], anchor: str = "topleft", shadow: bool = False,
              alpha: int = 255) -> pygame.Rect:
    rendered = render_text_surface(text, size, color)
    rect = rendered.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    if shadow:
        surface.blit(render_text_surface(text, size, (0, 0, 0)), rect.move(2, 2))
    if alpha < 255:
        rendered = rendered.copy()
        rendered.set_alpha(alpha)
    surface.blit(rendered, rect)
    return rect


def draw_panel(surface: pygame.Surface, rect: pygame.Rect, theme: Theme, focused: bool = False,
               t: float = 0.0) -> None:
    pygame.draw.rect(surface, theme.panel, rect, border_radius=10)
    if focused:
        pulse = int(2 * math.sin(t * 6))
        pygame.draw.rect(surface, theme.accent, rect.inflate(6 + pulse, 6 + pulse), width=2, border_radius=12)
    pygame.draw.rect(surface, theme.accent if focused else theme.edge, rect,
                     width=3 if focused else 2, border_radius=10)


class Widget:
    def __init__(self, label: str, enabled: bool = True) -> None:
        self.label = label
        self.enabled = enabled
        self.rect = pygame.Rect(0, 0, 0, 0)

    def activate(self) -> bool:
        return False

    def adjust(self, direction: int) -> bool:
        return False

    def press(self, pos: tuple[int, int]) -> bool:
        """Mouse press; return True to begin a drag. Default: act like Enter."""
        self.activate()
        return False

    def value_text(self) -> str:
        return ""

    def draw(self, surface: pygame.Surface, focused: bool, theme: Theme, t: float) -> None:
        draw_panel(surface, self.rect, theme, focused and self.enabled, t)
        color = theme.text if self.enabled else theme.dim
        draw_text(surface, self.label, 32, color, (self.rect.x + 20, self.rect.centery), "midleft")
        text = self.value_text()
        if text:
            draw_text(surface, text, 30, theme.accent if self.enabled else theme.dim,
                      (self.rect.right - 20, self.rect.centery), "midright")


class Button(Widget):
    def __init__(self, label: str, callback: Callable[[], None], enabled: bool = True) -> None:
        super().__init__(label, enabled)
        self.callback = callback

    def activate(self) -> bool:
        if not self.enabled:
            return False
        self.callback()
        return True

    def draw(self, surface: pygame.Surface, focused: bool, theme: Theme, t: float) -> None:
        draw_panel(surface, self.rect, theme, focused and self.enabled, t)
        color = theme.text if self.enabled else theme.dim
        if focused and self.enabled:
            color = theme.accent
        draw_text(surface, self.label, 38, color, self.rect.center, "center")


class Toggle(Widget):
    def __init__(self, label: str, getter: Callable[[], bool], setter: Callable[[bool], None]) -> None:
        super().__init__(label)
        self.getter, self.setter = getter, setter

    def activate(self) -> bool:
        self.setter(not self.getter())
        return True

    def adjust(self, direction: int) -> bool:
        return self.activate()

    def value_text(self) -> str:
        return "ON" if self.getter() else "OFF"


class Choice(Widget):
    def __init__(self, label: str, options: Sequence[str], getter: Callable[[], int],
                 setter: Callable[[int], None]) -> None:
        super().__init__(label)
        self.options = list(options)
        self.getter, self.setter = getter, setter

    def adjust(self, direction: int) -> bool:
        self.setter((self.getter() + direction) % len(self.options))
        return True

    def activate(self) -> bool:
        return self.adjust(1)

    def value_text(self) -> str:
        return self.options[self.getter() % len(self.options)]


class Slider(Widget):
    def __init__(self, label: str, getter: Callable[[], float], setter: Callable[[float], None],
                 step: float = 0.05) -> None:
        super().__init__(label)
        self.getter, self.setter, self.step = getter, setter, step

    @property
    def value(self) -> float:
        return max(0.0, min(1.0, self.getter()))

    def track_rect(self) -> pygame.Rect:
        return pygame.Rect(self.rect.right - 280, self.rect.centery - 5, 190, 10)

    def adjust(self, direction: int) -> bool:
        self.setter(max(0.0, min(1.0, round(self.value + direction * self.step, 4))))
        return True

    def set_from_x(self, x: int) -> None:
        track = self.track_rect()
        fraction = max(0.0, min(1.0, (x - track.x) / track.width))
        self.setter(round(round(fraction / self.step) * self.step, 4))

    def press(self, pos: tuple[int, int]) -> bool:
        if self.track_rect().inflate(24, 28).collidepoint(pos):
            self.set_from_x(pos[0])
            return True
        return False

    def draw(self, surface: pygame.Surface, focused: bool, theme: Theme, t: float) -> None:
        draw_panel(surface, self.rect, theme, focused, t)
        draw_text(surface, self.label, 32, theme.text, (self.rect.x + 20, self.rect.centery), "midleft")
        track = self.track_rect()
        pygame.draw.rect(surface, theme.edge, track, border_radius=5)
        fill = track.copy()
        fill.width = int(track.width * self.value)
        if fill.width > 0:
            pygame.draw.rect(surface, theme.accent, fill, border_radius=5)
        pygame.draw.circle(surface, theme.text, (track.x + int(track.width * self.value), track.centery), 9)
        draw_text(surface, f"{int(round(self.value * 100))}%", 30, theme.accent,
                  (self.rect.right - 18, self.rect.centery), "midright")


class MenuList:
    """Vertical list of widgets with keyboard, mouse, and slider-drag support."""

    def __init__(self, game: Any, widgets: Sequence[Widget], center_x: int, top: int,
                 width: int = 560, row_height: int = 54, spacing: int = 10) -> None:
        self.game = game
        self.widgets = list(widgets)
        self._dragging: Optional[Slider] = None
        y = top
        for widget in self.widgets:
            widget.rect = pygame.Rect(center_x - width // 2, y, width, row_height)
            y += row_height + spacing
        self.focus = next((i for i, w in enumerate(self.widgets) if w.enabled), 0)

    def _sound(self, name: str) -> None:
        self.game.audio.play(name)

    def move(self, step: int) -> None:
        count = len(self.widgets)
        index = self.focus
        for _ in range(count):
            index = (index + step) % count
            if self.widgets[index].enabled:
                break
        if index != self.focus:
            self.focus = index
            self._sound("ui_move")

    def _focus_at(self, pos: tuple[int, int]) -> Optional[int]:
        for i, widget in enumerate(self.widgets):
            if widget.enabled and widget.rect.collidepoint(pos):
                return i
        return None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            key = event.key
            if key in (pygame.K_UP, pygame.K_w):
                self.move(-1)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.move(1)
            elif key in (pygame.K_LEFT, pygame.K_a):
                if self.widgets[self.focus].adjust(-1):
                    self._sound("ui_move")
            elif key in (pygame.K_RIGHT, pygame.K_d):
                if self.widgets[self.focus].adjust(1):
                    self._sound("ui_move")
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                widget = self.widgets[self.focus]
                if widget.enabled and widget.activate():
                    self._sound("ui_select")
        elif event.type == pygame.MOUSEMOTION:
            if self._dragging is not None:
                self._dragging.set_from_x(event.pos[0])
                return
            hovered = self._focus_at(event.pos)
            if hovered is not None and hovered != self.focus:
                self.focus = hovered
                self._sound("ui_move")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hovered = self._focus_at(event.pos)
            if hovered is not None:
                self.focus = hovered
                widget = self.widgets[hovered]
                if widget.press(event.pos):
                    self._dragging = widget if isinstance(widget, Slider) else None
                    self._sound("ui_move")
                elif not isinstance(widget, Slider):
                    self._sound("ui_select")
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = None

    def draw(self, surface: pygame.Surface) -> None:
        theme = get_theme(self.game.settings.high_contrast)
        for i, widget in enumerate(self.widgets):
            widget.draw(surface, i == self.focus, theme, self.game.time)
