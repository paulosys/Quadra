"""Arena types — Side enum and field objects (PowerUp, Portal, CornerPowerUp)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Side(IntEnum):
    TOP    = 0
    BOTTOM = 1
    LEFT   = 2
    RIGHT  = 3
    SIDE4  = 4
    SIDE5  = 5
    SIDE6  = 6
    SIDE7  = 7


SIDE_NAMES: list[str] = ["top", "bottom", "left", "right", "side4", "side5", "side6", "side7"]


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


@dataclass
class CornerPowerUp:
    corner: int   # 0=TL, 1=TR, 2=BL, 3=BR
    type:   str   # effect type (e.g. "movinggoal")

    def to_dict(self) -> dict:
        return {"corner": self.corner, "type": self.type}
