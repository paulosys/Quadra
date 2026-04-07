"""Ball — physics entity with timer-driven behaviour methods."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional

from config import BALL_SPEED_MAX, SNITCH_TURN_CHANCE


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

    # ── Behaviour methods ─────────────────────────────────────────────────────

    def normalize_to(self, max_speed: float) -> None:
        """Cap velocity to max_speed, preserving direction."""
        spd = self.speed
        if spd > max_speed:
            self.vx = self.vx / spd * max_speed
            self.vy = self.vy / spd * max_speed

    def apply_boost(self, factor: float, duration: float) -> None:
        """Apply a speed boost: scale velocity by factor (capped) for duration seconds."""
        spd = self.speed
        if spd > 0:
            new_spd = min(spd * factor, BALL_SPEED_MAX * factor)
            self.vx = self.vx / spd * new_spd
            self.vy = self.vy / spd * new_spd
        self.boosted = True
        self.boost_timer = duration

    def apply_snitch(self, duration: float) -> None:
        """Activate snitch mode: dart in a random direction for duration seconds."""
        self.snitched = True
        self.snitch_timer = duration
        angle = random.uniform(0, math.pi * 2)
        spd = max(self.speed, BALL_SPEED_MAX * 0.55)
        self.vx = math.cos(angle) * spd
        self.vy = math.sin(angle) * spd

    def tick_timers(self, dt: float) -> None:
        """Decrement all countdown timers (boost, snitch, portal cooldown)."""
        if self.boosted:
            self.boost_timer -= dt
            if self.boost_timer <= 0:
                self.boosted = False
                self.normalize_to(BALL_SPEED_MAX)
        if self.snitched:
            self.snitch_timer -= dt
            if self.snitch_timer <= 0:
                self.snitched = False
        if self.portal_cooldown > 0:
            self.portal_cooldown = max(0.0, self.portal_cooldown - dt)

    def tick_snitch_movement(self) -> None:
        """Apply erratic direction changes while snitched. Call every tick."""
        if not self.snitched:
            return
        angle = math.atan2(self.vy, self.vx)
        if random.random() < SNITCH_TURN_CHANCE:
            angle += random.uniform(-math.pi * 0.72, math.pi * 0.72)
        else:
            angle += random.uniform(-0.13, 0.13)
        spd = self.speed
        self.vx = math.cos(angle) * spd
        self.vy = math.sin(angle) * spd

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
