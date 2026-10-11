"""Centralized audio: procedural UI/gameplay blips, optional file-based sfx and music.

Everything degrades gracefully: no mixer, no audio files, or an unexpected mixer
format simply means silence rather than a crash.
"""
from __future__ import annotations

import array
import math
from pathlib import Path
from typing import Optional

import pygame

from .settings import Settings

_SFX_EXTENSIONS = (".wav", ".ogg")
_MUSIC_EXTENSIONS = (".ogg", ".mp3", ".wav")


class AudioManager:
    def __init__(self, settings: Settings, asset_dir: Path) -> None:
        self.settings = settings
        self.asset_dir = Path(asset_dir)
        self.available = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.current_music: Optional[str] = None
        self._init_mixer()

    def _init_mixer(self) -> None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self.available = pygame.mixer.get_init() is not None
        except (pygame.error, NotImplementedError, OSError):
            self.available = False
            return
        self._build_procedural_sounds()
        self._load_sfx_folder()
        self.apply_volumes()

    # -- sound construction ------------------------------------------------
    def _tone(self, freq: float, duration: float, volume: float, wave: str = "sine", slide: float = 0.0):
        init = pygame.mixer.get_init()
        if not init or init[1] != -16:
            return None
        rate, _, channels = init
        count = max(1, int(rate * duration))
        samples = array.array("h")
        phase = 0.0
        for i in range(count):
            progress = i / count
            phase += math.tau * (freq + slide * progress) / rate
            wobble = math.sin(phase)
            value = wobble if wave == "sine" else (1.0 if wobble >= 0 else -1.0)
            envelope = min(1.0, i / (0.004 * rate)) * (1.0 - progress) ** 2
            sample = int(32767 * volume * envelope * value)
            for _ in range(channels):
                samples.append(sample)
        try:
            return pygame.mixer.Sound(buffer=samples.tobytes())
        except pygame.error:
            return None

    def _build_procedural_sounds(self) -> None:
        recipes = {
            "ui_move": (660, 0.05, 0.30, "sine", 0),
            "ui_select": (520, 0.10, 0.35, "sine", 520),
            "ui_back": (440, 0.09, 0.30, "sine", -200),
            "jump": (360, 0.12, 0.25, "square", 320),
            "dash": (220, 0.14, 0.25, "square", -120),
            "hit": (140, 0.12, 0.35, "square", -80),
            "swing": (300, 0.08, 0.18, "square", -160),
            "shoot": (520, 0.10, 0.20, "square", -300),
            "hurt": (200, 0.22, 0.40, "square", -150),
            "enemy_die": (260, 0.25, 0.35, "square", -200),
            "lose": (300, 0.60, 0.35, "sine", -220),
            "win": (440, 0.45, 0.35, "sine", 440),
        }
        for name, (freq, dur, vol, wave, slide) in recipes.items():
            sound = self._tone(freq, dur, vol, wave, slide)
            if sound is not None:
                self.sounds[name] = sound

    def _load_sfx_folder(self) -> None:
        folder = self.asset_dir / "sfx"
        if not folder.is_dir():
            return
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() in _SFX_EXTENSIONS:
                try:
                    self.sounds[path.stem] = pygame.mixer.Sound(str(path))
                except pygame.error:
                    continue

    # -- playback ----------------------------------------------------------
    @property
    def sfx_level(self) -> float:
        return self.settings.master_volume * self.settings.sfx_volume

    @property
    def music_level(self) -> float:
        return self.settings.master_volume * self.settings.music_volume

    def play(self, name: str) -> None:
        sound = self.sounds.get(name)
        level = self.sfx_level
        if not self.available or sound is None or level <= 0.001:
            return
        sound.set_volume(level)
        sound.play()

    def play_music(self, name: str, loop: bool = True) -> None:
        if not self.available or name == self.current_music:
            return
        self.current_music = name
        folder = self.asset_dir / "music"
        for ext in _MUSIC_EXTENSIONS:
            path = folder / f"{name}{ext}"
            if path.is_file():
                try:
                    pygame.mixer.music.load(str(path))
                    pygame.mixer.music.set_volume(self.music_level)
                    pygame.mixer.music.play(-1 if loop else 0)
                    return
                except pygame.error:
                    break
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass

    def apply_volumes(self) -> None:
        if not self.available:
            return
        try:
            pygame.mixer.music.set_volume(self.music_level)
        except pygame.error:
            pass

    def shutdown(self) -> None:
        if self.available:
            try:
                pygame.mixer.quit()
            except pygame.error:
                pass
            self.available = False
