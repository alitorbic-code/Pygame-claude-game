"""Launcher for Shattered Realms: Echoes of the Void."""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Shattered Realms: Echoes of the Void")
    parser.add_argument("--debug", action="store_true", help="show the diagnostics overlay (F3 toggles it in game)")
    args = parser.parse_args(argv)

    try:
        import pygame  # noqa: F401
    except ImportError:
        print("Pygame is required. Install it with:  pip install -r requirements.txt")
        return 1

    from srealms.game import Game

    Game(debug=args.debug).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
