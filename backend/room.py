"""
Room — a single game session (Facade pattern).

Thin coordinator over specialised managers. Holds identity and ball/powerup
state; delegates physics ticks and room-level effects to their subsystems.
"""
from __future__ import annotations

import asyncio
import json
import math
import random
from typing import Dict, List, Optional

from config import (
    BALL_R, BALL_SPEED_INIT, LIVES_START, MAX_PLAYERS, TICK_DT,
)
from events import EventBus, GameEvent
from managers import (
    CornerManager, HurricaneManager, MovingGoalManager,
    PortalManager, UpgradeManager,
)
from models import Ball, Player, PowerUp, Side
from physics import PhysicsEngine, compute_walls
from powerups import PowerUpManager


class Room:
    def __init__(self, room_id: str) -> None:
        self.id         = room_id
        self.state      = "waiting"
        self.lock       = asyncio.Lock()
        self.task:      Optional[asyncio.Task] = None
        self.generation = 0  # incremented on reset; used to ignore stale disconnects

        # Players: dict[slot → Player] replaces six parallel arrays
        self.players: Dict[int, Player] = {}

        # Arena
        self.n_sides: int = 4
        self._wall_defs   = compute_walls(4)

        # Balls and field power-ups
        self.balls:    List[Ball]    = []
        self.powerups: List[PowerUp] = []

        # Debug
        self.debug_freeze_goals:    bool         = False
        self.debug_mouse_ball_id:   Optional[int] = None

        # Kickoff phase state
        self.kickoff_event:  Optional[asyncio.Event] = None
        self.kickoff_angle:  Optional[float]         = None
        self.kickoff_scorer: Optional[int]            = None

        self._id_counter = 0
        self._physics    = PhysicsEngine()
        self._powerup_mgr = PowerUpManager()

        # EventBus — Observer pattern: decouples effect managers from power-up dispatch
        self._bus = EventBus()
        self._bus.subscribe(GameEvent.POWERUP_COLLECTED, self._on_powerup_collected)

        # Effect managers — extracted subsystems (Facade pattern)
        self._hurricane_mgr = HurricaneManager()
        self._goal_mgr      = MovingGoalManager(n_sides=4)
        self._portal_mgr    = PortalManager(next_id_fn=self._next_id)
        self._corner_mgr    = CornerManager(goal_mgr=self._goal_mgr)
        self._upgrade_mgr   = UpgradeManager()

    # ── Computed properties (read-only list views over Player state) ──────────

    @property
    def num_players(self) -> int:
        return len(self.players)

    @property
    def names(self) -> Dict[int, str]:
        return {slot: p.name for slot, p in self.players.items()}

    @property
    def lives(self) -> list[int]:
        return [self.players[i].lives if i in self.players else 0
                for i in range(self.n_sides)]

    @property
    def eliminated(self) -> list[bool]:
        return [self.players[i].eliminated if i in self.players else True
                for i in range(self.n_sides)]

    @property
    def goals_scored(self) -> list[int]:
        return [self.players[i].goals_scored if i in self.players else 0
                for i in range(self.n_sides)]

    @property
    def paddle_len_mult(self) -> list[float]:
        return [self.players[i].paddle_len_mult if i in self.players else 1.0
                for i in range(self.n_sides)]

    @property
    def speed_mult(self) -> list[float]:
        return [self.players[i].speed_mult if i in self.players else 1.0
                for i in range(self.n_sides)]

    # ── Identity / helpers ────────────────────────────────────────────────────

    def next_slot(self) -> Optional[int]:
        """Return the lowest free slot up to MAX_PLAYERS."""
        for i in range(MAX_PLAYERS):
            if i not in self.players:
                return i
        return None

    def alive_slots(self) -> List[int]:
        return [slot for slot in range(self.n_sides)
                if slot in self.players and not self.players[slot].eliminated]

    def set_n_sides(self, n: int) -> None:
        """Set arena size and reset per-slot player state. Called at game start."""
        self.n_sides  = n
        self._wall_defs = compute_walls(n)
        for slot in range(n):
            if slot in self.players:
                p = self.players[slot]
                p.lives           = LIVES_START
                p.eliminated      = False
                p.goals_scored    = 0
                p.paddle_pos      = 0.5
                p.paddle_len_mult = 1.0
                p.speed_mult      = 1.0
        self._goal_mgr.reset(n)
        self._corner_mgr.reset()

    def _next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    def _ordered_players(self) -> list[Optional[Player]]:
        """Return list indexed by slot [0..n_sides-1], None for absent slots."""
        return [self.players.get(i) for i in range(self.n_sides)]

    # ── Round lifecycle ───────────────────────────────────────────────────────

    def handle_kick_direction(self, slot: int, angle: float) -> None:
        if slot != self.kickoff_scorer or self.kickoff_event is None:
            return
        self.kickoff_angle = float(angle)
        self.kickoff_event.set()

    def launch_ball(self, kick_angle: Optional[float] = None) -> None:
        """Reset moveable state and spawn the first ball of a round."""
        for p in self.players.values():
            p.paddle_pos = 0.5

        # Preserve mouse ball owner across rounds
        mouse_owner: Optional[int] = None
        if self.debug_mouse_ball_id is not None:
            for b in self.balls:
                if b.id == self.debug_mouse_ball_id:
                    mouse_owner = b.last_touch
                    break

        if kick_angle is not None:
            vx = math.cos(kick_angle) * BALL_SPEED_INIT
            vy = math.sin(kick_angle) * BALL_SPEED_INIT
            self.balls = [self._make_ball(vx=vx, vy=vy)]
        else:
            self.balls = [self._make_ball()]
        self.powerups = []
        self._powerup_mgr.reset()
        self._goal_mgr.reset(self.n_sides)
        self._portal_mgr.reset()
        self._hurricane_mgr.reset()
        self._corner_mgr.reset()

        # Re-create mouse ball if it was active
        if mouse_owner is not None:
            self.debug_mouse_ball_id = None
            self.debug_activate_mouse_ball(mouse_owner)

    def reset_for_new_game(self) -> None:
        """Reset between full games (post-gameover)."""
        self.n_sides            = 4
        self._wall_defs         = compute_walls(4)
        self.state              = "waiting"
        self.players            = {}
        self.generation        += 1
        self.debug_mouse_ball_id = None
        self._upgrade_mgr.reset()
        self._goal_mgr.reset(4)
        self._corner_mgr.reset()
        self._hurricane_mgr.reset()
        self._portal_mgr.reset()

    # ── Upgrade phase (delegated to UpgradeManager) ───────────────────────────

    def begin_upgrade_phase(self) -> asyncio.Event:
        """Start the upgrade phase. Returns an Event fired when all players pick."""
        return self._upgrade_mgr.begin_round(self.alive_slots())

    def handle_upgrade_pick(self, slot: int, card: Optional[str]) -> None:
        """Process a player's upgrade card selection. Must hold room.lock."""
        if slot not in self.players or self.players[slot].eliminated:
            return
        self._upgrade_mgr.handle_pick(slot, card, self.players[slot])

    # ── Physics tick ──────────────────────────────────────────────────────────

    def tick(self) -> tuple[Optional[Side], Optional[int], List[str]]:
        """
        Advance one physics step.
        Returns (scored_side | None, scorer_slot | None, list of collected powerup types).
        """
        dt = TICK_DT

        # Ball timer countdowns (boost, snitch, portal cooldown)
        for ball in self.balls:
            ball.tick_timers(dt)
            ball.tick_snitch_movement()

        # Manager ticks — each owns its slice of room state
        self._hurricane_mgr.tick(dt, self.balls)
        self._goal_mgr.tick(dt, self.n_sides)
        self._portal_mgr.tick(dt, self.balls)
        self._corner_mgr.tick(dt, self.n_sides, self.players)

        # Power-up spawn + collision — effects dispatched via EventBus
        collected_with_owners = self._powerup_mgr.tick(
            self.powerups, self.balls, self._next_id, self._bus
        )
        collected = [t for t, _ in collected_with_owners]

        # Physics loop — derive per-slot lists from Player objects
        ordered   = self._ordered_players()
        paddles   = [p.paddle_pos      if p else 0.5  for p in ordered]
        elim      = [p.eliminated      if p else True  for p in ordered]
        len_mults = [p.paddle_len_mult if p else 1.0  for p in ordered]
        wall_defs = self._wall_defs if self.n_sides > 4 else None

        scored: Optional[Side] = None
        scorer: Optional[int]  = None
        for ball in self.balls:
            if ball.id in self._portal_mgr.pending_teleport_ids:
                continue  # frozen inside portal — skip physics
            result = self._physics.tick_ball(
                ball, paddles, elim, set(self.players.keys()),
                self._goal_mgr.goal_offsets, len_mults, wall_defs
            )
            if result is not None and scored is None and not self.debug_freeze_goals:
                scored = result
                scorer = ball.last_touch

        return scored, scorer, collected

    # ── EventBus subscriber ───────────────────────────────────────────────────

    def _on_powerup_collected(self, effect: str, collector: int | None) -> None:
        """React to room-level power-up effects signalled via EventBus."""
        if effect == "movinggoal":
            self._goal_mgr.activate_global()
        elif effect == "portal":
            self._portal_mgr.activate()
        elif effect == "hurricane":
            self._hurricane_mgr.activate()
        elif effect == "ghostgoal":
            if collector is not None and collector in self.players:
                self.players[collector].goals_scored += 1

    # ── Networking ────────────────────────────────────────────────────────────

    async def broadcast(self, msg: dict) -> None:
        data = json.dumps(msg)
        dead: List[int] = []
        for slot, player in list(self.players.items()):
            if not player.is_connected():
                continue
            try:
                await player.ws.send(data)
            except Exception:
                dead.append(slot)
        for s in dead:
            self.players.pop(s, None)

    def state_snapshot(self, collected: Optional[List[str]] = None) -> dict:
        ordered = self._ordered_players()
        return {
            "type":          "state",
            "num_sides":     self.n_sides,
            "balls":         [b.to_dict() for b in self.balls],
            "paddles":       [p.paddle_pos      if p else 0.5  for p in ordered],
            "lives":         [p.lives           if p else 0    for p in ordered],
            "eliminated":    [p.eliminated      if p else True for p in ordered],
            "names":         [p.name            if p else ""   for p in ordered],
            "goals_scored":  [p.goals_scored    if p else 0    for p in ordered],
            "game_state":    self.state,
            "powerups":      [pu.to_dict() for pu in self.powerups],
            "powerup_queue": self._powerup_mgr.queue_snapshot(),
            "collected":     collected or [],
            "goal_offsets":  self._goal_mgr.goal_offsets[:],
            "goal_moving":   self._goal_mgr.is_active,
            "portals":          [p.to_dict() for p in self._portal_mgr.portals],
            "hurricane_active": self._hurricane_mgr.is_active,
            "corner_powerups":  self._corner_mgr.snapshot(),
            "corner_goals_active": self._goal_mgr.slot_goals_active,
            "debug_freeze_goals":    self.debug_freeze_goals,
            "debug_mouse_ball_id":   self.debug_mouse_ball_id,
            "paddle_len_mult":    [p.paddle_len_mult if p else 1.0 for p in ordered],
            "speed_mult":         [p.speed_mult      if p else 1.0 for p in ordered],
            "powerup_spawn_timer": self._powerup_mgr.spawn_timer,
        }

    # ── Debug helpers ─────────────────────────────────────────────────────────

    def debug_spawn_powerup(self, ptype: str, x: float, y: float) -> None:
        from config import POWERUP_TYPES
        if ptype not in POWERUP_TYPES:
            return
        self.powerups.append(PowerUp(id=self._next_id(), x=float(x), y=float(y), type=ptype))

    def debug_teleport_ball(self, x: float, y: float) -> None:
        """Teleport the first non-mouse ball to (x, y)."""
        for ball in self.balls:
            if ball.id != self.debug_mouse_ball_id:
                ball.x = float(x)
                ball.y = float(y)
                return

    def debug_add_ball(self) -> None:
        from config import MAX_BALLS
        if len(self.balls) < MAX_BALLS:
            self.balls.append(self._make_ball())

    def debug_remove_ball(self) -> None:
        """Remove the last non-mouse ball (allows 0 regular balls)."""
        for i in range(len(self.balls) - 1, -1, -1):
            if self.balls[i].id != self.debug_mouse_ball_id:
                self.balls.pop(i)
                return

    def debug_activate_mouse_ball(self, slot: int) -> None:
        """Spawn a mouse-controlled ball and track its id."""
        if self.debug_mouse_ball_id is not None:
            return
        ball = Ball(id=self._next_id(), x=0.5, y=0.5, vx=0.0, vy=0.0, last_touch=slot)
        self.balls.append(ball)
        self.debug_mouse_ball_id = ball.id

    def debug_deactivate_mouse_ball(self) -> None:
        """Remove the mouse-controlled ball."""
        if self.debug_mouse_ball_id is None:
            return
        self.balls = [b for b in self.balls if b.id != self.debug_mouse_ball_id]
        self.debug_mouse_ball_id = None

    def debug_update_mouse_ball(self, x: float, y: float, slot: int) -> None:
        """Drive the mouse ball toward (x, y) via velocity — lets physics handle paddle collisions."""
        if self.debug_mouse_ball_id is None:
            return
        for ball in self.balls:
            if ball.id == self.debug_mouse_ball_id:
                ball.vx = float(x) - ball.x
                ball.vy = float(y) - ball.y
                ball.last_touch = slot
                break

    # ── Internals ─────────────────────────────────────────────────────────────

    def _make_ball(self, x: float = 0.5, y: float = 0.5,
                   vx: Optional[float] = None, vy: Optional[float] = None) -> Ball:
        if vx is None:
            angle = random.uniform(0, math.pi * 2)
            vx = math.cos(angle) * BALL_SPEED_INIT
            vy = math.sin(angle) * BALL_SPEED_INIT
        return Ball(id=self._next_id(), x=x, y=y, vx=vx, vy=vy)
