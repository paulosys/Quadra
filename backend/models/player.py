"""Player — per-slot mutable state (Value Object)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import LIVES_START


@dataclass
class Player:
    """A connected player slot — consolidates all per-player mutable state.

    Replaces the six parallel arrays (lives, eliminated, goals_scored,
    paddles, paddle_len_mult, speed_mult) previously held by Room.
    """
    slot:            int
    name:            str
    ws:              Any  # WebSocketServerProtocol — avoid runtime import
    lives:               int   = field(default_factory=lambda: LIVES_START)
    eliminated:          bool  = False
    pending_elimination: bool  = False   # true while player is offered to buy a life
    goals_scored:        int   = 0
    paddle_pos:          float = 0.5
    paddle_len_mult:     float = 1.0
    speed_mult:          float = 1.0

    def is_alive(self) -> bool:
        return not self.eliminated and self.lives > 0

    def is_connected(self) -> bool:
        return self.ws is not None

    def to_dict(self) -> dict:
        return {
            "slot":         self.slot,
            "name":         self.name,
            "lives":        self.lives,
            "eliminated":   self.eliminated,
            "goals_scored": self.goals_scored,
        }
