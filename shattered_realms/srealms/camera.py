"""Smooth-follow camera clamped to the world (no pygame dependency)."""
from __future__ import annotations

import math


class Camera:
    def __init__(self, view_w: float, view_h: float, world_w: float, world_h: float,
                 smoothing: float = 7.0) -> None:
        self.view_w, self.view_h = view_w, view_h
        self.world_w, self.world_h = world_w, world_h
        self.smoothing = smoothing
        self.x = 0.0
        self.y = 0.0

    def _clamp(self, x: float, y: float) -> tuple[float, float]:
        if self.world_w <= self.view_w:
            x = (self.world_w - self.view_w) / 2
        else:
            x = max(0.0, min(self.world_w - self.view_w, x))
        if self.world_h <= self.view_h:
            y = (self.world_h - self.view_h) / 2
        else:
            y = max(0.0, min(self.world_h - self.view_h, y))
        return x, y

    def snap(self, target_x: float, target_y: float) -> None:
        self.x, self.y = self._clamp(target_x - self.view_w / 2, target_y - self.view_h / 2)

    def follow(self, target_x: float, target_y: float, dt: float) -> None:
        """Frame-rate-independent exponential smoothing toward the target."""
        blend = 1.0 - math.exp(-self.smoothing * dt)
        goal_x, goal_y = self._clamp(target_x - self.view_w / 2, target_y - self.view_h / 2)
        self.x += (goal_x - self.x) * blend
        self.y += (goal_y - self.y) * blend

    def to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        return int(wx - self.x), int(wy - self.y)

    def is_visible(self, x: float, y: float, w: float, h: float, margin: float = 64.0) -> bool:
        return (x + w > self.x - margin and x < self.x + self.view_w + margin
                and y + h > self.y - margin and y < self.y + self.view_h + margin)
