"""SpeedEffect — boosts the ball's speed for a fixed duration."""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from config import SPEED_BOOST_DURATION, SPEED_BOOST_FACTOR
from models import Ball
from powerups.effects.base import PowerUpEffect

if TYPE_CHECKING:
    from events import EventBus


class SpeedEffect(PowerUpEffect):
    def apply_to_ball(self, ball: Ball, balls: list[Ball], next_id: Callable[[], int]) -> None:
        ball.apply_boost(SPEED_BOOST_FACTOR, SPEED_BOOST_DURATION)

    def apply_to_room(self, bus: "EventBus", collector: int | None) -> None:
        pass
