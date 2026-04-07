"""
PortalManager — portal spawning, rotation, and ball teleportation.

Extracted from Room._tick_portals() and Room._create_portals().
"""
from __future__ import annotations

import math
import random
from typing import Callable, List

from config import (
    BALL_R,
    FIELD_MARGIN,
    PORTAL_COOLDOWN,
    PORTAL_DURATION,
    PORTAL_ENTRY_DELAY,
    PORTAL_MIN_DIST,
    PORTAL_RADIUS,
    PORTAL_ROT_SPEED,
    TICK_DT,
)
from models import Ball, Portal


class PortalManager:
    """Manages the portal power-up room-level effect."""

    def __init__(self, next_id_fn: Callable[[], int]) -> None:
        self.portals:             List[Portal] = []
        self._timer:              float        = 0.0
        self._pending_teleports:  dict         = {}  # ball_id → entry info
        self._next_id = next_id_fn

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def pending_teleport_ids(self) -> set[int]:
        return set(self._pending_teleports.keys())

    def activate(self) -> None:
        """Spawn a new pair of portals."""
        self._create_portals()

    def reset(self) -> None:
        self.portals            = []
        self._timer             = 0.0
        self._pending_teleports = {}

    def tick(self, dt: float, balls: List[Ball]) -> None:
        """Advance portal rotation, handle entry delay, and teleport balls."""
        # 1. Rotate active portals
        for portal in self.portals:
            portal.rotation = (portal.rotation + PORTAL_ROT_SPEED * dt) % (math.pi * 2)

        # 2. Tick portal cooldowns on balls
        for ball in balls:
            if ball.portal_cooldown > 0:
                ball.portal_cooldown = max(0.0, ball.portal_cooldown - dt)

        # 3. Process pending teleports: freeze ball at entry, fire when timer expires
        portal_map = {p.id: p for p in self.portals}
        done: list = []
        for ball_id, pt in self._pending_teleports.items():
            ball = next((b for b in balls if b.id == ball_id), None)
            if ball is None:
                done.append(ball_id)
                continue
            ball.x = pt["entry_x"]
            ball.y = pt["entry_y"]
            pt["timer"] -= dt
            if pt["timer"] <= 0:
                partner = portal_map.get(pt["partner_id"])
                if partner:
                    ball.x  = partner.x
                    ball.y  = partner.y
                    ball.vx = math.cos(partner.rotation) * pt["speed"]
                    ball.vy = math.sin(partner.rotation) * pt["speed"]
                    ball.portal_cooldown = PORTAL_COOLDOWN
                else:
                    # Portals expired mid-transit — restore original velocity
                    ball.vx = pt["orig_vx"]
                    ball.vy = pt["orig_vy"]
                done.append(ball_id)
        for ball_id in done:
            del self._pending_teleports[ball_id]

        # 4. Tick portal lifetime
        if not self.portals:
            return
        self._timer -= dt
        if self._timer <= 0:
            self.portals = []
            for ball_id, pt in list(self._pending_teleports.items()):
                ball = next((b for b in balls if b.id == ball_id), None)
                if ball:
                    ball.vx = pt["orig_vx"]
                    ball.vy = pt["orig_vy"]
            self._pending_teleports.clear()
            return

        # 5. Detect new ball entries
        for ball in balls:
            if ball.portal_cooldown > 0 or ball.id in self._pending_teleports:
                continue
            for portal in self.portals:
                dx = ball.x - portal.x
                dy = ball.y - portal.y
                if math.sqrt(dx * dx + dy * dy) < BALL_R + PORTAL_RADIUS:
                    self._pending_teleports[ball.id] = {
                        "timer":      PORTAL_ENTRY_DELAY,
                        "entry_x":    portal.x,
                        "entry_y":    portal.y,
                        "partner_id": portal.pair_id,
                        "speed":      ball.speed,
                        "orig_vx":    ball.vx,
                        "orig_vy":    ball.vy,
                    }
                    ball.vx = 0.0
                    ball.vy = 0.0
                    break  # one entry per ball per tick

    # ── Internals ─────────────────────────────────────────────────────────────

    def _create_portals(self) -> None:
        """Spawn two portals at least PORTAL_MIN_DIST apart."""
        fm = FIELD_MARGIN + 0.12
        for _ in range(60):
            x1 = random.uniform(fm, 1.0 - fm)
            y1 = random.uniform(fm, 1.0 - fm)
            x2 = random.uniform(fm, 1.0 - fm)
            y2 = random.uniform(fm, 1.0 - fm)
            if math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) >= PORTAL_MIN_DIST:
                id1 = self._next_id()
                id2 = self._next_id()
                self.portals = [
                    Portal(id=id1, x=x1, y=y1, pair_id=id2,
                           rotation=random.uniform(0, math.pi * 2)),
                    Portal(id=id2, x=x2, y=y2, pair_id=id1,
                           rotation=random.uniform(0, math.pi * 2)),
                ]
                self._timer = PORTAL_DURATION
                return
