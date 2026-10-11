# SHATTERED REALMS: ECHOES OF THE VOID

A 2D action-RPG / roguelike built with Python and Pygame. All graphics and sound are
generated procedurally, so the game launches with no external assets.

**Current build: Phase 2 of 8 (movement, combat, enemies).** See "Status" below.

## Install and run

Requires Python 3.10+.

    pip install -r requirements.txt
    python main.py            # add --debug for the diagnostics overlay

Run the tests (pure-logic tests need no pygame; the smoke test uses real pygame with dummy
drivers if installed, otherwise a stand-in):

    python -m unittest discover -s tests -t .

Count real source lines (excludes blanks, comments, docstrings):

    python tools/count_lines.py

## Controls (defaults)

| Action | Key |
|---|---|
| Menus | Arrows or WASD, Enter/Space select, Esc back, mouse supported |
| Move | A / D or Left / Right |
| Jump | Space or Up. Hold for full height, tap for a short hop |
| Double jump | Press jump again in the air |
| Wall slide / wall jump | Hold toward a wall while falling, then jump |
| Drop through a thin platform | S (or Down) + Jump |
| Dash (brief invulnerability, one per air time) | Left Shift |
| Attack (3-hit combo, last hit is heavy) | J or left mouse button |
| Pause | Esc |
| Fullscreen / debug overlay | F11 (or Alt+Enter) / F3 |

Tips: swinging at an enemy projectile deflects it back at the shooter. Dashing through a
shot dodges it. Defeat all nine guardians to break the seal on the exit portal.

Settings are stored per user (Windows: `%APPDATA%/ShatteredRealms`, macOS:
`~/Library/Application Support/ShatteredRealms`, Linux: `~/.local/share/shattered_realms`).
Set `SHATTERED_REALMS_HOME` to override. A corrupt settings file is renamed to
`settings.json.corrupt` and never silently overwritten.

## Layout

    main.py                   launcher
    srealms/config.py         constants and palette
    srealms/settings.py       validated settings + atomic save/load      (no pygame)
    srealms/state_manager.py  state stack with deferred transitions      (no pygame)
    srealms/physics.py        AABB tile-map collision, one-way platforms (no pygame)
    srealms/combat.py         health, i-frames, damage/armor/crit math   (no pygame)
    srealms/camera.py         smooth follow camera                       (no pygame)
    srealms/world.py          simulation: player, enemies, projectiles   (no pygame)
    srealms/entities/         player.py, enemies.py, projectile.py       (no pygame)
    srealms/levels.py         level builder + the Proving Grounds level  (no pygame)
    srealms/game.py           window, main loop, hotkeys, toasts, debug overlay
    srealms/render.py         procedural world rendering
    srealms/ui.py             widgets: Button, Slider, Toggle, Choice, MenuList
    srealms/graphics.py       background, particles, floating text
    srealms/audio.py          audio manager (procedural sounds, optional files)
    srealms/input_map.py      action -> key mapping
    srealms/states/           menu, settings, credits, play, pause, result
    tests/                    unit tests + headless smoke test
    assets/music, assets/sfx  optional: drop .ogg/.mp3/.wav files here

The simulation runs on a fixed 120 Hz step, independent of frame rate, and all game logic
lives in pygame-free modules so it can be unit-tested.

Optional audio: put `menu.ogg` / `explore.ogg` in `assets/music/`, or `.wav/.ogg` files in
`assets/sfx/` named like the built-in sounds (`jump`, `hit`, `swing`, ...) to override them.

## Status (Phase 2 of 8)

Working in tests and written for the game: platforming (run, variable-height jump, double
jump, coyote time, jump buffering, wall slide, wall jump, dash with i-frames, one-way
platform drop-through), 3-hit melee combo with lunge, crits, knockback, stagger and hit-stop,
projectile deflection, three enemy types (Walker, Flyer, Shooter) with sight/patrol/chase/
telegraphed-attack AI, spikes and void-fall respawn, smooth camera with culling, damage
numbers, particles, screen shake, HUD, game-over and victory screens, plus the Phase 1
menus/settings/pause.

Not yet built: items, loot, inventory, equipment, abilities/skill trees, procedural
generation, biomes, bosses, NPCs/quests/dialogue, crafting, progress save/load,
achievements, and most of the 300-idea list. Those are Phases 3 to 8.

## Known limitations

- Automated tests cover the logic, plus a smoke test that drives the whole game through
  its screens. No one has yet *played* it with a real window: feel, balance and visuals
  are unverified.
- Level reachability (e.g. the wall-shaft route) is designed by arithmetic, not verified
  by a bot. An alternate stair route leads to the same ledge.
- "Continue" is disabled until the progress-save system exists.
- Key rebinding is stored in settings but has no in-game UI yet.
