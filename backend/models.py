"""
Domain models — plain data containers for game entities.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class Side(IntEnum):
    TOP    = 0
    BOTTOM = 1
    LEFT   = 2
    RIGHT  = 3


SIDE_NAMES: list[str] = ["top", "bottom", "left", "right"]


@dataclass
class Ball:
    id:          int
    x:           float
    y:           float
    vx:          float
    vy:          float
    boosted:         bool          = False
    boost_timer:     float         = 0.0
    bounce:          bool          = False
    snitched:        bool          = False
    snitch_timer:    float         = 0.0
    portal_cooldown: float         = 0.0
    last_touch:      Optional[int] = None

    @property
    def speed(self) -> float:
        return math.sqrt(self.vx ** 2 + self.vy ** 2)

    def to_dict(self) -> dict:
        return {
            "id":       self.id,
            "x":        self.x,
            "y":        self.y,
            "vx":       self.vx,
            "vy":       self.vy,
            "boosted":  self.boosted,
            "bounce":   self.bounce,
            "snitched": self.snitched,
        }


@dataclass
class PowerUp:
    id:   int
    x:    float
    y:    float
    type: str

    def to_dict(self) -> dict:
        return {"id": self.id, "x": self.x, "y": self.y, "type": self.type}


@dataclass
class Portal:
    id:       int
    x:        float
    y:        float
    pair_id:  int    # id of the linked partner portal
    rotation: float = 0.0  # exit-direction angle in radians (rotates each tick)

    def to_dict(self) -> dict:
        return {"id": self.id, "x": self.x, "y": self.y, "pair_id": self.pair_id,
                "rotation": self.rotation}
