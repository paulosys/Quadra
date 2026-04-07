"""
UpgradeManager — upgrade card selection phase.

Extracted from Room.handle_upgrade_pick() and the inline setup in
game_loop._run_upgrade_phase().
"""
from __future__ import annotations

import asyncio
from typing import Optional

from models import Player


class UpgradeManager:
    """Manages the upgrade phase: collecting player picks and applying card effects."""

    def __init__(self) -> None:
        self._picks:    dict[int, Optional[str]] = {}
        self._all_done: Optional[asyncio.Event]  = None

    # ── Public API ────────────────────────────────────────────────────────────

    def begin_round(self, alive_slots: list[int]) -> asyncio.Event:
        """Initialise a new upgrade phase. Returns an Event fired when all alive
        players have picked (or timed out externally)."""
        self._picks    = {}
        self._all_done = asyncio.Event()
        self._alive_slots = list(alive_slots)
        return self._all_done

    def reset(self) -> None:
        self._picks    = {}
        self._all_done = None

    def handle_pick(
        self,
        slot:   int,
        card:   Optional[str],
        player: Player,
    ) -> None:
        """Process a single player's upgrade pick. Mutates player in-place."""
        if slot in self._picks:
            return  # already picked

        self._picks[slot] = card

        if card == "life":
            if player.goals_scored >= 3:
                player.goals_scored -= 3
                player.lives += 1
        elif card == "paddle":
            if player.goals_scored >= 2:
                player.goals_scored -= 2
                player.paddle_len_mult = round(player.paddle_len_mult + 0.05, 4)
        elif card == "speed":
            if player.goals_scored >= 2:
                player.goals_scored -= 2
                player.speed_mult = round(player.speed_mult + 0.10, 4)

        # Fire event when all alive players have picked
        if self._all_done and all(s in self._picks for s in self._alive_slots):
            self._all_done.set()
