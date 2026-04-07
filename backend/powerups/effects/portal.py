"""PortalEffect — spawns two linked portals in the arena."""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from models import Ball
from powerups.effects.base import PowerUpEffect

if TYPE_CHECKING:
    from events import EventBus


class PortalEffect(PowerUpEffect):
    def apply_to_ball(self, ball: Ball, balls: list[Ball], next_id: Callable[[], int]) -> None:
        pass

    def apply_to_room(self, bus: "EventBus", collector: int | None) -> None:
        from events import GameEvent
        bus.publish(GameEvent.POWERUP_COLLECTED, effect="portal", collector=collector)
