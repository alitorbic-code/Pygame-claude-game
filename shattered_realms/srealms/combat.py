"""Combat math shared by the player, enemies, and projectiles (no pygame dependency)."""
from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Health:
    max_hp: float
    invuln_time: float = 0.0  # seconds of invulnerability granted after taking damage
    hp: float = field(init=False)
    invuln: float = field(default=0.0, init=False)
    flash: float = field(default=0.0, init=False)  # drives the white hit-flash

    def __post_init__(self) -> None:
        self.hp = float(self.max_hp)

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def fraction(self) -> float:
        return max(0.0, min(1.0, self.hp / self.max_hp)) if self.max_hp > 0 else 0.0

    def update(self, dt: float) -> None:
        self.invuln = max(0.0, self.invuln - dt)
        self.flash = max(0.0, self.flash - dt)

    def damage(self, amount: float, ignore_invuln: bool = False) -> float:
        """Apply damage and return the amount actually dealt (0 if blocked)."""
        if amount <= 0 or not self.alive or (self.invuln > 0 and not ignore_invuln):
            return 0.0
        dealt = min(self.hp, float(amount))
        self.hp -= dealt
        self.invuln = self.invuln_time
        self.flash = 0.12
        return dealt

    def heal(self, amount: float) -> float:
        if amount <= 0 or not self.alive:
            return 0.0
        healed = min(self.max_hp - self.hp, float(amount))
        self.hp += healed
        return healed


def mitigate(amount: float, armor: float) -> float:
    """Diminishing-returns armor: 100 armor halves damage."""
    return amount * 100.0 / (100.0 + max(0.0, armor))


def roll_damage(base: float, crit_chance: float, crit_mult: float, armor: float,
                rng: random.Random) -> tuple[int, bool]:
    """Return (final damage, was_crit). Damage is always at least 1."""
    crit = rng.random() < crit_chance
    amount = base * (crit_mult if crit else 1.0)
    return max(1, round(mitigate(amount, armor))), crit
