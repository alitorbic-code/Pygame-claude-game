"""Player settings: defaults, validation, and safe persistence (no pygame dependency)."""
from __future__ import annotations

import json
import math
import os
import sys
import tempfile
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Mapping, Optional

from . import config

SETTINGS_FILENAME = "settings.json"
SETTINGS_FORMAT_VERSION = 1

# Action name -> pygame key name (as understood by pygame.key.key_code).
DEFAULT_BINDINGS: dict[str, str] = {
    "move_left": "a",
    "move_right": "d",
    "move_up": "w",
    "move_down": "s",
    "jump": "space",
    "dash": "left shift",
    "attack": "j",
    "ability": "k",
    "interact": "e",
    "inventory": "tab",
    "pause": "escape",
}


def user_data_dir() -> Path:
    """Per-user folder for settings and (later) save files."""
    override = os.environ.get("SHATTERED_REALMS_HOME")
    if override:
        return Path(override)
    if sys.platform.startswith("win"):
        return Path(os.environ.get("APPDATA") or Path.home()) / "ShatteredRealms"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ShatteredRealms"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "shattered_realms"


def settings_path() -> Path:
    return user_data_dir() / SETTINGS_FILENAME


def _number(value: Any, default: float, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if math.isnan(value) or math.isinf(value):
        return default
    return max(low, min(high, float(value)))


def _index(value: Any, default: int, count: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value if 0 <= value < count else default


def _flag(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _binding_name(value: Any, default: str) -> str:
    if isinstance(value, str):
        name = value.strip()
        if 1 <= len(name) <= 24 and name.isprintable():
            return name
    return default


@dataclass
class Settings:
    master_volume: float = 0.8
    music_volume: float = 0.7
    sfx_volume: float = 0.8
    screen_shake: float = 1.0
    fullscreen: bool = False
    resolution_index: int = config.DEFAULT_RESOLUTION_INDEX
    show_fps: bool = False
    high_contrast: bool = False
    bindings: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_BINDINGS))

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"format_version": SETTINGS_FORMAT_VERSION}
        for item in fields(self):
            value = getattr(self, item.name)
            data[item.name] = dict(value) if isinstance(value, dict) else value
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Settings":
        """Build settings from untrusted data; every bad field falls back to its default."""
        s = cls()
        s.master_volume = _number(data.get("master_volume"), s.master_volume, 0.0, 1.0)
        s.music_volume = _number(data.get("music_volume"), s.music_volume, 0.0, 1.0)
        s.sfx_volume = _number(data.get("sfx_volume"), s.sfx_volume, 0.0, 1.0)
        s.screen_shake = _number(data.get("screen_shake"), s.screen_shake, 0.0, 1.0)
        s.fullscreen = _flag(data.get("fullscreen"), s.fullscreen)
        s.resolution_index = _index(data.get("resolution_index"), s.resolution_index, len(config.RESOLUTIONS))
        s.show_fps = _flag(data.get("show_fps"), s.show_fps)
        s.high_contrast = _flag(data.get("high_contrast"), s.high_contrast)
        raw = data.get("bindings")
        if isinstance(raw, Mapping):
            for action, default in DEFAULT_BINDINGS.items():
                s.bindings[action] = _binding_name(raw.get(action), default)
        return s

    def reset_to_defaults(self) -> None:
        fresh = Settings()
        for item in fields(self):
            setattr(self, item.name, getattr(fresh, item.name))


def _quarantine(path: Path, message: str) -> str:
    """Move an unreadable settings file aside so it is never silently overwritten."""
    target = path.with_suffix(path.suffix + ".corrupt")
    try:
        os.replace(path, target)
    except OSError:
        return f"{message} Using defaults."
    return f"{message} Backed up as {target.name}; using defaults."


def load_settings(path: Optional[Path] = None) -> tuple[Settings, Optional[str]]:
    """Return (settings, warning). A missing file is normal and produces no warning."""
    path = Path(path) if path else settings_path()
    if not path.exists():
        return Settings(), None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # JSONDecodeError/UnicodeDecodeError are ValueErrors
        return Settings(), _quarantine(path, f"Settings file unreadable ({type(exc).__name__}).")
    if not isinstance(raw, dict):
        return Settings(), _quarantine(path, "Settings file had an unexpected format.")
    return Settings.from_dict(raw), None


def save_settings(settings: Settings, path: Optional[Path] = None) -> bool:
    """Atomically write settings; returns False (and leaves any old file intact) on failure."""
    path = Path(path) if path else settings_path()
    temp_name: Optional[str] = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix="settings_", suffix=".tmp", delete=False
        ) as handle:
            temp_name = handle.name
            json.dump(settings.to_dict(), handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        return True
    except (OSError, TypeError, ValueError):
        if temp_name:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
        return False
