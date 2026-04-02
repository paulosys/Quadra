"""
QUADRA — Multiplayer Ball Game Server
Python + websockets, authoritative server-side physics
"""

import asyncio
import json
import math
import random
import time
import logging
from typing import Dict, Optional, List
import websockets
from websockets.server import WebSocketServerProtocol

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("quadra")

# ── Constants ──────────────────────────────────────────────────────────────────
TICK_RATE        = 60
TICK_DT          = 1.0 / TICK_RATE

FIELD_MARGIN     = 0.08
PADDLE_THICK     = 0.03
PADDLE_LEN_H     = 0.16        # reduzido de 0.22
PADDLE_LEN_V     = 0.16        # reduzido de 0.22
PADDLE_SPEED     = 0.012
BALL_R           = 0.022
GOAL_DEPTH       = 0.07
GOAL_HALF_H      = 0.168
GOAL_HALF_V      = 0.168
BALL_SPEED_INIT  = 0.008
BALL_SPEED_MAX   = 0.022
BALL_SPEED_INC   = 0.00015
LIVES_START      = 3
GOAL_PAUSE       = 2.0
COUNTDOWN_SECS   = 3

# Power-up constants
POWERUP_RADIUS        = 0.038
POWERUP_SPAWN_MIN     = 8.0
POWERUP_SPAWN_MAX     = 14.0
POWERUP_TYPES         = ['double', 'speed', 'movinggoal']
POWERUP_WEIGHTS       = [3, 3, 1]
SPEED_BOOST_FACTOR    = 1.65
SPEED_BOOST_DURATION  = 5.0
MAX_BALLS             = 4
MAX_POWERUPS_ON_FIELD = 2
POWERUP_QUEUE_SIZE    = 4
MOVING_GOAL_SPEED     = 1.1   # rad/s
MOVING_GOAL_AMP       = 0.17  # max offset from centre
MOVING_GOAL_DURATION  = 9.0

TOP    = 0
BOTTOM = 1
LEFT   = 2
RIGHT  = 3
SIDE_NAMES = ["top", "bottom", "left", "right"]


class Room:
    def __init__(self, room_id: str):
        self.id = room_id
        self.players: Dict[int, WebSocketServerProtocol] = {}
        self.names: Dict[int, str] = {}
        self.lives      = [LIVES_START] * 4
        self.eliminated = [False] * 4
        self.paddles    = [0.5, 0.5, 0.5, 0.5]
        self.balls: List[dict] = []
        self.powerups: List[dict] = []
        self.powerup_queue: List[str] = []
        self.powerup_spawn_timer = 0.0
        self.goal_offsets      = [0.0, 0.0, 0.0, 0.0]
        self.goal_moving_timer = 0.0
        self.goal_move_time    = 0.0
        self._id_counter = 0
        self.state = "waiting"
        self.lock  = asyncio.Lock()
        self.task: Optional[asyncio.Task] = None

    @property
    def num_players(self):
        return len(self.players)

    def next_slot(self):
        for i in range(4):
            if i not in self.players:
                return i
        return None

    def alive_slots(self):
        return [i for i in range(4) if not self.eliminated[i] and i in self.players]

    def _next_id(self):
        self._id_counter += 1
        return self._id_counter

    def _make_ball(self, x=0.5, y=0.5, vx=None, vy=None):
        if vx is None:
            angle = random.uniform(0, math.pi * 2)
            vx = math.cos(angle) * BALL_SPEED_INIT
            vy = math.sin(angle) * BALL_SPEED_INIT
        return {
            "id": self._next_id(),
            "x": x, "y": y,
            "vx": vx, "vy": vy,
            "boosted": False,
            "boost_timer": 0.0,
            "bounce": False,
        }

    def launch_ball(self):
        self.paddles = [0.5, 0.5, 0.5, 0.5]
        self.balls = [self._make_ball()]
        self.powerups = []
        self._init_powerup_queue()
        self.powerup_spawn_timer = random.uniform(POWERUP_SPAWN_MIN, POWERUP_SPAWN_MAX)
        self.goal_offsets      = [0.0, 0.0, 0.0, 0.0]
        self.goal_moving_timer = 0.0
        self.goal_move_time    = 0.0

    def _init_powerup_queue(self):
        self.powerup_queue = [random.choices(POWERUP_TYPES, weights=POWERUP_WEIGHTS)[0] for _ in range(POWERUP_QUEUE_SIZE)]

    def _spawn_powerup(self):
        if len(self.powerups) >= MAX_POWERUPS_ON_FIELD:
            return
        ptype = self.powerup_queue.pop(0)
        self.powerup_queue.append(random.choices(POWERUP_TYPES, weights=POWERUP_WEIGHTS)[0])
        fm = FIELD_MARGIN + 0.18
        x = random.uniform(fm, 1 - fm)
        y = random.uniform(fm, 1 - fm)
        self.powerups.append({"id": self._next_id(), "x": x, "y": y, "type": ptype})

    def _apply_powerup(self, ball: dict, pu: dict):
        if pu["type"] == "double":
            if len(self.balls) < MAX_BALLS:
                angle = math.atan2(ball["vy"], ball["vx"]) + math.pi + random.uniform(-0.5, 0.5)
                spd = math.sqrt(ball["vx"]**2 + ball["vy"]**2)
                self.balls.append(self._make_ball(
                    x=ball["x"], y=ball["y"],
                    vx=math.cos(angle) * spd,
                    vy=math.sin(angle) * spd,
                ))
        elif pu["type"] == "speed":
            spd = math.sqrt(ball["vx"]**2 + ball["vy"]**2)
            if spd > 0:
                new_spd = min(spd * SPEED_BOOST_FACTOR, BALL_SPEED_MAX * SPEED_BOOST_FACTOR)
                ball["vx"] = ball["vx"] / spd * new_spd
                ball["vy"] = ball["vy"] / spd * new_spd
            ball["boosted"] = True
            ball["boost_timer"] = SPEED_BOOST_DURATION
        elif pu["type"] == "movinggoal":
            if self.goal_moving_timer <= 0:
                self.goal_move_time = 0.0
            self.goal_moving_timer = MOVING_GOAL_DURATION

    def _in_goal(self, pos, half, offset=0.0):
        c = 0.5 + offset
        return c - half <= pos <= c + half

    def _tick_ball(self, ball: dict):
        """Process physics for one ball. Returns scored side or None."""
        b = ball
        r = BALL_R
        fm = FIELD_MARGIN
        fL, fR, fT, fB = fm, 1 - fm, fm, 1 - fm
        pt = PADDLE_THICK

        b["bounce"] = False
        b["x"] += b["vx"]
        b["y"] += b["vy"]

        speed_cap = BALL_SPEED_MAX * SPEED_BOOST_FACTOR if b["boosted"] else BALL_SPEED_MAX
        spd = math.sqrt(b["vx"]**2 + b["vy"]**2)
        if spd < speed_cap and not b["boosted"]:
            b["vx"] *= (1 + BALL_SPEED_INC)
            b["vy"] *= (1 + BALL_SPEED_INC)

        scored = None

        # TOP
        if not self.eliminated[TOP] and TOP in self.players:
            py = fT + pt / 2
            px = self.paddles[TOP]
            pL, pR = px - PADDLE_LEN_H / 2, px + PADDLE_LEN_H / 2
            if b["y"] - r <= py + pt / 2 and b["vy"] < 0:
                if pL <= b["x"] <= pR:
                    b["vy"] = abs(b["vy"])
                    rel = (b["x"] - px) / (PADDLE_LEN_H / 2)
                    b["vx"] += rel * 0.004
                    b["y"] = py + pt / 2 + r + 0.001
                    b["bounce"] = True
            if b["y"] - r < fT:
                if self._in_goal(b["x"], GOAL_HALF_H, self.goal_offsets[TOP]):
                    if b["y"] - r < fT - GOAL_DEPTH:
                        scored = TOP
                else:
                    b["vy"] = abs(b["vy"])
                    b["y"] = fT + r
        else:
            if b["y"] - r < fT:
                b["vy"] = abs(b["vy"])
                b["y"] = fT + r

        # BOTTOM
        if not self.eliminated[BOTTOM] and BOTTOM in self.players:
            py = fB - pt / 2
            px = self.paddles[BOTTOM]
            pL, pR = px - PADDLE_LEN_H / 2, px + PADDLE_LEN_H / 2
            if b["y"] + r >= py - pt / 2 and b["vy"] > 0:
                if pL <= b["x"] <= pR:
                    b["vy"] = -abs(b["vy"])
                    rel = (b["x"] - px) / (PADDLE_LEN_H / 2)
                    b["vx"] += rel * 0.004
                    b["y"] = py - pt / 2 - r - 0.001
                    b["bounce"] = True
            if b["y"] + r > fB:
                if self._in_goal(b["x"], GOAL_HALF_H, self.goal_offsets[BOTTOM]):
                    if b["y"] + r > fB + GOAL_DEPTH:
                        scored = BOTTOM
                else:
                    b["vy"] = -abs(b["vy"])
                    b["y"] = fB - r
        else:
            if b["y"] + r > fB:
                b["vy"] = -abs(b["vy"])
                b["y"] = fB - r

        # LEFT
        if not self.eliminated[LEFT] and LEFT in self.players:
            px = fL + pt / 2
            py = self.paddles[LEFT]
            pT, pB = py - PADDLE_LEN_V / 2, py + PADDLE_LEN_V / 2
            if b["x"] - r <= px + pt / 2 and b["vx"] < 0:
                if pT <= b["y"] <= pB:
                    b["vx"] = abs(b["vx"])
                    rel = (b["y"] - py) / (PADDLE_LEN_V / 2)
                    b["vy"] += rel * 0.004
                    b["x"] = px + pt / 2 + r + 0.001
                    b["bounce"] = True
            if b["x"] - r < fL:
                if self._in_goal(b["y"], GOAL_HALF_V, self.goal_offsets[LEFT]):
                    if b["x"] - r < fL - GOAL_DEPTH:
                        scored = LEFT
                else:
                    b["vx"] = abs(b["vx"])
                    b["x"] = fL + r
        else:
            if b["x"] - r < fL:
                b["vx"] = abs(b["vx"])
                b["x"] = fL + r

        # RIGHT
        if not self.eliminated[RIGHT] and RIGHT in self.players:
            px = fR - pt / 2
            py = self.paddles[RIGHT]
            pT, pB = py - PADDLE_LEN_V / 2, py + PADDLE_LEN_V / 2
            if b["x"] + r >= px - pt / 2 and b["vx"] > 0:
                if pT <= b["y"] <= pB:
                    b["vx"] = -abs(b["vx"])
                    rel = (b["y"] - py) / (PADDLE_LEN_V / 2)
                    b["vy"] += rel * 0.004
                    b["x"] = px - pt / 2 - r - 0.001
                    b["bounce"] = True
            if b["x"] + r > fR:
                if self._in_goal(b["y"], GOAL_HALF_V, self.goal_offsets[RIGHT]):
                    if b["x"] + r > fR + GOAL_DEPTH:
                        scored = RIGHT
                else:
                    b["vx"] = -abs(b["vx"])
                    b["x"] = fR - r
        else:
            if b["x"] + r > fR:
                b["vx"] = -abs(b["vx"])
                b["x"] = fR - r

        # Clamp speed
        spd2 = math.sqrt(b["vx"]**2 + b["vy"]**2)
        if spd2 > speed_cap:
            b["vx"] = b["vx"] / spd2 * speed_cap
            b["vy"] = b["vy"] / spd2 * speed_cap

        return scored

    def tick(self):
        """Run one physics step. Returns (scored_side or None, list of collected powerup types)."""
        # Boost timers
        for ball in self.balls:
            if ball["boosted"]:
                ball["boost_timer"] -= TICK_DT
                if ball["boost_timer"] <= 0:
                    ball["boosted"] = False
                    spd = math.sqrt(ball["vx"]**2 + ball["vy"]**2)
                    if spd > BALL_SPEED_MAX:
                        ball["vx"] = ball["vx"] / spd * BALL_SPEED_MAX
                        ball["vy"] = ball["vy"] / spd * BALL_SPEED_MAX

        # Powerup spawn timer
        self.powerup_spawn_timer -= TICK_DT
        if self.powerup_spawn_timer <= 0:
            self._spawn_powerup()
            self.powerup_spawn_timer = random.uniform(POWERUP_SPAWN_MIN, POWERUP_SPAWN_MAX)

        # Moving goals
        if self.goal_moving_timer > 0:
            self.goal_moving_timer -= TICK_DT
            self.goal_move_time    += TICK_DT
            t = self.goal_move_time * MOVING_GOAL_SPEED
            self.goal_offsets = [
                MOVING_GOAL_AMP * math.sin(t),
                MOVING_GOAL_AMP * math.sin(t + math.pi),
                MOVING_GOAL_AMP * math.sin(t + math.pi / 2),
                MOVING_GOAL_AMP * math.sin(t + 3 * math.pi / 2),
            ]
            if self.goal_moving_timer <= 0:
                self.goal_offsets = [0.0, 0.0, 0.0, 0.0]

        scored = None
        collected = []

        for ball in self.balls:
            ball_scored = self._tick_ball(ball)
            if ball_scored is not None and scored is None:
                scored = ball_scored

        # Check powerup collisions
        for ball in self.balls:
            for pu in self.powerups[:]:
                if pu not in self.powerups:
                    continue
                dx = ball["x"] - pu["x"]
                dy = ball["y"] - pu["y"]
                if math.sqrt(dx * dx + dy * dy) < BALL_R + POWERUP_RADIUS:
                    collected.append(pu["type"])
                    self._apply_powerup(ball, pu)
                    if pu in self.powerups:
                        self.powerups.remove(pu)

        return scored, collected

    async def broadcast(self, msg: dict):
        data = json.dumps(msg)
        dead = []
        for slot, ws in list(self.players.items()):
            try:
                await ws.send(data)
            except Exception:
                dead.append(slot)
        for s in dead:
            self.players.pop(s, None)

    def state_snapshot(self, collected=None):
        balls_data = [
            {
                "id": b["id"], "x": b["x"], "y": b["y"],
                "vx": b["vx"], "vy": b["vy"],
                "boosted": b["boosted"], "bounce": b["bounce"],
            }
            for b in self.balls
        ]
        return {
            "type":          "state",
            "balls":         balls_data,
            "paddles":       self.paddles[:],
            "lives":         self.lives[:],
            "eliminated":    self.eliminated[:],
            "names":         [self.names.get(i, "") for i in range(4)],
            "game_state":    self.state,
            "powerups":      [p.copy() for p in self.powerups],
            "powerup_queue": self.powerup_queue[:],
            "collected":     collected or [],
            "goal_offsets":  self.goal_offsets[:],
            "goal_moving":   self.goal_moving_timer > 0,
        }


# ── Game loop ──────────────────────────────────────────────────────────────────
async def game_loop(room: Room):
    log.info(f"[{room.id}] game loop started")

    room.state = "countdown"
    for n in range(COUNTDOWN_SECS, 0, -1):
        await room.broadcast({"type": "countdown", "value": n})
        await asyncio.sleep(1.0)

    room.launch_ball()
    room.state = "playing"
    await room.broadcast({"type": "start"})

    last = time.monotonic()

    while True:
        now = time.monotonic()
        last = now

        async with room.lock:
            if room.num_players == 0:
                log.info(f"[{room.id}] all players left, stopping loop")
                room.state = "waiting"
                return

            if room.state == "playing":
                scored, collected = room.tick()

                if scored is not None and not room.eliminated[scored]:
                    room.lives[scored] -= 1
                    eliminated_now = room.lives[scored] <= 0
                    if eliminated_now:
                        room.eliminated[scored] = True

                    alive = room.alive_slots()
                    game_over = len(alive) <= 1

                    room.state = "goal"
                    await room.broadcast({
                        "type":           "goal",
                        "player":         scored,
                        "lives":          room.lives[:],
                        "eliminated":     room.eliminated[:],
                        "eliminated_now": eliminated_now,
                        "game_over":      game_over,
                        "winner":         alive[0] if game_over and alive else -1,
                        "names":          [room.names.get(i, "") for i in range(4)],
                    })

                    if game_over:
                        room.state = "gameover"
                        return

                    await asyncio.sleep(GOAL_PAUSE)
                    if room.num_players == 0:
                        return
                    room.state = "countdown"
                    for n in range(COUNTDOWN_SECS, 0, -1):
                        await room.broadcast({"type": "countdown", "value": n})
                        await asyncio.sleep(1.0)
                    room.launch_ball()
                    room.state = "playing"
                    await room.broadcast({"type": "start"})
                    last = time.monotonic()
                    continue

                await room.broadcast(room.state_snapshot(collected))

        sleep_time = TICK_DT - (time.monotonic() - now)
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)


# ── Room registry ──────────────────────────────────────────────────────────────
rooms: Dict[str, Room] = {}

def get_or_create_room(room_id: str) -> Room:
    if room_id not in rooms:
        rooms[room_id] = Room(room_id)
        log.info(f"Created room {room_id}")
    return rooms[room_id]


# ── WebSocket handler ──────────────────────────────────────────────────────────
async def handler(ws: WebSocketServerProtocol):
    room: Optional[Room] = None
    slot: Optional[int] = None

    try:
        raw = await asyncio.wait_for(ws.recv(), timeout=15)
        msg = json.loads(raw)

        if msg.get("type") != "join":
            await ws.send(json.dumps({"type": "error", "msg": "Expected join"}))
            return

        room_id = msg.get("room", "default")[:20]
        name    = str(msg.get("name", "Player"))[:16]

        room = get_or_create_room(room_id)

        async with room.lock:
            if room.state not in ("waiting", "gameover"):
                await ws.send(json.dumps({"type": "error", "msg": "Game already in progress"}))
                return

            if room.state == "gameover":
                room.lives      = [LIVES_START] * 4
                room.eliminated = [False] * 4
                room.paddles    = [0.5, 0.5, 0.5, 0.5]
                room.state      = "waiting"
                room.players    = {}
                room.names      = {}

            slot = room.next_slot()
            if slot is None:
                await ws.send(json.dumps({"type": "error", "msg": "Room full"}))
                return

            room.players[slot] = ws
            room.names[slot]   = name
            log.info(f"[{room_id}] Player '{name}' joined as slot {slot} ({SIDE_NAMES[slot]})")

            await ws.send(json.dumps({
                "type":    "joined",
                "slot":    slot,
                "side":    SIDE_NAMES[slot],
                "room":    room_id,
                "names":   [room.names.get(i, "") for i in range(4)],
                "players": list(room.players.keys()),
            }))

            await room.broadcast({
                "type":    "player_joined",
                "slot":    slot,
                "name":    name,
                "players": list(room.players.keys()),
                "names":   [room.names.get(i, "") for i in range(4)],
            })

        async for raw in ws:
            msg = json.loads(raw)
            t = msg.get("type")

            if t == "move":
                pos = msg.get("pos")
                if pos is not None and slot is not None:
                    async with room.lock:
                        room.paddles[slot] = max(0.0, min(1.0, float(pos)))

            elif t == "start_game":
                async with room.lock:
                    if room.state == "waiting" and room.num_players >= 2:
                        if not (room.task and not room.task.done()):
                            room.task = asyncio.create_task(game_loop(room))

    except (websockets.exceptions.ConnectionClosed, asyncio.TimeoutError):
        pass
    except Exception as e:
        log.exception(f"Handler error: {e}")
    finally:
        if room and slot is not None:
            async with room.lock:
                room.players.pop(slot, None)
                log.info(f"[{room.id}] Slot {slot} disconnected")
                await room.broadcast({
                    "type":    "player_left",
                    "slot":    slot,
                    "players": list(room.players.keys()),
                    "names":   [room.names.get(i, "") for i in range(4)],
                })
            if room.num_players == 0:
                rooms.pop(room.id, None)
                log.info(f"[{room.id}] Room deleted (empty)")


async def main():
    log.info("QUADRA server starting on 0.0.0.0:8765")
    async with websockets.serve(handler, "0.0.0.0", 8765, ping_interval=20, ping_timeout=30):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
