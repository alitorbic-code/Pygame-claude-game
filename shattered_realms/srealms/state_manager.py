"""Stack-based state manager (no pygame dependency, so it is unit-testable).

Transitions are queued and applied once per frame by ``apply_pending`` so a state
can safely push/pop itself from inside ``update`` or ``handle_event``.
"""
from __future__ import annotations

from typing import Any, Callable


class State:
    """Base class for menus, gameplay screens, and overlays."""

    name = "state"
    transparent = False  # if True, the state underneath is drawn first (pause overlays)

    def __init__(self, game: Any) -> None:
        self.game = game

    def enter(self, **kwargs: Any) -> None: ...
    def exit(self) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def on_focus_lost(self) -> None: ...
    def handle_event(self, event: Any) -> None: ...
    def update(self, dt: float) -> None: ...
    def draw(self, surface: Any) -> None: ...

    def debug_info(self) -> list[str]:
        return []


class StateManager:
    def __init__(self, game: Any) -> None:
        self.game = game
        self._factories: dict[str, Callable[[Any], State]] = {}
        self._stack: list[State] = []
        self._pending: list[tuple[str, str, dict[str, Any]]] = []

    def register(self, name: str, factory: Callable[[Any], State]) -> None:
        self._factories[name] = factory

    def _require(self, name: str) -> None:
        if name not in self._factories:
            raise KeyError(f"Unknown state: {name!r}")

    def push(self, name: str, **kwargs: Any) -> None:
        self._require(name)
        self._pending.append(("push", name, kwargs))

    def pop(self) -> None:
        self._pending.append(("pop", "", {}))

    def switch(self, name: str, **kwargs: Any) -> None:
        """Replace the top state."""
        self._require(name)
        self._pending.append(("switch", name, kwargs))

    def reset(self, name: str, **kwargs: Any) -> None:
        """Discard the whole stack and start fresh from one state."""
        self._require(name)
        self._pending.append(("reset", name, kwargs))

    def apply_pending(self) -> None:
        while self._pending:
            op, name, kwargs = self._pending.pop(0)
            if op == "push":
                if self._stack:
                    self._stack[-1].pause()
                self._enter_new(name, kwargs)
            elif op == "pop":
                if self._stack:
                    self._stack.pop().exit()
                    if self._stack:
                        self._stack[-1].resume()
            elif op == "switch":
                if self._stack:
                    self._stack.pop().exit()
                self._enter_new(name, kwargs)
            elif op == "reset":
                while self._stack:
                    self._stack.pop().exit()
                self._enter_new(name, kwargs)

    def _enter_new(self, name: str, kwargs: dict[str, Any]) -> None:
        state = self._factories[name](self.game)
        self._stack.append(state)
        state.enter(**kwargs)

    @property
    def current(self) -> State | None:
        return self._stack[-1] if self._stack else None

    @property
    def is_empty(self) -> bool:
        return not self._stack

    @property
    def has_pending(self) -> bool:
        return bool(self._pending)

    @property
    def stack_names(self) -> list[str]:
        return [state.name for state in self._stack]

    def on_focus_lost(self) -> None:
        if self._stack:
            self._stack[-1].on_focus_lost()

    def handle_event(self, event: Any) -> None:
        if self._stack:
            self._stack[-1].handle_event(event)

    def update(self, dt: float) -> None:
        if self._stack:
            self._stack[-1].update(dt)

    def draw(self, surface: Any) -> None:
        if not self._stack:
            return
        start = len(self._stack) - 1
        while start > 0 and self._stack[start].transparent:
            start -= 1
        for state in self._stack[start:]:
            state.draw(surface)
