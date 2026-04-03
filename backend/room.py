"""
Room — a single game session.

Holds all mutable game state and delegates physics/powerup work to their
respective engines. Knows nothing about WebSocket framing or game-loop
orchestration.
"""
from __future__ import annotations

import asyncio
import json
import math
import random
from typing import Dict, List, Optional

import websockets
from websockets.server import WebSocketServerProtocol

from config import (
    BALL_R, BALL_SPEED_INIT, BALL_SPEED_MAX, FIELD_MARGIN, LIVES_START,
    MOVING_GOAL_AMP, MOVING_GOAL_DURATION, MOVING_GOAL_SPEED,
    PORTAL_COOLDOWN, PORTAL_DURATION, PORTAL_ENTRY_DELAY, PORTAL_MIN_DIST,
    PORTAL_RADIUS, PORTAL_ROT_SPEED,
    SNITCH_TURN_CHANCE,
    SPEED_BOOST_FACTOR, TICK_DT,
    HURRICANE_DURATION, HURRICANE_RADIUS, HURRICANE_STRENGTH,
    CORNER_POWERUP_SPAWN_MIN, CORNER_POWERUP_SPAWN_MAX,
    CORNER_CHARGE_TIME, CORNER_PROXIMITY, CORNER_GOAL_DURATION,
)
from models import Ball, CornerPowerUp, Portal, PowerUp, Side, SIDE_NAMES
from physics import PhysicsEngine
from powerups import PowerUpManager

# Corner definitions: (owner_a, owner_b, adv_a, adv_b, check_a, check_b)
# check_*: (slot, 'low'|'high')  — 'low' = paddle near 0, 'high' = paddle near 1
_CORNER_DEFS = [
    (0, 2, 1, 3, (0, 'low'),  (2, 'low')),   # TL: TOP+LEFT  → adversaries BOTTOM+RIGHT
    (0, 3, 1, 2, (0, 'high'), (3, 'low')),   # TR: TOP+RIGHT → adversaries BOTTOM+LEFT
    (1, 2, 0, 3, (1, 'low'),  (2, 'high')),  # BL: BOT+LEFT  → adversaries TOP+RIGHT
    (1, 3, 0, 2, (1, 'high'), (3, 'high')),  # BR: BOT+RIGHT → adversaries TOP+LEFT
]
_CORNER_POWERUP_TYPES = ["movinggoal"]


class Room:
    def __init__(self, room_id: str) -> None:
        self.id       = room_id
        self.state    = "waiting"
        self.lock     = asyncio.Lock()
        self.task:    Optional[asyncio.Task] = None

        # Players
        self.players: Dict[int, WebSocketServerProtocol] = {}
        self.names:   Dict[int, str] = {}

        # Game state
        self.lives:        list[int]  = [LIVES_START] * 4
        self.eliminated:   list[bool] = [False] * 4
        self.goals_scored: list[int]  = [0] * 4
        self.paddles:   list[float] = [0.5, 0.5, 0.5, 0.5]
        self.balls:     List[Ball]    = []
        self.powerups:  List[PowerUp] = []

        # Moving-goal effect (room-level, applied here after powerup signal)
        self.goal_offsets:       list[float] = [0.0, 0.0, 0.0, 0.0]
        self._goal_moving_timer: float       = 0.0
        self._goal_move_time:    float       = 0.0

        # Portal effect (room-level)
        self.portals:            List[Portal] = []
        self._portal_timer:      float        = 0.0
        self._pending_teleports: dict         = {}  # ball_id → entry info

        # Hurricane effect (room-level)
        self._hurricane_timer: float = 0.0

        # Corner power-up system (only active with 4 players)
        self.corner_powerups:     list[Optional[CornerPowerUp]] = [None, None, None, None]
        self._corner_charge:      list[float]                   = [0.0, 0.0, 0.0, 0.0]
        self._corner_spawn_timer: float                         = CORNER_POWERUP_SPAWN_MIN
        # Per-slot moving-goal timers triggered by corner activation
        self._corner_goal_timers:    list[float] = [0.0, 0.0, 0.0, 0.0]
        self._corner_goal_move_time: float       = 0.0

        self.debug_freeze_goals: bool = False

        self._id_counter = 0
        self._physics    = PhysicsEngine()
        self._powerup_mgr = PowerUpManager()

    # ── Identity / helpers ────────────────────────────────────────────────────

    @property
    def num_players(self) -> int:
        return len(self.players)

    def next_slot(self) -> Optional[int]:
        for i in range(4):
            if i not in self.players:
                return i
        return None

    def alive_slots(self) -> List[int]:
        return [i for i in range(4) if not self.eliminated[i] and i in self.players]

    def _next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    # ── Round lifecycle ───────────────────────────────────────────────────────

    def launch_ball(self) -> None:
        """Reset moveable state and spawn the first ball of a round."""
        self.paddles  = [0.5, 0.5, 0.5, 0.5]
        self.balls    = [self._make_ball()]
        self.powerups = []
        self._powerup_mgr.reset()
        self.goal_offsets       = [0.0, 0.0, 0.0, 0.0]
        self._goal_moving_timer = 0.0
        self._goal_move_time    = 0.0
        self.portals             = []
        self._portal_timer       = 0.0
        self._pending_teleports  = {}
        self._hurricane_timer = 0.0
        self.corner_powerups         = [None, None, None, None]
        self._corner_charge          = [0.0, 0.0, 0.0, 0.0]
        self._corner_spawn_timer     = CORNER_POWERUP_SPAWN_MIN
        self._corner_goal_timers     = [0.0, 0.0, 0.0, 0.0]
        self._corner_goal_move_time  = 0.0

    def reset_for_new_game(self) -> None:
        """Reset between full games (post-gameover)."""
        self.lives        = [LIVES_START] * 4
        self.eliminated   = [False] * 4
        self.goals_scored = [0] * 4
        self.paddles    = [0.5, 0.5, 0.5, 0.5]
        self.state      = "waiting"
        self.players    = {}
        self.names      = {}

    # ── Physics tick ──────────────────────────────────────────────────────────

    def tick(self) -> tuple[Optional[Side], Optional[int], List[str]]:
        """
        Advance one physics step.
        Returns (scored_side | None, scorer_slot | None, list of collected powerup types).
        scorer_slot is the player who last touched the ball that scored.
        """
        self._tick_boost_timers()
        self._tick_snitch_movement()
        self._tick_moving_goals()
        self._tick_portals()
        self._tick_hurricane()
        self._tick_corner_powerups()

        collected = self._powerup_mgr.tick(self.powerups, self.balls, self._next_id)
        self._apply_room_effects(collected)

        players_set = set(self.players.keys())
        scored: Optional[Side] = None
        scorer: Optional[int]  = None
        for ball in self.balls:
            if ball.id in self._pending_teleports:
                continue  # frozen inside portal — skip physics
            result = self._physics.tick_ball(
                ball, self.paddles, self.eliminated, players_set, self.goal_offsets
            )
            if result is not None and scored is None and not self.debug_freeze_goals:
                scored = result
                scorer = ball.last_touch

        return scored, scorer, collected

    def _tick_boost_timers(self) -> None:
        for ball in self.balls:
            if ball.boosted:
                ball.boost_timer -= TICK_DT
                if ball.boost_timer <= 0:
                    ball.boosted = False
                    spd = ball.speed
                    if spd > BALL_SPEED_MAX:
                        ball.vx = ball.vx / spd * BALL_SPEED_MAX
                        ball.vy = ball.vy / spd * BALL_SPEED_MAX

    def _tick_snitch_movement(self) -> None:
        for ball in self.balls:
            if not ball.snitched:
                continue
            ball.snitch_timer -= TICK_DT
            if ball.snitch_timer <= 0:
                ball.snitched = False
                continue
            angle = math.atan2(ball.vy, ball.vx)
            if random.random() < SNITCH_TURN_CHANCE:
                # Sharp random turn (±130°)
                angle += random.uniform(-math.pi * 0.72, math.pi * 0.72)
            else:
                # Continuous slight angular drift
                angle += random.uniform(-0.13, 0.13)
            spd = ball.speed
            ball.vx = math.cos(angle) * spd
            ball.vy = math.sin(angle) * spd

    def _tick_moving_goals(self) -> None:
        phases = [0.0, math.pi, math.pi / 2, 3 * math.pi / 2]

        # Regular powerup: affects all 4 goals
        if self._goal_moving_timer > 0:
            self._goal_moving_timer -= TICK_DT
            self._goal_move_time    += TICK_DT

        # Corner effect: per-slot timers
        self._corner_goal_move_time += TICK_DT
        for i in range(4):
            if self._corner_goal_timers[i] > 0:
                self._corner_goal_timers[i] -= TICK_DT

        # Build final offsets: regular takes priority; corner fills in where regular is inactive
        new_offsets = [0.0, 0.0, 0.0, 0.0]
        for i in range(4):
            reg = 0.0
            if self._goal_moving_timer > 0:
                reg = MOVING_GOAL_AMP * math.sin(self._goal_move_time * MOVING_GOAL_SPEED + phases[i])
            crn = 0.0
            if self._corner_goal_timers[i] > 0:
                crn = MOVING_GOAL_AMP * math.sin(self._corner_goal_move_time * MOVING_GOAL_SPEED + phases[i])
            new_offsets[i] = reg if self._goal_moving_timer > 0 else crn
        self.goal_offsets = new_offsets

    def _tick_corner_powerups(self) -> None:
        """Spawn corner power-ups and handle activation when both owners are near."""
        if len(self.players) < 4:
            # Clear corners if a player leaves mid-game
            self.corner_powerups  = [None, None, None, None]
            self._corner_charge   = [0.0, 0.0, 0.0, 0.0]
            return

        # Spawn: only one active corner power-up at a time
        if not any(cp is not None for cp in self.corner_powerups):
            self._corner_spawn_timer -= TICK_DT
            if self._corner_spawn_timer <= 0:
                corner = random.randint(0, 3)
                ptype  = random.choice(_CORNER_POWERUP_TYPES)
                self.corner_powerups[corner] = CornerPowerUp(corner=corner, type=ptype)
                self._corner_spawn_timer = random.uniform(
                    CORNER_POWERUP_SPAWN_MIN, CORNER_POWERUP_SPAWN_MAX
                )

        # Check activation for each occupied corner
        for corner, cp in enumerate(self.corner_powerups):
            if cp is None:
                self._corner_charge[corner] = 0.0
                continue
            if self._both_owners_near(corner):
                self._corner_charge[corner] += TICK_DT
                if self._corner_charge[corner] >= CORNER_CHARGE_TIME:
                    self._activate_corner_power(corner, cp.type)
                    self.corner_powerups[corner]  = None
                    self._corner_charge[corner]   = 0.0
                    self._corner_spawn_timer = random.uniform(
                        CORNER_POWERUP_SPAWN_MIN, CORNER_POWERUP_SPAWN_MAX
                    )
            else:
                # Slowly decay charge when owners leave
                self._corner_charge[corner] = max(
                    0.0, self._corner_charge[corner] - TICK_DT * 2
                )

    def _both_owners_near(self, corner: int) -> bool:
        """Return True when both owner paddles are positioned near the given corner."""
        owner_a, owner_b, _, _, check_a, check_b = _CORNER_DEFS[corner]
        for slot, (chk_slot, side) in ((owner_a, check_a), (owner_b, check_b)):
            if slot not in self.players or self.eliminated[slot]:
                return False
            pos = self.paddles[chk_slot]
            if side == 'low'  and pos > CORNER_PROXIMITY:
                return False
            if side == 'high' and pos < 1.0 - CORNER_PROXIMITY:
                return False
        return True

    def _activate_corner_power(self, corner: int, ptype: str) -> None:
        """Apply the corner power-up effect to the two adversary players."""
        _, _, adv_a, adv_b, _, _ = _CORNER_DEFS[corner]
        if ptype == "movinggoal":
            self._corner_goal_timers[adv_a] = CORNER_GOAL_DURATION
            self._corner_goal_timers[adv_b] = CORNER_GOAL_DURATION
            self._corner_goal_move_time = 0.0

    def _apply_room_effects(self, collected: List[str]) -> None:
        """Apply powerup effects that live at room level (not ball level)."""
        for ptype in collected:
            if ptype == "movinggoal":
                if self._goal_moving_timer <= 0:
                    self._goal_move_time = 0.0
                self._goal_moving_timer = MOVING_GOAL_DURATION
            elif ptype == "portal":
                self._create_portals()
            elif ptype == "hurricane":
                self._hurricane_timer = HURRICANE_DURATION

    def _create_portals(self) -> None:
        """Spawn two portals at random positions at least PORTAL_MIN_DIST apart."""
        fm = FIELD_MARGIN + 0.12
        for _ in range(60):
            x1 = random.uniform(fm, 1.0 - fm)
            y1 = random.uniform(fm, 1.0 - fm)
            x2 = random.uniform(fm, 1.0 - fm)
            y2 = random.uniform(fm, 1.0 - fm)
            if math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) >= PORTAL_MIN_DIST:
                id1 = self._next_id()
                id2 = self._next_id()
                self.portals      = [
                    Portal(id=id1, x=x1, y=y1, pair_id=id2,
                           rotation=random.uniform(0, math.pi * 2)),
                    Portal(id=id2, x=x2, y=y2, pair_id=id1,
                           rotation=random.uniform(0, math.pi * 2)),
                ]
                self._portal_timer = PORTAL_DURATION
                return

    def _tick_hurricane(self) -> None:
        """Apply rotational vortex force to balls within hurricane radius."""
        if self._hurricane_timer <= 0:
            return
        self._hurricane_timer -= TICK_DT
        cx, cy = 0.5, 0.5
        for ball in self.balls:
            dx = ball.x - cx
            dy = ball.y - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if 0 < dist < HURRICANE_RADIUS:
                factor      = 1.0 - dist / HURRICANE_RADIUS
                speed       = math.sqrt(ball.vx * ball.vx + ball.vy * ball.vy)
                angle_delta = HURRICANE_STRENGTH * factor * max(1.0, speed / BALL_SPEED_INIT)
                cos_a = math.cos(angle_delta)
                sin_a = math.sin(angle_delta)
                ball.vx, ball.vy = (
                    ball.vx * cos_a - ball.vy * sin_a,
                    ball.vx * sin_a + ball.vy * cos_a,
                )

    def _tick_portals(self) -> None:
        """Advance portal rotation, handle entry delay, and teleport balls."""
        # 1. Advance rotation on active portals
        for portal in self.portals:
            portal.rotation = (portal.rotation + PORTAL_ROT_SPEED * TICK_DT) % (math.pi * 2)

        # 2. Tick portal cooldowns
        for ball in self.balls:
            if ball.portal_cooldown > 0:
                ball.portal_cooldown = max(0.0, ball.portal_cooldown - TICK_DT)

        # 3. Process pending teleports: lock position, fire when timer expires
        portal_map = {p.id: p for p in self.portals}
        done: list = []
        for ball_id, pt in self._pending_teleports.items():
            ball = next((b for b in self.balls if b.id == ball_id), None)
            if ball is None:
                done.append(ball_id)
                continue
            # Keep ball frozen at portal entry point
            ball.x = pt['entry_x']
            ball.y = pt['entry_y']
            pt['timer'] -= TICK_DT
            if pt['timer'] <= 0:
                partner = portal_map.get(pt['partner_id'])
                if partner:
                    ball.x  = partner.x
                    ball.y  = partner.y
                    ball.vx = math.cos(partner.rotation) * pt['speed']
                    ball.vy = math.sin(partner.rotation) * pt['speed']
                    ball.portal_cooldown = PORTAL_COOLDOWN
                else:
                    # Portals expired mid-transit — restore original velocity
                    ball.vx = pt['orig_vx']
                    ball.vy = pt['orig_vy']
                done.append(ball_id)
        for ball_id in done:
            del self._pending_teleports[ball_id]

        # 4. Tick portal lifetime
        if not self.portals:
            return
        self._portal_timer -= TICK_DT
        if self._portal_timer <= 0:
            self.portals = []
            # Release any balls still in transit
            for ball_id, pt in list(self._pending_teleports.items()):
                ball = next((b for b in self.balls if b.id == ball_id), None)
                if ball:
                    ball.vx = pt['orig_vx']
                    ball.vy = pt['orig_vy']
            self._pending_teleports.clear()
            return

        # 5. Detect new entries
        for ball in self.balls:
            if ball.portal_cooldown > 0 or ball.id in self._pending_teleports:
                continue
            for portal in self.portals:
                dx = ball.x - portal.x
                dy = ball.y - portal.y
                if math.sqrt(dx * dx + dy * dy) < BALL_R + PORTAL_RADIUS:
                    self._pending_teleports[ball.id] = {
                        'timer':      PORTAL_ENTRY_DELAY,
                        'entry_x':    portal.x,
                        'entry_y':    portal.y,
                        'partner_id': portal.pair_id,
                        'speed':      ball.speed,
                        'orig_vx':    ball.vx,
                        'orig_vy':    ball.vy,
                    }
                    ball.vx = 0.0
                    ball.vy = 0.0
                    break  # one entry per ball per tick

    # ── Networking ────────────────────────────────────────────────────────────

    async def broadcast(self, msg: dict) -> None:
        data = json.dumps(msg)
        dead: List[int] = []
        for slot, ws in list(self.players.items()):
            try:
                await ws.send(data)
            except Exception:
                dead.append(slot)
        for s in dead:
            self.players.pop(s, None)

    def state_snapshot(self, collected: Optional[List[str]] = None) -> dict:
        return {
            "type":          "state",
            "balls":         [b.to_dict() for b in self.balls],
            "paddles":       self.paddles[:],
            "lives":         self.lives[:],
            "eliminated":    self.eliminated[:],
            "names":         [self.names.get(i, "") for i in range(4)],
            "goals_scored":  self.goals_scored[:],
            "game_state":    self.state,
            "powerups":      [p.to_dict() for p in self.powerups],
            "powerup_queue": self._powerup_mgr.queue_snapshot(),
            "collected":     collected or [],
            "goal_offsets":  self.goal_offsets[:],
            "goal_moving":   self._goal_moving_timer > 0,
            "portals":          [p.to_dict() for p in self.portals],
            "hurricane_active": self._hurricane_timer > 0,
            "corner_powerups":  [
                {**cp.to_dict(), "charge": self._corner_charge[i]}
                if cp is not None else None
                for i, cp in enumerate(self.corner_powerups)
            ],
            "corner_goals_active": [t > 0 for t in self._corner_goal_timers],
            "debug_freeze_goals":  self.debug_freeze_goals,
        }

    # ── Internals ─────────────────────────────────────────────────────────────

    def _make_ball(self, x: float = 0.5, y: float = 0.5,
                   vx: Optional[float] = None, vy: Optional[float] = None) -> Ball:
        if vx is None:
            angle = random.uniform(0, math.pi * 2)
            vx = math.cos(angle) * BALL_SPEED_INIT
            vy = math.sin(angle) * BALL_SPEED_INIT
        return Ball(id=self._next_id(), x=x, y=y, vx=vx, vy=vy)
