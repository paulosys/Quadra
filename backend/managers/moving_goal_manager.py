"""
MovingGoalManager — oscillating goal-zone offsets.

Extracted from Room._tick_moving_goals() and the corner goal timer logic.
Two activation modes:
  - activate_global(): regular power-up, affects all goals simultaneously.
  - activate_slot(slot): corner power-up, affects one adversary's goal.
"""
from __future__ import annotations

import math

from config import (
    CORNER_GOAL_DURATION,
    MOVING_GOAL_AMP,
    MOVING_GOAL_DURATION,
    MOVING_GOAL_SPEED,
    TICK_DT,
)


class MovingGoalManager:
    """Manages goal-offset animations for moving-goal power-up effects."""

    def __init__(self, n_sides: int) -> None:
        self.goal_offsets: list[float] = [0.0] * n_sides
        self._global_timer:     float  = 0.0
        self._global_move_time: float  = 0.0
        self._slot_timers:   list[float] = [0.0] * n_sides
        self._corner_move_time: float  = 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    def activate_global(self) -> None:
        """Start (or reset) the global moving-goal effect."""
        if self._global_timer <= 0:
            self._global_move_time = 0.0
        self._global_timer = MOVING_GOAL_DURATION

    def activate_slot(self, slot: int, duration: float = CORNER_GOAL_DURATION) -> None:
        """Activate the moving-goal effect for one specific slot (corner power-up)."""
        self._slot_timers[slot] = duration
        self._corner_move_time = 0.0

    def reset(self, n_sides: int) -> None:
        self.goal_offsets     = [0.0] * n_sides
        self._global_timer    = 0.0
        self._global_move_time = 0.0
        self._slot_timers     = [0.0] * n_sides
        self._corner_move_time = 0.0

    @property
    def is_active(self) -> bool:
        return self._global_timer > 0

    @property
    def slot_goals_active(self) -> list[bool]:
        return [t > 0 for t in self._slot_timers]

    def tick(self, dt: float, n_sides: int) -> None:
        """Advance timers and recompute goal_offsets."""
        phases = [i * 2 * math.pi / n_sides for i in range(n_sides)]

        # Global power-up timer
        if self._global_timer > 0:
            self._global_timer    -= dt
            self._global_move_time += dt

        # Corner effect elapsed time (shared phase for all corner-affected slots)
        self._corner_move_time += dt

        # Per-slot corner timers
        for i in range(n_sides):
            if self._slot_timers[i] > 0:
                self._slot_timers[i] -= dt

        # Build final offsets: global takes priority; corner fills where global is inactive
        new_offsets = [0.0] * n_sides
        for i in range(n_sides):
            if self._global_timer > 0:
                new_offsets[i] = MOVING_GOAL_AMP * math.sin(
                    self._global_move_time * MOVING_GOAL_SPEED + phases[i]
                )
            elif self._slot_timers[i] > 0:
                new_offsets[i] = MOVING_GOAL_AMP * math.sin(
                    self._corner_move_time * MOVING_GOAL_SPEED + phases[i]
                )
        self.goal_offsets = new_offsets
