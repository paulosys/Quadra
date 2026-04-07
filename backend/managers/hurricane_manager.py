"""
HurricaneManager — vortex effect that spins balls near the arena center.

Extracted from Room._tick_hurricane().
"""
from __future__ import annotations

import math
from typing import List

from config import (
    BALL_SPEED_INIT,
    HURRICANE_DURATION,
    HURRICANE_PULL,
    HURRICANE_RADIUS,
    HURRICANE_STRENGTH,
    TICK_DT,
)
from models import Ball


class HurricaneManager:
    """Manages the hurricane power-up room-level effect."""

    def __init__(self) -> None:
        self._timer: float = 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    def activate(self) -> None:
        """Start (or restart) the hurricane effect."""
        self._timer = HURRICANE_DURATION

    def reset(self) -> None:
        self._timer = 0.0

    @property
    def is_active(self) -> bool:
        return self._timer > 0

    def tick(self, dt: float, balls: List[Ball]) -> None:
        """Apply rotational vortex force to balls within hurricane radius."""
        if self._timer <= 0:
            return
        self._timer -= dt
        cx, cy = 0.5, 0.5
        for ball in balls:
            dx = ball.x - cx
            dy = ball.y - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if 0 < dist < HURRICANE_RADIUS:
                factor = 1.0 - dist / HURRICANE_RADIUS
                speed = math.sqrt(ball.vx * ball.vx + ball.vy * ball.vy)

                # Rotate velocity vector — creates orbital spin
                angle_delta = HURRICANE_STRENGTH * factor * max(1.0, speed / BALL_SPEED_INIT)
                cos_a = math.cos(angle_delta)
                sin_a = math.sin(angle_delta)
                ball.vx, ball.vy = (
                    ball.vx * cos_a - ball.vy * sin_a,
                    ball.vx * sin_a + ball.vy * cos_a,
                )

                # Centripetal pull toward center — keeps ball spiraling inward
                pull = HURRICANE_PULL * factor
                ball.vx -= (dx / dist) * pull
                ball.vy -= (dy / dist) * pull
