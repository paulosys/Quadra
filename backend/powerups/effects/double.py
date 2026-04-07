"""DoubleEffect — spawns a second ball in the opposite direction."""
from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Callable

from config import MAX_BALLS
from models import Ball
from powerups.effects.base import PowerUpEffect

if TYPE_CHECKING:
    from events import EventBus


class DoubleEffect(PowerUpEffect):
    def apply_to_ball(self, ball: Ball, balls: list[Ball], next_id: Callable[[], int]) -> None:
        if len(balls) < MAX_BALLS:
            angle = math.atan2(ball.vy, ball.vx) + math.pi + random.uniform(-0.5, 0.5)
            spd = ball.speed
            balls.append(Ball(
                id=next_id(),
                x=ball.x, y=ball.y,
                vx=math.cos(angle) * spd,
                vy=math.sin(angle) * spd,
            ))

    def apply_to_room(self, bus: "EventBus", collector: int | None) -> None:
        pass
