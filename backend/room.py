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
    BALL_SPEED_INIT, BALL_SPEED_MAX, LIVES_START,
    MOVING_GOAL_AMP, MOVING_GOAL_DURATION, MOVING_GOAL_SPEED,
    SPEED_BOOST_FACTOR, TICK_DT,
)
from models import Ball, PowerUp, Side, SIDE_NAMES
from physics import PhysicsEngine
from powerups import PowerUpManager


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
        self.lives:     list[int]  = [LIVES_START] * 4
        self.eliminated: list[bool] = [False] * 4
        self.paddles:   list[float] = [0.5, 0.5, 0.5, 0.5]
        self.balls:     List[Ball]    = []
        self.powerups:  List[PowerUp] = []

        # Moving-goal effect (room-level, applied here after powerup signal)
        self.goal_offsets:       list[float] = [0.0, 0.0, 0.0, 0.0]
        self._goal_moving_timer: float       = 0.0
        self._goal_move_time:    float       = 0.0

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

    def reset_for_new_game(self) -> None:
        """Reset between full games (post-gameover)."""
        self.lives      = [LIVES_START] * 4
        self.eliminated = [False] * 4
        self.paddles    = [0.5, 0.5, 0.5, 0.5]
        self.state      = "waiting"
        self.players    = {}
        self.names      = {}

    # ── Physics tick ──────────────────────────────────────────────────────────

    def tick(self) -> tuple[Optional[Side], List[str]]:
        """
        Advance one physics step.
        Returns (scored_side | None, list of collected powerup types).
        """
        self._tick_boost_timers()
        self._tick_moving_goals()

        collected = self._powerup_mgr.tick(self.powerups, self.balls, self._next_id)
        self._apply_room_effects(collected)

        players_set = set(self.players.keys())
        scored: Optional[Side] = None
        for ball in self.balls:
            result = self._physics.tick_ball(
                ball, self.paddles, self.eliminated, players_set, self.goal_offsets
            )
            if result is not None and scored is None:
                scored = result

        return scored, collected

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

    def _tick_moving_goals(self) -> None:
        if self._goal_moving_timer <= 0:
            return
        self._goal_moving_timer -= TICK_DT
        self._goal_move_time    += TICK_DT
        t = self._goal_move_time * MOVING_GOAL_SPEED
        self.goal_offsets = [
            MOVING_GOAL_AMP * math.sin(t),
            MOVING_GOAL_AMP * math.sin(t + math.pi),
            MOVING_GOAL_AMP * math.sin(t + math.pi / 2),
            MOVING_GOAL_AMP * math.sin(t + 3 * math.pi / 2),
        ]
        if self._goal_moving_timer <= 0:
            self.goal_offsets = [0.0, 0.0, 0.0, 0.0]

    def _apply_room_effects(self, collected: List[str]) -> None:
        """Apply powerup effects that live at room level (not ball level)."""
        for ptype in collected:
            if ptype == "movinggoal":
                if self._goal_moving_timer <= 0:
                    self._goal_move_time = 0.0
                self._goal_moving_timer = MOVING_GOAL_DURATION

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
            "game_state":    self.state,
            "powerups":      [p.to_dict() for p in self.powerups],
            "powerup_queue": self._powerup_mgr.queue_snapshot(),
            "collected":     collected or [],
            "goal_offsets":  self.goal_offsets[:],
            "goal_moving":   self._goal_moving_timer > 0,
        }

    # ── Internals ─────────────────────────────────────────────────────────────

    def _make_ball(self, x: float = 0.5, y: float = 0.5,
                   vx: Optional[float] = None, vy: Optional[float] = None) -> Ball:
        if vx is None:
            angle = random.uniform(0, math.pi * 2)
            vx = math.cos(angle) * BALL_SPEED_INIT
            vy = math.sin(angle) * BALL_SPEED_INIT
        return Ball(id=self._next_id(), x=x, y=y, vx=vx, vy=vy)
