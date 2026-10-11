"""Game states (screens and overlays) and their registration."""
from __future__ import annotations

from ..state_manager import StateManager
from .credits import CreditsState
from .menu import MenuState
from .pause import PauseState
from .play import PlayState
from .result import ResultState
from .settings_menu import SettingsState


def register_all(manager: StateManager) -> None:
    for state_class in (MenuState, SettingsState, CreditsState, PlayState, PauseState, ResultState):
        manager.register(state_class.name, state_class)
