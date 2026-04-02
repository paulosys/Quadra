"""
game_loop — async coroutine that drives one Room through its full lifecycle:
  countdown → playing → goal pause → countdown → … → gameover
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from config import COUNTDOWN_SECS, GOAL_PAUSE, LIVES_START, TICK_DT

if TYPE_CHECKING:
    from room import Room

log = logging.getLogger("quadra")


async def game_loop(room: Room) -> None:
    log.info(f"[{room.id}] game loop started")

    await _run_countdown(room)

    room.launch_ball()
    room.state = "playing"
    await room.broadcast({"type": "start"})

    while True:
        tick_start = time.monotonic()

        async with room.lock:
            if room.num_players == 0:
                log.info(f"[{room.id}] all players left, stopping loop")
                room.state = "waiting"
                return

            if room.state == "playing":
                scored, scorer, collected = room.tick()

                if scored is not None and not room.eliminated[scored]:
                    done = await _handle_goal(room, scored, scorer)
                    if done:
                        return
                    continue  # timing reset handled inside _handle_goal

                await room.broadcast(room.state_snapshot(collected))

        elapsed = time.monotonic() - tick_start
        sleep   = TICK_DT - elapsed
        if sleep > 0:
            await asyncio.sleep(sleep)


async def _run_countdown(room: Room) -> None:
    room.state = "countdown"
    for n in range(COUNTDOWN_SECS, 0, -1):
        await room.broadcast({"type": "countdown", "value": n})
        await asyncio.sleep(1.0)


async def _handle_goal(room: Room, scored: int, scorer: int | None) -> bool:
    """
    Process a goal event. Returns True if the game ended (gameover).
    Must be called while holding room.lock.
    scorer is the player slot who last touched the ball (may be None).
    """
    room.lives[scored] -= 1
    eliminated_now = room.lives[scored] <= 0
    if eliminated_now:
        room.eliminated[scored] = True

    # Award goal to scorer and check for life bonus (every 3 goals, max LIVES_START)
    life_gained = False
    if scorer is not None and scorer in room.players:
        room.goals_scored[scorer] += 1
        if room.goals_scored[scorer] % 3 == 0 and room.lives[scorer] < LIVES_START:
            room.lives[scorer] += 1
            life_gained = True

    alive     = room.alive_slots()
    game_over = len(alive) <= 1

    room.state = "goal"
    await room.broadcast({
        "type":           "goal",
        "player":         scored,
        "scorer":         scorer,
        "lives":          room.lives[:],
        "eliminated":     room.eliminated[:],
        "eliminated_now": eliminated_now,
        "game_over":      game_over,
        "winner":         alive[0] if game_over and alive else -1,
        "names":          [room.names.get(i, "") for i in range(4)],
        "goals_scored":   room.goals_scored[:],
        "life_gained":    life_gained,
    })

    if game_over:
        room.state = "gameover"
        return True

    await asyncio.sleep(GOAL_PAUSE)
    if room.num_players == 0:
        return True

    await _run_countdown(room)
    room.launch_ball()
    room.state = "playing"
    await room.broadcast({"type": "start"})
    return False
