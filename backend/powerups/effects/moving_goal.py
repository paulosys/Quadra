"""MovingGoalEffect — causes all goal zones to oscillate."""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from models import Ball
from powerups.effects.base import PowerUpEffect

if TYPE_CHECKING:
    from events import EventBus


class MovingGoalEffect(PowerUpEffect):
    def apply_to_ball(self, ball: Ball, balls: list[Ball], next_id: Callable[[], int]) -> None:
        pass

    def apply_to_room(self, bus: "EventBus", collector: int | None) -> None:
        from events import GameEvent
        bus.publish(GameEvent.POWERUP_COLLECTED, effect="movinggoal", collector=collector)
