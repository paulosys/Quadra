"""
events.py — Observer pattern: EventBus + GameEvent enum.

Decouples Room-level effect managers from PowerUpManager and from each other.
"""
from __future__ import annotations

from enum import Enum, auto
from typing import Any, Callable


class GameEvent(Enum):
    GOAL_SCORED       = auto()  # kwargs: scored_side, scorer_slot
    PLAYER_ELIMINATED = auto()  # kwargs: slot
    POWERUP_COLLECTED = auto()  # kwargs: effect, collector
    ROUND_START       = auto()
    GAME_OVER         = auto()


class EventBus:
    """Simple synchronous pub/sub bus for in-process game events."""

    def __init__(self) -> None:
        self._listeners: dict[GameEvent, list[Callable[..., None]]] = {}

    def subscribe(self, event: GameEvent, callback: Callable[..., None]) -> None:
        self._listeners.setdefault(event, []).append(callback)

    def publish(self, event: GameEvent, **kwargs: Any) -> None:
        for cb in self._listeners.get(event, []):
            cb(**kwargs)
