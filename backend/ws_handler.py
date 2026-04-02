"""
ws_handler — WebSocket connection handler.

One coroutine per connected client. Responsible only for:
  - parsing the initial "join" handshake
  - routing incoming messages to room actions
  - cleaning up on disconnect
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

import websockets
from websockets.server import WebSocketServerProtocol

from game_loop import game_loop
from models import SIDE_NAMES
from room import Room
from room_registry import registry

log = logging.getLogger("quadra")


async def handler(ws: WebSocketServerProtocol) -> None:
    room: Optional[Room] = None
    slot: Optional[int]  = None

    try:
        room, slot = await _join(ws)
        if room is None:
            return
        await _message_loop(ws, room, slot)

    except (websockets.exceptions.ConnectionClosed, asyncio.TimeoutError):
        pass
    except Exception as e:
        log.exception(f"Handler error: {e}")
    finally:
        await _disconnect(room, slot)


# ── Phases ────────────────────────────────────────────────────────────────────

async def _join(ws: WebSocketServerProtocol) -> tuple[Optional[Room], Optional[int]]:
    """Receive and process the initial join message. Returns (room, slot) or (None, None)."""
    raw = await asyncio.wait_for(ws.recv(), timeout=15)
    msg = json.loads(raw)

    if msg.get("type") != "join":
        await ws.send(json.dumps({"type": "error", "msg": "Expected join"}))
        return None, None

    room_id = msg.get("room", "default")[:20]
    name    = str(msg.get("name", "Player"))[:16]
    room    = registry.get_or_create(room_id)

    async with room.lock:
        if room.state not in ("waiting", "gameover"):
            await ws.send(json.dumps({"type": "error", "msg": "Game already in progress"}))
            return None, None

        if room.state == "gameover":
            room.reset_for_new_game()

        slot = room.next_slot()
        if slot is None:
            await ws.send(json.dumps({"type": "error", "msg": "Room full"}))
            return None, None

        room.players[slot] = ws
        room.names[slot]   = name
        log.info(f"[{room_id}] '{name}' joined slot {slot} ({SIDE_NAMES[slot]})")

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

    return room, slot


async def _message_loop(ws: WebSocketServerProtocol, room: Room, slot: int) -> None:
    async for raw in ws:
        msg = json.loads(raw)
        t   = msg.get("type")

        if t == "move":
            pos = msg.get("pos")
            if pos is not None:
                async with room.lock:
                    room.paddles[slot] = max(0.0, min(1.0, float(pos)))

        elif t == "start_game":
            async with room.lock:
                if room.state == "waiting" and room.num_players >= 2:
                    if not (room.task and not room.task.done()):
                        room.task = asyncio.create_task(game_loop(room))


async def _disconnect(room: Optional[Room], slot: Optional[int]) -> None:
    if room is None or slot is None:
        return
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
        registry.delete(room.id)
