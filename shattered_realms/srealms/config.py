"""Central configuration: every tunable constant lives here."""
from __future__ import annotations

from pathlib import Path

TITLE = "SHATTERED REALMS: ECHOES OF THE VOID"
SHORT_TITLE = "Shattered Realms"
VERSION = "0.2.0"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSET_DIR = PROJECT_ROOT / "assets"

# The game always renders to a fixed-size canvas that is scaled to the window.
BASE_W = 1280
BASE_H = 720
FPS_TARGET = 60
MAX_FRAME_DT = 1.0 / 20.0  # clamp long frames so physics never explodes

RESOLUTIONS = ((960, 540), (1280, 720), (1600, 900), (1920, 1080))
DEFAULT_RESOLUTION_INDEX = 1

MAX_PARTICLES = 1500
TOAST_SECONDS = 3.0
MAX_TOASTS = 4


class Palette:
    BG_TOP = (8, 6, 22)
    BG_BOTTOM = (30, 14, 54)
    VOID_PURPLE = (140, 90, 255)
    CYAN = (90, 220, 255)
    GOLD = (255, 210, 110)
    EMBER = (255, 130, 80)
    TEXT = (232, 232, 248)
    TEXT_DIM = (130, 130, 165)
    DANGER = (255, 90, 110)
    PANEL = (18, 16, 36)
    PANEL_EDGE = (70, 60, 120)
