"""SnitchEffect — makes the ball dart and dodge erratically."""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from config import SNITCH_DURATION
from models import Ball
from powerups.effects.base import PowerUpEffect

if TYPE_CHECKING:
    from events import EventBus


class SnitchEffect(PowerUpEffect):
    def apply_to_ball(self, ball: Ball, balls: list[Ball], next_id: Callable[[], int]) -> None:
        ball.apply_snitch(SNITCH_DURATION)

    def apply_to_room(self, bus: "EventBus", collector: int | None) -> None:
        pass
