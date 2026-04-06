"""
PowerUpManager — owns the spawn queue/timer and applies ball-level effects.

Room-level effects (e.g. moving goals) are signalled by returning the
powerup type in the collected list; the Room applies them itself, keeping
this class free of room state.
"""
from __future__ import annotations

import math
import random
from typing import Callable, List

from config import (
    BALL_R, BALL_SPEED_MAX, FIELD_MARGIN,
    MAX_BALLS, MAX_POWERUPS_ON_FIELD,
    POWERUP_QUEUE_SIZE, POWERUP_RADIUS,
    POWERUP_SPAWN_MAX, POWERUP_SPAWN_MIN,
    POWERUP_TYPES, POWERUP_WEIGHTS,
    SNITCH_DURATION,
    SPEED_BOOST_DURATION, SPEED_BOOST_FACTOR,
    TICK_DT,
)
from models import Ball, PowerUp


class PowerUpManager:
    """Manages powerup lifecycle: queue, spawning, collision, and ball effects."""

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
    ) -> List[tuple[str, int | None]]:
        """
        Advance one tick: maybe spawn, detect collections, apply ball effects.
        Returns list of (powerup_type, collector_slot) tuples (Room handles room-level ones).
        """
        self.spawn_timer -= TICK_DT
        if self.spawn_timer <= 0:
            self._spawn(powerups, next_id)
            self.spawn_timer = random.uniform(POWERUP_SPAWN_MIN, POWERUP_SPAWN_MAX)

        return self._check_collisions(powerups, balls, next_id)

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
                    collected.append((pu.type, ball.last_touch))
                    self._apply_to_ball(ball, pu, balls, next_id)
                    hit.add(id(pu))

        for pu in list(powerups):
            if id(pu) in hit:
                powerups.remove(pu)

        return collected

    def _apply_to_ball(
        self,
        ball:    Ball,
        pu:      PowerUp,
        balls:   List[Ball],
        next_id: Callable[[], int],
    ) -> None:
        """Apply ball-level effect. Room-level effects are left for the Room."""

        if pu.type == "double":
            if len(balls) < MAX_BALLS:
                angle = math.atan2(ball.vy, ball.vx) + math.pi + random.uniform(-0.5, 0.5)
                spd   = ball.speed
                balls.append(Ball(
                    id=next_id(),
                    x=ball.x, y=ball.y,
                    vx=math.cos(angle) * spd,
                    vy=math.sin(angle) * spd,
                ))

        elif pu.type == "speed":
            spd = ball.speed
            if spd > 0:
                new_spd = min(spd * SPEED_BOOST_FACTOR, BALL_SPEED_MAX * SPEED_BOOST_FACTOR)
                ball.vx = ball.vx / spd * new_spd
                ball.vy = ball.vy / spd * new_spd
            ball.boosted     = True
            ball.boost_timer = SPEED_BOOST_DURATION

        elif pu.type == "snitch":
            ball.snitched     = True
            ball.snitch_timer = SNITCH_DURATION
            # Dart away in a random direction at moderate speed
            angle = random.uniform(0, math.pi * 2)
            spd   = max(ball.speed, BALL_SPEED_MAX * 0.55)
            ball.vx = math.cos(angle) * spd
            ball.vy = math.sin(angle) * spd

        # "movinggoal" has no ball-level effect; Room reacts to it via collected list.
