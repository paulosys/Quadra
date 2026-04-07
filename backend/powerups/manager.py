"""
PowerUpManager — spawn queue/timer and power-up collision detection.

Ball-level and room-level effects are delegated to PowerUpEffectFactory
(Strategy + Factory patterns), eliminating the if/elif dispatch chain.
"""
from __future__ import annotations

import math
import random
from typing import Callable, List

from config import (
    BALL_R,
    FIELD_MARGIN,
    MAX_POWERUPS_ON_FIELD,
    POWERUP_QUEUE_SIZE,
    POWERUP_RADIUS,
    POWERUP_SPAWN_MAX,
    POWERUP_SPAWN_MIN,
    POWERUP_TYPES,
    POWERUP_WEIGHTS,
    TICK_DT,
)
from models import Ball, PowerUp
from powerups.effects.factory import PowerUpEffectFactory

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from events import EventBus


class PowerUpManager:
    """Manages powerup lifecycle: queue, spawning, collision detection, and effect dispatch."""

    def __init__(self) -> None:
        self.spawn_timer: float = 0.0
        self._queue: List[str] = []
        self._refill_queue()

    # ── Public API ────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Call at the start of each round."""
        self._refill_queue()
        self.spawn_timer = random.uniform(POWERUP_SPAWN_MIN, POWERUP_SPAWN_MAX)

    def tick(
        self,
        powerups: List[PowerUp],
        balls:    List[Ball],
        next_id:  Callable[[], int],
        bus:      "EventBus",
    ) -> List[tuple[str, int | None]]:
        """
        Advance one tick: maybe spawn, detect collections, dispatch effects.
        Returns list of (powerup_type, collector_slot) tuples.
        """
        self.spawn_timer -= TICK_DT
        if self.spawn_timer <= 0:
            self._spawn(powerups, next_id)
            self.spawn_timer = random.uniform(POWERUP_SPAWN_MIN, POWERUP_SPAWN_MAX)

        return self._check_collisions(powerups, balls, next_id, bus)

    def queue_snapshot(self) -> List[str]:
        return self._queue[:]

    # ── Internals ─────────────────────────────────────────────────────────────

    def _refill_queue(self) -> None:
        self._queue = [
            random.choices(POWERUP_TYPES, weights=POWERUP_WEIGHTS)[0]
            for _ in range(POWERUP_QUEUE_SIZE)
        ]

    def _next_from_queue(self) -> str:
        ptype = self._queue.pop(0)
        self._queue.append(random.choices(POWERUP_TYPES, weights=POWERUP_WEIGHTS)[0])
        return ptype

    def _spawn(self, powerups: List[PowerUp], next_id: Callable[[], int]) -> None:
        if len(powerups) >= MAX_POWERUPS_ON_FIELD:
            return
        fm = FIELD_MARGIN + 0.18
        powerups.append(PowerUp(
            id=next_id(),
            x=random.uniform(fm, 1 - fm),
            y=random.uniform(fm, 1 - fm),
            type=self._next_from_queue(),
        ))

    def _check_collisions(
        self,
        powerups: List[PowerUp],
        balls:    List[Ball],
        next_id:  Callable[[], int],
        bus:      "EventBus",
    ) -> List[tuple[str, int | None]]:
        collected: List[tuple[str, int | None]] = []
        hit: set[int] = set()

        for ball in balls:
            for pu in powerups:
                if id(pu) in hit:
                    continue
                dx = ball.x - pu.x
                dy = ball.y - pu.y
                if math.sqrt(dx * dx + dy * dy) < BALL_R + POWERUP_RADIUS:
                    collector = ball.last_touch
                    collected.append((pu.type, collector))
                    effect = PowerUpEffectFactory.create(pu.type)
                    effect.apply_to_ball(ball, balls, next_id)
                    effect.apply_to_room(bus, collector)
                    hit.add(id(pu))

        for pu in list(powerups):
            if id(pu) in hit:
                powerups.remove(pu)

        return collected
