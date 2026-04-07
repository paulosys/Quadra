"""
CornerManager — corner power-up system (4-player square arena only).

Extracted from Room._tick_corner_powerups(), _both_owners_near(),
and _activate_corner_power().

Two teams of two players can collaborate near their shared corner to charge
a power-up that disadvantages their two adversaries.
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING, List, Optional

from config import (
    CORNER_CHARGE_TIME,
    CORNER_GOAL_DURATION,
    CORNER_POWERUP_SPAWN_MAX,
    CORNER_POWERUP_SPAWN_MIN,
    CORNER_PROXIMITY,
    TICK_DT,
)
from models import CornerPowerUp, Player

if TYPE_CHECKING:
    from managers.moving_goal_manager import MovingGoalManager

# Corner definitions: (owner_a, owner_b, adv_a, adv_b, check_a, check_b)
# check_*: (slot, 'low'|'high')  — 'low' = paddle near 0, 'high' = paddle near 1
_CORNER_DEFS = [
    (0, 2, 1, 3, (0, "low"),  (2, "low")),   # TL: TOP+LEFT  → adversaries BOTTOM+RIGHT
    (0, 3, 1, 2, (0, "high"), (3, "low")),   # TR: TOP+RIGHT → adversaries BOTTOM+LEFT
    (1, 2, 0, 3, (1, "low"),  (2, "high")),  # BL: BOT+LEFT  → adversaries TOP+RIGHT
    (1, 3, 0, 2, (1, "high"), (3, "high")),  # BR: BOT+RIGHT → adversaries TOP+LEFT
]
_CORNER_POWERUP_TYPES = ["movinggoal"]


class CornerManager:
    """Manages corner power-ups for 4-player square arenas."""

    def __init__(self, goal_mgr: "MovingGoalManager") -> None:
        self.corner_powerups: list[Optional[CornerPowerUp]] = [None, None, None, None]
        self._charge:         list[float]                   = [0.0, 0.0, 0.0, 0.0]
        self._spawn_timer:    float                         = CORNER_POWERUP_SPAWN_MIN
        self._goal_mgr = goal_mgr

    # ── Public API ────────────────────────────────────────────────────────────

    def reset(self) -> None:
        self.corner_powerups = [None, None, None, None]
        self._charge         = [0.0, 0.0, 0.0, 0.0]
        self._spawn_timer    = CORNER_POWERUP_SPAWN_MIN

    def snapshot(self) -> list:
        """Return serialisable corner state for state_snapshot()."""
        return [
            {**cp.to_dict(), "charge": self._charge[i]}
            if cp is not None else None
            for i, cp in enumerate(self.corner_powerups)
        ]

    def tick(self, dt: float, n_sides: int, players: dict[int, Player]) -> None:
        """Spawn corner power-ups and handle activation when both owners are near."""
        if n_sides != 4:
            return  # corner system only for square arena
        if len(players) < 4:
            # Clear corners if a player leaves mid-game
            self.corner_powerups = [None, None, None, None]
            self._charge         = [0.0, 0.0, 0.0, 0.0]
            return

        # Spawn: only one active corner power-up at a time
        if not any(cp is not None for cp in self.corner_powerups):
            self._spawn_timer -= dt
            if self._spawn_timer <= 0:
                corner = random.randint(0, 3)
                ptype  = random.choice(_CORNER_POWERUP_TYPES)
                self.corner_powerups[corner] = CornerPowerUp(corner=corner, type=ptype)
                self._spawn_timer = random.uniform(
                    CORNER_POWERUP_SPAWN_MIN, CORNER_POWERUP_SPAWN_MAX
                )

        # Check activation for each occupied corner
        for corner, cp in enumerate(self.corner_powerups):
            if cp is None:
                self._charge[corner] = 0.0
                continue
            if self._both_owners_near(corner, players):
                self._charge[corner] += dt
                if self._charge[corner] >= CORNER_CHARGE_TIME:
                    self._activate_corner_power(corner, cp.type)
                    self.corner_powerups[corner] = None
                    self._charge[corner]         = 0.0
                    self._spawn_timer = random.uniform(
                        CORNER_POWERUP_SPAWN_MIN, CORNER_POWERUP_SPAWN_MAX
                    )
            else:
                # Slowly decay charge when owners leave
                self._charge[corner] = max(0.0, self._charge[corner] - dt * 2)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _both_owners_near(self, corner: int, players: dict[int, Player]) -> bool:
        """Return True when both owner paddles are positioned near the given corner."""
        owner_a, owner_b, _, _, check_a, check_b = _CORNER_DEFS[corner]
        for slot, (chk_slot, side) in ((owner_a, check_a), (owner_b, check_b)):
            if slot not in players or players[slot].eliminated:
                return False
            pos = players[chk_slot].paddle_pos
            if side == "low"  and pos > CORNER_PROXIMITY:
                return False
            if side == "high" and pos < 1.0 - CORNER_PROXIMITY:
                return False
        return True

    def _activate_corner_power(self, corner: int, ptype: str) -> None:
        """Apply the corner power-up effect to the two adversary players."""
        _, _, adv_a, adv_b, _, _ = _CORNER_DEFS[corner]
        if ptype == "movinggoal":
            self._goal_mgr.activate_slot(adv_a, CORNER_GOAL_DURATION)
            self._goal_mgr.activate_slot(adv_b, CORNER_GOAL_DURATION)
