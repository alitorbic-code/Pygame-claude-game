"""Maps gameplay actions to pygame key codes using the player's bindings."""
from __future__ import annotations

from typing import Any, Mapping

import pygame

from .settings import DEFAULT_BINDINGS


class InputMap:
    def __init__(self, bindings: Mapping[str, str]) -> None:
        self.key_for: dict[str, int] = {}
        self._actions_for_key: dict[int, list[str]] = {}
        self.rebuild(bindings)

    @staticmethod
    def _resolve(name: str, fallback: str) -> int:
        for candidate in (name, fallback):
            try:
                return pygame.key.key_code(candidate)
            except ValueError:
                continue
        return pygame.K_UNKNOWN

    def rebuild(self, bindings: Mapping[str, str]) -> None:
        self.key_for = {}
        self._actions_for_key = {}
        for action, default in DEFAULT_BINDINGS.items():
            key = self._resolve(bindings.get(action, default), default)
            self.key_for[action] = key
            self._actions_for_key.setdefault(key, []).append(action)

    def actions_for_key(self, key: int) -> list[str]:
        return self._actions_for_key.get(key, [])

    def is_down(self, action: str, pressed: Any) -> bool:
        key = self.key_for.get(action, pygame.K_UNKNOWN)
        return key != pygame.K_UNKNOWN and bool(pressed[key])

    def key_name(self, action: str) -> str:
        key = self.key_for.get(action, pygame.K_UNKNOWN)
        return pygame.key.name(key) if key != pygame.K_UNKNOWN else "?"
