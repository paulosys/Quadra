"""
Domain models — plain data containers for game entities.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum


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
    boosted:     bool  = False
    boost_timer: float = 0.0
    bounce:      bool  = False

    @property
    def speed(self) -> float:
        return math.sqrt(self.vx ** 2 + self.vy ** 2)

    def to_dict(self) -> dict:
        return {
            "id":      self.id,
            "x":       self.x,
            "y":       self.y,
            "vx":      self.vx,
            "vy":      self.vy,
            "boosted": self.boosted,
            "bounce":  self.bounce,
        }


@dataclass
class PowerUp:
    id:   int
    x:    float
    y:    float
    type: str

    def to_dict(self) -> dict:
        return {"id": self.id, "x": self.x, "y": self.y, "type": self.type}
