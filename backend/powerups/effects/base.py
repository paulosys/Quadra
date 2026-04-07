"""PowerUpEffect — abstract base for all power-up effects (Strategy pattern)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable

from models import Ball

if TYPE_CHECKING:
    from events import EventBus


class PowerUpEffect(ABC):
    """Each subclass handles exactly one power-up type.

    Ball-level effects are applied immediately; room-level effects are
    signalled through the EventBus so Room managers can react independently.
    """

    @abstractmethod
    def apply_to_ball(
        self,
        ball: Ball,
        balls: list[Ball],
        next_id: Callable[[], int],
    ) -> None:
        """Apply ball-level effect. May add new balls (e.g. double)."""

    @abstractmethod
    def apply_to_room(self, bus: "EventBus", collector: int | None) -> None:
        """Signal room-level effect via the EventBus."""
